"""Local company briefs, explicit human acceptance, and reusable workflow guidance."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from services.api.store import now, uid
from services.api.operations import validate_operations_fields
from functools import wraps
from datetime import datetime
from typing import Literal


class WorkItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    workflow_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=30)
    priority: Literal["low", "normal", "high"] = "normal"
    due_at: datetime | None = None
    owner_agent_id: str | None = None
    queue_requested: bool = False


TEMPLATES = [
    {
        "id": key,
        "name": name,
        "description": description,
        "roles": roles,
        "steps": [
            {
                "role": role,
                "instructions": instruction,
                "deliverable": {"filename": filename},
            }
            for role, instruction, filename in steps
        ],
    }
    for key, name, description, roles, steps in [
        (
            "research-brief",
            "Research brief",
            "Assess supplied sources and document gaps; no live research implied.",
            ["Researcher", "Reviewer"],
            [
                (
                    "Researcher",
                    "Read supplied workspace sources. Produce a sourced brief; distinguish evidence, uncertainty and unanswered questions. Never invent external research.",
                    "research-brief.md",
                ),
                (
                    "Reviewer",
                    "Review the brief against sources and acceptance criteria; flag unsupported claims and missing evidence.",
                    "research-review.md",
                ),
            ],
        ),
        (
            "content-production",
            "Content production",
            "Plan, draft and review content from supplied material.",
            ["Planner", "Writer", "Reviewer"],
            [
                (
                    "Planner",
                    "Develop a content outline from the brief and supplied source material; state audience and factual constraints.",
                    "content-outline.md",
                ),
                (
                    "Writer",
                    "Draft content using the prior outline and supplied sources. Mark claims requiring verification.",
                    "content-draft.md",
                ),
                (
                    "Reviewer",
                    "Review factual support, audience fit and acceptance criteria; provide explicit revision requests.",
                    "content-review.md",
                ),
            ],
        ),
        (
            "operations-report",
            "Operations report",
            "Analyze supplied operational records and propose actions, without executing them.",
            ["Analyst", "Reviewer"],
            [
                (
                    "Analyst",
                    "Analyze supplied operational records. Report observations, risks and proposed actions with evidence; never claim actions were executed.",
                    "operations-report.md",
                ),
                (
                    "Reviewer",
                    "Check the operations analysis against supplied records and acceptance criteria; identify unsupported recommendations.",
                    "operations-review.md",
                ),
            ],
        ),
        (
            "coding-review",
            "Coding review",
            "Review supplied code evidence; executable tools remain separately granted.",
            ["Developer", "Reviewer"],
            [
                (
                    "Developer",
                    "Assess the requested implementation using supplied code and test evidence. Clearly distinguish proposed code from files actually written or tests actually run.",
                    "coding-report.md",
                ),
                (
                    "Reviewer",
                    "Independently inspect code/report evidence and test results; state limitations and failures accurately.",
                    "coding-review.md",
                ),
            ],
        ),
    ]
]


def projected_item(store, item):
    """Read projection only: run completion never silently accepts work."""
    value = dict(item)
    run = (
        store.get("run", item.get("latest_run_id"))
        if item.get("latest_run_id")
        else None
    )
    if not run or run.get("brief_revision", 1) != item.get("brief_revision", 1):
        value["status"] = "queued" if item.get("queue_requested") else "backlog"
    elif run["state"] == "completed":
        reviews = [r for r in item.get("reviews", []) if r["run_id"] == run["id"]]
        value["status"] = (
            ("done" if reviews[-1]["decision"] == "accepted" else "backlog")
            if reviews
            else "review"
        )
    else:
        value["status"] = {
            "queued": "running",
            "running": "running",
            "waiting_approval": "waiting_approval",
            "waiting_review": "waiting_review",
            "failed": "failed",
            "cancelled": "cancelled",
        }.get(run["state"], "backlog")
    if item.get("queue_requested") and value["status"] not in (
        "running",
        "waiting_approval",
        "waiting_review",
        "review",
        "done",
    ):
        value["status"] = "queued"
    return value


def create_company_router(app, start_run, run_model):
    router = APIRouter()

    def store():
        return app.state.store

    def serialized(fn):
        @wraps(fn)
        def locked(*args, **kwargs):
            with store().lock:
                return fn(*args, **kwargs)

        return locked

    def get(kind, id):
        result = store().get(kind, id)
        if not result:
            raise HTTPException(404, kind + " not found")
        return result

    def criteria(values):
        if (
            not isinstance(values, list)
            or len(values) > 30
            or any(not isinstance(x, str) or not 1 <= len(x) <= 2000 for x in values)
        ):
            raise HTTPException(
                422,
                "Acceptance criteria require at most30 nonempty strings, each max2000 characters",
            )

    @router.get("/api/workflow-templates")
    def templates():
        return TEMPLATES

    @router.get("/api/work-items")
    def items(workspace_id: str):
        get("workspace", workspace_id)
        return [
            projected_item(store(), x) for x in store().list("work_item", workspace_id)
        ]

    @router.post("/api/work-items")
    def create(body: WorkItemInput):
        get("workspace", body.workspace_id)
        workflow = get("workflow", body.workflow_id)
        if workflow["workspace_id"] != body.workspace_id:
            raise HTTPException(403, "Workflow outside workspace")
        validate_operations_fields(
            store(), body.workspace_id, body.model_dump(mode="json")
        )
        criteria(body.acceptance_criteria)
        value = dict(
            body.model_dump(mode="json"),
            id=uid(),
            run_ids=[],
            latest_run_id=None,
            reviews=[],
            brief_revision=1,
            created_at=now(),
            updated_at=now(),
        )
        store().put("work_item", value)
        return projected_item(store(), value)

    @router.get("/api/work-items/{id}")
    def item(id: str):
        return projected_item(store(), get("work_item", id))

    @router.patch("/api/work-items/{id}")
    @serialized
    def patch(id: str, body: dict):
        value = get("work_item", id)
        if projected_item(store(), value)["status"] in (
            "running",
            "waiting_approval",
            "waiting_review",
        ):
            raise HTTPException(409, "Active brief is immutable")
        if set(body) - {
            "title",
            "description",
            "acceptance_criteria",
            "priority",
            "due_at",
            "owner_agent_id",
            "queue_requested",
        }:
            raise HTTPException(422, "Only brief fields can change")
        for key, maximum in (("title", 200), ("description", 20000)):
            if key in body and (
                not isinstance(body[key], str) or not 1 <= len(body[key]) <= maximum
            ):
                raise HTTPException(422, "Invalid " + key)
        validate_operations_fields(store(), value["workspace_id"], body)
        criteria(body.get("acceptance_criteria", value["acceptance_criteria"]))
        if any(
            value.get(key) != content
            for key, content in body.items()
            if key in ("title", "description", "acceptance_criteria")
        ):
            value["brief_revision"] = value.get("brief_revision", 1) + 1
        value.update(body, updated_at=now())
        store().put("work_item", value)
        return projected_item(store(), value)

    @router.post("/api/work-items/{id}/runs")
    async def launch(id: str, body: dict):
        return launch_locked(id, body)

    @serialized
    def launch_locked(id: str, body: dict):
        from pydantic import ValidationError

        value = get("work_item", id)
        prompt = (
            value["title"]
            + "\n\n"
            + value["description"]
            + "\n\nAcceptance criteria:\n"
            + "\n".join("- " + x for x in value["acceptance_criteria"])
        )
        try:
            parsed = run_model(**{"input": prompt, **body})
        except ValidationError:
            raise HTTPException(422, "Invalid run fields") from None
        value["queue_requested"] = False
        return start_run(value["workflow_id"], parsed, work_item=value)

    @router.post("/api/work-items/{id}/review")
    @serialized
    def review(id: str, body: dict):
        value = get("work_item", id)
        if (
            set(body) != {"decision", "comment"}
            or body.get("decision") not in ("accepted", "changes_requested")
            or not isinstance(body.get("comment"), str)
            or not 1 <= len(body["comment"]) <= 8000
        ):
            raise HTTPException(422, "Review requires decision and nonempty comment")
        run = (
            store().get("run", value.get("latest_run_id"))
            if value.get("latest_run_id")
            else None
        )
        if (
            not run
            or run["state"] != "completed"
            or projected_item(store(), value)["status"] != "review"
        ):
            raise HTTPException(
                409, "Only latest completed unreviewed run can be reviewed"
            )
        value["reviews"].append(
            dict(body, reviewer="human", run_id=run["id"], created_at=now())
        )
        value["updated_at"] = now()
        store().put("work_item", value)
        return projected_item(store(), value)

    return router
