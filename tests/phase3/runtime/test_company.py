"""Deterministic providers, actual graph checkpoints, HTTP API and local exports."""

import hashlib
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app


def wait(
    client, run_id, states=("completed", "failed", "waiting_approval", "cancelled")
):
    for _ in range(500):
        run = client.get("/api/runs/" + run_id).json()
        if run["state"] in states:
            return run
        time.sleep(0.01)
    raise AssertionError("Run did not settle")


def fixture(client, filename="report.md", grant=True):
    ws = client.get("/api/workspaces").json()[0]
    agent = client.get("/api/agents", params={"workspace_id": ws["id"]}).json()[0]
    client.patch(
        "/api/agents/" + agent["id"],
        json={"tool_grants": [{"id": "artifacts.write_text", "allow": True}]}
        if grant
        else {"tool_grants": []},
    )
    nodes = [
        {"id": "start", "type": "start"},
        {
            "id": "analysis",
            "type": "agent",
            "agent_id": agent["id"],
            "instructions": "Analyze supplied operations data; identify risk",
            "deliverable": {"filename": filename},
        },
        {"id": "end", "type": "end"},
    ]
    response = client.post(
        "/api/workflows",
        json={
            "workspace_id": ws["id"],
            "name": "Operations",
            "graph": {
                "nodes": nodes,
                "edges": [
                    {"source": "start", "target": "analysis"},
                    {"source": "analysis", "target": "end"},
                ],
            },
        },
    )
    assert response.status_code == 200, response.text
    workflow = response.json()
    item = client.post(
        "/api/work-items",
        json={
            "workspace_id": ws["id"],
            "workflow_id": workflow["id"],
            "title": "Risk report",
            "description": "Use only provided operations data",
            "acceptance_criteria": ["State evidence and uncertainty"],
        },
    ).json()
    return ws, agent, workflow, item


def launch(client, item):
    response = client.post("/api/work-items/" + item["id"] + "/runs", json={})
    assert response.status_code == 200, response.text
    return response.json()


def pending(client, run):
    assert wait(client, run["id"])["state"] == "waiting_approval"
    return [
        a
        for a in client.get("/api/runs/" + run["id"] + "/approvals").json()
        if a["status"] == "pending"
    ][0]


def test_generated_output_approval_restart_exact_export_and_human_review(
    tmp_path, monkeypatch
):
    calls = []
    output = "# Operations report\nRisk: supplied data is incomplete.\n"

    async def brain(agent, text, budget, metadata):
        calls.append(text)
        return output, 7

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        ws, agent, workflow, item = fixture(client)
        run = launch(client, item)
        approval = pending(client, run)
        assert "Analyze supplied operations data" in calls[0]
        assert "State evidence and uncertainty" in calls[0]
        assert approval["payload"] == {"filename": "report.md", "content": output}
        assert approval["node_id"] == "analysis"
        assert wait(client, run["id"])["token_spent"] == 7
        assert not list(Path(ws["root_path"]).rglob("report.md"))
        assert (
            client.patch(
                "/api/work-items/" + item["id"], json={"title": "changed"}
            ).status_code
            == 409
        )
    with TestClient(create_app(tmp_path)) as client:
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 200
        )
        result = wait(client, run["id"], ("completed", "failed"))
        assert result["state"] == "completed", result
        assert len(calls) == 1 and result["token_spent"] == 7
        artifact = result["artifacts"][0]
        assert (Path(ws["root_path"]) / artifact["path"]).read_text() == output
        assert artifact["sha256"] == hashlib.sha256(output.encode()).hexdigest()
        assert artifact["node_id"] == "analysis" and artifact["run_id"] == run["id"]
        assert result["work_item_id"] == item["id"]
        value = client.get("/api/work-items/" + item["id"]).json()
        assert value["status"] == "review"
        assert client.app.state.store.get("work_item", item["id"]).get("status") is None
        reviewed = client.post(
            "/api/work-items/" + item["id"] + "/review",
            json={"decision": "accepted", "comment": "Checked evidence"},
        )
        assert reviewed.json()["status"] == "done"
        assert reviewed.json()["reviews"][0]["reviewer"] == "human"
        assert (
            client.post(
                "/api/work-items/" + item["id"] + "/review",
                json={"decision": "accepted", "comment": "again"},
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 409
        )


@pytest.mark.parametrize("decision", ["denied", "cancelled", "expired"])
def test_deliverable_denial_cancel_expiry_never_writes(tmp_path, monkeypatch, decision):
    async def brain(*args):
        return "generated honest report", 2

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        ws, _, _, item = fixture(client)
        run = launch(client, item)
        approval = pending(client, run)
        if decision == "cancelled":
            client.post("/api/runs/" + run["id"] + "/cancel")
        elif decision == "expired":
            approval["expires_at"] = "2000-01-01T00:00:00+00:00"
            client.app.state.store.put("approval", approval)
            assert (
                client.post(
                    "/api/approvals/" + approval["id"] + "/decision",
                    json={"decision": "approved"},
                ).status_code
                == 409
            )
            client.post("/api/runs/" + run["id"] + "/cancel")
        else:
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "denied"},
            )
        assert wait(client, run["id"], ("failed", "cancelled"))["state"] in (
            "failed",
            "cancelled",
        )
        assert not list(Path(ws["root_path"]).rglob("report.md"))


def test_missing_grant_and_path_rejected(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        ws, agent, workflow, item = fixture(client, grant=False)
        result = wait(client, launch(client, item)["id"])
        assert result["state"] == "failed" and "grant denied" in result["error"]
        assert not list(Path(ws["root_path"]).rglob("report.md"))
        for filename in (
            "../escape.md",
            "/tmp/escape.md",
            "script.py",
            "a/b.txt",
            "x" * 101 + ".md",
        ):
            graph = workflow["graph"]
            graph["nodes"][1]["deliverable"] = {"filename": filename}
            response = client.post(
                "/api/workflows",
                json={"workspace_id": ws["id"], "name": "invalid", "graph": graph},
            )
            assert response.status_code == 400, response.text


def test_scope_templates_review_changes_requested_and_brief_snapshot(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        ws, _, workflow, item = fixture(client)
        templates = client.get("/api/workflow-templates").json()
        assert {t["id"] for t in templates} == {
            "research-brief",
            "content-production",
            "operations-report",
            "coding-review",
        }
        assert all(t["steps"] and t["roles"] for t in templates)
        other = client.get("/api/workspaces").json()[1]
        assert (
            client.post(
                "/api/work-items",
                json={
                    "workspace_id": other["id"],
                    "workflow_id": workflow["id"],
                    "title": "cross",
                    "description": "denied",
                },
            ).status_code
            == 403
        )
        assert (
            client.patch(
                "/api/work-items/" + item["id"], json={"workflow_id": workflow["id"]}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/work-items/" + item["id"] + "/review",
                json={"decision": "accepted", "comment": "premature"},
            ).status_code
            == 409
        )
        run = launch(client, item)
        approval = pending(client, run)
        assert (
            client.post("/api/work-items/" + item["id"] + "/runs", json={}).status_code
            == 409
        )
        client.post(
            "/api/approvals/" + approval["id"] + "/decision",
            json={"decision": "approved"},
        )
        assert wait(client, run["id"], ("completed", "failed"))["state"] == "completed"
        assert (
            client.post(
                "/api/work-items/" + item["id"] + "/review",
                json={
                    "decision": "changes_requested",
                    "comment": "Need further evidence",
                },
            ).json()["status"]
            == "backlog"
        )
        client.patch("/api/work-items/" + item["id"], json={"description": "Revised"})
        assert (
            client.get("/api/runs/" + run["id"]).json()["brief_snapshot"]["description"]
            == "Use only provided operations data"
        )


def test_same_agent_distinct_nodes_objectives_exports_and_usage_once(
    tmp_path, monkeypatch
):
    calls = []

    async def brain(agent, text, budget, metadata):
        calls.append(text)
        return f"arbitrary business output {len(calls)}", 3

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        ws, agent, workflow, item = fixture(client)
        graph = workflow["graph"]
        graph["nodes"].insert(
            2,
            {
                "id": "review",
                "type": "agent",
                "agent_id": agent["id"],
                "instructions": "Review original analysis for unsupported claims",
                "deliverable": {"filename": "review.txt"},
            },
        )
        graph["edges"] = [
            {"source": "start", "target": "analysis"},
            {"source": "analysis", "target": "review"},
            {"source": "review", "target": "end"},
        ]
        # Existing workflow API stores immutable workflows; create a new editable graph.
        wf = client.post(
            "/api/workflows",
            json={"workspace_id": ws["id"], "name": "Two objectives", "graph": graph},
        ).json()
        run = client.post(
            "/api/workflows/" + wf["id"] + "/runs", json={"input": "business brief"}
        ).json()
        for _ in range(2):
            approval = pending(client, run)
            current = client.get("/api/runs/" + run["id"]).json()
            assert current["tasks"][-1]["output"] == approval["payload"]["content"]
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            )
        result = wait(client, run["id"], ("completed", "failed"))
        assert result["state"] == "completed", result
        assert len(calls) == 2 and result["token_spent"] == 6
        assert "Analyze supplied operations data" in calls[0]
        assert "Review original analysis" in calls[1]
        assert "arbitrary business output 1" in calls[1]
        assert "business brief" in calls[1]
        assert len(result["artifacts"]) == 2 and len(result["tasks"]) == 2


@pytest.mark.parametrize("attack", ["oversize", "symlink", "payload_tamper"])
def test_text_export_fail_closed(tmp_path, monkeypatch, attack):
    async def brain(*args):
        return ("x" * (128 * 1024 + 1) if attack == "oversize" else "report body"), 2

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        ws, _, _, item = fixture(client)
        run = launch(client, item)
        if attack == "oversize":
            # Validation must occur before presenting unexportable generated text for approval.
            result = wait(client, run["id"])
            if result["state"] == "waiting_approval":
                approval = pending(client, run)
                client.post(
                    "/api/approvals/" + approval["id"] + "/decision",
                    json={"decision": "approved"},
                )
        else:
            approval = pending(client, run)
            if attack == "payload_tamper":
                approval["payload"]["content"] = "changed preview"
                client.app.state.store.put("approval", approval)
            else:
                outside = tmp_path / "outside"
                outside.mkdir()
                (Path(ws["root_path"]) / "artifacts").symlink_to(
                    outside, target_is_directory=True
                )
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            )
        result = wait(client, run["id"], ("failed",))
        assert result["state"] == "failed" and not result["artifacts"]
        assert not list(tmp_path.rglob("report.md"))


def test_concurrent_review_serialized_and_edited_accepted_brief_requires_new_run(
    tmp_path,
):
    from concurrent.futures import ThreadPoolExecutor

    with TestClient(create_app(tmp_path)) as client:
        _, _, _, item = fixture(client)
        run = launch(client, item)
        approval = pending(client, run)
        client.post(
            "/api/approvals/" + approval["id"] + "/decision",
            json={"decision": "approved"},
        )
        assert wait(client, run["id"], ("completed", "failed"))["state"] == "completed"

        def review(_):
            return client.post(
                "/api/work-items/" + item["id"] + "/review",
                json={"decision": "accepted", "comment": "Verified"},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(review, range(2)))
        assert sorted(statuses) == [200, 409]
        response = client.patch(
            "/api/work-items/" + item["id"],
            json={"acceptance_criteria": ["New scope must rerun"]},
        )
        assert response.json()["status"] == "backlog"
        assert response.json()["brief_revision"] == 2
        assert len(response.json()["reviews"]) == 1
        assert (
            client.post(
                "/api/work-items/" + item["id"] + "/review",
                json={"decision": "accepted", "comment": "old run"},
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    "node_patch",
    [
        {"instructions": []},
        {"instructions": "x" * 8001},
        {"deliverable": {"filename": "report.md", "content": "injected"}},
        {"deliverable": {"filename": "with\u0000control.md"}},
        {"deliverable": {"filename": "unicode-é.md"}},
        {"deliverable": {"filename": ["not-string.md"]}},
    ],
)
def test_invalid_node_configuration_rejected(tmp_path, node_patch):
    with TestClient(create_app(tmp_path)) as client:
        ws, _, workflow, _ = fixture(client)
        workflow["graph"]["nodes"][1].update(node_patch)
        response = client.post(
            "/api/workflows",
            json={
                "workspace_id": ws["id"],
                "name": "invalid",
                "graph": workflow["graph"],
            },
        )
        assert response.status_code == 400, response.text


def test_every_node_receives_original_immutable_brief_without_echo_dependency(
    tmp_path, monkeypatch
):
    captured = []

    async def brain(agent, text, budget, metadata):
        captured.append(text)
        return "compact output; original brief deliberately omitted", 2

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        ws, agent, workflow, _ = fixture(client)
        graph = workflow["graph"]
        graph["nodes"][1].pop("deliverable")
        graph["nodes"].insert(
            2,
            {
                "id": "review",
                "type": "agent",
                "agent_id": agent["id"],
                "instructions": "Verify immutable acceptance criteria independently",
            },
        )
        graph["edges"] = [
            {"source": "start", "target": "analysis"},
            {"source": "analysis", "target": "review"},
            {"source": "review", "target": "end"},
        ]
        wf = client.post(
            "/api/workflows",
            json={"workspace_id": ws["id"], "name": "Brief alignment", "graph": graph},
        ).json()
        item = client.post(
            "/api/work-items",
            json={
                "workspace_id": ws["id"],
                "workflow_id": wf["id"],
                "title": "ORIGINAL_TITLE",
                "description": "ORIGINAL_DESCRIPTION",
                "acceptance_criteria": ["ORIGINAL_CRITERION"],
            },
        ).json()
        run = client.post(
            "/api/work-items/" + item["id"] + "/runs",
            json={"input": "explicit override objective"},
        ).json()
        assert wait(client, run["id"])["state"] == "completed"
        assert len(captured) == 2
        for text in captured:
            assert "ORIGINAL_TITLE" in text
            assert "ORIGINAL_DESCRIPTION" in text
            assert "ORIGINAL_CRITERION" in text
            assert "explicit override objective" in text
        assert "Verify immutable acceptance criteria independently" in captured[1]
        assert "compact output; original brief deliberately omitted" in captured[1]
