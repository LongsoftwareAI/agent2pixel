"""Workspace-scoped durable console; projections never manufacture runtime outcomes."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from services.api.store import uid, now
from services.api.domain import hydrate
from services.api.company import projected_item
from services.worker.data_tools import create_source


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationInput(Input):
    workspace_id: str
    agent_id: str | None = None
    title: str = Field(min_length=1, max_length=200)


class MessageInput(Input):
    content: str = Field(min_length=1, max_length=18000)
    client_request_id: str = Field(min_length=1, max_length=128)
    workflow_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)


class SoulInput(Input):
    content: str = Field(min_length=1, max_length=20000)
    revision: int = Field(ge=1, strict=True)


class SkillInput(Input):
    package_id: str
    operation: Literal["install", "update", "remove"]


class ApplyInput(Input):
    approval_id: str


class AttachmentInput(Input):
    workspace_id: str
    name: str = Field(min_length=1, max_length=200)
    media_type: Literal["text/plain", "text/csv", "text/markdown"]
    content: str = Field(min_length=1, max_length=1024 * 1024)


DEFAULTS = dict(
    theme="dark",
    accent="blue",
    sidebar="full",
    font="medium",
    density="comfortable",
    office_enabled=True,
    start_page="overview",
    refresh="slow",
    revision=1,
)
CHOICES = dict(
    theme=["light", "dark", "system"],
    accent=["blue", "black"],
    sidebar=["full", "collapsed"],
    font=["small", "medium", "large"],
    density=["comfortable", "compact"],
    start_page=[
        "overview",
        "inbox",
        "room",
        "agents",
        "bots",
        "preferences",
        "workboard",
        "workflows",
        "schedules",
        "skills",
        "memory",
        "channels",
        "topology",
        "usage",
        "sessions",
        "logs",
        "audit",
        "settings",
        "office",
        "sources",
        "runs",
        "chat",
    ],
    refresh=["fast", "slow", "off"],
)


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def token_summary(events):
    """Keep runtime estimates separate from provider-reported and unknown usage.

    Totals describe recorded token counts only; none establish provider billing.
    Legacy events without provenance remain unknown rather than becoming estimates.
    """
    counts = {kind: 0 for kind in ("estimated", "provider", "unknown")}
    tokens = {kind: 0 for kind in counts}
    for event in events:
        payload = event.get("payload", {})
        amount = payload.get("tokens")
        valid = type(amount) is int and amount >= 0
        kind = payload.get("token_accounting", "unknown")
        if not isinstance(kind, str) or kind not in counts or not valid:
            kind = "unknown"
        counts[kind] += 1
        if valid:
            tokens[kind] += amount
    present = [kind for kind, count in counts.items() if count]
    return dict(
        requests=len(events),
        total_tokens=sum(tokens.values()),
        token_accounting=present[0] if len(present) == 1 else "mixed" if present else "unknown",
        accounting_counts=counts,
        tokens_by_accounting=tokens,
        input_tokens=None,
        output_tokens=None,
        cache_tokens=None,
        actual_cost=None,
        estimated_cost=None,
    )


def config_revision_record(agent):
    """Snapshot operator-editable configuration, never runtime status or credentials."""
    from services.api.main import AgentInput

    return dict(
        id=uid(),
        workspace_id=agent["workspace_id"],
        agent_id=agent["id"],
        revision=agent.get("agent_config_revision", 1),
        config={
            key: value for key, value in agent.items() if key in AgentInput.model_fields
        },
        created_at=now(),
    )


def create_console_router(app, start_run, run_model):
    router = APIRouter(prefix="/api/console")

    def store():
        return app.state.store

    def locked(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with store().lock:
                return fn(*args, **kwargs)

        return wrapper

    def get(kind, id, workspace_id=None):
        value = store().get(kind, id)
        if not value or (
            workspace_id is not None and value.get("workspace_id") != workspace_id
        ):
            raise HTTPException(404, kind + " not found in workspace")
        return value

    def ws(workspace_id):
        return get("workspace", workspace_id)

    def audit(workspace_id, action, target, revision=None):
        value = dict(
            id=uid(),
            workspace_id=workspace_id,
            actor="local-operator",
            action=action,
            target_id=target,
            revision=revision,
            outcome="success",
            created_at=now(),
        )
        store().put("audit", value)
        store().event(
            workspace_id, "console." + action, dict(target_id=target, revision=revision)
        )

    def capabilities(workspace_id):
        ws(workspace_id)
        return dict(
            chat=dict(
                state="healthy",
                reason="Uses configured agent workflow runtime; mock brains remain labeled",
            ),
            attachments=dict(
                state="healthy", reason="UTF-8 text, CSV and Markdown only"
            ),
            images=dict(state="unconfigured", reason="No validated image adapter"),
            stt=dict(
                state="unconfigured",
                reason="No speech-to-text adapter installed; no audio is captured or transcribed",
            ),
            schedules=dict(
                state="unconfigured",
                reason="No reviewed local scheduler observation adapter configured",
            ),
            outbound=dict(
                state="unconfigured", reason="No external messaging connector"
            ),
            observed_at=now(),
        )

    @router.get("/capabilities")
    def caps(workspace_id: str):
        return capabilities(workspace_id)

    @router.get("/conversations")
    def conversations(workspace_id: str):
        ws(workspace_id)
        return store().list("conversation", workspace_id)

    @router.post("/conversations")
    @locked
    def conversation_create(body: ConversationInput):
        ws(body.workspace_id)
        if body.agent_id:
            get("agent", body.agent_id, body.workspace_id)
        value = dict(body.model_dump(), id=uid(), created_at=now())
        store().put("conversation", value)
        audit(body.workspace_id, "conversation.created", value["id"])
        return value

    def reconcile(conversation):
        messages = store().list("console_message", conversation["workspace_id"])
        messages = [m for m in messages if m["conversation_id"] == conversation["id"]]
        for message in list(messages):
            if message["role"] != "user" or not message.get("run_id"):
                continue
            run = get("run", message["run_id"], conversation["workspace_id"])
            if run["state"] not in (
                "completed",
                "failed",
                "cancelled",
                "waiting_approval",
                "waiting_review",
            ):
                continue
            # One stable projection per input; reconcile again when a waiting run advances.
            projected = dict(
                id="console-result:" + message["id"],
                workspace_id=conversation["workspace_id"],
                conversation_id=conversation["id"],
                role="assistant" if run.get("output") else "system",
                content=run.get("output")
                or run.get("error")
                or (
                    "Run awaits human approval"
                    if run["state"] == "waiting_approval"
                    else "Run " + run["state"]
                ),
                run_id=run["id"],
                work_item_id=message["work_item_id"],
                state=run["state"],
                error=run.get("error"),
                created_at=run.get("ended_at") or message["created_at"],
                provenance="runtime",
                artifacts=run.get("artifacts", []),
            )
            store().put("console_message", projected)
        return sorted(
            [
                m
                for m in store().list("console_message", conversation["workspace_id"])
                if m["conversation_id"] == conversation["id"]
            ],
            key=lambda m: (m["created_at"], m["role"] != "user"),
        )

    @router.get("/conversations/{id}")
    @locked
    def conversation_detail(id: str, workspace_id: str):
        ws(workspace_id)
        conversation = get("conversation", id, workspace_id)
        return dict(conversation, messages=reconcile(conversation))

    @router.post("/conversations/{id}/messages")
    async def message_send(id: str, body: MessageInput, workspace_id: str):
        # No await between reservation and scheduling: same loop + Store RLock covers retries.
        with store().lock:
            ws(workspace_id)
            conversation = get("conversation", id, workspace_id)
            payload_hash = digest(body.model_dump())
            message_id = "console-message:" + digest([id, body.client_request_id])
            existing = store().get("console_message", message_id)
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise HTTPException(
                        409, "Idempotency key already used for a different payload"
                    )
                return dict(
                    message=existing,
                    run_id=existing["run_id"],
                    work_item_id=existing["work_item_id"],
                )
            source_context = []
            for attachment_id in body.attachment_ids:
                attachment = get("console_attachment", attachment_id, workspace_id)
                source = get("source", attachment["source_id"], workspace_id)
                source_context.append(
                    f"UNTRUSTED attachment {attachment['name']} (source {source['id']}):\n{source['content']}"
                )
            content = body.content + (
                "\n\n" + "\n\n".join(source_context) if source_context else ""
            )
            if len(content) > 20000:
                raise HTTPException(
                    422,
                    "Combined message and attachments exceed runtime input limit (20000 characters)",
                )
            if body.workflow_id:
                workflow = get("workflow", body.workflow_id, workspace_id)
            else:
                if not conversation["agent_id"]:
                    raise HTTPException(
                        422, "Common room requires an explicit configured workflow"
                    )
                agent = get("agent", conversation["agent_id"], workspace_id)
                workflow_id = "console-workflow:" + conversation["id"]
                workflow = store().get("workflow", workflow_id)
                if not workflow:
                    workflow = dict(
                        id=workflow_id,
                        workspace_id=workspace_id,
                        name="Chat: " + agent["name"],
                        version=1,
                        graph=dict(
                            nodes=[
                                dict(id="start", type="start"),
                                dict(id="agent", type="agent", agent_id=agent["id"]),
                                dict(id="end", type="end"),
                            ],
                            edges=[
                                dict(source="start", target="agent"),
                                dict(source="agent", target="end"),
                            ],
                        ),
                    )
                    store().put("workflow", workflow)
            if conversation["agent_id"] and conversation["agent_id"] not in [
                n.get("agent_id") for n in workflow["graph"]["nodes"]
            ]:
                raise HTTPException(
                    422, "Selected workflow does not include conversation agent"
                )
            work = dict(
                id=uid(),
                workspace_id=workspace_id,
                workflow_id=workflow["id"],
                title=body.content[:200],
                description=body.content,
                acceptance_criteria=[],
                priority="normal",
                due_at=None,
                owner_agent_id=conversation["agent_id"],
                queue_requested=False,
                run_ids=[],
                latest_run_id=None,
                reviews=[],
                brief_revision=1,
                created_at=now(),
                updated_at=now(),
            )
            message = dict(
                id=message_id,
                workspace_id=workspace_id,
                conversation_id=id,
                role="user",
                content=body.content,
                attachment_ids=body.attachment_ids,
                client_request_id=body.client_request_id,
                payload_hash=payload_hash,
                run_id=None,
                work_item_id=work["id"],
                created_at=now(),
            )
            run = start_run(
                workflow["id"], run_model(input=content), work, dispatch_message=message
            )
            audit(workspace_id, "message.dispatched", message_id)
            return dict(message=message, run_id=run["id"], work_item_id=work["id"])

    @router.get("/sessions")
    def sessions(workspace_id: str):
        ws(workspace_id)
        links = {
            m["run_id"]: m["conversation_id"]
            for m in store().list("console_message", workspace_id)
            if m.get("run_id")
        }
        return [
            dict(
                id=r["id"],
                run_id=r["id"],
                workflow_id=r["workflow_id"],
                work_item_id=r.get("work_item_id"),
                conversation_id=links.get(r["id"]),
                state=r["state"],
                started_at=r.get("started_at"),
                ended_at=r.get("ended_at"),
                agent_ids=list(r.get("agent_specs", {})),
                error=r.get("error"),
            )
            for r in store().list("run", workspace_id)
        ]

    @router.get("/inbox")
    def inbox(workspace_id: str):
        ws(workspace_id)
        result = []
        for kind in ("approval", "gate"):
            for item in store().list(kind, workspace_id):
                if item.get("state", item.get("status")) in (
                    "pending",
                    "waiting",
                    "waiting_review",
                ):
                    result.append(
                        dict(
                            item,
                            kind="approval" if kind == "approval" else "review_gate",
                        )
                    )
        for item in store().list("work_item", workspace_id):
            projection = projected_item(store(), item)
            if projection["status"] == "review":
                result.append(
                    dict(
                        id=item["id"],
                        kind="work_acceptance",
                        work_item_id=item["id"],
                        run_id=item.get("latest_run_id"),
                        title=item["title"],
                        status=projection["status"],
                        brief_revision=item.get("brief_revision", 1),
                    )
                )
        return result

    @router.get("/health")
    def health(workspace_id: str):
        ws(workspace_id)
        timestamp = now()
        items = [
            dict(
                id="sqlite",
                name="SQLite persistence",
                kind="service",
                state="healthy",
                reason="Current database query succeeded",
                observed_at=timestamp,
            ),
            dict(
                id="runtime",
                name="Local LangGraph runtime",
                kind="service",
                state="healthy",
                reason="Local runtime initialized; not a remote gateway probe",
                observed_at=timestamp,
            ),
        ]
        for agent in store().list("agent", workspace_id):
            brain = agent.get("brain", {})
            secret_ref = brain.get("secret_ref")
            provider = brain.get("provider", "mock")
            secret_names = (
                [secret_ref]
                if secret_ref
                else (
                    {
                        "openai": ["AGENTVERSE_OPENAI_API_KEY", "OPENAI_API_KEY"],
                        "deepseek": ["AGENTVERSE_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"],
                    }.get(provider, [])
                )
            )
            configured = any(bool(os.getenv(name)) for name in secret_names)
            state = (
                "healthy"
                if provider == "mock"
                else (
                    "unknown" if configured or provider == "ollama" else "unconfigured"
                )
            )
            items.append(
                dict(
                    id="provider:" + agent["id"],
                    agent_id=agent["id"],
                    name=agent["name"] + " / " + provider,
                    kind="provider",
                    state=state,
                    reason="Deterministic local mock; not live inference"
                    if provider == "mock"
                    else "Not actively probed"
                    if state == "unknown"
                    else "Missing provider secret reference",
                    secret_names=secret_names,
                    configured=configured or provider == "mock",
                    observed_at=timestamp,
                )
            )
        items.extend(
            dict(id=k, name=k, kind="capability", observed_at=timestamp, **v)
            for k, v in capabilities(workspace_id).items()
            if isinstance(v, dict) and k in ("stt", "schedules", "outbound")
        )
        return dict(items=items, observed_at=timestamp)

    @router.get("/topology")
    def topology(workspace_id: str):
        ws(workspace_id)
        nodes = [
            dict(id=workspace_id, label="Workspace", kind="workspace", state="healthy")
        ]
        edges = []
        for kind in ("agent", "workflow"):
            for value in store().list(kind, workspace_id):
                nodes.append(
                    dict(
                        id=value["id"],
                        label=value.get("name", value["id"]),
                        kind=kind,
                        state=value.get("status", "configured"),
                    )
                )
                edges.append(dict(source=workspace_id, target=value["id"]))
                if kind == "agent":
                    spec = hydrate(value)
                    brain = spec.get("brain", {})
                    provider_id = "provider:" + value["id"]
                    observed = next(
                        i
                        for i in health(workspace_id)["items"]
                        if i["id"] == provider_id
                    )
                    nodes.append(
                        dict(
                            id=provider_id,
                            label=brain.get("provider", "unknown")
                            + ": "
                            + brain.get("model", "unknown"),
                            kind="model",
                            state=observed["state"],
                            reason=observed["reason"],
                        )
                    )
                    edges.append(dict(source=value["id"], target=provider_id))
                    for binding in spec.get("skill_bindings", []):
                        skill_id = (
                            "skill:" + binding["id"] + ":" + str(binding["version"])
                        )
                        if not any(n["id"] == skill_id for n in nodes):
                            nodes.append(
                                dict(
                                    id=skill_id,
                                    label=binding["id"]
                                    + " v"
                                    + str(binding["version"]),
                                    kind="skill",
                                    state="configured",
                                )
                            )
                        edges.append(dict(source=value["id"], target=skill_id))
                    for tool in spec.get("tool_grants", []):
                        tool_id = (
                            "tool:" + tool["tool"]
                            if "tool" in tool
                            else "tool:" + tool.get("id", "")
                        )
                        if not any(n["id"] == tool_id for n in nodes):
                            nodes.append(
                                dict(
                                    id=tool_id,
                                    label=tool_id[5:],
                                    kind="tool",
                                    state="configured",
                                )
                            )
                        edges.append(
                            dict(
                                source=value["id"],
                                target=tool_id,
                                allowed=tool.get("allow", False),
                                approval_required=tool.get("approval_required", True),
                            )
                        )
                else:
                    for node in value["graph"]["nodes"]:
                        if node.get("agent_id"):
                            edges.append(
                                dict(source=value["id"], target=node["agent_id"])
                            )
        return dict(nodes=nodes, edges=edges, observed_at=now())

    @router.get("/usage")
    def usage(workspace_id: str, period: Literal["7", "30", "90", "all"] = "30"):
        ws(workspace_id)
        cutoff = (
            None
            if period == "all"
            else datetime.now(timezone.utc) - timedelta(days=int(period))
        )
        events = [
            e
            for e in store().events(workspace_id)
            if e["event_type"] == "model.completed"
            and (cutoff is None or datetime.fromisoformat(e["created_at"]) >= cutoff)
        ]
        daily, by_agent, by_model = {}, {}, {}
        for event in events:
            run = store().get("run", event.get("run_id")) or {}
            spec = run.get("agent_specs", {}).get(event.get("agent_id"), {})
            model = spec.get("brain", {}).get("model", "unknown")
            for target, key in (
                (daily, event["created_at"][:10]),
                (by_agent, event.get("agent_id") or "unknown"),
                (by_model, model),
            ):
                target.setdefault(key, []).append(event)
        daily = {key: dict(id=key, **token_summary(value)) for key, value in daily.items()}
        by_agent = {key: dict(id=key, **token_summary(value)) for key, value in by_agent.items()}
        by_model = {key: dict(id=key, **token_summary(value)) for key, value in by_model.items()}
        totals = token_summary(events)
        return dict(
            daily=[dict(v, date=k) for k, v in sorted(daily.items())],
            by_agent=[dict(v, agent_id=k) for k, v in by_agent.items()],
            by_model=[dict(v, model=k) for k, v in by_model.items()],
            totals=totals,
            pricing=[],
            accounting=totals["token_accounting"],
            period=period,
            timezone="UTC",
            observed_at=now(),
        )

    @router.get("/overview")
    def overview(workspace_id: str):
        ws(workspace_id)
        agents = store().list("agent", workspace_id)
        runs = store().list("run", workspace_id)
        work = [
            projected_item(store(), w) for w in store().list("work_item", workspace_id)
        ]
        active = [
            r
            for r in runs
            if r["state"] in ("queued", "running", "waiting_approval", "waiting_review")
        ]
        busy_ids = {a for r in active for a in r.get("agent_specs", {})}
        return dict(
            agents=dict(total=len(agents), busy=len(busy_ids)),
            work=dict(
                total=len(work),
                pending_review=sum(w["status"] == "review" for w in work),
                completed=sum(w["status"] == "done" for w in work),
            ),
            runs=dict(total=len(runs), active=len(active)),
            usage=usage(workspace_id)["totals"],
            activity=[
                {
                    k: e.get(k)
                    for k in (
                        "id",
                        "event_type",
                        "run_id",
                        "agent_id",
                        "created_at",
                        "seq",
                    )
                }
                for e in store().events(workspace_id)[-20:][::-1]
            ],
            services=health(workspace_id)["items"],
            observed_at=now(),
        )

    @router.get("/schedules")
    def schedules(workspace_id: str):
        ws(workspace_id)
        return dict(
            items=store().list("schedule_observation", workspace_id),
            capability=capabilities(workspace_id)["schedules"],
            observed_at=now(),
        )

    @router.get("/agents/{id}/soul")
    def soul(id: str, workspace_id: str):
        agent = get("agent", id, workspace_id)
        return dict(
            agent_id=id,
            content=agent["system_prompt"],
            revision=agent.get("soul_revision", 1),
            updated_at=agent.get("soul_updated_at"),
        )

    @router.patch("/agents/{id}/soul")
    @locked
    def soul_patch(id: str, body: SoulInput, workspace_id: str):
        agent = get("agent", id, workspace_id)
        revision = agent.get("soul_revision", 1)
        if body.revision != revision:
            raise HTTPException(409, "SOUL revision changed; reload before editing")
        prior = dict(
            id=uid(),
            workspace_id=workspace_id,
            agent_id=id,
            content=agent["system_prompt"],
            revision=revision,
            created_at=now(),
        )
        config_prior = config_revision_record(agent)
        agent.update(
            system_prompt=body.content,
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
        audit(workspace_id, "soul.updated", id, revision + 1)
        return soul(id, workspace_id)

    def packages():
        # Code-owned declarative versions; no dynamic executable installation.
        versions = []
        for version, suffix in ((1, "-v1"), (2, "")):
            content = "Preserve evidence, state assumptions and report unexecuted checks honestly."
            if version == 2:
                content += " Distinguish observed facts from estimates and attach source identifiers to conclusions."
            package = dict(
                id="console-evidence" + suffix,
                registry_id="console-evidence",
                version=version,
                license="MIT",
                description="Reviewed local evidence-writing instructions v"
                + str(version),
                dependencies=[],
                tool_grants=[],
                instructions=content,
                name="Evidence-based work",
            )
            versions.append(dict(package, sha256=digest(package)))
        return versions

    @router.get("/skills")
    def skills(workspace_id: str, agent_id: str | None = None):
        ws(workspace_id)
        agents = (
            [get("agent", agent_id, workspace_id)]
            if agent_id
            else store().list("agent", workspace_id)
        )
        return dict(
            packages=packages(),
            bindings=[
                dict(
                    agent_id=a["id"],
                    package_id=b["id"],
                    version=b["version"],
                    state="active_for_future_runs",
                )
                for a in agents
                for b in hydrate(a)["skill_bindings"]
            ],
        )

    @router.post("/agents/{id}/skills/preview")
    @locked
    def skill_preview(id: str, body: SkillInput, workspace_id: str):
        agent = get("agent", id, workspace_id)
        manifest = next((p for p in packages() if p["id"] == body.package_id), None)
        if not manifest:
            raise HTTPException(
                422, "Package is not in the code-reviewed local catalog"
            )
        before = hydrate(agent)["skill_bindings"]
        registry_id = manifest.get("registry_id", manifest["id"])
        installed = next((b for b in before if b["id"] == registry_id), None)
        if body.operation == "install" and installed:
            raise HTTPException(409, "Package already installed")
        if body.operation != "install" and not installed:
            raise HTTPException(409, "Package is not installed")
        if body.operation == "update" and installed["version"] == manifest["version"]:
            raise HTTPException(409, "Package is already current")
        after = [b for b in before if b["id"] != registry_id]
        if body.operation != "remove":
            after.append(dict(id=registry_id, version=manifest["version"]))
        value = dict(
            id=uid(),
            workspace_id=workspace_id,
            agent_id=id,
            operation=body.operation,
            manifest=manifest,
            before=before,
            after=after,
            before_hash=digest(before),
            status="pending",
            created_at=now(),
        )
        store().put("skill_approval", value)
        audit(workspace_id, "skill.previewed", value["id"])
        return dict(
            approval_id=value["id"],
            manifest=manifest,
            diff=dict(before=before, after=after),
            activation="Future runs only; existing snapshots unchanged",
        )

    @router.post("/agents/{id}/skills/apply")
    @locked
    def skill_apply(id: str, body: ApplyInput, workspace_id: str):
        agent = get("agent", id, workspace_id)
        approval = get("skill_approval", body.approval_id, workspace_id)
        if approval["agent_id"] != id:
            raise HTTPException(404, "Approval not found for agent")
        if approval["status"] == "applied":
            if hydrate(agent)["skill_bindings"] != approval["after"]:
                raise HTTPException(
                    409, "Historical approval was superseded; preview current bindings"
                )
            return dict(
                approval_id=approval["id"],
                state="applied",
                activation="active_for_future_runs",
                bindings=approval["after"],
            )
        if digest(hydrate(agent)["skill_bindings"]) != approval["before_hash"]:
            raise HTTPException(409, "Agent bindings changed since preview")
        manifest = next(
            (p for p in packages() if p["id"] == approval["manifest"]["id"]), None
        )
        if manifest != approval["manifest"]:
            raise HTTPException(409, "Reviewed manifest changed")
        config_prior = config_revision_record(agent)
        agent["skill_bindings"] = approval["after"]
        agent["agent_config_revision"] = agent.get("agent_config_revision", 1) + 1
        approval.update(status="applied", applied_at=now())
        records = [
            ("agent", agent),
            ("agent_config_history", config_prior),
            ("skill_approval", approval),
            (
                "skill_activation",
                dict(
                    id=uid(),
                    workspace_id=workspace_id,
                    agent_id=id,
                    before=approval["before"],
                    after=approval["after"],
                    manifest_hash=manifest["sha256"],
                    created_at=now(),
                    state="active_for_future_runs",
                ),
            ),
        ]
        if approval["operation"] != "remove":
            skill = dict(
                id=manifest.get("registry_id", manifest["id"]),
                version=manifest["version"],
                name=manifest["name"],
                instructions=manifest["instructions"],
                allowed_tools=[],
            )
            records += [
                ("skill", skill),
                (
                    "skill_version",
                    dict(
                        skill,
                        id="skill:" + skill["id"] + ":" + str(skill["version"]),
                        registry_id=skill["id"],
                    ),
                ),
            ]
        store().put_many(records)
        audit(workspace_id, "skill.applied", id)
        return dict(
            approval_id=approval["id"],
            state="applied",
            activation="active_for_future_runs",
            bindings=approval["after"],
        )

    @router.get("/preferences")
    def preferences(workspace_id: str):
        ws(workspace_id)
        record = store().get("console_preferences", "preferences:" + workspace_id)
        return (
            {k: record.get(k, v) for k, v in DEFAULTS.items()}
            if record
            else dict(DEFAULTS)
        )

    @router.patch("/preferences")
    @locked
    def preferences_patch(body: dict, workspace_id: str):
        value = preferences(workspace_id)
        if set(body) - set(DEFAULTS):
            raise HTTPException(422, "Unknown preference")
        if "revision" not in body:
            raise HTTPException(422, "Preferences revision is required")
        if type(body["revision"]) is not int or body["revision"] != value["revision"]:
            raise HTTPException(409, "Preferences revision changed")
        for key, item in body.items():
            if key in CHOICES and item not in CHOICES[key]:
                raise HTTPException(422, "Invalid " + key)
            if key == "office_enabled" and type(item) is not bool:
                raise HTTPException(422, "office_enabled must be boolean")
        value.update(body)
        value["revision"] += 1
        store().put(
            "console_preferences",
            dict(value, id="preferences:" + workspace_id, workspace_id=workspace_id),
        )
        audit(workspace_id, "preferences.updated", workspace_id, value["revision"])
        return value

    @router.get("/logs")
    def logs(
        workspace_id: str,
        kind: Literal["system", "audit"] = "system",
        limit: int = 100,
        before: str | None = None,
    ):
        ws(workspace_id)
        if not 1 <= limit <= 200:
            raise HTTPException(422, "Limit must be 1..200")
        records = (
            store().list("audit", workspace_id)
            if kind == "audit"
            else store().events(workspace_id)
        )
        records = sorted(
            records, key=lambda r: (r.get("created_at", ""), r["id"]), reverse=True
        )
        if before:
            index = next(
                (i for i, row in enumerate(records) if row["id"] == before), None
            )
            if index is None:
                raise HTTPException(422, "Invalid workspace-scoped cursor")
            records = records[index + 1 :]
        # Allowlist projection: arbitrary event payloads / model prompts / credential text never leave logs.
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
            items=[{k: row[k] for k in fields if k in row} for row in records[:limit]],
            next_cursor=records[limit - 1]["id"] if len(records) > limit else None,
        )

    @router.post("/attachments")
    @locked
    def attachment_create(body: AttachmentInput):
        ws(body.workspace_id)
        if (
            "\\" in body.name
            or "/" in body.name
            or body.name in (".", "..")
            or "\x00" in body.name
        ):
            raise HTTPException(422, "Attachment requires a plain filename")
        if len(body.content.encode("utf-8")) > 1024 * 1024 or "\x00" in body.content:
            raise HTTPException(
                422, "Attachment exceeds UTF-8 limit or contains binary content"
            )
        try:
            source = create_source(
                store(), body.workspace_id, body.name, body.content, body.media_type
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        value = dict(
            id=uid(),
            workspace_id=body.workspace_id,
            source_id=source["id"],
            name=body.name,
            media_type=body.media_type,
            size=len(body.content.encode("utf-8")),
            sha256=hashlib.sha256(body.content.encode("utf-8")).hexdigest(),
            created_at=now(),
        )
        store().put("console_attachment", value)
        audit(body.workspace_id, "attachment.created", value["id"])
        return value

    return router
