# Phase 2 integration evidence

Independent QA **APPROVE for the implemented localhost scope**, application candidate `3b7b138`; [review](../AI_LOGS/reviews/P2-08-final-review.md). This file supersedes v0.1 validation for Phase 2; historical v0.1 approval is not Phase 2 approval.

## Implemented scope

Actual Habblaud Canvas2D world/UI and procedural graphics are vendored under MIT, with Pixelify Sans OFL notices and a source/hash patch ledger. Two-workspace localhost application, persistent characters, native additive furniture editor and appearance persistence. Role, Brain, Skill bindings, Tool grants and scoped Memory are stored per agent. Actual LangGraph StateGraph uses persistent SQLite checkpoints and approval interrupts. Official DeepSeek Harness SDK/runtime0.1.5rc1 loads the reviewed Cordis plugin and invokes the same permission-checked dispatcher. Read [approval contract](contracts/phase2/TOOLS_APPROVAL.md).

## Integrator checks, 2026-10-18

- Python backend/runtime/Harness/projection/layout suite: **88 passed**, no skips; one upstream AnyIO deprecation warning.
- Office: typecheck PASS, **10 tests passed**, production build PASS.
- Control: **17 tests passed**, lint and TypeScript/production build PASS. Existing approximately740kB chunk warning retained.
- Python correctness Ruff PASS; Docker Compose config PASS. Docker image validation tracked separately below.
- Started/restarted actual three-service launcher against preserved `var/acceptance-final`. API health and office/control routing verified.
- Migration evidence retains all original11terminal runs/116events/63resources; added registry records are distinguished from preserved data. See [inventory](../tests/phase2/evidence/final/migration-results.json).
- Independent live API acceptance verifies three distinct approvals, actual file hashes, actual2pytest passes read by Reviewer, scoped memory call, cross-workspace denial, consumed approval409, remote Origin403 and exact new-run SSE sequence. [Evidence](../tests/phase2/evidence/final/live-api-with-memory.json).
- Intermediate real-data browser capture has10screens at1366/1920 plus contact sheets. [Office](../tests/phase2/evidence/final/live-office-1366.png). Final native furniture/appearance add/move/reject/reload/delete and character edit/save/reload passed independently; exact unmasked Habblaud canvas parity0pixels at both sizes. Corrected unknown-usage drawer and334-file provenance audit also pass. [Final evidence](../tests/phase2/evidence/3b7b138/).

## Honest limits

No live DeepSeek/OpenAI credential is present. Actual Harness runtime/Cordis/SQLite integration is exercised with a local OpenAI-compatible provider stub. Native deterministic Brain tests are labeled. Neither test proves paid model service availability. LangGraph executes predeclared, reviewed calculator writes/tests after approval before Harness assignment; Harness can retrieve their results. Arbitrary model-authored code generation or model-originated side effects is not implemented. There is no shell tool.

Harness is a developer-preview binary. Official wheel MIT/third-party notices and consumed-artifact pins are retained; upstream's broad workspace disclosure is not a complete selected-binary transitive SBOM. Do not describe all binary dependencies as verified MIT. No SaaS, public deployment, city or multiplayer.

Reusable cloud installation/start instructions saved as a draft; this does not publish an environment or prove restoration in a new task. To apply that snapshot, review/save environment settings and publish through the product.

## Container and dependency checks

Both Phase2 Docker images built successfully with locked installs and verified TLS using the optional trusted BuildKit CA. Temporary isolated containers passed office `/`, control `/control/`, `/health`, `/api/office/snapshot` (two rooms/six agents), and `/api/catalog` (both engines available) through the office proxy. These are development images, not a public deployment. Original localhost data was not mounted into the test containers.

`npm audit --omit=dev` for control reports0 production advisories; office install reports0 overall. Control development/test dependencies retain3 audit findings: tinypool critical (GHSA-5gmw-xhrv-c9v3 and GHSA-85c8-ppgw-ccpr), Vitest critical aggregate and @vitest/mocker moderate (GHSA-82fw-gwwq-j7x9). Current Vitest3 dependency tree has no complete automatic fix. No test UI/server is launched or exposed. This is a known remaining development-tool risk, not a claim of security-clean dependencies; review upgrade separately before accepting untrusted test configurations.
