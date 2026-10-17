# AgentVerse Harness bridge — verified tool-less foundation

Official PyPI SDK and runtime **0.1.5rc1**, Linux x86_64/Python3.12. Install both exact pins; SDK requires pydantic>=2.12,<3. No upstream source build or unverified fallback. `ARTIFACTS.json` pins the actual installed executable, rg sidecar and SDK client/API hashes. Release wheel does not attest its source commit; do not equate it with inspected HEAD687f282. Wheel metadata internally says0.0.0-dev; distribution pair is0.1.5rc1. `release-*.yml` are actual official runtime `--dump-default-config` / `--dump-config` outputs, not hand-written approximation.

`tool-less.patch.yml` disables every release sdk-minimal OS execution service and tool producer. There are no FS/PTC/plugin-install/terminal/tool producers in this exact profile. Runtime worker checks effective config bytes on every invocation before SDK startup; unknown custom/home overlays fail closed. Provider stub receives tools absent. Root/runtime/patch integrity mismatch makes engine unavailable. AgentVerse app-domain tool and memory operations are not falsely reported as Harness tool calls.

Outer Python subprocess receives allowlisted env before SDK imports (SDK env={} alone inherits parent). Explicit isolated home/workspace per workspace+agent+run; UUID sessions; worker deadlines, bounded concurrency, process-group cancellation. Only selected provider secret enters worker environment. Runtime stderr/events are private; API errors sanitized. Tokens use release assistant/message.usage.totalTokens, otherwise estimated. Model max_tokens bounds output, app enforces total returned usage; provider-side charges cannot be rolled back.

## License and distribution

No runtime binary or optional Office/Claude/Web payload copied into repository. Official wheel installed separately over verified TLS. `notices/` retains unmodified MIT and broad third-party disclosure from exact installed wheel. That disclosure is workspace-level, not a precise binary SBOM; upstream does not include a complete selected binary transitive notice manifest. `ARTIFACTS.json` identifies the consumed closure at artifact level, not an unsupported claim all dependencies are MIT. No code/artwork from optional Claude Code or Office plugins imported. Full binary license closure review remains an integration limitation.

## Gate status

Real SDK/runtime + loopback provider stub: PASS. Real paid/live provider: UNRUN (no credential requirement added for optional engine). Text-only engine works. Full Cordis tool/skill/memory bridge P2-07: IN PROGRESS; capability tools/memory_bridge false until real plugin broker test passes. No unsafe sdk/default profile selectable.

Run tests from checkout:
`/path/to/sdk-venv/bin/python -m unittest discover -s tests/harness -v`
Optional packages absent: runtime tests explicitly SKIP; unit boundary tests run.
