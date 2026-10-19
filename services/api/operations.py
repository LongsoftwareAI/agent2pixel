"""Explicit local dispatch, verified text evidence, and auditable memory edits."""

from datetime import datetime
from difflib import unified_diff
from functools import wraps
from hashlib import sha256
from pathlib import Path

from fastapi import APIRouter, HTTPException
from services.api.store import now

ACTIVE = ("queued", "running", "waiting_approval", "waiting_review")


def validate_operations_fields(store, workspace_id, body):
    if "priority" in body and body["priority"] not in ("low", "normal", "high"):
        raise HTTPException(422, "Invalid priority")
    if "queue_requested" in body and type(body["queue_requested"]) is not bool:
        raise HTTPException(422, "queue_requested must be boolean")
    if body.get("due_at") is not None:
        try:
            stamp = datetime.fromisoformat(body["due_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(
                422, "due_at requires ISO timestamp with timezone"
            ) from None
    owner = body.get("owner_agent_id")
    if owner is not None:
        agent = store.get("agent", owner) if isinstance(owner, str) else None
        if not agent or agent["workspace_id"] != workspace_id:
            raise HTTPException(403, "Owner outside workspace")


def create_operations_router(app, start_run=None, run_model=None):
    router = APIRouter()

    def store():
        return app.state.store

    def get(kind, id):
        value = store().get(kind, id)
        if not value:
            raise HTTPException(404, kind + " not found")
        return value

    def locked(fn):
        @wraps(fn)
        def call(*args, **kwargs):
            with store().lock:
                return fn(*args, **kwargs)

        return call

    def queue(workspace_id):
        from services.api.company import projected_item

        get("workspace", workspace_id)
        values = [
            projected_item(store(), item)
            for item in store().list("work_item", workspace_id)
        ]
        values = [
            item
            for item in values
            if item.get("queue_requested")
            and not item.get("archived")
            and item["status"]
            not in ("running", "waiting_approval", "waiting_review", "review", "done")
        ]
        return sorted(
            values,
            key=lambda item: (
                {"high": 0, "normal": 1, "low": 2}[item.get("priority", "normal")],
                datetime.fromisoformat(
                    item["due_at"].replace("Z", "+00:00")
                ).timestamp()
                if item.get("due_at")
                else float("inf"),
                item["created_at"],
                item["id"],
            ),
        )

    def active(workspace_id):
        return [
            run for run in store().list("run", workspace_id) if run["state"] in ACTIVE
        ]

    @router.get("/api/work-queue")
    @locked
    def work_queue(workspace_id: str):
        return queue(workspace_id)

    @router.post("/api/work-items/{id}/enqueue")
    @locked
    def enqueue(id: str):
        from services.api.company import projected_item

        item = get("work_item", id)
        if item.get("archived"):
            raise HTTPException(409, "Restore archived work before enqueueing")
        if projected_item(store(), item)["status"] in (
            "running",
            "waiting_approval",
            "waiting_review",
            "review",
            "done",
        ):
            raise HTTPException(409, "Work item is active or requires review/revision")
        item.update(queue_requested=True, updated_at=now())
        store().put("work_item", item)
        return projected_item(store(), item)

    @router.post("/api/work-items/{id}/dequeue")
    @locked
    def dequeue(id: str):
        from services.api.company import projected_item

        item = get("work_item", id)
        item.update(queue_requested=False, updated_at=now())
        store().put("work_item", item)
        return projected_item(store(), item)

    @router.post("/api/work-queue/dispatch")
    async def dispatch(body: dict):
        # Runtime.schedule creates asyncio tasks on the API event loop.
        return dispatch_locked(body)

    @locked
    def dispatch_locked(body: dict):
        if set(body) != {"workspace_id"} or not isinstance(body["workspace_id"], str):
            raise HTTPException(422, "workspace_id required")
        workspace_id = body["workspace_id"]
        get("workspace", workspace_id)
        if active(workspace_id):
            raise HTTPException(409, "Workspace already has active work")
        candidates = queue(workspace_id)
        if not candidates:
            raise HTTPException(409, "No queued work")
        if not start_run or not run_model:
            raise HTTPException(503, "Runtime unavailable")
        item = candidates[0]
        prompt = (
            item["title"]
            + "\n\n"
            + item["description"]
            + "\n\nAcceptance criteria:\n"
            + "\n".join("- " + x for x in item["acceptance_criteria"])
        )
        item["queue_requested"] = False
        return start_run(item["workflow_id"], run_model(input=prompt), work_item=item)

    @router.get("/api/operations")
    @locked
    def operations(workspace_id: str):
        get("workspace", workspace_id)
        runs = active(workspace_id)
        agents = []
        active_ids = {run["id"] for run in runs}
        tool_calls = [
            record
            for record in store().list("flow_tool_result", workspace_id)
            if record.get("status") == "started" and record.get("run_id") in active_ids
        ]
        for agent in store().list("agent", workspace_id):
            matching = [
                (run, task)
                for run in runs
                for task in run.get("tasks", [])
                if task.get("agent_id") == agent["id"] and task.get("state") in ACTIVE
            ]
            matching_tools = [
                record for record in tool_calls if record.get("agent_id") == agent["id"]
            ]
            agents.append(
                {
                    "agent_id": agent["id"],
                    "name": agent["name"],
                    "active_tasks": len(matching),
                    "active_tool_calls": len(matching_tools),
                    "active_run_ids": sorted(
                        {run["id"] for run, _ in matching}
                        | {record["run_id"] for record in matching_tools}
                    ),
                }
            )
        return {
            "workspace_id": workspace_id,
            "active_run_ids": [run["id"] for run in runs],
            "queue_count": len(queue(workspace_id)),
            "agents": agents,
        }

    def text_artifact(run, artifact_id):
        artifact = next(
            (value for value in run.get("artifacts", []) if value["id"] == artifact_id),
            None,
        )
        if not artifact:
            raise HTTPException(404, "Artifact not linked to run")
        root = Path(get("workspace", run["workspace_id"])["root_path"]).resolve()
        relative = Path(artifact.get("path", ""))
        expected = Path("artifacts") / run["id"]
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.is_relative_to(expected)
        ):
            raise HTTPException(403, "Artifact outside run directory")
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise HTTPException(403, "Artifact symlink forbidden")
        if not current.resolve().is_relative_to(root) or not current.is_file():
            raise HTTPException(404, "Artifact file unavailable")
        if current.stat().st_size > 1048576:
            raise HTTPException(413, "Artifact exceeds text limit")
        content = current.read_bytes()
        if sha256(content).hexdigest() != artifact.get("sha256") or len(
            content
        ) != artifact.get("size"):
            raise HTTPException(409, "Artifact integrity check failed")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(415, "Artifact is not UTF-8 text") from None
        return {**artifact, "content": text}

    @router.get("/api/runs/{id}/artifacts/{artifact_id}")
    @locked
    def artifact(id: str, artifact_id: str):
        return text_artifact(get("run", id), artifact_id)

    @router.get("/api/work-items/{id}/comparison")
    @locked
    def comparison(id: str, previous_run_id: str, current_run_id: str):
        item = get("work_item", id)
        runs = [get("run", key) for key in (previous_run_id, current_run_id)]
        if any(
            run["id"] not in item["run_ids"]
            or run.get("work_item_id") != id
            or run["workspace_id"] != item["workspace_id"]
            for run in runs
        ):
            raise HTTPException(403, "Comparison requires linked work item runs")
        if any(run["state"] != "completed" for run in runs):
            raise HTTPException(409, "Comparison requires completed runs")
        mappings = [
            {
                Path(value["path"]).name: value
                for value in run.get("artifacts", [])
                if value.get("path")
            }
            for run in runs
        ]
        diffs = []
        for name in sorted(mappings[0].keys() | mappings[1].keys()):
            artifacts = [mapping.get(name) for mapping in mappings]
            texts = [
                text_artifact(run, value["id"])["content"] if value else ""
                for run, value in zip(runs, artifacts)
            ]
            diff = "".join(
                unified_diff(
                    texts[0].splitlines(keepends=True),
                    texts[1].splitlines(keepends=True),
                    fromfile="previous/" + name,
                    tofile="current/" + name,
                )
            )
            if len(diff) > 1048576:
                raise HTTPException(413, "Comparison exceeds text limit")
            diffs.append(
                {
                    "name": name,
                    "previous_artifact_id": artifacts[0] and artifacts[0]["id"],
                    "current_artifact_id": artifacts[1] and artifacts[1]["id"],
                    "diff": diff,
                }
            )
        if not diffs:
            diff = "".join(
                unified_diff(
                    runs[0].get("output", "").splitlines(keepends=True),
                    runs[1].get("output", "").splitlines(keepends=True),
                    fromfile="previous/output",
                    tofile="current/output",
                )
            )
            if len(diff) > 1048576:
                raise HTTPException(413, "Comparison exceeds text limit")
            diffs = [
                {
                    "name": "output",
                    "previous_artifact_id": None,
                    "current_artifact_id": None,
                    "diff": diff,
                }
            ]
        return {
            "previous_run_id": previous_run_id,
            "current_run_id": current_run_id,
            "diffs": diffs,
            "acceptance_criteria": item["acceptance_criteria"],
            "reviews": item.get("reviews", []),
        }

    def provenance(memory, source_id):
        if source_id is None:
            return None
        if not isinstance(source_id, str):
            raise HTTPException(422, "source_id must be string or null")
        source = get("source", source_id)
        if source["workspace_id"] != memory["workspace_id"]:
            raise HTTPException(403, "Source outside memory workspace")
        return {
            "source_id": source_id,
            "sha256": source.get("sha256"),
            "url": source.get("url"),
            "recorded_at": now(),
        }

    @router.patch("/api/memories/{id}")
    @locked
    def edit_memory(id: str, body: dict, workspace_id: str | None = None):
        memory = get("memory", id)
        if workspace_id is not None and memory["workspace_id"] != workspace_id:
            raise HTTPException(404, "Memory not found in workspace")
        if memory.get("deleted_at"):
            raise HTTPException(410, "Memory deleted")
        expected_revision = body.get("expected_revision")
        if "expected_revision" in body and (
            type(expected_revision) is not int or expected_revision < 1
        ):
            raise HTTPException(422, "expected_revision must be a positive integer")
        if expected_revision is not None and expected_revision != memory.get("revision", 1):
            raise HTTPException(409, "Memory revision conflict; reload before editing")
        if (
            not body
            or set(body) - {"content", "source_id", "expected_revision"}
            or not ({"content", "source_id"} & set(body))
            or (
                "content" in body
                and (
                    not isinstance(body["content"], str)
                    or not 1 <= len(body["content"]) <= 20000
                )
            )
        ):
            raise HTTPException(422, "Only nonempty content and source_id can change")
        before = {key: value for key, value in memory.items() if key != "history"}
        if "source_id" in body:
            memory["provenance"] = provenance(memory, body["source_id"])
        memory.update(
            {key: value for key, value in body.items() if key != "expected_revision"},
            revision=memory.get("revision", 1) + 1,
            updated_at=now(), editor="human",
        )
        memory.setdefault("history", []).append(
            {
                "action": "edited",
                "editor": "human",
                "created_at": now(),
                "before": before,
            }
        )
        store().put("memory", memory)
        store().event(memory["workspace_id"], "memory.updated", {"memory_id": id})
        return memory

    @router.delete("/api/memories/{id}")
    @locked
    def delete_memory(
        id: str, workspace_id: str | None = None, expected_revision: int | None = None
    ):
        memory = get("memory", id)
        if workspace_id is not None and memory["workspace_id"] != workspace_id:
            raise HTTPException(404, "Memory not found in workspace")
        if memory.get("deleted_at"):
            raise HTTPException(410, "Memory already deleted")
        if expected_revision is not None:
            if expected_revision < 1:
                raise HTTPException(422, "expected_revision must be positive")
            if expected_revision != memory.get("revision", 1):
                raise HTTPException(409, "Memory revision conflict; reload before deleting")
        before = {key: value for key, value in memory.items() if key != "history"}
        memory.update(
            deleted_at=now(), updated_at=now(), editor="human",
            revision=memory.get("revision", 1) + 1,
        )
        memory.setdefault("history", []).append(
            {
                "action": "deleted",
                "editor": "human",
                "created_at": now(),
                "before": before,
            }
        )
        store().put("memory", memory)
        store().event(memory["workspace_id"], "memory.deleted", {"memory_id": id})
        return {"id": id, "deleted_at": memory["deleted_at"]}

    @router.get("/api/memories/{id}/history")
    @locked
    def memory_history(id: str):
        return get("memory", id).get("history", [])

    return router
