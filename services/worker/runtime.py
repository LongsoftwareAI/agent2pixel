import asyncio
from collections import deque
from services.api.store import now, uid
from services.worker.adapters import run_brain
from services.worker.tools import (
    native_context,
    execute_action,
    payload_hash,
    validate_text_payload,
)
from services.api.domain import execution_prompt, engines, snapshot_spec
from typing import TypedDict
import json
from datetime import datetime, timezone, timedelta
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import interrupt, Command
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda


def validate_graph(graph, store, workspace):
    errors = []
    if not isinstance(graph, dict):
        return ["Graph must be an object"]
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if (
        not isinstance(nodes, list)
        or not isinstance(edges, list)
        or not 2 <= len(nodes) <= 32
    ):
        return ["Graph requires 2–32 nodes"]
    if any(not isinstance(n, dict) or not isinstance(n.get("id"), str) for n in nodes):
        return ["Node IDs must be strings"]
    by_id = {n["id"]: n for n in nodes}
    if len(by_id) != len(nodes):
        errors.append("Duplicate node IDs")
    starts = [n for n in nodes if n.get("type") == "start"]
    if len(starts) != 1:
        errors.append("Exactly one start required")
    if not any(n.get("type") == "end" for n in nodes):
        errors.append("End required")
    incoming = {id: [] for id in by_id}
    outgoing = {id: [] for id in by_id}
    if any(not isinstance(e, dict) for e in edges):
        return ["Edges must be objects"]
    if any(
        not isinstance(e.get("source"), str) or not isinstance(e.get("target"), str)
        for e in edges
    ):
        return ["Edge IDs must be strings"]
    if any("label" in e and e["label"] not in ("true", "false") for e in edges):
        return ["Edge label must be true or false"]
    for e in edges:
        if (
            not isinstance(e, dict)
            or e.get("source") not in by_id
            or e.get("target") not in by_id
        ):
            errors.append("Edge references missing node")
            continue
        outgoing[e["source"]].append(e)
        incoming[e["target"]].append(e)
    for n in nodes:
        if n.get("type") not in ("start", "agent", "condition", "end"):
            errors.append("Unknown node type")
        if n.get("type") == "agent":
            if "instructions" in n and (
                not isinstance(n["instructions"], str) or len(n["instructions"]) > 8000
            ):
                errors.append("Node instructions must be a string max8000")
            if "deliverable" in n:
                try:
                    if not isinstance(n["deliverable"], dict) or set(
                        n["deliverable"]
                    ) != {"filename"}:
                        raise ValueError("Invalid deliverable")
                    validate_text_payload(dict(n["deliverable"], content=""))
                except ValueError:
                    errors.append("Deliverable requires safe text filename")
            agent = (
                store.get("agent", n.get("agent_id"))
                if isinstance(n.get("agent_id"), str)
                else None
            )
            if not agent or agent["workspace_id"] != workspace or not agent["enabled"]:
                errors.append("Agent missing, disabled or outside workspace")
        if n.get("type") == "start" and incoming[n["id"]]:
            errors.append("Start has incoming edges")
        if n.get("type") == "end" and outgoing[n["id"]]:
            errors.append("End has outgoing edges")
        if n.get("type") != "end" and not outgoing[n["id"]]:
            errors.append("Non-end node has no outgoing edge")
        if n.get("type") == "condition":
            if sorted(e.get("label", "") for e in outgoing[n["id"]]) != [
                "false",
                "true",
            ]:
                errors.append("Condition requires one true and one false edge")
            condition = n.get("condition", {})
            if (
                not isinstance(condition, dict)
                or condition.get("field") not in ("input", "output")
                or not isinstance(condition.get("equals"), str)
            ):
                errors.append("Condition requires field input/output and string equals")
    degree = {id: len(incoming[id]) for id in by_id}
    queue = deque(id for id in by_id if not degree[id])
    order = []
    while queue:
        id = queue.popleft()
        order.append(id)
        for e in outgoing[id]:
            degree[e["target"]] -= 1
            if degree[e["target"]] == 0:
                queue.append(e["target"])
    if len(order) != len(nodes):
        errors.append("Cycles are forbidden")
    reached = set()

    def visit(id):
        if id in reached:
            return
        reached.add(id)
        for e in outgoing[id]:
            visit(e["target"])

    if starts:
        visit(starts[0]["id"])
    if reached != set(by_id):
        errors.append("Unreachable nodes")
    return sorted(set(errors))


class GraphState(TypedDict):
    outputs: dict
    active: list
    tokens: int
    steps: int


class Runtime:
    """LangGraph owns scheduling/checkpoints; domain commits are idempotency markers."""

    def __init__(self, store):
        self.store = store
        self.jobs = {}
        self.semaphore = asyncio.Semaphore(2)
        self.checkpointer = None
        self.checkpoint_context = None
        self.init_lock = asyncio.Lock()

    async def saver(self):
        async with self.init_lock:
            if self.checkpointer is None:
                self.checkpoint_context = AsyncSqliteSaver.from_conn_string(
                    str(self.store.root / "checkpoints.sqlite3")
                )
                self.checkpointer = await self.checkpoint_context.__aenter__()
                await self.checkpointer.setup()
        return self.checkpointer

    async def close(self):
        if self.checkpoint_context:
            await self.checkpoint_context.__aexit__(None, None, None)

    def schedule(self, run, resume=False):
        if run["id"] in self.jobs:
            return
        job = asyncio.create_task(self.execute(run["id"], resume))
        self.jobs[run["id"]] = job
        job.add_done_callback(lambda _: self.jobs.pop(run["id"], None))

    def cancel(self, id):
        job = self.jobs.get(id)
        if job:
            job.cancel()

    def event(self, run, kind, payload=None, agent=None):
        return self.store.event(run["workspace_id"], kind, payload, run["id"], agent)

    async def action(self, run, agent, index, action):
        store = self.store
        grants = {g["id"]: g for g in agent["tool_grants"] if g["allow"]}
        if action["tool"] not in grants:
            raise ValueError("Tool grant denied")
        action_id = run["id"] + ":" + str(index)
        existing = store.get("tool_result", action_id)
        digest = payload_hash(action["payload"])
        approval = next(
            (
                a
                for a in store.list("approval", run["workspace_id"])
                if a["action_id"] == action_id
            ),
            None,
        )
        if approval is None:
            approval = dict(
                id=uid(),
                workspace_id=run["workspace_id"],
                run_id=run["id"],
                agent_id=agent["id"],
                action_id=action_id,
                tool=action["tool"],
                payload=action["payload"],
                payload_hash=digest,
                node_id=action.get("node_id"),
                status="pending",
                created_at=now(),
                expires_at=(
                    datetime.now(timezone.utc) + timedelta(minutes=15)
                ).isoformat(),
            )
            store.put("approval", approval)
            self.event(
                run,
                "approval.required",
                {
                    "approval_id": approval["id"],
                    "tool": action["tool"],
                    "payload_hash": digest,
                },
                agent["id"],
            )
        if approval["status"] == "pending":
            current = store.get("run", run["id"])
            current["state"] = "waiting_approval"
            current["checkpoint"]["resumable"] = True
            store.put("run", current)
            live = store.get("agent", agent["id"])
            live["status"] = "waiting"
            store.put("agent", live)
        interrupt({"approval_id": approval["id"]})
        approval = store.get("approval", approval["id"])
        if any(
            approval.get(k) != v
            for k, v in dict(
                run_id=run["id"],
                workspace_id=run["workspace_id"],
                agent_id=agent["id"],
                tool=action["tool"],
                payload_hash=digest,
                node_id=action.get("node_id"),
            ).items()
        ):
            raise ValueError("Approval binding mismatch")
        if payload_hash(approval.get("payload")) != digest:
            raise ValueError("Approval payload mismatch")
        if existing and approval["status"] == "consumed":
            return existing["result"]
        if approval["status"] != "approved":
            raise ValueError("Approval denied or already consumed")
        if datetime.fromisoformat(approval["expires_at"]) < datetime.now(timezone.utc):
            raise ValueError("Approval expired")
        # Consume before side effect. A crash here requires reconciliation, never automatic repeat.
        approval["status"] = "consumed"
        store.put("approval", approval)
        self.event(
            run,
            "tool.requested",
            {"tool": action["tool"], "approval_id": approval["id"]},
            agent["id"],
        )
        result = await execute_action(store, run, agent, action)
        store.put(
            "tool_result",
            dict(
                id=action_id,
                workspace_id=run["workspace_id"],
                run_id=run["id"],
                result=result,
            ),
        )
        self.event(
            run,
            "tool.completed",
            {"tool": action["tool"], "result": result},
            agent["id"],
        )
        return result

    async def assignment(self, run, node, text, state):
        store = self.store
        id = run["id"]
        ws = run["workspace_id"]
        agent = run.get("agent_specs", {}).get(node["agent_id"]) or snapshot_spec(
            store.get("agent", node["agent_id"]), store
        )
        live = store.get("agent", agent["id"])
        if not live or not live["enabled"]:
            raise ValueError("Agent disabled")
        completed = next(
            (
                t
                for t in run["tasks"]
                if t["node_id"] == node["id"] and t["state"] == "completed"
            ),
            None,
        )
        if completed:
            return completed["output"], completed["tokens"]
        task = next(
            (
                t
                for t in run["tasks"]
                if t["node_id"] == node["id"]
                and t["state"] in ("running", "queued", "failed")
            ),
            None,
        )
        if task is None:
            task = dict(
                id=uid(),
                node_id=node["id"],
                agent_id=agent["id"],
                state="queued",
                input=text,
                output="",
                retry_count=0,
                error=None,
            )
            run["tasks"].append(task)
            store.put("run", run)
            self.event(run, "task.queued", {"task_id": task["id"]}, agent["id"])
            for edge in run["graph"]["edges"]:
                sender = next(
                    (
                        n.get("agent_id")
                        for n in run["graph"]["nodes"]
                        if n["id"] == edge["source"]
                    ),
                    None,
                )
                if (
                    edge["target"] == node["id"]
                    and sender
                    and edge["source"] in state["outputs"]
                ):
                    store.put(
                        "message",
                        dict(
                            id=uid(),
                            workspace_id=ws,
                            run_id=id,
                            sender=sender,
                            recipient=agent["id"],
                            payload=state["outputs"][edge["source"]],
                            timestamp=now(),
                            correlation_id=task["id"],
                        ),
                    )
            task["state"] = "running"
            live["status"] = "working"
            store.put("agent", live)
            store.put("run", run)
            self.event(
                run,
                "task.started",
                {
                    "task_id": task["id"],
                    "node_id": node["id"],
                    "engine": agent["execution"]["engine"],
                },
                agent["id"],
            )
        elif task["state"] == "failed":
            task.update(state="running", error=None)
            store.put("run", run)
        generated = store.get("node_output", id + ":" + node["id"])
        if generated:
            return await self.finish_assignment(run, node, agent, generated)
        denied = [
            t
            for t in agent["tools"]
            if t
            not in (
                "documents.list",
                "documents.read",
                "memory.read",
                "artifacts.write_python",
                "tests.run_pytest",
                "artifacts.write_text",
            )
        ]
        if denied:
            self.event(
                run,
                "approval.required",
                {"decision": "denied", "tools": denied},
                agent["id"],
            )
            store.put(
                "audit",
                dict(
                    id=uid(),
                    workspace_id=ws,
                    actor=agent["id"],
                    action="tool.execute",
                    target=denied,
                    decision="denied",
                    created_at=now(),
                ),
            )
            raise ValueError("Tool policy denied; side effects cannot execute")
        allowed = [g["id"] for g in agent["tool_grants"] if g["allow"]]
        readonly = [
            t
            for t in allowed
            if t in ("documents.list", "documents.read", "memory.read")
        ]
        context = await native_context(store, run, agent, readonly)
        for skill in agent.get("resolved_skills", []):
            self.event(
                run,
                "skill.activated",
                {"id": skill["id"], "version": skill["version"]},
                agent["id"],
            )
        if "memory.read" in readonly:
            self.event(
                run,
                "memory.read",
                {"scope": agent["memory_config"]["scope"]},
                agent["id"],
            )
        for index, action in enumerate(run.get("actions", [])):
            if action["agent_id"] != agent["id"]:
                continue
            result = await self.action(run, agent, index, action)
            # action() may commit waiting state; refresh while preserving task references.
            latest = store.get("run", id)
            if not any(a["id"] == result["id"] for a in latest["artifacts"]):
                latest["artifacts"].append(result)
            latest["state"] = "running"
            store.put("run", latest)
            run.update(latest)
        artifact_context = json.dumps(run.get("artifacts", []), ensure_ascii=False)
        model_input = (
            text
            + "\n\nOriginal workflow objective (immutable run input):\n"
            + run["input"]
            + (
                "\n\nOriginal work brief and acceptance criteria (immutable snapshot):\n"
                + json.dumps(run["brief_snapshot"], ensure_ascii=False)
                if run.get("brief_snapshot")
                else ""
            )
            + (
                "\n\nNode objective and acceptance requirements:\n"
                + node["instructions"]
                if node.get("instructions")
                else ""
            )
            + ("\n\nWorkspace context:\n" + context if context else "")
            + (
                "\n\nCommitted artifacts and test evidence:\n" + artifact_context
                if run.get("artifacts")
                else ""
            )
        )
        spec = dict(agent, system_prompt=execution_prompt(agent))
        engine = agent["execution"]["engine"]
        capability = next((e for e in engines() if e["id"] == engine), {})
        if not capability.get("available"):
            raise ValueError(
                "Execution engine unavailable: "
                + str(capability.get("reason", "unknown"))
            )
        used_total = 0
        for attempt in range(task["retry_count"], run["retry_limit"] + 1):
            if store.get("run", id).get("token_spent", 0) >= run["token_budget"]:
                raise ValueError("Token budget exhausted")
            try:
                accounting = {}
                if engine == "deepseek_harness":
                    from services.worker.executors.harness import execute_assignment

                    output, usage = await execute_assignment(
                        spec,
                        model_input,
                        max(
                            0,
                            run["token_budget"]
                            - store.get("run", id).get("token_spent", 0),
                        ),
                        store,
                        id,
                        lambda kind, payload=None: self.event(
                            run, kind, payload, agent["id"]
                        ),
                    )
                    used = usage["tokens"]
                    accounting = usage
                else:
                    # Real LangChain prompt/runnable pipeline; the provider remains independently configured.
                    prompt = ChatPromptTemplate.from_messages(
                        [("system", "{instructions}"), ("human", "{assignment}")]
                    )

                    async def invoke(messages):
                        parts = messages.to_messages()
                        return await run_brain(
                            dict(spec, system_prompt=parts[0].content),
                            parts[1].content,
                            max(
                                0,
                                run["token_budget"]
                                - store.get("run", id).get("token_spent", 0),
                            ),
                            accounting,
                        )

                    chain = prompt | RunnableLambda(invoke)
                    output, used = await chain.ainvoke(
                        {
                            "instructions": spec["system_prompt"],
                            "assignment": model_input,
                        }
                    )
                used_total += used
                spent = store.get("run", id)
                spent["token_spent"] = spent.get("token_spent", 0) + used
                store.put("run", spent)
                if used_total > state["tokens"]:
                    raise ValueError("Token budget exhausted")
                schema = agent["role_config"].get("output_schema")
                if schema:
                    try:
                        parsed = json.loads(output)
                    except (ValueError, TypeError):
                        raise ValueError("Role output is not valid JSON") from None
                    from jsonschema import Draft202012Validator

                    if not Draft202012Validator(schema).is_valid(parsed):
                        raise ValueError("Role output schema failed")
                break
            except ValueError:
                if attempt >= run["retry_limit"]:
                    raise
                run = store.get("run", id)
                task = next(
                    t
                    for t in run["tasks"]
                    if t["node_id"] == node["id"] and t["state"] == "running"
                )
                task["retry_count"] += 1
                store.put("run", run)
                self.event(
                    run,
                    "task.progress",
                    {"retry_count": task["retry_count"]},
                    agent["id"],
                )
                await asyncio.sleep(0.05)
        # Persist generated result and accounting before any post-generation interrupt.
        generated = dict(
            id=id + ":" + node["id"],
            run_id=id,
            workspace_id=ws,
            node_id=node["id"],
            agent_id=agent["id"],
            output=output,
            tokens=used_total,
            accounting=accounting,
        )
        persisted = store.get("run", id)
        persisted_task = next(
            t for t in persisted["tasks"] if t["node_id"] == node["id"]
        )
        persisted_task.update(
            output=output, tokens=used_total, output_generated_at=now()
        )
        store.put_many([("node_output", generated), ("run", persisted)])
        return await self.finish_assignment(run, node, agent, generated)

    async def finish_assignment(self, run, node, agent, generated):
        store = self.store
        id = run["id"]
        output, used_total = generated["output"], generated["tokens"]
        if node.get("deliverable"):
            validate_text_payload(dict(node["deliverable"], content=output))
            result = await self.action(
                run,
                agent,
                "node:" + node["id"],
                {
                    "tool": "artifacts.write_text",
                    "node_id": node["id"],
                    "payload": dict(node["deliverable"], content=output),
                },
            )
            latest = store.get("run", id)
            if not any(a["id"] == result["id"] for a in latest["artifacts"]):
                latest["artifacts"].append(result)
            latest["state"] = "running"
            store.put("run", latest)
        # Refresh task after interrupt/resume and commit before checkpoint.
        run = store.get("run", id)
        task = next(t for t in run["tasks"] if t["node_id"] == node["id"])
        task.update(state="completed", output=output, tokens=used_total)
        live = store.get("agent", agent["id"])
        live["status"] = "completed"
        store.put("agent", live)
        store.put("run", run)
        self.event(
            run,
            "task.completed",
            {
                "task_id": task["id"],
                "output": output,
                "tokens": used_total,
                "token_accounting": generated["accounting"].get(
                    "token_accounting", "estimated"
                ),
            },
            agent["id"],
        )
        return output, used_total

    async def compile(self, run):
        graph = run["graph"]
        nodes = {n["id"]: n for n in graph["nodes"]}
        # Compile a stable topological graph. Inactive branch nodes are checkpointed skips;
        # merge nodes receive only activated incoming outputs, including shared end nodes.
        order = []
        pending = list(nodes)
        while pending:
            ready = [
                n
                for n in pending
                if all(e["source"] in order for e in graph["edges"] if e["target"] == n)
            ]
            if not ready:
                raise ValueError("Invalid dependency graph")
            order.extend(ready)
            pending = [n for n in pending if n not in ready]
        builder = StateGraph(GraphState)
        for node_id in order:
            node = nodes[node_id]

            def make_step(node):
                async def step(state):
                    current = self.store.get("run", run["id"])
                    if current["state"] == "cancelled":
                        raise asyncio.CancelledError()
                    incoming = [
                        (i, e)
                        for i, e in enumerate(graph["edges"])
                        if e["target"] == node["id"]
                    ]
                    if incoming and not any(i in state["active"] for i, _ in incoming):
                        return {}
                    steps = state["steps"] + 1
                    if steps > run["max_steps"]:
                        raise ValueError("Maximum workflow steps exceeded")
                    text = (
                        "\n\n".join(
                            state["outputs"][e["source"]]
                            for i, e in incoming
                            if i in state["active"]
                        )
                        if incoming
                        else run["input"]
                    )
                    output = text
                    used = 0
                    if node["type"] == "agent":
                        output, used = await self.assignment(current, node, text, state)
                    active = list(state["active"])
                    for i, edge in enumerate(graph["edges"]):
                        if edge["source"] != node["id"]:
                            continue
                        if node["type"] == "condition":
                            matched = text == node["condition"]["equals"]
                            if edge["label"] != str(matched).lower():
                                continue
                        if i not in active:
                            active.append(i)
                    return dict(
                        outputs={**state["outputs"], node["id"]: output},
                        active=active,
                        steps=steps,
                        tokens=state["tokens"] - used,
                    )

                return step

            builder.add_node(node_id, make_step(node))
        builder.add_edge(START, order[0])
        for left, right in zip(order, order[1:]):
            builder.add_edge(left, right)
        builder.add_edge(order[-1], END)
        return builder.compile(checkpointer=await self.saver())

    async def execute(self, id, resume=False):
        store = self.store
        run = store.get("run", id)
        try:
            async with self.semaphore:
                if run["state"] == "cancelled":
                    return
                run.update(state="running", started_at=run.get("started_at") or now())
                store.put("run", run)
                graph = await self.compile(run)
                config = {
                    "configurable": {"thread_id": run["checkpoint"]["thread_id"]},
                    "recursion_limit": 256,
                }
                initial = dict(
                    outputs={}, active=[], tokens=run["token_budget"], steps=0
                )
                state = await graph.aget_state(config)
                value = (
                    Command(resume=True)
                    if resume and state.interrupts
                    else (None if resume and state.values else initial)
                )
                result = await graph.ainvoke(value, config)
                run = store.get("run", id)
                if "__interrupt__" in result:
                    run["state"] = "waiting_approval"
                    run["checkpoint"]["resumable"] = True
                    store.put("run", run)
                    return
                run.update(
                    state="completed",
                    output="\n\n".join(
                        result["outputs"][n["id"]]
                        for n in run["graph"]["nodes"]
                        if n["type"] == "end" and n["id"] in result["outputs"]
                    ),
                    ended_at=now(),
                    tokens_used=run.get(
                        "token_spent", run["token_budget"] - result["tokens"]
                    ),
                )
                run["checkpoint"]["resumable"] = False
                store.put("run", run)
                self.event(run, "workflow.completed", {"output": run["output"]})
        except asyncio.CancelledError:
            run = store.get("run", id)
            run.update(state="cancelled", ended_at=now())
            for task in run["tasks"]:
                if task["state"] in ("queued", "running"):
                    task["state"] = "cancelled"
                    self.event(
                        run, "task.cancelled", {"task_id": task["id"]}, task["agent_id"]
                    )
                    agent = store.get("agent", task["agent_id"])
                    agent["status"] = "idle"
                    store.put("agent", agent)
            run["checkpoint"]["resumable"] = False
            store.put("run", run)
            self.event(run, "workflow.cancelled")
        except Exception as exc:
            error = (
                str(exc) if isinstance(exc, ValueError) else "Runtime execution failed"
            )
            run = store.get("run", id)
            run.update(state="failed", error=error, ended_at=now())
            run["checkpoint"]["resumable"] = True
            for task in run["tasks"]:
                if task["state"] in ("queued", "running"):
                    task.update(state="failed", error=error)
                    self.event(
                        run,
                        "task.failed",
                        {"task_id": task["id"], "error": error},
                        task["agent_id"],
                    )
                    agent = store.get("agent", task["agent_id"])
                    agent["status"] = "error"
                    store.put("agent", agent)
            store.put("run", run)
            self.event(run, "workflow.failed", {"error": error})
