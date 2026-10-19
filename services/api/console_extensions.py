"""Versioned local console policies and reversible history operations."""

from datetime import datetime, timezone
from functools import wraps
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from services.api.store import now, uid


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BudgetInput(Input):
    revision: int = Field(ge=1, strict=True)
    monthly_token_threshold: int | None = Field(default=None, ge=1, strict=True)
    monthly_cost_threshold: float | None = Field(
        default=None, gt=0, allow_inf_nan=False
    )
    currency: Literal["USD"] = "USD"


class ArchiveInput(Input):
    revision: int = Field(ge=1, strict=True)
    archived: StrictBool


class RollbackInput(Input):
    revision: int = Field(ge=1, strict=True)
    target_revision: int = Field(ge=1, strict=True)


def create_console_extensions_router(app):
    router = APIRouter(prefix="/api/console")

    def store():
        return app.state.store

    def locked(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with store().lock:
                return fn(*args, **kwargs)

        return wrapper

    def get(kind, id, workspace_id):
        value = store().get(kind, id)
        if not value or value.get("workspace_id") != workspace_id:
            raise HTTPException(404, "Resource not found in workspace")
        return value

    def ws(workspace_id):
        value = store().get("workspace", workspace_id)
        if not value:
            raise HTTPException(404, "Workspace not found")
        return value

    def audit(workspace_id, action, target, revision):
        store().put(
            "audit",
            dict(
                id=uid(),
                workspace_id=workspace_id,
                actor="local-operator",
                action=action,
                target_id=target,
                revision=revision,
                outcome="success",
                created_at=now(),
            ),
        )
        store().event(
            workspace_id, "console." + action, dict(target_id=target, revision=revision)
        )

    def policy(workspace_id):
        ws(workspace_id)
        return store().get("budget_policy", "budget:" + workspace_id) or dict(
            id="budget:" + workspace_id,
            workspace_id=workspace_id,
            revision=1,
            monthly_token_threshold=None,
            monthly_cost_threshold=None,
            currency="USD",
        )

    @router.get("/budget")
    def budget(workspace_id: str):
        value = policy(workspace_id)
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        events = [
            e
            for e in store().events(workspace_id)
            if e["event_type"] == "model.completed"
            and e["created_at"].startswith(month)
        ]
        from services.api.console import token_summary

        accounting = token_summary(events)
        total = accounting["total_tokens"]
        threshold = value["monthly_token_threshold"]
        return dict(
            policy=value,
            period=month,
            timezone="UTC",
            total_tokens=total,
            token_accounting=accounting["token_accounting"],
            accounting_counts=accounting["accounting_counts"],
            tokens_by_accounting=accounting["tokens_by_accounting"],
            actual_cost=None,
            enforcement="monitor-only",
            alerts=[
                dict(
                    kind="token_threshold",
                    state="exceeded",
                    observed=total,
                    token_accounting=accounting["token_accounting"],
                    threshold=threshold,
                )
            ]
            if threshold and total >= threshold
            else [],
            cost_state="unknown",
            cost_reason="Provider billing is unavailable; cost threshold cannot be evaluated",
        )

    @router.patch("/budget")
    @locked
    def budget_patch(body: BudgetInput, workspace_id: str):
        value = policy(workspace_id)
        if body.revision != value["revision"]:
            raise HTTPException(409, "Budget policy revision changed")
        prior = dict(value, id=uid(), policy_id=value["id"], created_at=now())
        value.update(
            body.model_dump(exclude={"revision"}, exclude_unset=True),
            revision=value["revision"] + 1,
            updated_at=now(),
        )
        store().put_many([("budget_policy_revision", prior), ("budget_policy", value)])
        audit(workspace_id, "budget.updated", value["id"], value["revision"])
        return budget(workspace_id)

    @router.get("/budget/history")
    def budget_history(workspace_id: str):
        ws(workspace_id)
        return sorted(
            store().list("budget_policy_revision", workspace_id),
            key=lambda x: x["revision"],
        )

    @router.post("/work-items/{id}/archive")
    @locked
    def archive(id: str, body: ArchiveInput, workspace_id: str):
        item = get("work_item", id, workspace_id)
        revision = item.get("archive_revision", 1)
        if body.revision != revision:
            raise HTTPException(409, "Archive revision changed")
        run = (
            store().get("run", item.get("latest_run_id"))
            if item.get("latest_run_id")
            else None
        )
        if body.archived and (
            item.get("queue_requested")
            or (
                run
                and run["state"]
                in ("queued", "running", "waiting_approval", "waiting_review")
            )
        ):
            raise HTTPException(409, "Active or queued work cannot be archived")
        prior = dict(
            id=uid(),
            workspace_id=workspace_id,
            work_item_id=id,
            archived=item.get("archived", False),
            revision=revision,
            created_at=now(),
        )
        item.update(
            archived=body.archived,
            archive_revision=revision + 1,
            archive_updated_at=now(),
        )
        store().put_many([("work_archive_revision", prior), ("work_item", item)])
        audit(
            workspace_id,
            "work.archived" if body.archived else "work.restored",
            id,
            revision + 1,
        )
        return item

    @router.get("/work-items/{id}/archive/history")
    def archive_history(id: str, workspace_id: str):
        get("work_item", id, workspace_id)
        return sorted(
            [
                v
                for v in store().list("work_archive_revision", workspace_id)
                if v["work_item_id"] == id
            ],
            key=lambda x: x["revision"],
        )

    @router.get("/agents/{id}/soul/history")
    def soul_history(id: str, workspace_id: str):
        get("agent", id, workspace_id)
        return sorted(
            [
                v
                for v in store().list("agent_document_revision", workspace_id)
                if v["agent_id"] == id
            ],
            key=lambda x: x["revision"],
        )

    @router.post("/agents/{id}/soul/rollback")
    @locked
    def soul_rollback(id: str, body: RollbackInput, workspace_id: str):
        agent = get("agent", id, workspace_id)
        revision = agent.get("soul_revision", 1)
        if body.revision != revision:
            raise HTTPException(409, "SOUL revision changed")
        target = next(
            (
                v
                for v in soul_history(id, workspace_id)
                if v["revision"] == body.target_revision
            ),
            None,
        )
        if not target:
            raise HTTPException(404, "SOUL historical revision not found")
        prior = dict(
            id=uid(),
            workspace_id=workspace_id,
            agent_id=id,
            content=agent["system_prompt"],
            revision=revision,
            created_at=now(),
        )
        from services.api.console import config_revision_record

        config_prior = config_revision_record(agent)
        agent.update(
            system_prompt=target["content"],
            soul_revision=revision + 1,
            soul_updated_at=now(),
            agent_config_revision=agent.get("agent_config_revision", 1) + 1,
        )
        store().put_many(
            [
                ("agent_document_revision", prior),
                ("agent_config_history", config_prior),
                ("agent", agent),
            ]
        )
        audit(workspace_id, "soul.rolled_back", id, revision + 1)
        return dict(
            agent_id=id,
            content=agent["system_prompt"],
            revision=revision + 1,
            updated_at=agent["soul_updated_at"],
        )

    @router.get("/agents/{id}/config/history")
    def config_history(id: str, workspace_id: str):
        get("agent", id, workspace_id)
        return sorted(
            [
                v
                for v in store().list("agent_config_history", workspace_id)
                if v["agent_id"] == id
            ],
            key=lambda x: x["revision"],
        )

    @router.post("/agents/{id}/config/rollback")
    @locked
    def config_rollback(id: str, body: RollbackInput, workspace_id: str):
        from pydantic import ValidationError
        from services.api.main import AgentInput, normalize_agent
        from services.api.policy import validate_brain
        from services.api.domain import validate_spec
        from services.api.console import config_revision_record

        agent = get("agent", id, workspace_id)
        revision = agent.get("agent_config_revision", 1)
        if body.revision != revision:
            raise HTTPException(409, "Agent configuration revision changed")
        target = next(
            (
                v
                for v in config_history(id, workspace_id)
                if v["revision"] == body.target_revision
            ),
            None,
        )
        if not target:
            raise HTTPException(
                404, "Agent configuration historical revision not found"
            )
        if target["config"].get("workspace_id") != workspace_id:
            raise HTTPException(422, "Historical configuration workspace mismatch")
        try:
            config = normalize_agent(AgentInput(**target["config"]).model_dump())
        except ValidationError:
            raise HTTPException(422, "Historical configuration is invalid") from None
        validate_brain(config["brain"])
        validate_spec(config, store())
        records = [("agent_config_history", config_revision_record(agent))]
        if config["system_prompt"] != agent["system_prompt"]:
            soul_revision = agent.get("soul_revision", 1)
            records.append(
                (
                    "agent_document_revision",
                    dict(
                        id=uid(),
                        workspace_id=workspace_id,
                        agent_id=id,
                        content=agent["system_prompt"],
                        revision=soul_revision,
                        created_at=now(),
                    ),
                )
            )
            agent.update(soul_revision=soul_revision + 1, soul_updated_at=now())
        agent.update(config, agent_config_revision=revision + 1)
        records.append(("agent", agent))
        store().put_many(records)
        audit(workspace_id, "agent.config_rolled_back", id, revision + 1)
        return dict(agent_id=id, revision=revision + 1, config=config)

    @router.get("/logs/export")
    def log_export(
        workspace_id: str,
        kind: Literal["system", "audit"] = "system",
        limit: int = 100,
        before: str | None = None,
    ):
        ws(workspace_id)
        if not 1 <= limit <= 200:
            raise HTTPException(422, "Limit must be 1..200")
        rows = (
            store().list("audit", workspace_id)
            if kind == "audit"
            else store().events(workspace_id)
        )
        rows = sorted(
            rows, key=lambda r: (r.get("created_at", ""), r["id"]), reverse=True
        )
        if before:
            index = next((i for i, row in enumerate(rows) if row["id"] == before), None)
            if index is None:
                raise HTTPException(422, "Invalid workspace-scoped cursor")
            rows = rows[index + 1 :]
        fields = (
            ("id", "created_at", "event_type", "run_id", "agent_id", "seq")
            if kind == "system"
            else (
                "id",
                "created_at",
                "actor",
                "action",
                "target_id",
                "revision",
                "outcome",
                "run_id",
            )
        )
        return dict(
            schema_version=1,
            kind=kind,
            workspace_id=workspace_id,
            exported_at=now(),
            items=[{k: r[k] for k in fields if k in r} for r in rows[:limit]],
            next_cursor=rows[limit - 1]["id"] if len(rows) > limit else None,
            redaction="allowlist; no payloads, prompts or environment values",
        )

    return router
