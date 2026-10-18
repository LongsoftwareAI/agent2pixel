"""Behavioral integration tests: actual SQLite checkpoints, files and pytest processes."""

import time
from pathlib import Path
from fastapi.testclient import TestClient
from services.api.main import create_app


def setup(client):
    ws = client.get("/api/workspaces").json()[0]
    return client.get("/api/bootstrap", params={"workspace_id": ws["id"]}).json()


def wait(client, id, states=("completed", "failed", "cancelled", "waiting_approval")):
    for _ in range(500):
        value = client.get("/api/runs/" + id).json()
        if value["state"] in states:
            return value
        time.sleep(0.01)
    raise AssertionError("Run did not reach expected state")


def start(client, b, **extra):
    response = client.post(
        "/api/workflows/" + b["workflows"][0]["id"] + "/runs",
        json={"input": "Implement and verify calculator", **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


def actions_for(agent):
    return [
        dict(
            agent_id=agent["id"],
            tool="artifacts.write_python",
            payload={"filename": "calculator.py", "template": "calculator-v1"},
        ),
        dict(
            agent_id=agent["id"],
            tool="artifacts.write_python",
            payload={
                "filename": "test_calculator.py",
                "template": "calculator-tests-v1",
            },
        ),
        dict(agent_id=agent["id"], tool="tests.run_pytest", payload={}),
    ]


def grant(client, agent):
    response = client.patch(
        "/api/agents/" + agent["id"],
        json={
            "tool_grants": [
                {"id": t, "allow": True, "approval_required": True}
                for t in ("artifacts.write_python", "tests.run_pytest")
            ]
        },
    )
    assert response.status_code == 200, response.text


def test_real_approved_artifact_and_pytest_reviewer(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer))
        approvals = []
        for _ in range(3):
            current = wait(client, run["id"])
            assert current["state"] == "waiting_approval", current
            pending = [
                a
                for a in client.get("/api/runs/" + run["id"] + "/approvals").json()
                if a["status"] == "pending"
            ]
            assert len(pending) == 1
            approval = pending[0]
            approvals.append(approval["id"])
            assert (
                client.post(
                    "/api/approvals/" + approval["id"] + "/decision",
                    json={"decision": "approved"},
                ).status_code
                == 200
            )
        result = wait(client, run["id"], ("completed", "failed"))
        assert result["state"] == "completed", result
        assert len(result["tasks"]) == 3
        assert len(result["artifacts"]) == 3
        assert result["artifacts"][-1]["exit_code"] == 0
        assert "2 passed" in result["artifacts"][-1]["report"]
        assert "2 passed" in result["tasks"][-1]["output"]
        root = Path(b["workspaces"][0]["root_path"])
        assert (
            root / result["artifacts"][0]["path"]
        ).read_text() == "def add(a, b):\n    return a + b\n"
        assert (tmp_path / "checkpoints.sqlite3").is_file()
        assert (
            client.post(
                "/api/approvals/" + approvals[0] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 409
        )
        events = client.get("/api/runs/" + run["id"] + "/events").json()
        assert len([e for e in events if e["event_type"] == "task.completed"]) == 3
        assert (
            len(
                [
                    e
                    for e in events
                    if e["event_type"] == "tool.completed"
                    and e["payload"]["tool"]
                    in ("artifacts.write_python", "tests.run_pytest")
                ]
            )
            == 3
        )


def test_denied_approval_no_write_and_restart_preserves_pause(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer)[:1])
        assert wait(client, run["id"])["state"] == "waiting_approval"
        approval = client.get("/api/runs/" + run["id"] + "/approvals").json()[0]
        original_ids = [a["id"] for a in b["agents"]]
    with TestClient(create_app(tmp_path)) as client:
        assert [a["id"] for a in setup(client)["agents"]] == original_ids
        assert (
            client.get("/api/runs/" + run["id"]).json()["state"] == "waiting_approval"
        )
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "denied"},
            ).status_code
            == 200
        )
        result = wait(client, run["id"], ("failed",))
        assert "Approval denied" in result["error"]
        assert not list(Path(b["workspaces"][0]["root_path"]).rglob("calculator.py"))


def test_skills_role_memory_real_context_and_version_pin(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        other = b["agents"][1]
        skill = client.post(
            "/api/skills",
            json={
                "name": "Spec",
                "instructions": "UNIQUE_SKILL_TEXT",
                "allowed_tools": [],
            },
        ).json()
        patch = {
            "skill_bindings": [{"id": skill["id"], "version": skill["version"]}],
            "role_config": {
                "id": "custom",
                "version": 1,
                "instructions": "UNIQUE_ROLE_TEXT",
                "responsibilities": ["design"],
            },
            "tool_grants": [{"id": "memory.read", "allow": True}],
            "memory_config": {"scope": "agent"},
        }
        assert client.patch("/api/agents/" + agent["id"], json=patch).status_code == 200
        for owner, content in ((agent, "OWN_MEMORY"), (other, "PRIVATE_OTHER")):
            assert (
                client.post(
                    "/api/memories",
                    json={
                        "workspace_id": agent["workspace_id"],
                        "agent_id": owner["id"],
                        "scope": "agent",
                        "content": content,
                    },
                ).status_code
                == 200
            )
        run = start(client, b)
        client.patch(
            "/api/skills/" + skill["id"], json={"instructions": "CHANGED_SKILL"}
        )
        result = wait(client, run["id"])
        assert result["state"] == "completed"
        assert (
            "OWN_MEMORY" in result["output"] and "PRIVATE_OTHER" not in result["output"]
        )
        assert (
            result["agent_specs"][agent["id"]]["resolved_skills"][0]["instructions"]
            == "UNIQUE_SKILL_TEXT"
        )
        assert client.patch("/api/agents/" + agent["id"], json=patch).status_code == 200
        events = client.get("/api/runs/" + run["id"] + "/events").json()
        assert any(e["event_type"] == "skill.activated" for e in events)
        assert any(
            e["event_type"] == "memory.read" and e["payload"]["scope"] == "agent"
            for e in events
        )


def test_permissions_expiry_tamper_and_unavailable_engine(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        run = start(client, b, actions=actions_for(developer)[:1])
        assert "Tool grant denied" in wait(client, run["id"])["error"]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer)[:1])
        assert wait(client, run["id"])["state"] == "waiting_approval"
        approval = client.get("/api/runs/" + run["id"] + "/approvals").json()[0]
        store = client.app.state.store
        approval["expires_at"] = "2000-01-01T00:00:00+00:00"
        store.put("approval", approval)
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 409
        )
        client.post("/api/runs/" + run["id"] + "/cancel")
        assert (
            client.patch(
                "/api/agents/" + developer["id"],
                json={"execution": {"engine": "missing"}},
            ).status_code
            == 422
        )
        response = client.post(
            "/api/workflows/" + b["workflows"][0]["id"] + "/runs",
            json={
                "input": "x",
                "actions": [
                    {"agent_id": developer["id"], "tool": "shell", "payload": {}}
                ],
            },
        )
        assert response.status_code == 422


def test_cancel_waiting_no_late_success(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer)[:1])
        assert wait(client, run["id"])["state"] == "waiting_approval"
        approval = client.get("/api/runs/" + run["id"] + "/approvals").json()[0]
        assert client.post("/api/runs/" + run["id"] + "/cancel").status_code == 200
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 409
        )
        time.sleep(0.1)
        assert client.get("/api/runs/" + run["id"]).json()["state"] == "cancelled"
        assert not list(Path(b["workspaces"][0]["root_path"]).rglob("calculator.py"))


def test_system_prompt_really_contains_role_and_skill(tmp_path, monkeypatch):
    captured = []

    async def brain(agent, text, budget, metadata):
        captured.append(agent["system_prompt"])
        metadata["token_accounting"] = "estimated"
        return "real-output", 1

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        role = {
            "id": "planner",
            "version": 1,
            "instructions": "ROLE_ACTUAL_INSTRUCTIONS",
            "responsibilities": ["ARCHITECTURE"],
        }
        assert (
            client.patch(
                "/api/agents/" + agent["id"],
                json={
                    "role_config": role,
                    "skill_bindings": [{"id": "code-report", "version": 1}],
                },
            ).status_code
            == 200
        )
        result = wait(client, start(client, b)["id"])
        assert result["state"] == "completed"
        assert "ROLE_ACTUAL_INSTRUCTIONS" in captured[0]
        assert "ARCHITECTURE" in captured[0]
        assert "never report unexecuted tests as passing" in captured[0]


def test_resume_failed_node_keeps_previous_output_and_budget(tmp_path, monkeypatch):
    calls = []

    async def brain(agent, text, budget, metadata):
        calls.append(agent["role"])
        metadata["token_accounting"] = "estimated"
        if agent["role"] == "Developer" and calls.count("Developer") == 1:
            raise ValueError("temporary failure")
        return agent["role"] + " output", 3

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        run = start(client, b, retry_limit=0)
        failed = wait(client, run["id"])
        assert failed["state"] == "failed"
        assert client.post("/api/runs/" + run["id"] + "/resume").status_code == 200
        result = wait(client, run["id"])
        assert result["state"] == "completed"
        assert calls == ["Planner", "Developer", "Developer", "Reviewer"]
        assert result["token_spent"] == 9
        assert len([t for t in result["tasks"] if t["node_id"] == "planner"]) == 1


def test_schema_failure_is_not_success_and_consumes_budget(tmp_path, monkeypatch):
    async def brain(agent, text, budget, metadata):
        metadata["token_accounting"] = "estimated"
        return '{"ok":"wrong-type"}', 5

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        role = dict(
            agent["role_config"],
            output_schema={
                "type": "object",
                "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}},
            },
        )
        assert (
            client.patch(
                "/api/agents/" + agent["id"], json={"role_config": role}
            ).status_code
            == 200
        )
        result = wait(client, start(client, b, retry_limit=1)["id"])
        assert result["state"] == "failed" and result["token_spent"] == 10
        assert "schema" in result["error"]


def test_invalid_rich_config_remote_schema_and_origin_rejected(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        for field, value in [
            ("role_config", {}),
            ("memory_config", {"scope": "other"}),
            ("tool_grants", [{}]),
            ("skill_bindings", [{}]),
            ("appearance", {}),
            (
                "role_config",
                dict(
                    agent["role_config"],
                    output_schema={
                        "type": "object",
                        "properties": {"x": {"$ref": "https://example.invalid/schema"}},
                    },
                ),
            ),
        ]:
            assert (
                client.patch(
                    "/api/agents/" + agent["id"], json={field: value}
                ).status_code
                == 422
            )
        assert (
            client.post(
                "/api/workspaces",
                json={"name": "CSRF"},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )


def test_shared_broker_refuses_grants_scope_override_and_unapproved_write(tmp_path):
    import asyncio
    from services.worker.tools import dispatch_tool

    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        client.patch(
            "/api/agents/" + agent["id"],
            json={
                "tool_grants": [
                    {"id": "memory.read", "allow": True},
                    {"id": "artifacts.write_python", "allow": True},
                ]
            },
        )
        run = start(client, b)
        wait(client, run["id"])
        store = client.app.state.store
        value = store.get("run", run["id"])
        value["state"] = "running"
        store.put("run", value)
        import pytest

        with pytest.raises(ValueError, match="scope"):
            asyncio.run(
                dispatch_tool(
                    store,
                    value,
                    agent,
                    "memory.read",
                    {"agent_id": b["agents"][1]["id"]},
                )
            )
        with pytest.raises(ValueError, match="approved"):
            asyncio.run(
                dispatch_tool(
                    store,
                    value,
                    agent,
                    "artifacts.write_python",
                    actions_for(agent)[0]["payload"],
                )
            )
        with pytest.raises(ValueError, match="grant"):
            asyncio.run(
                dispatch_tool(
                    store, value, agent, "documents.read", {"path": "README.md"}
                )
            )
        value["state"] = "completed"
        store.put("run", value)


def test_nested_adversarial_config_returns_422_not_500(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        agent = b["agents"][0]
        for patch in [
            {"skill_bindings": [{"id": {"malformed": True}, "version": 1}]},
            {"skill_bindings": [{"id": [], "version": 1}]},
            {
                "tool_grants": [
                    {"id": "memory.read", "allow": True, "approval_required": "false"}
                ]
            },
            {"execution": {"engine": "langchain", "version": True}},
            {"execution": {"engine": "langchain", "version": {}}},
            {
                "role_config": dict(
                    agent["role_config"],
                    output_schema={
                        "type": "object",
                        "$dynamicRef": "https://example.invalid/schema",
                    },
                )
            },
        ]:
            response = client.patch("/api/agents/" + agent["id"], json=patch)
            assert response.status_code == 422, (patch, response.text)
        assert client.get("/api/agents/" + agent["id"]).json() == agent


def test_malformed_local_origin_cannot_mutate(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        for origin in [
            "http://localhost:invalid",
            "http://localhost:99999",
            "http://localhost/path",
            "http://localhost?query=x",
            "http://localhost#fragment",
            "http://user@localhost",
        ]:
            response = client.post(
                "/api/workspaces", json={"name": "denied"}, headers={"Origin": origin}
            )
            assert response.status_code == 403, origin
        assert (
            client.post(
                "/api/workspaces",
                json={"name": "allowed"},
                headers={"Origin": "http://localhost:3000"},
            ).status_code
            == 200
        )


def test_approval_tamper_binding_never_writes(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer)[:1])
        assert wait(client, run["id"])["state"] == "waiting_approval"
        approval = client.get("/api/runs/" + run["id"] + "/approvals").json()[0]
        approval["payload_hash"] = "0" * 64
        client.app.state.store.put("approval", approval)
        assert (
            client.post(
                "/api/approvals/" + approval["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 200
        )
        result = wait(client, run["id"], ("failed",))
        assert "Approval binding mismatch" in result["error"]
        assert not list(Path(b["workspaces"][0]["root_path"]).rglob("calculator.py"))


def test_restart_then_approve_checkpoint_executes_each_action_once(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        developer = b["agents"][1]
        grant(client, developer)
        run = start(client, b, actions=actions_for(developer)[:2])
        assert wait(client, run["id"])["state"] == "waiting_approval"
        approval = client.get("/api/runs/" + run["id"] + "/approvals").json()[0]
        client.post(
            "/api/approvals/" + approval["id"] + "/decision",
            json={"decision": "approved"},
        )
        assert wait(client, run["id"])["state"] == "waiting_approval"
    with TestClient(create_app(tmp_path)) as client:
        pending = [
            a
            for a in client.get("/api/runs/" + run["id"] + "/approvals").json()
            if a["status"] == "pending"
        ]
        assert len(pending) == 1
        assert (
            client.post(
                "/api/approvals/" + pending[0]["id"] + "/decision",
                json={"decision": "approved"},
            ).status_code
            == 200
        )
        result = wait(client, run["id"], ("completed", "failed"))
        assert result["state"] == "completed", result
        assert len(result["artifacts"]) == 2
        events = client.get("/api/runs/" + run["id"] + "/events").json()
        assert (
            len(
                [
                    e
                    for e in events
                    if e["event_type"] == "tool.completed"
                    and e["payload"]["tool"] == "artifacts.write_python"
                ]
            )
            == 2
        )


def test_budget_exhaustion_never_retries_provider_with_zero_budget(
    tmp_path, monkeypatch
):
    calls = []

    async def brain(agent, text, budget, metadata):
        calls.append(budget)
        metadata["token_accounting"] = "estimated"
        return "spent", 2

    monkeypatch.setattr("services.worker.runtime.run_brain", brain)
    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        result = wait(client, start(client, b, token_budget=1, retry_limit=3)["id"])
        assert result["state"] == "failed"
        assert "budget exhausted" in result["error"]
        assert result["token_spent"] == 2
        assert calls == [1]


def test_v1_additive_migration_preserves_ids_history_settings_and_backup(tmp_path):
    import json
    import sqlite3

    from services.api.store import Store

    with TestClient(create_app(tmp_path)) as client:
        b = setup(client)
        store = client.app.state.store
        expected_ids = {
            kind: [v["id"] for v in store.list(kind)]
            for kind in ("workspace", "agent", "workflow", "room")
        }
        marker = store.event(
            b["workspaces"][0]["id"], "migration.fixture", {"sentinel": "preserve"}
        )
        store.put(
            "settings",
            {"id": "legacy-settings", "provider": "ollama", "model": "keep-me"},
        )
        # Reconstruct persisted v1 records by removing only new optional spec fields.
        for agent in store.list("agent"):
            for key in (
                "execution",
                "role_config",
                "skill_bindings",
                "tool_grants",
                "memory_config",
                "appearance",
            ):
                agent.pop(key, None)
            store.put("agent", agent)
        store.db.execute("DELETE FROM schema_migrations WHERE version=2")
        store.db.commit()
    with TestClient(create_app(tmp_path)) as client:
        store = client.app.state.store
        assert {
            kind: [v["id"] for v in store.list(kind)] for kind in expected_ids
        } == expected_ids
        assert marker in store.events()
        assert store.get("settings", "legacy-settings")["model"] == "keep-me"
        assert all(
            agent["execution"]["engine"] == "langchain" for agent in store.list("agent")
        )
        assert (
            store.db.execute(
                "SELECT count(*) FROM schema_migrations WHERE version=2"
            ).fetchone()[0]
            == 1
        )
    with sqlite3.connect(tmp_path / "pre-schema-v2.sqlite3") as backup:
        legacy = json.loads(
            backup.execute(
                "SELECT body FROM resources WHERE kind='agent' LIMIT 1"
            ).fetchone()[0]
        )
        assert "execution" not in legacy
        assert (
            backup.execute(
                "SELECT count(*) FROM schema_migrations WHERE version=2"
            ).fetchone()[0]
            == 0
        )
    store = Store(tmp_path)
    assert store.get("settings", "legacy-settings")["model"] == "keep-me"
    store.db.close()
