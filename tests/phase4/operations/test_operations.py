"""Exercise actual persisted queue/evidence/memory without model timing assumptions."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from services.api.store import Store
from services.api.company import create_company_router
from services.api.operations import create_operations_router


class RunInput(BaseModel):
    input: str


@pytest.fixture
def env(tmp_path):
    app = FastAPI()
    store = app.state.store = Store(tmp_path / "store")
    for key in ("w", "foreign"):
        root = tmp_path / key
        root.mkdir()
        store.put("workspace", {"id": key, "root_path": str(root)})
        store.put("workflow", {"id": "flow-" + key, "workspace_id": key})
        store.put("agent", {"id": "agent-" + key, "workspace_id": key, "name": key})

    def start(id, body, work_item):
        if any(
            r["state"] == "queued" for r in store.list("run", work_item["workspace_id"])
        ):
            raise HTTPException(409)
        run = {
            "id": "run-" + work_item["id"],
            "workspace_id": work_item["workspace_id"],
            "work_item_id": work_item["id"],
            "state": "queued",
            "tasks": [],
            "artifacts": [],
            "input": body.input,
        }
        work_item.update(
            latest_run_id=run["id"], run_ids=work_item["run_ids"] + [run["id"]]
        )
        store.put_many([("run", run), ("work_item", work_item)])
        return run

    app.include_router(create_company_router(app, start, RunInput))
    app.include_router(create_operations_router(app, start, RunInput))
    with TestClient(app) as client:
        yield client, store
    store.db.close()


def create(client, **fields):
    response = client.post(
        "/api/work-items",
        json={
            "workspace_id": "w",
            "workflow_id": "flow-w",
            "title": "Brief",
            "description": "Do work",
            **fields,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_priority_deadline_atomic_dispatch_and_load(env):
    client, store = env
    low = create(client, priority="low", queue_requested=True)
    late = create(
        client, priority="high", due_at="2026-11-02T00:00:00Z", queue_requested=True
    )
    early = create(
        client,
        priority="high",
        due_at="2026-11-01T00:00:00Z",
        owner_agent_id="agent-w",
        queue_requested=True,
    )
    assert [x["id"] for x in client.get("/api/work-queue?workspace_id=w").json()] == [
        early["id"],
        late["id"],
        low["id"],
    ]
    with ThreadPoolExecutor(2) as pool:
        statuses = list(
            pool.map(
                lambda _: client.post(
                    "/api/work-queue/dispatch", json={"workspace_id": "w"}
                ).status_code,
                range(2),
            )
        )
    assert sorted(statuses) == [200, 409]
    assert len(store.list("run")) == 1
    assert store.get("work_item", early["id"])["queue_requested"] is False
    assert len(client.get("/api/work-queue?workspace_id=w").json()) == 2
    run = store.list("run")[0]
    run["tasks"] = [{"agent_id": "agent-w", "state": "running"}]
    store.put("run", run)
    data = client.get("/api/operations?workspace_id=w").json()
    assert data["agents"][0]["active_tasks"] == 1
    assert data["active_run_ids"] == [run["id"]]
    assert (
        client.get("/api/operations?workspace_id=foreign").json()["active_run_ids"]
        == []
    )


def test_validation_queue_and_revision_preservation(env):
    client, store = env
    item = create(client)
    for body, code in [
        ({"owner_agent_id": "agent-foreign"}, 403),
        ({"due_at": "2026-11-01"}, 422),
        ({"priority": "urgent"}, 422),
        ({"queue_requested": 1}, 422),
    ]:
        assert (
            client.patch("/api/work-items/" + item["id"], json=body).status_code == code
        )
    assert (
        client.patch("/api/work-items/" + item["id"], json={"priority": "high"}).json()[
            "brief_revision"
        ]
        == 1
    )
    assert (
        client.post("/api/work-items/" + item["id"] + "/enqueue").json()["status"]
        == "queued"
    )
    assert (
        client.post("/api/work-items/" + item["id"] + "/dequeue").json()["status"]
        == "backlog"
    )
    assert (
        client.post("/api/work-queue/dispatch", json={"workspace_id": "w"}).status_code
        == 409
    )
    assert client.get("/api/work-queue?workspace_id=missing").status_code == 404


def artifact(store, run_id, content):
    run = {
        "id": run_id,
        "workspace_id": "w",
        "work_item_id": "item",
        "state": "completed",
        "output": content,
        "artifacts": [],
    }
    relative = "artifacts/" + run_id + "/report.md"
    path = Path(store.get("workspace", "w")["root_path"]) / relative
    path.parent.mkdir(parents=True)
    path.write_text(content)
    value = {
        "id": "art-" + run_id,
        "path": relative,
        "sha256": sha256(content.encode()).hexdigest(),
        "size": len(content.encode()),
    }
    run["artifacts"] = [value]
    store.put("run", run)
    return run, path


def test_artifact_integrity_comparison_and_foreign_denial(env):
    client, store = env
    old, path = artifact(store, "old", "First\n")
    new, _ = artifact(store, "new", "Second\n")
    item = create(client)
    item.update(id="item", run_ids=["old", "new"])
    store.put("work_item", item)
    url = "/api/work-items/item/comparison?previous_run_id=old&current_run_id=new"
    assert "-First" in client.get(url).json()["diffs"][0]["diff"]
    assert client.get("/api/runs/old/artifacts/art-old").json()["content"] == "First\n"
    new["work_item_id"] = "foreign"
    store.put("run", new)
    assert client.get(url).status_code == 403
    path.write_text("Tampered")
    assert client.get("/api/runs/old/artifacts/art-old").status_code == 409
    path.unlink()
    path.symlink_to(Path(store.root) / "agentverse.sqlite3")
    assert client.get("/api/runs/old/artifacts/art-old").status_code == 403
    assert client.get("/api/runs/old/artifacts/art-new").status_code == 404


def test_memory_provenance_history_tombstone(env):
    client, store = env
    store.put(
        "memory",
        {"id": "memo", "workspace_id": "w", "content": "Before", "scope": "workspace"},
    )
    for key, ws in [("source", "w"), ("other-source", "foreign")]:
        store.put("source", {"id": key, "workspace_id": ws, "sha256": key})
    assert (
        client.patch(
            "/api/memories/memo", json={"source_id": "other-source"}
        ).status_code
        == 403
    )
    assert (
        client.patch("/api/memories/memo", json={"scope": "agent"}).status_code == 422
    )
    value = client.patch(
        "/api/memories/memo", json={"content": "After", "source_id": "source"}
    ).json()
    assert value["provenance"]["sha256"] == "source"
    assert (
        client.get("/api/memories/memo/history").json()[0]["before"]["content"]
        == "Before"
    )
    assert client.delete("/api/memories/memo").status_code == 200
    assert (
        client.patch("/api/memories/memo", json={"content": "Again"}).status_code == 410
    )
    assert len(client.get("/api/memories/memo/history").json()) == 2
    assert store.get("memory", "memo")["deleted_at"]
