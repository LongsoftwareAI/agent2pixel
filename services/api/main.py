"""AgentVerse localhost API. Run from repository root with uvicorn."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
from services.api.store import Store, uid, now
from services.api.policy import safe_document, validate_brain
from services.worker.runtime import Runtime, validate_graph
from services.worker.adapters import run_brain
from services.api.domain import (
    hydrate,
    seed_registry,
    validate_spec,
    snapshot_spec,
    engines,
    TOOLS,
)

ASSETS = [
    dict(
        id=id, name=name, kind=kind, license="CC0-1.0", author="AgentVerse contributors"
    )
    for id, name, kind in [
        ("desk", "Desk", "furniture"),
        ("chair", "Chair", "furniture"),
        ("plant", "Plant", "furniture"),
        ("bookshelf", "Bookshelf", "furniture"),
        ("sofa", "Sofa", "furniture"),
    ]
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspaceInput(Input):
    name: str = Field(min_length=1, max_length=100)


class AgentInput(Input):
    workspace_id: str
    name: str = Field(min_length=1, max_length=100)
    role: str = "Developer"
    system_prompt: str = "Complete the assigned task faithfully."
    brain: dict = Field(
        default_factory=lambda: dict(
            provider="mock", model="deterministic", endpoint=None, secret_ref=None
        )
    )
    skin: str = "blue"
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    memory_policy: str = "workspace"
    workstation: dict = Field(default_factory=lambda: dict(x=3, y=3))
    enabled: bool = True
    execution: dict = Field(default_factory=lambda: dict(engine="langchain", version=1))
    role_config: dict | None = None
    skill_bindings: list[dict] = Field(default_factory=list)
    tool_grants: list[dict] | None = None
    memory_config: dict | None = None
    appearance: dict | None = None

    @field_validator("workstation")
    @classmethod
    def valid_workstation(cls, value):
        if (
            type(value.get("x")) is not int
            or type(value.get("y")) is not int
            or not 0 <= value["x"] < 20
            or not 0 <= value["y"] < 14
        ):
            raise ValueError("Workstation must be an in-bounds integer tile")
        return value


class WorkflowInput(Input):
    workspace_id: str
    name: str = Field(min_length=1, max_length=100)
    graph: dict


class RunInput(Input):
    input: str = Field(min_length=1, max_length=20000)
    max_steps: int = Field(default=32, ge=1, le=128)
    token_budget: int = Field(default=12000, ge=1, le=100000)
    retry_limit: int = Field(default=1, ge=0, le=3)
    actions: list[dict] = Field(default_factory=list, max_length=12)


class LayoutInput(Input):
    furniture: list[dict]
    assignments: dict


class MemoryInput(Input):
    workspace_id: str
    content: str = Field(min_length=1, max_length=20000)
    kind: str = "note"
    agent_id: str | None = None
    scope: str = "workspace"
    source_id: str | None = None


class ProviderInput(Input):
    provider: str
    model: str
    endpoint: str | None = None


def create_app(data_dir=None):
    @asynccontextmanager
    async def lifespan(app):
        store = Store(data_dir or os.getenv("AGENTVERSE_DATA_DIR", "var/agentverse"))
        app.state.store = store
        app.state.runtime = Runtime(store)
        if not store.list("workspace"):
            for name in ("Coding", "Research"):
                ws = workspace_create(store, name)
                agents = []
                for i, role in enumerate(("Planner", "Developer", "Reviewer")):
                    value = AgentInput(
                        workspace_id=ws["id"],
                        name=role,
                        role=role,
                        skin=("blue", "purple", "green")[i],
                        workstation={"x": 3 + i * 5, "y": 5},
                    ).model_dump()
                    value.update(id=uid(), status="idle")
                    if role == "Reviewer":
                        value["tools"] = ["documents.list", "documents.read"]
                        value["skill_bindings"] = [{"id": "code-report", "version": 1}]
                    store.put("agent", value)
                    agents.append(value)
                room = store.list("room", ws["id"])[0]
                room["assignments"] = {a["id"]: a["workstation"] for a in agents}
                room["furniture"] = [
                    dict(id=uid(), asset_id="desk", x=3 + i * 5, y=4, rotation=0)
                    for i in range(3)
                ]
                room["furniture"] += [
                    dict(id=uid(), asset_id=asset, x=x, y=y, rotation=0)
                    for asset, x, y in [
                        ("chair", 3, 6),
                        ("chair", 8, 6),
                        ("chair", 13, 6),
                        ("plant", 1, 2),
                        ("plant", 18, 2),
                        ("plant", 18, 11),
                        ("bookshelf", 2, 1),
                        ("bookshelf", 3, 1),
                        ("bookshelf", 4, 1),
                        ("sofa", 15, 10),
                        ("sofa", 16, 10),
                        ("plant", 14, 10),
                    ]
                ]
                store.put("room", room)
                nodes = (
                    [dict(id="start", type="start")]
                    + [
                        dict(id=a["role"].lower(), type="agent", agent_id=a["id"])
                        for a in agents
                    ]
                    + [dict(id="end", type="end")]
                )
                graph = {
                    "nodes": nodes,
                    "edges": [
                        {"source": a["id"], "target": b["id"]}
                        for a, b in zip(nodes, nodes[1:])
                    ],
                }
                store.put(
                    "workflow",
                    dict(
                        id=uid(),
                        workspace_id=ws["id"],
                        name="Planner → Developer → Reviewer",
                        version=1,
                        graph=graph,
                    ),
                )
        seed_registry(store)
        yield
        for run_id, job in list(app.state.runtime.jobs.items()):
            if store.get("run", run_id)["state"] != "waiting_approval":
                job.cancel()
        if app.state.runtime.jobs:
            await asyncio.gather(
                *list(app.state.runtime.jobs.values()), return_exceptions=True
            )
        await app.state.runtime.close()
        store.db.close()

    app = FastAPI(title="AgentVerse localhost", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def local_origin(request, call_next):
        origin = request.headers.get("origin")
        if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
            try:
                parsed = urlparse(origin)
                valid = (
                    parsed.scheme == "http"
                    and parsed.hostname in ("localhost", "127.0.0.1", "::1")
                    and not parsed.username
                    and not parsed.password
                    and not parsed.path
                    and not parsed.query
                    and not parsed.fragment
                    and (parsed.port is None or 1 <= parsed.port <= 65535)
                )
            except ValueError:
                valid = False
            if not valid:
                return JSONResponse(
                    {"detail": "Only localhost origins may mutate state"},
                    status_code=403,
                )
        return await call_next(request)

    def store():
        return app.state.store

    def get(kind, id):
        value = store().get(kind, id)
        if not value:
            raise HTTPException(404, f"{kind} not found")
        return value

    def workspace(id):
        return get("workspace", id)

    @app.get("/health")
    def health():
        return {"status": "ok", "schema_version": 1}

    @app.get("/api/workspaces")
    def workspaces():
        return store().list("workspace")

    @app.post("/api/workspaces")
    def new_workspace(body: WorkspaceInput):
        return workspace_create(store(), body.name)

    @app.get("/api/bootstrap")
    def bootstrap(workspace_id: str):
        workspace(workspace_id)
        return dict(
            workspaces=workspaces(),
            agents=store().list("agent", workspace_id),
            workflows=store().list("workflow", workspace_id),
            room=store().list("room", workspace_id)[0],
            assets=ASSETS,
            runs=store().list("run", workspace_id),
        )

    @app.get("/api/agents")
    def agents(workspace_id: str):
        workspace(workspace_id)
        return store().list("agent", workspace_id)

    @app.post("/api/agents")
    def new_agent(body: AgentInput):
        value = normalize_agent(body.model_dump())
        workspace(body.workspace_id)
        validate_brain(value["brain"])
        validate_spec(value, store())
        value.update(id=uid(), status="idle")
        store().put("agent", value)
        store().event(
            body.workspace_id, "agent.created", {"name": body.name}, agent=value["id"]
        )
        return value

    @app.get("/api/agents/{id}")
    def agent(id: str):
        return get("agent", id)

    @app.patch("/api/agents/{id}")
    def patch_agent(id: str, body: dict):
        with store().lock:
            return patch_agent_locked(id, body)

    def patch_agent_locked(id, body):
        value = get("agent", id)
        if "workspace_id" in body and body["workspace_id"] != value["workspace_id"]:
            raise HTTPException(403, "Agent workspace is immutable")
        if set(body) - set(AgentInput.model_fields):
            raise HTTPException(422, "Unknown agent fields")
        try:
            merged = AgentInput(
                **{
                    **{k: v for k, v in value.items() if k in AgentInput.model_fields},
                    **body,
                }
            ).model_dump()
        except ValidationError:
            raise HTTPException(422, "Invalid agent fields") from None
        if "tools" in body and "tool_grants" not in body:
            merged["tool_grants"] = [
                dict(id=t, allow=True, approval_required=False)
                for t in merged["tools"]
                if any(x["id"] == t for x in TOOLS)
            ]
        if "memory_policy" in body and "memory_config" not in body:
            merged["memory_config"] = {"scope": merged["memory_policy"]}
        merged = normalize_agent(merged)
        validate_brain(merged["brain"])
        validate_spec(merged, store())
        merged = {**value, **merged, "id": id, "status": value["status"]}
        records = []
        if any(merged.get(key) != value.get(key) for key in AgentInput.model_fields):
            from services.api.console import config_revision_record

            records.append(("agent_config_history", config_revision_record(value)))
            merged["agent_config_revision"] = value.get("agent_config_revision", 1) + 1
        if merged["system_prompt"] != value["system_prompt"]:
            revision = value.get("soul_revision", 1)
            records.append(
                (
                    "agent_document_revision",
                    dict(
                        id=uid(),
                        workspace_id=value["workspace_id"],
                        agent_id=id,
                        content=value["system_prompt"],
                        revision=revision,
                        created_at=now(),
                    ),
                )
            )
            merged.update(soul_revision=revision + 1, soul_updated_at=now())
        records.append(("agent", merged))
        store().put_many(records)
        store().event(
            value["workspace_id"], "agent.updated", {"name": merged["name"]}, agent=id
        )
        return merged

    @app.delete("/api/agents/{id}")
    def delete_agent(id: str):
        value = get("agent", id)
        value["enabled"] = False
        store().put("agent", value)
        store().event(value["workspace_id"], "agent.disabled", agent=id)
        return value

    @app.get("/api/workflows")
    def workflows(workspace_id: str):
        workspace(workspace_id)
        return store().list("workflow", workspace_id)

    @app.post("/api/workflows")
    def new_workflow(body: WorkflowInput):
        workspace(body.workspace_id)
        errors = validate_graph(body.graph, store(), body.workspace_id)
        if errors:
            raise HTTPException(400, "; ".join(errors))
        return store().put("workflow", dict(id=uid(), version=1, **body.model_dump()))

    @app.post("/api/workflows/{id}/validate")
    def validate(id: str):
        value = get("workflow", id)
        errors = validate_graph(value["graph"], store(), value["workspace_id"])
        return dict(valid=not errors, errors=errors)

    def start_run(id, body, work_item=None, dispatch_message=None):
        with store().lock:
            return start_run_locked(id, body, work_item, dispatch_message)

    def start_run_locked(id, body, work_item=None, dispatch_message=None):
        workflow = get("workflow", id)
        errors = validate_graph(workflow["graph"], store(), workflow["workspace_id"])
        if errors:
            raise HTTPException(400, "; ".join(errors))
        if any(
            r["state"] in ("queued", "running", "waiting_approval")
            for r in store().list("run", workflow["workspace_id"])
        ):
            raise HTTPException(409, "Workspace already has an active run")
        if len(app.state.runtime.jobs) >= 16:
            raise HTTPException(409, "Run queue full")
        value = dict(
            id=uid(),
            workflow_id=id,
            workspace_id=workflow["workspace_id"],
            state="queued",
            output="",
            error=None,
            started_at=None,
            ended_at=None,
            tasks=[],
            graph=workflow["graph"],
            **body.model_dump(),
        )
        for action in value["actions"]:
            if (
                set(action) != {"agent_id", "tool", "payload"}
                or not isinstance(action["payload"], dict)
                or action["tool"] not in ("artifacts.write_python", "tests.run_pytest")
            ):
                raise HTTPException(422, "Invalid approved tool action")
            actor = get("agent", action["agent_id"])
            if actor["workspace_id"] != value["workspace_id"] or actor["id"] not in [
                n.get("agent_id") for n in value["graph"]["nodes"]
            ]:
                raise HTTPException(403, "Action agent outside workflow")
        value["agent_specs"] = {
            n["agent_id"]: snapshot_spec(get("agent", n["agent_id"]), store())
            for n in value["graph"]["nodes"]
            if n["type"] in ("agent", "tool")
        }
        value.update(
            artifacts=[],
            engine_version="langgraph-1.2.16",
            checkpoint={
                "engine": "langgraph",
                "thread_id": value["workspace_id"] + ":" + value["id"],
                "resumable": True,
            },
            token_spent=0,
        )
        if work_item:
            value["work_item_id"] = work_item["id"]
            value["brief_revision"] = work_item.get("brief_revision", 1)
            value["brief_snapshot"] = {
                key: work_item[key]
                for key in ("title", "description", "acceptance_criteria")
            }
            work_item = dict(
                work_item,
                latest_run_id=value["id"],
                run_ids=work_item["run_ids"] + [value["id"]],
                updated_at=now(),
            )
            records = [("run", value), ("work_item", work_item)]
            if dispatch_message is not None:
                dispatch_message["run_id"] = value["id"]
                records.append(("console_message", dispatch_message))
            store().put_many(records)
        else:
            store().put("run", value)
        app.state.runtime.schedule(value)
        return value

    @app.post("/api/workflows/{id}/runs")
    async def new_run(id: str, body: RunInput):
        return start_run(id, body)

    @app.get("/api/runs")
    def runs(workspace_id: str):
        workspace(workspace_id)
        return store().list("run", workspace_id)

    @app.get("/api/runs/{id}")
    def run(id: str):
        return get("run", id)

    @app.post("/api/runs/{id}/cancel")
    async def cancel(id: str):
        value = get("run", id)
        if value["state"] in ("completed", "failed", "cancelled"):
            raise HTTPException(409, "Run is already terminal")
        value.update(state="cancelled", ended_at=now())
        value.get("checkpoint", {})["resumable"] = False
        if id not in app.state.runtime.jobs:
            for task in value["tasks"]:
                if task["state"] in ("queued", "running"):
                    task["state"] = "cancelled"
                    store().event(
                        value["workspace_id"],
                        "task.cancelled",
                        {"task_id": task["id"]},
                        id,
                        task["agent_id"],
                    )
                    actor = get("agent", task["agent_id"])
                    actor["status"] = "idle"
                    store().put("agent", actor)
            store().event(value["workspace_id"], "workflow.cancelled", run=id)
        store().put("run", value)
        app.state.runtime.cancel(id)
        return value

    @app.post("/api/runs/{id}/retry")
    async def retry(id: str):
        value = get("run", id)
        if value["state"] not in ("failed", "cancelled"):
            raise HTTPException(409, "Only failed or cancelled runs may retry")
        return start_run(
            value["workflow_id"],
            RunInput(**{k: value[k] for k in RunInput.model_fields}),
        )

    @app.get("/api/runs/{id}/messages")
    def messages(id: str):
        value = get("run", id)
        return [
            m
            for m in store().list("message", value["workspace_id"])
            if m["run_id"] == id
        ]

    @app.get("/api/runs/{id}/events")
    def run_events(id: str):
        get("run", id)
        return store().events(run=id)

    @app.get("/api/events")
    def events(workspace_id: str, after: int = 0):
        workspace(workspace_id)
        return store().events(workspace=workspace_id, after=after)

    @app.websocket("/ws/workspaces/{id}/events")
    async def websocket(websocket: WebSocket, id: str, after: int = 0):
        origin = websocket.headers.get("origin")
        if origin and origin not in ("http://localhost:3000", "http://127.0.0.1:3000"):
            await websocket.close(code=1008)
            return
        if not store().get("workspace", id):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                for value in store().events(workspace=id, after=after):
                    await websocket.send_json(value)
                    after = value["seq"]
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.15)
                except asyncio.TimeoutError:
                    pass
        except WebSocketDisconnect:
            pass

    @app.get("/api/assets")
    def assets():
        return ASSETS

    @app.get("/api/rooms/{id}/layout")
    def room(id: str):
        return get("room", id)

    @app.put("/api/rooms/{id}/layout")
    def layout(id: str, body: LayoutInput):
        value = get("room", id)
        occupied = set()
        ids = set()

        def position(item):
            if not isinstance(item, dict):
                raise HTTPException(400, "Tile must be an object")
            x, y = item.get("x"), item.get("y")
            if type(x) != int or type(y) != int or not 0 <= x < 20 or not 0 <= y < 14:
                raise HTTPException(400, "Tile out of bounds")
            if (x, y) in occupied:
                raise HTTPException(409, "Tile collision")
            occupied.add((x, y))

        for item in body.furniture:
            if item.get("asset_id") not in tuple(a["id"] for a in ASSETS):
                raise HTTPException(400, "Unknown asset")
            if (
                not isinstance(item.get("id"), str)
                or not item["id"]
                or item["id"] in ids
            ):
                raise HTTPException(400, "Duplicate or missing furniture id")
            ids.add(item["id"])
            position(item)
            if item.get("rotation", 0) not in (0, 90, 180, 270):
                raise HTTPException(400, "Invalid rotation")
        for agent_id, item in body.assignments.items():
            if get("agent", agent_id)["workspace_id"] != value["workspace_id"]:
                raise HTTPException(403, "Agent outside room workspace")
            position(item)
        value.update(body.model_dump())
        store().put("room", value)
        store().event(value["workspace_id"], "room.layout.updated", {"room_id": id})
        return value

    @app.get("/api/memories")
    def memories(
        workspace_id: str, scope: str = "workspace", agent_id: str | None = None
    ):
        workspace(workspace_id)
        if scope not in ("workspace", "agent"):
            raise HTTPException(422, "Invalid memory scope")
        if scope == "agent" and (
            not agent_id or get("agent", agent_id)["workspace_id"] != workspace_id
        ):
            raise HTTPException(403, "Agent namespace required")
        return [
            m
            for m in store().list("memory", workspace_id)
            if not m.get("deleted_at")
            and (
                m.get("agent_id") == agent_id
                if scope == "agent"
                else not m.get("agent_id")
            )
        ]

    @app.post("/api/memories")
    def memory(body: MemoryInput):
        workspace(body.workspace_id)
        if body.agent_id and "scope" not in body.model_fields_set:
            body.scope = "agent"
        if body.scope not in ("agent", "workspace"):
            raise HTTPException(422, "Invalid memory scope")
        if body.scope == "agent" and not body.agent_id:
            raise HTTPException(422, "Agent scope requires owner")
        if (
            body.agent_id
            and get("agent", body.agent_id)["workspace_id"] != body.workspace_id
        ):
            raise HTTPException(403, "Agent outside workspace")
        if body.agent_id and body.scope != "agent":
            raise HTTPException(422, "Agent-owned memory requires agent scope")
        if body.source_id:
            source = get("source", body.source_id)
            if source["workspace_id"] != body.workspace_id:
                raise HTTPException(403, "Source outside workspace")
        provenance = (
            {"source_id": source["id"], "sha256": source["sha256"]}
            if body.source_id
            else None
        )
        return store().put(
            "memory",
            dict(
                id=uid(), created_at=now(), provenance=provenance, **body.model_dump()
            ),
        )

    @app.get("/api/documents")
    def documents(workspace_id: str):
        root = Path(workspace(workspace_id)["root_path"])
        result = []
        for path in root.rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and path.resolve().is_relative_to(root)
            ):
                result.append(
                    dict(path=str(path.relative_to(root)), size=path.stat().st_size)
                )
        return result[:1000]

    @app.get("/api/documents/content")
    def document(workspace_id: str, path: str):
        target = safe_document(workspace(workspace_id)["root_path"], path)
        try:
            content = target.read_text()
        except UnicodeError:
            raise HTTPException(400, "Document is not UTF-8 text")
        return dict(path=path, content=content)

    @app.get("/api/settings")
    def settings():
        return dict(
            providers=[
                dict(provider="mock", ready=True),
                dict(
                    provider="openai",
                    ready=bool(
                        os.getenv("OPENAI_API_KEY")
                        or os.getenv("AGENTVERSE_OPENAI_API_KEY")
                    ),
                ),
                dict(
                    provider="ollama",
                    ready=False,
                    message="Test local model connection",
                ),
            ],
            policy=dict(
                shell=False,
                file_write=False,
                external_tools=False,
                read_only_tools=["documents.list", "documents.read", "memory.read"],
            ),
            data_dir=str(store().root),
        )

    @app.post("/api/providers/test")
    async def provider_test(body: ProviderInput):
        brain = body.model_dump()
        brain["secret_ref"] = (
            "AGENTVERSE_OPENAI_API_KEY"
            if os.getenv("AGENTVERSE_OPENAI_API_KEY")
            else "OPENAI_API_KEY"
        )
        validate_brain(brain)
        try:
            await run_brain(
                dict(brain=brain, role="Test", system_prompt="Reply briefly"),
                "Connection check",
                128,
            )
            return dict(ok=True, message="Provider connection succeeded")
        except ValueError as exc:
            return dict(ok=False, message=str(exc))

    @app.get("/api/catalog")
    def catalog():
        return dict(
            roles=[v for v in store().list("role") if not v.get("archived")],
            skills=[v for v in store().list("skill") if not v.get("archived")],
            tools=TOOLS,
            engines=engines(),
        )

    def registry_save(kind, body, id=None):
        allowed = (
            {"id", "name", "version", "instructions", "allowed_tools"}
            if kind == "skill"
            else {
                "id",
                "name",
                "version",
                "instructions",
                "responsibilities",
                "output_schema",
            }
        )
        if set(body) - allowed:
            raise HTTPException(422, "Unknown registry fields")
        previous = get(kind, id) if id else None
        value = {**(previous or {}), **body}
        value["id"] = id or body.get("id") or uid()
        if not isinstance(value["id"], str) or not 1 <= len(value["id"]) <= 128:
            raise HTTPException(422, "Invalid registry id")
        occupied = store().resource_kind(value["id"])
        if occupied and occupied != kind:
            raise HTTPException(409, "Resource identity exists")
        if (
            not isinstance(value.get("name"), str)
            or not value["name"]
            or not isinstance(value.get("instructions"), str)
            or not value["instructions"]
        ):
            raise HTTPException(422, "Registry requires name/instructions")
        if previous:
            value["version"] = previous["version"] + 1
        else:
            if store().get(kind, value["id"]):
                raise HTTPException(409, "Registry id exists")
            value.setdefault("version", 1)
        if type(value["version"]) is not int or value["version"] < 1:
            raise HTTPException(422, "Invalid version")
        if kind == "skill":
            value.setdefault("allowed_tools", [])
            if not isinstance(value["allowed_tools"], list) or any(
                t not in [x["id"] for x in TOOLS] for t in value["allowed_tools"]
            ):
                raise HTTPException(422, "Unknown skill tools")
        else:
            value.setdefault("responsibilities", [])
            value.setdefault("output_schema", None)
            validate_spec(
                hydrate(
                    {
                        "role_config": {
                            k: v
                            for k, v in value.items()
                            if k
                            in (
                                "id",
                                "version",
                                "instructions",
                                "responsibilities",
                                "output_schema",
                            )
                        }
                    }
                ),
                store(),
            )
        store().put(
            kind + "_version",
            dict(
                value,
                id=kind + ":" + value["id"] + ":" + str(value["version"]),
                registry_id=value["id"],
            ),
        )
        return store().put(kind, value)

    @app.post("/api/skills")
    def create_skill(body: dict):
        return registry_save("skill", body)

    @app.patch("/api/skills/{id}")
    def update_skill(id: str, body: dict):
        return registry_save("skill", body, id)

    @app.post("/api/roles")
    def create_role(body: dict):
        return registry_save("role", body)

    @app.patch("/api/roles/{id}")
    def update_role(id: str, body: dict):
        return registry_save("role", body, id)

    @app.get("/api/skills")
    def skills():
        return [v for v in store().list("skill") if not v.get("archived")]

    @app.get("/api/skills/{id}")
    def skill(id: str):
        return get("skill", id)

    @app.get("/api/roles")
    def roles():
        return [v for v in store().list("role") if not v.get("archived")]

    @app.get("/api/roles/{id}")
    def role(id: str):
        return get("role", id)

    def archive(kind, id):
        value = get(kind, id)
        value["archived"] = True
        return store().put(kind, value)

    @app.delete("/api/skills/{id}")
    def delete_skill(id: str):
        return archive("skill", id)

    @app.delete("/api/roles/{id}")
    def delete_role(id: str):
        return archive("role", id)

    @app.get("/api/runs/{id}/approvals")
    def approvals(id: str):
        value = get("run", id)
        return [
            a
            for a in store().list("approval", value["workspace_id"])
            if a["run_id"] == id
        ]

    @app.post("/api/approvals/{id}/decision")
    async def decision(id: str, body: dict):
        from datetime import datetime, timezone

        approval = get("approval", id)
        value = get("run", approval["run_id"])
        if body not in ({"decision": "approved"}, {"decision": "denied"}):
            raise HTTPException(422, "Invalid decision")
        if approval["status"] != "pending" or value["state"] != "waiting_approval":
            raise HTTPException(409, "Approval is not pending")
        if datetime.fromisoformat(approval["expires_at"]) < datetime.now(timezone.utc):
            raise HTTPException(409, "Approval expired")
        approval["status"] = body["decision"]
        store().put("approval", approval)
        store().event(
            value["workspace_id"],
            "approval.decided",
            {"approval_id": id, "decision": body["decision"]},
            value["id"],
            approval["agent_id"],
        )
        job = app.state.runtime.jobs.get(value["id"])
        if job:
            await asyncio.shield(job)
        value = store().get("run", value["id"])
        value["state"] = "queued"
        store().put("run", value)
        app.state.runtime.schedule(value, resume=True)
        return approval

    @app.get("/api/runs/{id}/tool-results")
    def tool_results(id: str):
        value = get("run", id)
        return [
            r
            for r in store().list("flow_tool_result", value["workspace_id"])
            if r["run_id"] == id
        ]

    @app.get("/api/runs/{id}/gates")
    def gates(id: str):
        value = get("run", id)
        return [
            g for g in store().list("gate", value["workspace_id"]) if g["run_id"] == id
        ]

    @app.post("/api/gates/{id}/decision")
    async def gate_decision(id: str, body: dict):
        if (
            set(body) != {"decision", "comment"}
            or not isinstance(body.get("comment"), str)
            or len(body["comment"]) > 8000
        ):
            raise HTTPException(422, "Decision requires decision and comment max8000")
        with store().lock:
            gate = get("gate", id)
            value = get("run", gate["run_id"])
            if gate["status"] != "pending" or value["state"] != "waiting_approval":
                raise HTTPException(409, "Gate is not pending")
            if body["decision"] not in gate["allowed_decisions"]:
                raise HTTPException(422, "Decision is not allowed at this revision")
            gate.update(
                status=body["decision"], comment=body["comment"], decided_at=now()
            )
            store().put("gate", gate)
            store().event(
                value["workspace_id"],
                "review.decided",
                {
                    "gate_id": id,
                    "decision": body["decision"],
                    "revision": gate["revision"],
                },
                value["id"],
            )
        job = app.state.runtime.jobs.get(value["id"])
        if job:
            await asyncio.shield(job)
        value = get("run", value["id"])
        if value["state"] == "cancelled":
            raise HTTPException(409, "Run was cancelled")
        value["state"] = "queued"
        store().put("run", value)
        app.state.runtime.schedule(value, resume=True)
        return gate

    @app.post("/api/runs/{id}/resume")
    async def resume(id: str):
        value = get("run", id)
        if value["state"] != "failed" or not value.get("checkpoint", {}).get(
            "resumable"
        ):
            raise HTTPException(409, "Run has no resumable checkpoint")
        if any(
            r["state"] in ("queued", "running", "waiting_approval")
            for r in store().list("run", value["workspace_id"])
        ):
            raise HTTPException(409, "Workspace already has an active run")
        value["state"] = "queued"
        store().put("run", value)
        app.state.runtime.schedule(value, resume=True)
        return value

    @app.get("/api/audit")
    def audit(workspace_id: str):
        workspace(workspace_id)
        return store().list("audit", workspace_id)

    from services.api.office_projection import create_office_router
    from services.api.company import create_company_router
    from services.api.operations import create_operations_router
    from services.api.data_sources import create_data_router

    from services.api.console import create_console_router
    from services.api.console_extensions import create_console_extensions_router

    app.include_router(create_console_router(app, start_run, RunInput))
    app.include_router(create_console_extensions_router(app))
    app.include_router(create_data_router(app))
    app.include_router(create_company_router(app, start_run, RunInput))
    app.include_router(create_operations_router(app, start_run, RunInput))
    app.include_router(create_office_router(app))
    return app


def normalize_agent(value):
    value = {k: v for k, v in value.items() if v is not None}
    return hydrate(value)


def workspace_create(store, name):
    id = uid()
    root = store.root / "workspaces" / id
    root.mkdir(parents=True)
    (root / "README.md").write_text(
        f"# {name}\n\nIsolated AgentVerse project directory.\n"
    )
    value = store.put(
        "workspace", dict(id=id, name=name, root_path=str(root), created_at=now())
    )
    store.put(
        "room",
        dict(
            id=uid(), workspace_id=id, width=20, height=14, furniture=[], assignments={}
        ),
    )
    return value


app = create_app()
