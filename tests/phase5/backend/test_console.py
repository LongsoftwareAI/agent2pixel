import time
import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c


def context(c):
    workspaces = c.get("/api/workspaces").json()
    ws = workspaces[0]["id"]
    return (
        {"workspace_id": ws},
        c.get("/api/bootstrap", params={"workspace_id": ws}).json(),
        workspaces[1]["id"],
    )


def wait(c, id):
    for _ in range(300):
        value = c.get("/api/runs/" + id).json()
        if value["state"] not in ("queued", "running"):
            return value
        time.sleep(0.01)
    pytest.fail("run did not finish")


def chat(c, p, b, agent=True):
    value = c.post(
        "/api/console/conversations",
        json={
            **p,
            "agent_id": b["agents"][0]["id"] if agent else None,
            "title": "Research team",
        },
    ).json()
    return value["id"]


def test_real_chat_idempotency_reconciliation_and_work_acceptance(client):
    p, b, other = context(client)
    id = chat(client, p, b)
    path = "/api/console/conversations/" + id
    payload = {
        "content": "Summarize supplied research and identify missing evidence",
        "client_request_id": "research-1",
    }
    result = client.post(path + "/messages", params=p, json=payload)
    assert result.status_code == 200, result.text
    result = result.json()
    run = wait(client, result["run_id"])
    assert run["state"] == "completed"
    duplicate = client.post(path + "/messages", params=p, json=payload)
    assert duplicate.json()["run_id"] == run["id"]
    assert len(client.get("/api/runs", params=p).json()) == 1
    assert (
        client.post(
            path + "/messages", params=p, json={**payload, "content": "changed"}
        ).status_code
        == 409
    )
    messages = client.get(path, params=p).json()["messages"]
    assert len(messages) == 2
    assert messages[1]["content"] == run["output"]
    assert messages[1]["provenance"] == "runtime"
    assert client.get(path, params={"workspace_id": other}).status_code == 404
    inbox = client.get("/api/console/inbox", params=p).json()
    assert any(
        i["work_item_id"] == result["work_item_id"] and i["kind"] == "work_acceptance"
        for i in inbox
    )
    overview = client.get("/api/console/overview", params=p).json()
    assert overview["work"]["completed"] == 0
    assert overview["work"]["pending_review"] == 1
    assert (
        client.get("/api/console/sessions", params=p).json()[0]["conversation_id"] == id
    )
    assert (
        client.post(
            path + "/messages", params={"workspace_id": other}, json=payload
        ).status_code
        == 404
    )


def test_room_explicit_workflow_and_attachment_isolation(client):
    p, b, other = context(client)
    id = chat(client, p, b, False)
    path = "/api/console/conversations/" + id + "/messages"
    payload = {"content": "Analyze this evidence", "client_request_id": "a"}
    assert client.post(path, params=p, json=payload).status_code == 422
    attachment = client.post(
        "/api/console/attachments",
        json={
            **p,
            "name": "evidence.md",
            "media_type": "text/markdown",
            "content": "Verified source excerpt",
        },
    ).json()
    assert attachment["size"] > 0
    assert (
        client.post(path, params={"workspace_id": other}, json=payload).status_code
        == 404
    )
    foreign = client.post(
        "/api/console/attachments",
        json={
            "workspace_id": other,
            "name": "private.txt",
            "media_type": "text/plain",
            "content": "private",
        },
    ).json()
    assert (
        client.post(
            path,
            params=p,
            json={
                **payload,
                "workflow_id": b["workflows"][0]["id"],
                "attachment_ids": [foreign["id"]],
            },
        ).status_code
        == 404
    )
    result = client.post(
        path,
        params=p,
        json={
            **payload,
            "workflow_id": b["workflows"][0]["id"],
            "attachment_ids": [attachment["id"]],
        },
    ).json()
    run = wait(client, result["run_id"])
    assert (
        "UNTRUSTED attachment" in run["input"]
        and attachment["source_id"] in run["input"]
    )
    assert (
        client.post(
            "/api/console/attachments",
            json={
                **p,
                "name": "../bad.txt",
                "media_type": "text/plain",
                "content": "bad",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/console/attachments",
            json={
                **p,
                "name": "x.png",
                "media_type": "image/png",
                "content": "not image",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/console/attachments",
            json={
                **p,
                "name": "x.txt",
                "media_type": "text/plain",
                "content": "\x00binary",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, params=p, json={**payload, "content": "x" * 18001}
        ).status_code
        == 422
    )


def test_soul_revision_and_snapshot_immutability(client):
    p, b, other = context(client)
    aid = b["agents"][0]["id"]
    path = "/api/console/agents/" + aid + "/soul"
    before = client.get(path, params=p).json()
    id = chat(client, p, b)
    result = client.post(
        "/api/console/conversations/" + id + "/messages",
        params=p,
        json={"content": "Draft an outline", "client_request_id": "outline"},
    ).json()
    snapshot = client.get("/api/runs/" + result["run_id"]).json()["agent_specs"][aid][
        "system_prompt"
    ]
    updated = client.patch(
        path,
        params=p,
        json={"content": "Revised safe role", "revision": before["revision"]},
    )
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert (
        client.patch(
            path, params=p, json={"content": "Lost update", "revision": 1}
        ).status_code
        == 409
    )
    assert (
        client.get("/api/runs/" + result["run_id"]).json()["agent_specs"][aid][
            "system_prompt"
        ]
        == snapshot
    )
    assert client.get(path, params={"workspace_id": other}).status_code == 404
    assert (
        client.patch(path, params=p, json={"content": "", "revision": 2}).status_code
        == 422
    )
    wait(client, result["run_id"])


def test_reviewed_skill_install_remove_conflicts_and_atomic_bindings(client):
    p, b, other = context(client)
    aid = b["agents"][0]["id"]
    path = "/api/console/agents/" + aid + "/skills/"
    catalog = client.get("/api/console/skills", params=p).json()
    manifest = catalog["packages"][0]
    assert manifest["license"] and len(manifest["sha256"]) == 64
    assert manifest["tool_grants"] == []
    grants = client.get("/api/agents/" + aid).json()["tool_grants"]
    preview = client.post(
        path + "preview",
        params=p,
        json={"package_id": manifest["id"], "operation": "install"},
    ).json()
    assert "after" in preview["diff"]
    assert (
        client.post(
            path + "apply",
            params={"workspace_id": other},
            json={"approval_id": preview["approval_id"]},
        ).status_code
        == 404
    )
    applied = client.post(
        path + "apply", params=p, json={"approval_id": preview["approval_id"]}
    )
    assert applied.status_code == 200
    assert (
        client.post(
            path + "apply", params=p, json={"approval_id": preview["approval_id"]}
        ).json()
        == applied.json()
    )
    assert client.get("/api/agents/" + aid).json()["tool_grants"] == grants
    assert (
        client.post(
            path + "preview",
            params=p,
            json={"package_id": manifest["id"], "operation": "install"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "preview",
            params=p,
            json={"package_id": "https://malicious/install.sh", "operation": "install"},
        ).status_code
        == 422
    )
    remove = client.post(
        path + "preview",
        params=p,
        json={"package_id": manifest["id"], "operation": "remove"},
    ).json()
    assert (
        client.post(
            path + "apply", params=p, json={"approval_id": remove["approval_id"]}
        ).status_code
        == 200
    )
    assert not any(
        x["package_id"] == manifest.get("registry_id", manifest["id"])
        and x["agent_id"] == aid
        for x in client.get("/api/console/skills", params=p).json()["bindings"]
    )


def test_preferences_health_usage_topology_logs_and_errors(client, monkeypatch):
    p, b, other = context(client)
    assert client.get("/api/console/preferences", params=p).json()["theme"] == "dark"
    result = client.patch(
        "/api/console/preferences",
        params=p,
        json={"theme": "light", "font": "large", "refresh": "off", "revision": 1},
    )
    assert result.json()["revision"] == 2
    assert (
        client.patch(
            "/api/console/preferences", params=p, json={"theme": "pink", "revision": 2}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/console/preferences",
            params=p,
            json={"office_enabled": "true", "revision": 2},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/console/preferences", params=p, json={"revision": 1}
        ).status_code
        == 409
    )
    assert (
        client.get("/api/console/preferences", params={"workspace_id": other}).json()[
            "theme"
        ]
        == "dark"
    )
    monkeypatch.setenv("CONSOLE_TEST_KEY", "never-visible-provider-value")
    aid = b["agents"][0]["id"]
    client.patch(
        "/api/agents/" + aid,
        json={
            "brain": {
                "provider": "openai",
                "model": "gpt-test",
                "secret_ref": "CONSOLE_TEST_KEY",
            }
        },
    )
    response = client.get("/api/console/health", params=p)
    assert "never-visible-provider-value" not in response.text
    assert any(i["state"] == "unknown" for i in response.json()["items"])
    assert (
        client.get("/api/console/capabilities", params=p).json()["stt"]["state"]
        == "unconfigured"
    )
    assert client.get("/api/console/schedules", params=p).json()["items"] == []
    usage = client.get("/api/console/usage", params=p).json()
    assert (
        usage["totals"]["actual_cost"] is None
        and usage["totals"]["input_tokens"] is None
    )
    assert usage["totals"]["requests"] == 0
    assert (
        client.get("/api/console/usage", params={**p, "period": "bad"}).status_code
        == 422
    )
    topology = client.get("/api/console/topology", params=p).json()
    ids = {n["id"] for n in topology["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in topology["edges"])
    client.app.state.store.event(
        p["workspace_id"],
        "diagnostic.error",
        {"secret": "never-log-this", "prompt": "private content"},
    )
    response = client.get("/api/console/logs", params={**p, "limit": 1})
    assert (
        "never-log-this" not in response.text and "private content" not in response.text
    )
    assert (
        client.get("/api/console/logs", params={**p, "before": "invalid"}).status_code
        == 422
    )
    assert (
        client.get("/api/console/logs", params={**p, "limit": 201}).status_code == 422
    )
    audit = client.get("/api/console/logs", params={**p, "kind": "audit"}).json()[
        "items"
    ]
    assert any(i["action"] == "preferences.updated" for i in audit)
    for endpoint in (
        "overview",
        "health",
        "usage",
        "topology",
        "preferences",
        "capabilities",
        "schedules",
        "sessions",
        "inbox",
        "skills",
        "conversations",
        "logs",
    ):
        assert (
            client.get(
                "/api/console/" + endpoint, params={"workspace_id": "not-found"}
            ).status_code
            == 404
        ), endpoint


def test_restart_migration_and_durable_chat(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        p, b, other = context(c)
        id = chat(c, p, b)
        payload = {"content": "Prepare a project brief", "client_request_id": "durable"}
        result = c.post(
            "/api/console/conversations/" + id + "/messages", params=p, json=payload
        ).json()
        wait(c, result["run_id"])
        c.patch(
            "/api/console/preferences",
            params=p,
            json={"accent": "black", "revision": 1},
        )
        old_agent_id = b["agents"][0]["id"]
    with TestClient(create_app(tmp_path)) as c:
        assert c.get("/api/agents/" + old_agent_id).status_code == 200
        detail = c.get("/api/console/conversations/" + id, params=p).json()
        assert len(detail["messages"]) == 2
        assert (
            c.post(
                "/api/console/conversations/" + id + "/messages", params=p, json=payload
            ).json()["run_id"]
            == result["run_id"]
        )
        assert c.get("/api/console/preferences", params=p).json()["accent"] == "black"
        assert (
            c.app.state.store.db.execute(
                "select max(version) from schema_migrations"
            ).fetchone()[0]
            == 3
        )
    assert (tmp_path / "pre-schema-v3.sqlite3").is_file()


def test_legacy_agent_edits_preserve_soul_revision(client):
    p, b, _ = context(client)
    aid = b["agents"][0]["id"]
    path = "/api/console/agents/" + aid + "/soul"
    assert (
        client.patch(
            path, params=p, json={"content": "First revision", "revision": 1}
        ).status_code
        == 200
    )
    assert (
        client.patch("/api/agents/" + aid, json={"name": "Renamed"}).status_code == 200
    )
    assert client.get(path, params=p).json()["revision"] == 2
    assert (
        client.patch(
            "/api/agents/" + aid, json={"system_prompt": "Legacy studio edit"}
        ).status_code
        == 200
    )
    assert client.get(path, params=p).json()["revision"] == 3
    assert (
        client.patch(
            path, params=p, json={"content": "Overwrite stale", "revision": 2}
        ).status_code
        == 409
    )


def test_failed_chat_never_synthesizes_success_and_retries_dedupe(client, monkeypatch):
    import services.worker.runtime as runtime

    async def unavailable(*args, **kwargs):
        raise ValueError("Fixture provider unavailable")

    monkeypatch.setattr(runtime, "run_brain", unavailable)
    p, b, _ = context(client)
    id = chat(client, p, b)
    path = "/api/console/conversations/" + id
    payload = {"content": "Prepare a sourced brief", "client_request_id": "failure"}
    result = client.post(path + "/messages", params=p, json=payload).json()
    run = wait(client, result["run_id"])
    assert run["state"] == "failed"
    detail = client.get(path, params=p).json()
    assert detail["messages"][-1]["state"] == "failed"
    assert detail["messages"][-1]["role"] == "system"
    assert "unavailable" in detail["messages"][-1]["content"]
    assert (
        client.post(path + "/messages", params=p, json=payload).json()["run_id"]
        == run["id"]
    )
    assert len(client.get("/api/runs", params=p).json()) == 1
    assert (
        client.get("/api/console/overview", params=p).json()["usage"]["requests"] == 0
    )


def test_chat_cancel_and_restart_reconcile_durable_run(client, monkeypatch):
    import asyncio
    import services.worker.runtime as runtime

    async def slow(*args, **kwargs):
        await asyncio.sleep(30)
        return "unused", 1

    monkeypatch.setattr(runtime, "run_brain", slow)
    p, b, _ = context(client)
    id = chat(client, p, b)
    path = "/api/console/conversations/" + id
    result = client.post(
        path + "/messages",
        params=p,
        json={"content": "Wait for cancellation", "client_request_id": "cancel"},
    ).json()
    response = client.post("/api/runs/" + result["run_id"] + "/cancel")
    assert response.status_code == 200
    detail = client.get(path, params=p).json()
    assert detail["messages"][-1]["state"] == "cancelled"
    assert detail["messages"][-1]["provenance"] == "runtime"
    assert client.get("/api/console/overview", params=p).json()["runs"]["active"] == 0


def test_skill_stale_preview_cannot_override_new_bindings(client):
    p, b, _ = context(client)
    aid = b["agents"][0]["id"]
    path = "/api/console/agents/" + aid + "/skills/"
    preview = client.post(
        path + "preview",
        params=p,
        json={"package_id": "console-evidence", "operation": "install"},
    ).json()
    result = client.patch(
        "/api/agents/" + aid,
        json={"skill_bindings": [{"id": "code-report", "version": 1}]},
    )
    assert result.status_code == 200
    assert (
        client.post(
            path + "apply", params=p, json={"approval_id": preview["approval_id"]}
        ).status_code
        == 409
    )
    assert client.get("/api/agents/" + aid).json()["skill_bindings"] == [
        {"id": "code-report", "version": 1}
    ]


def test_reviewed_skill_update_and_rollback_versions(client):
    p, b, _ = context(client)
    aid = b["agents"][0]["id"]
    path = "/api/console/agents/" + aid + "/skills/"
    approvals = []
    for package_id, operation, version in [
        ("console-evidence-v1", "install", 1),
        ("console-evidence", "update", 2),
        ("console-evidence-v1", "update", 1),
    ]:
        preview = client.post(
            path + "preview",
            params=p,
            json={"package_id": package_id, "operation": operation},
        )
        assert preview.status_code == 200, preview.text
        approval_id = preview.json()["approval_id"]
        approvals.append(approval_id)
        applied = client.post(
            path + "apply", params=p, json={"approval_id": approval_id}
        )
        assert applied.status_code == 200, applied.text
        assert {"id": "console-evidence", "version": version} in applied.json()[
            "bindings"
        ]
        assert (
            client.app.state.store.get(
                "skill_version", "skill:console-evidence:" + str(version)
            )["version"]
            == version
        )
    assert (
        client.post(
            path + "apply", params=p, json={"approval_id": approvals[1]}
        ).status_code
        == 409
    )
    assert len(client.app.state.store.list("skill_activation", p["workspace_id"])) == 3


def test_usage_retains_estimated_provider_and_unknown_provenance(client):
    p, _, _ = context(client)
    store = client.app.state.store
    store.event(p["workspace_id"], "model.completed", {"tokens": 25, "token_accounting": "estimated"})
    usage = client.get("/api/console/usage", params=p).json()
    assert usage["accounting"] == "estimated"
    for row in [usage["totals"], *usage["daily"], *usage["by_agent"], *usage["by_model"]]:
        assert row["token_accounting"] == "estimated"
        assert row["accounting_counts"] == {"estimated": 1, "provider": 0, "unknown": 0}
        assert row["tokens_by_accounting"]["estimated"] == 25
        assert row["actual_cost"] is None and row["estimated_cost"] is None
    store.event(p["workspace_id"], "model.completed", {"tokens": 75, "token_accounting": "provider"})
    # Legacy usage and invalid provenance must never acquire provider certainty.
    store.event(p["workspace_id"], "model.completed", {"tokens": 10})
    store.event(p["workspace_id"], "model.completed", {"tokens": -3, "token_accounting": "provider"})
    usage = client.get("/api/console/usage", params=p).json()
    assert usage["accounting"] == "mixed"
    for row in [usage["totals"], *usage["daily"], *usage["by_agent"], *usage["by_model"]]:
        assert row["token_accounting"] == "mixed"
        assert row["total_tokens"] == 110
        assert row["accounting_counts"] == {"estimated": 1, "provider": 1, "unknown": 2}
        assert row["tokens_by_accounting"] == {"estimated": 25, "provider": 75, "unknown": 10}
        assert row["actual_cost"] is None and row["estimated_cost"] is None
    overview = client.get("/api/console/overview", params=p).json()
    assert overview["usage"] == usage["totals"]
    budget = client.get("/api/console/budget", params=p).json()
    assert budget["token_accounting"] == "mixed"
    assert budget["accounting_counts"] == usage["totals"]["accounting_counts"]
    assert budget["tokens_by_accounting"] == usage["totals"]["tokens_by_accounting"]
    assert budget["actual_cost"] is None
    alert = client.patch("/api/console/budget", params=p, json={"revision": 1, "monthly_token_threshold": 100}).json()
    assert client.get("/api/console/budget", params=p).json()["alerts"][0]["token_accounting"] == "mixed"
    assert alert["policy"]["revision"] == 2
