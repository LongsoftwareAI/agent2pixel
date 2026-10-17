# INC-001 — invalid test attempt during dependency reinstall

Owner: Integrator. Status: RESOLVED. Observed 2026-10-17 around10:47UTC in tool output. Scope: development/test processes only; no application data reset or lockfile changes.

Integrator mistakenly launched repeat `bash scripts/install.sh` concurrently with `npm --prefix apps/web test` and an existing Vite process. `npm ci` replaced node_modules while those processes were importing modules. Vitest reported missing agent-base/tinypool modules and zero executed tests; Vite reported an internal module-not-found error during QA probe. That attempt is FAILED/INVALID and is not counted as a passing suite or an application defect.

Recovery: finish installer (exit0); run lint,9-test suite and TypeScript/Vite build sequentially (all exit0); terminate/restart only the owned dev process tree; QA rerun actual localhost screenshots/interactions (clean console/HTTP), then tighten and rerun exact new-run WebSocket replay. Database was preserved. QA independent review records the invalid attempt.

Prevention: saved start instructions and docs require install to finish before services/tests; never run npm ci against a running Vite dependency tree. No assertions, checksums, TLS checks or lint rules were disabled to recover.
