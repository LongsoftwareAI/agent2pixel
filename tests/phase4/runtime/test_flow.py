"""Actual LangGraph checkpoints and durable tool/gate API with deterministic model."""

import time
from fastapi.testclient import TestClient
from services.api.main import create_app


def wait(client, rid):
    for _ in range(500):
        value = client.get("/api/runs/" + rid).json()
        if value["state"] in ("completed", "failed", "waiting_approval", "cancelled"):
            return value
        time.sleep(0.01)
    raise AssertionError("Run did not settle")


def setup(client, review=True):
    ws = client.get("/api/workspaces").json()[0]
    agent = client.get("/api/agents", params={"workspace_id": ws["id"]}).json()[0]
    assert (
        client.patch(
            "/api/agents/" + agent["id"],
            json={"tool_grants": [{"id": "documents.list", "allow": True}]},
        ).status_code
        == 200
    )
    nodes = [
        {"id": "start", "type": "start"},
        {
            "id": "tool",
            "type": "tool",
            "agent_id": agent["id"],
            "tool": {"id": "documents.list", "payload": {}},
        },
        {"id": "writer", "type": "agent", "agent_id": agent["id"]},
    ]
    if review:
        nodes.append(
            {
                "id": "review",
                "type": "review",
                "rework_target": "writer",
                "max_revisions": 1,
                "instructions": "Check evidence",
            }
        )
    nodes.append({"id": "end", "type": "end"})
    graph = {
        "nodes": nodes,
        "edges": [
            {"source": a["id"], "target": b["id"]} for a, b in zip(nodes, nodes[1:])
        ],
    }
    response = client.post(
        "/api/workflows",
        json={"workspace_id": ws["id"], "name": "Real tool review", "graph": graph},
    )
    assert response.status_code == 200, response.text
    return response.json(), agent, ws


def launch(client, wf):
    response = client.post(
        "/api/workflows/" + wf["id"] + "/runs",
        json={"input": "Prepare evidence report"},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def gate(client, rid):
    return [
        g
        for g in client.get("/api/runs/" + rid + "/gates").json()
        if g["status"] == "pending"
    ][0]


def test_read_tool_rework_bound_and_exact_once(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        wf, agent, ws = setup(client)
        rid = launch(client, wf)
        first = wait(client, rid)
        assert first["state"] == "waiting_approval", first
        assert len(first["tasks"]) == 1
        g = gate(client, rid)
        assert g["revision"] == 0 and "rework" in g["allowed_decisions"]
        assert (
            client.post(
                "/api/gates/" + g["id"] + "/decision",
                json={"decision": "rework", "comment": "Add uncertainty"},
            ).status_code
            == 200
        )
        second = wait(client, rid)
        assert second["state"] == "waiting_approval", second
        assert [t["node_id"] for t in second["tasks"]] == ["writer", "writer~review~r1"]
        g2 = gate(client, rid)
        assert g2["revision"] == 1 and "rework" not in g2["allowed_decisions"]
        assert (
            client.post(
                "/api/gates/" + g2["id"] + "/decision",
                json={"decision": "rework", "comment": ""},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/gates/" + g2["id"] + "/decision",
                json={"decision": "approved", "comment": "Accepted"},
            ).status_code
            == 200
        )
        assert wait(client, rid)["state"] == "completed"
        assert (
            client.post(
                "/api/gates/" + g2["id"] + "/decision",
                json={"decision": "approved", "comment": ""},
            ).status_code
            == 409
        )
        events = client.get(
            "/api/events", params={"workspace_id": ws["id"], "run_id": rid}
        ).json()
        assert (
            sum(
                e["event_type"] == "tool.completed"
                and e["payload"].get("node_id") == "tool"
                for e in events
            )
            == 1
        )
        models = [e for e in events if e["event_type"] == "model.completed"]
        assert len(models) == 2 and all(
            e["payload"]["duration_ms"] >= 0 for e in models
        )


def test_gate_survives_restart_and_denial_fails_closed(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        wf, _, _ = setup(client)
        rid = launch(client, wf)
        assert wait(client, rid)["state"] == "waiting_approval"
        gid = gate(client, rid)["id"]
    with TestClient(create_app(tmp_path)) as client:
        assert gate(client, rid)["id"] == gid
        assert (
            client.post(
                "/api/gates/" + gid + "/decision",
                json={"decision": "denied", "comment": "Insufficient sources"},
            ).status_code
            == 200
        )
        result = wait(client, rid)
        assert result["state"] == "failed" and "denied" in result["error"]


def test_tool_grant_denial_and_invalid_rework_graph(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        wf, agent, ws = setup(client)
        graph = wf["graph"]
        graph["nodes"][3]["rework_target"] = "end"
        response = client.post(
            "/api/workflows",
            json={"workspace_id": ws["id"], "name": "Bad ancestor", "graph": graph},
        )
        assert response.status_code == 400 and "ancestor" in response.text
        graph["nodes"][3]["rework_target"] = "writer"
        graph["nodes"][1]["tool"]["id"] = "artifacts.write_text"
        response = client.post(
            "/api/workflows",
            json={"workspace_id": ws["id"], "name": "Unsafe tool", "graph": graph},
        )
        assert response.status_code == 400 and "read-only" in response.text


def test_independent_readonly_tools_actually_overlap_and_join(tmp_path, monkeypatch):
    import asyncio
    import services.worker.runtime as module

    original = module.dispatch_tool
    entered = set()
    both_entered = None

    async def observe(store, run, agent, tool_id, payload):
        nonlocal both_entered
        if both_entered is None:
            both_entered = asyncio.Event()
        entered.add(tool_id)
        if len(entered) == 2:
            both_entered.set()
        await asyncio.wait_for(both_entered.wait(), 0.5)
        return await original(store, run, agent, tool_id, payload)

    monkeypatch.setattr(module, "dispatch_tool", observe)
    with TestClient(create_app(tmp_path)) as client:
        wf, agent, ws = setup(client, review=False)
        assert (
            client.patch(
                "/api/agents/" + agent["id"],
                json={
                    "tool_grants": [
                        {"id": t, "allow": True}
                        for t in ("documents.list", "memory.read")
                    ]
                },
            ).status_code
            == 200
        )
        graph = {
            "nodes": [
                {"id": "start", "type": "start"},
                {
                    "id": "a",
                    "type": "tool",
                    "agent_id": agent["id"],
                    "tool": {"id": "documents.list", "payload": {}},
                },
                {
                    "id": "b",
                    "type": "tool",
                    "agent_id": agent["id"],
                    "tool": {"id": "memory.read", "payload": {}},
                },
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"source": "start", "target": "a"},
                {"source": "start", "target": "b"},
                {"source": "a", "target": "end"},
                {"source": "b", "target": "end"},
            ],
        }
        response = client.post(
            "/api/workflows",
            json={"workspace_id": ws["id"], "name": "Parallel reads", "graph": graph},
        )
        assert response.status_code == 200, response.text
        rid = launch(client, response.json())
        result = wait(client, rid)
        assert result["state"] == "completed", result
        assert entered == {"documents.list", "memory.read"}
        assert result["output"].index("documents.list") < result["output"].index(
            "memory.read"
        )


def test_cancel_pending_gate_does_not_resume(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        wf, _, _ = setup(client)
        rid = launch(client, wf)
        assert wait(client, rid)["state"] == "waiting_approval"
        g = gate(client, rid)
        assert client.post("/api/runs/" + rid + "/cancel").status_code == 200
        assert (
            client.post(
                "/api/gates/" + g["id"] + "/decision",
                json={"decision": "approved", "comment": ""},
            ).status_code
            == 409
        )
        assert client.get("/api/runs/" + rid).json()["state"] == "cancelled"


def test_rework_comments_feed_model_and_exports_have_distinct_names(
    tmp_path, monkeypatch
):
    import services.worker.runtime as module

    calls = []

    async def brain(agent, text, budget, accounting):
        calls.append(text)
        return ("Revision " + str(len(calls)), 3)

    monkeypatch.setattr(module, "run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        wf, agent, ws = setup(client)
        assert (
            client.patch(
                "/api/agents/" + agent["id"],
                json={
                    "tool_grants": [
                        {"id": t, "allow": True}
                        for t in ("documents.list", "artifacts.write_text")
                    ]
                },
            ).status_code
            == 200
        )
        wf["graph"]["nodes"][2]["deliverable"] = {"filename": "report.md"}
        response = client.post(
            "/api/workflows",
            json={
                "workspace_id": ws["id"],
                "name": "Revised export",
                "graph": wf["graph"],
            },
        )
        assert response.status_code == 200, response.text
        rid = launch(client, response.json())
        for revision in range(2):
            assert wait(client, rid)["state"] == "waiting_approval"
            approval = [
                a
                for a in client.get("/api/runs/" + rid + "/approvals").json()
                if a["status"] == "pending"
            ][0]
            assert approval["payload"]["filename"] == (
                "report.md" if revision == 0 else "report-review-r1.md"
            )
            assert (
                client.post(
                    "/api/approvals/" + approval["id"] + "/decision",
                    json={"decision": "approved"},
                ).status_code
                == 200
            )
            assert wait(client, rid)["state"] == "waiting_approval"
            g = gate(client, rid)
            assert (
                client.post(
                    "/api/gates/" + g["id"] + "/decision",
                    json={
                        "decision": "rework" if revision == 0 else "approved",
                        "comment": "Explain limitations",
                    },
                ).status_code
                == 200
            )
        result = wait(client, rid)
        assert result["state"] == "completed", result
        assert len(calls) == 2 and "Explain limitations" in calls[1]
        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["path"] != result["artifacts"][1]["path"]


def test_failed_tool_result_never_silently_reexecutes_on_resume(tmp_path, monkeypatch):
    import services.worker.runtime as module

    calls = []

    async def broken(*args):
        calls.append(1)
        raise ValueError("Source unavailable")

    monkeypatch.setattr(module, "dispatch_tool", broken)
    with TestClient(create_app(tmp_path)) as client:
        wf, _, _ = setup(client, review=False)
        rid = launch(client, wf)
        assert wait(client, rid)["state"] == "failed"
        assert client.post("/api/runs/" + rid + "/resume").status_code == 200
        result = wait(client, rid)
        assert result["state"] == "failed" and "reconcile" in result["error"]
        assert calls == [1]


def test_rework_respects_global_step_budget(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        wf, _, _ = setup(client)
        response = client.post(
            "/api/workflows/" + wf["id"] + "/runs",
            json={"input": "Report", "max_steps": 4},
        )
        assert response.status_code == 200, response.text
        rid = response.json()["id"]
        assert wait(client, rid)["state"] == "waiting_approval"
        g = gate(client, rid)
        assert (
            client.post(
                "/api/gates/" + g["id"] + "/decision",
                json={"decision": "rework", "comment": "Again"},
            ).status_code
            == 200
        )
        result = wait(client, rid)
        assert result["state"] == "failed" and "steps" in result["error"]
        assert len(result["tasks"]) == 1
