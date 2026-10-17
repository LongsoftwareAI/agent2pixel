"""Bounded, read-only workspace tools. No model-supplied code or file writes."""

import json
from pathlib import Path
from services.api.policy import safe_document


def tool_context(store, workspace_id, tools, agent=None):
    root = Path(store.get("workspace", workspace_id)["root_path"])
    values = {}
    paths = [
        p
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root)
    ][:30]
    if "documents.list" in tools:
        values["documents.list"] = [str(p.relative_to(root)) for p in paths]
    if "documents.read" in tools:
        docs = []
        for path in paths[:5]:
            try:
                target = safe_document(root, str(path.relative_to(root)))
                docs.append(
                    {
                        "path": str(path.relative_to(root)),
                        "content": target.read_text()[:4000],
                    }
                )
            except (UnicodeError, OSError):
                continue
        values["documents.read"] = docs
    if "memory.read" in tools:
        values["memory.read"] = [
            {"kind": m["kind"], "content": m["content"][:2000]}
            for m in (
                scoped_memories(store, workspace_id, agent)
                if agent
                else [
                    m
                    for m in store.list("memory", workspace_id)
                    if not m.get("agent_id")
                ]
            )[:10]
        ]
    return json.dumps(values, ensure_ascii=False) if values else ""


def scoped_memories(store, workspace_id, agent):
    from datetime import datetime, timezone, timedelta

    config = agent.get("memory_config", {})
    scope = config.get("scope", "workspace")
    if scope == "none":
        return []
    values = [
        m
        for m in store.list("memory", workspace_id)
        if (
            m.get("agent_id") == agent["id"]
            if scope == "agent"
            else not m.get("agent_id")
        )
    ]
    if config.get("retention"):
        cutoff = datetime.now(timezone.utc) - timedelta(days=config["retention"])
        values = [
            m for m in values if datetime.fromisoformat(m["created_at"]) >= cutoff
        ]
    return values


TEMPLATES = {
    "calculator-v1": ("calculator.py", "def add(a, b):\n    return a + b\n"),
    "calculator-tests-v1": (
        "test_calculator.py",
        "from calculator import add\n\ndef test_add_positive():\n    assert add(2, 3) == 5\n\ndef test_add_negative():\n    assert add(-2, 2) == 0\n",
    ),
}


def payload_hash(payload):
    import hashlib

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def artifact_root(store, workspace_id, run_id):
    root = Path(store.get("workspace", workspace_id)["root_path"]).resolve()
    target = root / "artifacts" / run_id
    # Refuse every symlink component including existing ancestors; mkdir cannot escape.
    current = root
    for part in ("artifacts", run_id):
        current = current / part
        if current.is_symlink():
            raise ValueError("Artifact symlink is forbidden")
        current.mkdir(exist_ok=True)
        if not current.resolve().is_relative_to(root):
            raise ValueError("Artifact path escaped workspace")
    return target


async def execute_action(store, run, agent, action):
    """Only fixed reviewed templates execute. Never eval, shell, pip, or model Python."""
    import asyncio
    import hashlib
    import os
    import sys
    from services.api.store import now, uid

    root = artifact_root(store, run["workspace_id"], run["id"])
    tool = action["tool"]
    payload = action["payload"]
    if tool == "artifacts.write_python":
        template = TEMPLATES.get(payload.get("template"))
        if (
            set(payload) != {"filename", "template"}
            or not template
            or payload["filename"] != template[0]
        ):
            raise ValueError("Only exact reviewed Python templates are writable")
        target = root / template[0]
        if target.exists() or target.is_symlink():
            raise ValueError("Artifact already exists; refusing overwrite")
        # O_NOFOLLOW + exclusive create prevents symlink substitution at the file.
        fd = os.open(
            target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "w") as stream:
            stream.write(template[1])
        content = target.read_bytes()
        return dict(
            id=uid(),
            path=str(
                target.relative_to(
                    Path(store.get("workspace", run["workspace_id"])["root_path"])
                )
            ),
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
            tool=tool,
            agent_id=agent["id"],
            created_at=now(),
        )
    if tool != "tests.run_pytest" or payload != {}:
        raise ValueError("Unknown action or tool payload")
    for filename in ("calculator.py", "test_calculator.py"):
        target = root / filename
        expected = next(
            content for name, content in TEMPLATES.values() if name == filename
        )
        if (
            target.is_symlink()
            or not target.is_file()
            or target.read_text() != expected
        ):
            raise ValueError("Test inputs must match reviewed template bytes")
    env = {
        "PATH": os.path.dirname(sys.executable) + ":/usr/bin:/bin",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "HOME": str(root),
        "LANG": "C.UTF-8",
    }
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-m",
        "pytest",
        "-q",
        "-c",
        "/dev/null",
        "--noconftest",
        "test_calculator.py",
        cwd=root,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    except BaseException:
        import signal

        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await proc.wait()
        raise
    report = output.decode(errors="replace")[:8000]
    if proc.returncode:
        raise ValueError("Reviewed fixture tests failed: " + report)
    return dict(
        id=uid(),
        tool=tool,
        agent_id=agent["id"],
        exit_code=proc.returncode,
        report=report,
        created_at=now(),
    )


async def dispatch_tool(store, run, agent, tool_id, payload):
    """Shared native/Harness broker. Identity is fixed by caller, never model args.

    Side effects must already have an exact committed approved LangGraph action;
    RPC callbacks cannot interrupt or create their own independent approval loop.
    """
    from services.api.domain import hydrate

    live_run = store.get("run", run["id"])
    live_agent = store.get("agent", agent["id"])
    if (
        not live_run
        or not live_agent
        or live_run["workspace_id"] != live_agent["workspace_id"]
        or live_run["state"] != "running"
    ):
        raise ValueError("Tool assignment ownership denied")
    spec = hydrate(live_run.get("agent_specs", {}).get(agent["id"], agent))
    if tool_id not in [g["id"] for g in spec["tool_grants"] if g["allow"]]:
        raise ValueError("Tool grant denied")
    if not isinstance(payload, dict):
        raise ValueError("Tool payload must be an object")
    root = Path(store.get("workspace", live_run["workspace_id"])["root_path"])
    if tool_id == "memory.read":
        if payload:
            raise ValueError("Memory scope comes from agent configuration")
        return [
            {"id": m["id"], "kind": m["kind"], "content": m["content"][:2000]}
            for m in scoped_memories(store, live_run["workspace_id"], spec)[:10]
        ]
    if tool_id == "documents.list":
        if payload:
            raise ValueError("Document listing accepts no path override")
        return [
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root)
        ][:100]
    if tool_id == "documents.read":
        if set(payload) != {"path"} or not isinstance(payload["path"], str):
            raise ValueError("Document read requires path")
        target = safe_document(root, payload["path"])
        try:
            return {"path": payload["path"], "content": target.read_text()[:8000]}
        except (UnicodeError, OSError):
            raise ValueError("Document is not readable text") from None
    if tool_id not in ("artifacts.write_python", "tests.run_pytest"):
        raise ValueError("Unknown registered tool")
    for index, action in enumerate(live_run.get("actions", [])):
        if (
            action["agent_id"] == agent["id"]
            and action["tool"] == tool_id
            and payload_hash(action["payload"]) == payload_hash(payload)
        ):
            action_id = run["id"] + ":" + str(index)
            approval = next(
                (
                    a
                    for a in store.list("approval", live_run["workspace_id"])
                    if a["action_id"] == action_id
                ),
                None,
            )
            result = store.get("tool_result", action_id)
            if (
                approval
                and approval["status"] == "consumed"
                and approval["payload_hash"] == payload_hash(payload)
                and result
            ):
                return result["result"]
    raise ValueError("Side effect requires exact approved committed workflow action")


async def native_context(store, run, agent, tools):
    values = {}
    for tool in tools:
        if tool == "documents.read":
            root = Path(store.get("workspace", run["workspace_id"])["root_path"])
            docs = []
            paths = [
                p
                for p in root.rglob("*")
                if p.is_file()
                and not p.is_symlink()
                and p.resolve().is_relative_to(root)
            ][:5]
            for path in paths:
                try:
                    docs.append(
                        await dispatch_tool(
                            store,
                            run,
                            agent,
                            tool,
                            {"path": str(path.relative_to(root))},
                        )
                    )
                except (ValueError, OSError):
                    continue
            values[tool] = docs
        else:
            values[tool] = await dispatch_tool(store, run, agent, tool, {})
        store.event(
            run["workspace_id"],
            "tool.completed",
            {"tool": tool, "read_only": True},
            run["id"],
            agent["id"],
        )
    return json.dumps(values, ensure_ascii=False) if values else ""
