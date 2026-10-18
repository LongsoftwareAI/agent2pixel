"""Versioned manifests and backward compatible AgentSpec hydration."""

import importlib.metadata
from fastapi import HTTPException

TOOLS = [
    dict(
        id="artifacts.write_text",
        version=1,
        name="Export generated text after review",
        approval_required=True,
        input_schema={
            "type": "object",
            "required": ["filename", "content"],
            "additionalProperties": False,
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
        },
    ),
    dict(
        id="documents.list",
        version=1,
        name="List documents",
        approval_required=False,
        input_schema={"type": "object"},
    ),
    dict(
        id="documents.read",
        version=1,
        name="Read documents",
        approval_required=False,
        input_schema={"type": "object"},
    ),
    dict(
        id="memory.read",
        version=1,
        name="Read scoped memory",
        approval_required=False,
        input_schema={"type": "object"},
    ),
    dict(
        id="artifacts.write_python",
        version=1,
        name="Write reviewed Python fixture",
        approval_required=True,
        input_schema={
            "type": "object",
            "required": ["filename", "template"],
            "properties": {
                "filename": {"enum": ["calculator.py", "test_calculator.py"]},
                "template": {"enum": ["calculator-v1", "calculator-tests-v1"]},
            },
        },
    ),
    dict(
        id="tests.run_pytest",
        version=1,
        name="Test reviewed Python fixture",
        approval_required=True,
        input_schema={"type": "object", "additionalProperties": False},
    ),
]


def engines():
    values = []
    try:
        version = importlib.metadata.version("langchain")
        available = True
    except importlib.metadata.PackageNotFoundError:
        version = None
        available = False
    values.append(
        dict(
            id="langchain",
            version=version,
            available=available,
            reason=None if available else "LangChain is not installed",
            capabilities={"read_only": True, "approved_fixture_tools": True},
        )
    )
    try:
        from services.worker.executors.harness import capabilities

        harness = capabilities()
        if isinstance(harness, list):
            values.extend(harness)
        else:
            values.append(
                dict(
                    id="deepseek_harness",
                    **{k: v for k, v in harness.items() if k != "id"},
                )
            )
    except ImportError:
        values.append(
            dict(
                id="deepseek_harness",
                available=False,
                reason="Harness adapter is not installed",
                capabilities={},
            )
        )
    return values


def hydrate(value):
    """Add rich fields to legacy records without replacing identities or legacy values."""
    value = {
        k: v
        for k, v in value.items()
        if v is not None
        or k not in ("role_config", "tool_grants", "memory_config", "appearance")
    }
    value.setdefault("execution", {"engine": "langchain", "version": 1})
    value.setdefault(
        "role_config",
        dict(
            id=value.get("role", "Developer").lower(),
            version=1,
            instructions=value.get("system_prompt", "Complete the task."),
            responsibilities=[],
        ),
    )
    value.setdefault("skill_bindings", [])
    value.setdefault(
        "tool_grants",
        [
            dict(id=t, allow=True, approval_required=False)
            for t in value.get("tools", [])
        ],
    )
    value.setdefault(
        "memory_config",
        dict(
            scope=value.get("memory_policy", "workspace")
            if value.get("memory_policy") in ("agent", "workspace", "none")
            else "workspace"
        ),
    )
    value.setdefault(
        "appearance", dict(seed=value.get("id", value.get("skin", "blue")))
    )
    return value


def seed_registry(store):
    for name in ("Planner", "Developer", "Reviewer", "Researcher"):
        record = dict(
            id=name.lower(),
            name=name,
            version=1,
            instructions=f"Act as {name}. Complete only the assigned responsibility; preserve evidence and report failures honestly.",
            responsibilities=[name.lower()],
            output_schema=None,
        )
        if not store.get("role", record["id"]):
            store.put("role", record)
    skill = dict(
        id="code-report",
        name="Evidence-based code report",
        version=1,
        instructions="Inspect the supplied artifacts and test report. State what was actually executed, identify failures, and never report unexecuted tests as passing.",
        allowed_tools=["documents.read", "documents.list", "memory.read"],
    )
    if not store.get("skill", skill["id"]):
        store.put("skill", skill)
    if not store.get("skill_version", "skill:code-report:1"):
        store.put(
            "skill_version",
            dict(skill, id="skill:code-report:1", registry_id=skill["id"]),
        )
    for agent in store.list("agent"):
        upgraded = hydrate(agent)
        if upgraded != agent:
            store.put("agent", upgraded)


def validate_spec(value, store):
    execution = value["execution"]
    if not isinstance(execution, dict) or execution.get("engine") not in (
        "langchain",
        "deepseek_harness",
    ):
        raise HTTPException(422, "Unknown execution engine")
    if set(execution) - {"engine", "profile", "version"}:
        raise HTTPException(422, "Unknown execution configuration")
    if execution.get("profile") is not None and (
        not isinstance(execution["profile"], str) or len(execution["profile"]) > 128
    ):
        raise HTTPException(422, "Invalid engine profile")
    if execution.get("version") is not None and (
        type(execution["version"]) is not int or execution["version"] < 1
    ):
        raise HTTPException(422, "Invalid engine version")
    role = value["role_config"]
    if (
        not isinstance(role, dict)
        or not isinstance(role.get("instructions"), str)
        or not isinstance(role.get("id"), str)
        or not role["id"]
        or type(role.get("version")) is not int
        or role["version"] < 1
    ):
        raise HTTPException(422, "Role requires id/version/instructions")
    if len(role["instructions"]) > 20000 or set(role) - {
        "id",
        "version",
        "instructions",
        "responsibilities",
        "output_schema",
    }:
        raise HTTPException(422, "Invalid role fields")
    if not isinstance(role.get("responsibilities", []), list) or any(
        not isinstance(item, str) for item in role.get("responsibilities", [])
    ):
        raise HTTPException(422, "Responsibilities must be strings")
    if role.get("output_schema") is not None:
        from jsonschema import Draft202012Validator, SchemaError

        try:
            if (
                not isinstance(role["output_schema"], dict)
                or role["output_schema"].get("type") != "object"
            ):
                raise ValueError()

            # Remote references are never fetched while validating model output.
            def refs(item):
                if isinstance(item, dict):
                    return (
                        any(
                            key in item and not str(item[key]).startswith("#")
                            for key in ("$ref", "$dynamicRef", "$recursiveRef")
                        )
                    ) or any(refs(v) for v in item.values())
                return any(refs(v) for v in item) if isinstance(item, list) else False

            if refs(role["output_schema"]):
                raise ValueError()
            Draft202012Validator.check_schema(role["output_schema"])
        except (SchemaError, ValueError):
            raise HTTPException(422, "Invalid or remote role output schema") from None
    for binding in value["skill_bindings"]:
        if (
            not isinstance(binding, dict)
            or set(binding) != {"id", "version"}
            or not isinstance(binding.get("id"), str)
            or not binding["id"]
            or type(binding.get("version")) is not int
            or binding["version"] < 1
        ):
            raise HTTPException(422, "Invalid skill binding")
        if (store.get("skill", binding.get("id")) or {}).get(
            "archived"
        ) or not resolve_skill(store, binding):
            raise HTTPException(422, "Unknown skill version")
    for grant in value["tool_grants"]:
        if (
            not isinstance(grant, dict)
            or set(grant) - {"id", "allow", "approval_required"}
            or not any(t["id"] == grant.get("id") for t in TOOLS)
            or type(grant.get("allow")) is not bool
            or (
                "approval_required" in grant
                and type(grant["approval_required"]) is not bool
            )
        ):
            raise HTTPException(422, "Unknown or invalid tool grant")
    memory = value["memory_config"]
    if (
        not isinstance(memory, dict)
        or set(memory) - {"scope", "retention"}
        or memory.get("scope") not in ("agent", "workspace", "none")
    ):
        raise HTTPException(422, "Invalid memory scope")
    if memory.get("retention") is not None and (
        type(memory["retention"]) is not int or not 1 <= memory["retention"] <= 3650
    ):
        raise HTTPException(422, "Retention is 1–3650 days")
    if (
        not isinstance(value["appearance"], dict)
        or not isinstance(value["appearance"].get("seed"), (str, int))
        or set(value["appearance"]) - {"seed", "parts"}
    ):
        raise HTTPException(422, "Appearance requires seed and optional parts")
    return value


def snapshot_spec(agent, store):
    value = hydrate(agent)
    value["resolved_skills"] = [
        resolve_skill(store, binding) for binding in value["skill_bindings"]
    ]
    return value


def execution_prompt(agent):
    role = agent["role_config"]
    skills = agent.get("resolved_skills", [])
    return "\n\n".join(
        [
            agent["system_prompt"],
            f"Role {role['id']} v{role['version']}: {role['instructions']}",
            "Responsibilities: " + ", ".join(role.get("responsibilities", [])),
        ]
        + [f"Skill {s['id']} v{s['version']}: {s['instructions']}" for s in skills]
    )


def resolve_skill(store, binding):
    if not isinstance(binding, dict):
        return None
    record = store.get("skill", binding.get("id"))
    if record and record["version"] == binding.get("version"):
        return record
    version = store.get(
        "skill_version",
        "skill:" + str(binding.get("id")) + ":" + str(binding.get("version")),
    )
    if version:
        return dict(version, id=version["registry_id"])
    return None
