# AgentVerse Harness bridge — pinned SDK and shared policy registry

Official PyPI SDK and runtime **0.1.5rc1**, Linux x86_64/Python3.12. Install both exact pins; SDK requires pydantic>=2.12,<3. No upstream source build or unverified fallback. `ARTIFACTS.json` pins the actual installed executable, rg sidecar and SDK client/API hashes. Release wheel does not attest its source commit; do not equate it with inspected HEAD687f282. Wheel metadata internally says0.0.0-dev; distribution pair is0.1.5rc1. `release-*.yml` are actual official runtime `--dump-default-config` / `--dump-config` outputs, not hand-written approximation.

`tool-less.patch.yml` disables every release sdk-minimal OS execution service and tool producer. There are no FS/PTC/plugin-install/terminal/tool producers in this exact profile. Runtime worker checks effective config bytes on every invocation before SDK startup; unknown custom/home overlays fail closed. Provider stub receives tools absent. Root/runtime/patch integrity mismatch makes engine unavailable. AgentVerse app-domain tool and memory operations are not falsely reported as Harness tool calls.

Outer Python subprocess receives allowlisted env before SDK imports (SDK env={} alone inherits parent). Explicit isolated home/workspace per workspace+agent+run; UUID sessions; worker deadlines, bounded concurrency, process-group cancellation. Only selected provider secret enters worker environment. Runtime stderr/events are private; API errors sanitized. Tokens use release assistant/message.usage.totalTokens, otherwise estimated. Model max_tokens bounds output, app enforces total returned usage; provider-side charges cannot be rolled back.

## License and distribution

No runtime binary or optional Office/Claude/Web payload copied into repository. Official wheel installed separately over verified TLS. `notices/` retains unmodified MIT and broad third-party disclosure from exact installed wheel. That disclosure is workspace-level, not a precise binary SBOM; upstream does not include a complete selected binary transitive notice manifest. `ARTIFACTS.json` identifies the consumed closure at artifact level, not an unsupported claim all dependencies are MIT. No code/artwork from optional Claude Code or Office plugins imported. Full binary license closure review remains an integration limitation.

## Gate status

Real SDK/runtime + loopback provider stub: PASS. Real paid/live provider: UNRUN (no credential requirement added for optional engine). Text-only engine works. Cordis registry bridge P2-07: SELF_TESTED using the real shared dispatcher and domain Store; independent review pending. Capability tools/memory_bridge remains false if the shared dispatcher or pinned artifacts are unavailable. No unsafe sdk/default profile selectable.

Run tests from checkout:
`/path/to/sdk-venv/bin/python -m pytest -q tests/harness`
Optional packages absent: runtime tests explicitly SKIP; unit boundary tests run.

## Verified registry plugin increment

`index.mjs` (version1.0.0, hash-pinned manifest) is a real Cordis plugin loaded by an explicit absolute `name` insert. No package-install command or extra Node runtime required. Actual released SDK binary loads it and advertises only `agentverse_dispatch` with tool_id enum of snapshotted permitted grants. Model functioncall executes plugin -> ephemeral authenticated loopback broker -> **services.worker.tools.dispatch_tool**, the same permission/namespace/action result dispatcher as native. Model cannot choose agent/workspace/run/session or broker endpoint/token. Broker token is random per assignment and excluded from saved logs/config; max16calls, schema/body/result bounds, deadlines. Disconnect/timeout/cancel closes broker and entire process group.

Skills remain version-resolved prompt context from backend (not a second independent skill registry). Memory read actually invokes domain scoped service through plugin. Approved artifact/test actions are currently executed by LangGraph before assignment; plugin may obtain only their exact committed approved result, never independently execute a side effect or claim it created the file. New model-requested side effects require separate workflow approval and are rejected here. This is an explicit limitation of current mixed-engine acceptance scope.

Capability tools/memory_bridge becomes true only when backend shared dispatcher is importable and SDK/runtime/bridge integrity pins match. Profile `agentverse-tool-less-v1` always disables plugin; `agentverse-registry-v1`/default uses declared grants. Unplugging the per-agent engine/profile preserves app data; old Harness sessions are not silently resumed. UUID assignment sessions prevent cross-retry stale completion.

`tests/harness/test_domain_integration.py` runs the **real official SDK/runtime and actual plugin** against the actual SQLite Store, shared domain dispatcher, FastAPI API and persisted LangGraph workflow. The only model substitute is a loopback OpenAI-compatible provider stub; no paid/live model is claimed. Native Planner → Harness Developer → native Reviewer completes after three explicit approvals commit reviewed fixtures and execute pytest. Actual plugin calls retrieve agent-scoped memory, read workspace text, and retrieve the committed approved test result. Provider request capture verifies role/skill instructions, tool-result delivery, and absence of foreign agent/workspace memories. Negative calls attempt path traversal, changed test payload and memory namespace override; all emit sanitized `harness.tool.failed` and create no additional artifact. A model can still emit final text after a denied tool; final text alone is never evidence that a rejected operation succeeded. Final independent review and root integration remain required. Live model UNRUN.

## General company-task exports

Harness accepts per-node research/content/operations objectives and arbitrary text output without coding templates. `test_domain_integration.py` additionally verifies real SDK/plugin operations output through the post-generation approval path, including actual app restart. Generated output/tokens are persisted before approval; resume exports exact original bytes with source node/run/agent provenance without another model call. A plugin request to `artifacts.write_text` during generation is rejected even with the grant: the orchestrator is the only writer after exact output approval. Denial creates no deliverable. These are deterministic loopback provider tests, not live-model or web-research claims.
