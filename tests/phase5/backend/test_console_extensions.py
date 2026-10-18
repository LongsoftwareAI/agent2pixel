import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c


def context(c):
    workspaces = c.get("/api/workspaces").json()
    ws, other = workspaces[0]["id"], workspaces[1]["id"]
    b = c.get("/api/bootstrap", params={"workspace_id": ws}).json()
    return {"workspace_id": ws}, b, {"workspace_id": other}


def test_budget_versioning_alerts_unknown_cost_and_workspace_isolation(client):
    p, b, other = context(client)
    path = "/api/console/budget"
    assert client.get(path, params=p).json()["policy"]["revision"] == 1
    client.app.state.store.event(p["workspace_id"], "model.completed", {"tokens": 80})
    payload = dict(revision=1, monthly_token_threshold=50, monthly_cost_threshold=1)
    result = client.patch(path, params=p, json=payload)
    assert result.status_code == 200, result.text
    value = result.json()
    assert value["policy"]["revision"] == 2 and value["alerts"][0]["observed"] == 80
    assert value["actual_cost"] is None and value["enforcement"] == "monitor-only"
    assert client.patch(path, params=p, json=payload).status_code == 409
    assert (
        client.patch(
            path,
            params=p,
            json={**payload, "revision": 2, "monthly_token_threshold": -1},
        ).status_code
        == 422
    )
    assert client.get(path, params=other).json()["policy"]["revision"] == 1
    assert len(client.get(path + "/history", params=p).json()) == 1
    partial = client.patch(
        path, params=p, json={"revision": 2, "monthly_cost_threshold": 2}
    ).json()
    assert partial["policy"]["monthly_token_threshold"] == 50
    assert partial["policy"]["monthly_cost_threshold"] == 2
    assert client.get(path + "/history", params=other).json() == []
    assert client.get(path, params={"workspace_id": "missing"}).status_code == 404


def test_archive_reversible_history_no_task_deletion_and_active_guard(client):
    p, b, other = context(client)
    store = client.app.state.store
    item = dict(
        id="archive-test",
        workspace_id=p["workspace_id"],
        title="Keep history",
        description="Retain all",
        brief_revision=3,
        reviews=[{"decision": "accepted"}],
    )
    store.put("work_item", item)
    path = "/api/console/work-items/archive-test/archive"
    result = client.post(path, params=p, json={"archived": True, "revision": 1})
    assert result.status_code == 200, result.text
    assert result.json()["reviews"] == item["reviews"]
    assert client.post("/api/work-items/archive-test/enqueue").status_code == 409
    assert client.post("/api/work-items/archive-test/runs", json={}).status_code == 409
    assert (
        client.patch(
            "/api/work-items/archive-test", json={"queue_requested": True}
        ).status_code
        == 409
    )
    assert all(
        v["id"] != "archive-test"
        for v in client.get("/api/work-queue", params=p).json()
    )
    assert (
        client.post(path, params=p, json={"archived": False, "revision": 1}).status_code
        == 409
    )
    assert (
        client.post(
            path, params=other, json={"archived": False, "revision": 2}
        ).status_code
        == 404
    )
    restored = client.post(
        path, params=p, json={"archived": False, "revision": 2}
    ).json()
    assert restored["archived"] is False and restored["brief_revision"] == 3
    assert len(client.get(path + "/history", params=p).json()) == 2
    assert client.get(path + "/history", params=other).status_code == 404
    store.put("work_item", {**restored, "queue_requested": True})
    assert (
        client.post(path, params=p, json={"archived": True, "revision": 3}).status_code
        == 409
    )


def test_soul_and_config_rollback_versions_isolation_and_invalid_history(client):
    p, b, other = context(client)
    agent = b["agents"][0]
    path = "/api/console/agents/" + agent["id"]
    original = client.get(path + "/soul", params=p).json()["content"]
    assert (
        client.patch(
            path + "/soul",
            params=p,
            json={"revision": 1, "content": "A changed instruction"},
        ).status_code
        == 200
    )
    history = client.get(path + "/soul/history", params=p).json()
    assert history[0]["content"] == original
    assert client.get(path + "/soul/history", params=other).status_code == 404
    result = client.post(
        path + "/soul/rollback", params=p, json={"revision": 2, "target_revision": 1}
    )
    assert result.status_code == 200, result.text
    assert result.json()["content"] == original and result.json()["revision"] == 3
    assert (
        client.post(
            path + "/soul/rollback",
            params=p,
            json={"revision": 2, "target_revision": 1},
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/soul/rollback",
            params=p,
            json={"revision": 3, "target_revision": 100},
        ).status_code
        == 404
    )
    assert (
        client.post(
            path + "/soul/rollback",
            params=other,
            json={"revision": 3, "target_revision": 1},
        ).status_code
        == 404
    )
    cfg = client.get(path + "/config/history", params=p).json()
    assert [v["revision"] for v in cfg] == [1, 2]
    result = client.post(
        path + "/config/rollback", params=p, json={"revision": 3, "target_revision": 2}
    )
    assert result.status_code == 200, result.text
    assert result.json()["config"]["system_prompt"] == "A changed instruction"
    assert client.get(path + "/soul", params=p).json()["revision"] == 4
    assert (
        client.post(
            path + "/config/rollback",
            params=p,
            json={"revision": 3, "target_revision": 1},
        ).status_code
        == 409
    )
    assert client.get(path + "/config/history", params=other).status_code == 404
    assert (
        client.post(
            path + "/config/rollback",
            params=other,
            json={"revision": 4, "target_revision": 1},
        ).status_code
        == 404
    )
    assert (
        client.post(
            path + "/config/rollback",
            params=p,
            json={"revision": 4, "target_revision": 999},
        ).status_code
        == 404
    )
    store = client.app.state.store
    store.put(
        "agent_config_history",
        dict(
            id="invalid-config",
            workspace_id=p["workspace_id"],
            agent_id=agent["id"],
            revision=999,
            config={"workspace_id": other["workspace_id"]},
        ),
    )
    assert (
        client.post(
            path + "/config/rollback",
            params=p,
            json={"revision": 4, "target_revision": 999},
        ).status_code
        == 422
    )


def test_logs_export_redacts_payload_and_bounds_workspace_scoped_cursor(client):
    p, b, other = context(client)
    store = client.app.state.store
    event = store.event(
        p["workspace_id"], "test.safe", {"secret": "DO-NOT-EXPORT", "prompt": "PRIVATE"}
    )
    foreign = store.event(other["workspace_id"], "foreign", {})
    path = "/api/console/logs/export"
    result = client.get(path, params={**p, "limit": 1})
    assert result.status_code == 200, result.text
    assert len(result.json()["items"]) == 1 and "DO-NOT-EXPORT" not in result.text
    assert (
        "PRIVATE" not in result.text and result.json()["items"][0]["id"] == event["id"]
    )
    assert client.get(path, params={**p, "limit": 201}).status_code == 422
    assert client.get(path, params={**p, "before": foreign["id"]}).status_code == 422
    assert client.get(path, params={**p, "kind": "audit"}).status_code == 200
    assert client.get(path, params={"workspace_id": "missing"}).status_code == 404
