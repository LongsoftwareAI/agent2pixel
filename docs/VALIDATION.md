# Localhost validation evidence

Application candidate reviewed/tested: `826c74c` (source commits listed in independent QA review). No remote push, SaaS deployment, or publication is implied by local commits or saved cloud setup instructions.

## Reproducible development setup

From repository root: `bash scripts/install.sh`, then `python3 scripts/dev.py`. Installer uses Python lock and `npm ci` with writable temporary caches; TLS and artifact integrity verification remain enabled. Installation finished successfully, including repeat installation. **Complete installation before starting services or tests.**

The final browser instance uses `AGENTVERSE_DATA_DIR=var/acceptance-final python3 scripts/dev.py`; earlier generated QA data remains preserved separately in `var/agentverse`. New clone setup follows README and `.env.example`; all data directories are ignored by Git. Restarted the actual launcher repeatedly; prior processes stopped and persisted data remained available. Defaults are loopback web3000/API8000. Browser evidence paths below are images, not web preview links.

## Automated checks

| Command | Outcome |
|---|---|
| `.venv/bin/python -m pytest tests/backend tests/e2e/runtime_security.py -q` | PASS: 29 tests (27 backend + 2 independent runtime-security tests) |
| `.venv/bin/python -m ruff check --select E9,F63,F7,F82 services tests/backend scripts` | PASS correctness lint |
| `npm --prefix apps/web run lint` | PASS ESLint |
| `npm --prefix apps/web test` | PASS: 9 tests |
| `npm --prefix apps/web run build` | PASS TypeScript + production bundle; main-chunk size warning retained |
| `node --test apps/web/src/office/model.check.ts` | PASS: 4 tests |
| `python3 tests/e2e/api_acceptance.py --base http://127.0.0.1:8000` | Independent QA API checks: see committed result |
| Browser/canvas interaction scripts | See final independent report and structured evidence; screenshots alone are not functional evidence |

Python run reports one upstream AnyIO deprecation warning. Vite reports ~732kB entry chunk (~233kB gzip); no warning was disabled. These are known non-failing limitations.

Coverage includes actual Planner→Developer→Reviewer input/output/messages; persisted history and SQLite foreign keys; validated conditions and DAG cycles; bounded retry, steps, token budget; real in-flight HTTP adapter cancellation with no late success; mock HTTP success/failure for OpenAI-compatible and Ollama; missing-key/config failures; policy denial without side effects; read-only tools; workspace traversal/symlink/isolation; event seq/replay and real uvicorn WebSocket; concurrent SQLite access; nested malformed request payloads; stale frontend responses after workspace changes; collision/path models.

## Browser evidence

QA owns `tests/e2e/` and `AI_LOGS/reviews/`, independently of application authors. Exact prerequisites and commands: [tests/e2e/README.md](../tests/e2e/README.md).

- [Office 1366×768](../tests/e2e/evidence/01-office-1366.png)
- [Agent Studio 1366×768](../tests/e2e/evidence/02-agent-studio-1366.png)
- [Workflow Builder 1366×768](../tests/e2e/evidence/03-workflow-1366.png)
- [Run Monitor 1366×768](../tests/e2e/evidence/04-run-monitor-1366.png)
- [Furniture Editor 1366×768](../tests/e2e/evidence/05-furniture-1366.png)
- [Settings 1366×768](../tests/e2e/evidence/06-settings-1366.png)
- [Office 1920×1080](../tests/e2e/evidence/07-office-1920.png)

Independent application verdict **APPROVE** is recorded in [QA-001 review](../AI_LOGS/reviews/QA-001-review.md) at candidate826c74c. Integrator reviewed the QA tests separately, tightened exact new-run replay proof, and reran browser7interactions with clean console/HTTP; result [here](evidence/integrator-browser-results.json). All10 screenshot hashes and dimensions match the committed manifest. The visual comparison and final verdict must be read with that review. Original procedural CC0 artwork, no upstream sprites copied. Habblaud room zoning/feed and Pixel Agents top-down workstation/furniture are design inspirations, with intentional light dashboard chrome and a smaller single-floor scope.

## Real failures investigated

1. Actual uvicorn initially lacked a WebSocket transport despite TestClient passing. Added pinned websockets and real-process handshake/replay/Origin regression tests; restarted and QA retested.
2. Initial browser favicon404, CSS-scaled canvas hit testing, viewport cropping, malformed nested request500s, and workspace switch stale responses were identified and fixed by their owners. Initial failing evidence is retained separately from final passing results.
3. Default npm cache was unwritable in this machine. Installer now uses a writable `/tmp` cache; dependency declarations, lock integrity and verification were preserved.
4. Integrator mistakenly ran repeat `npm ci` concurrently with frontend tests and a running Vite process. The resulting module-not-found/zero-test attempt is **FAILED/INVALID**, not a pass. Installation completed, then lint/test/build were rerun sequentially and Vite restarted before QA browser rerun. Do not infer an application defect or passing test from that invalid attempt.

## Docker evidence and cloud trust configuration

Docker28.4 is available. Both pinned images built successfully and Compose started API healthy + web in a separate QA project with alternate loopback ports18000/13000. The same independent 7-check API script passed through the **web proxy**, exercising persistent workflow output, not just health. Final images were rebuilt from the application candidate. QA project data is separate from development data; owned QA containers were stopped after validation, volumes preserved. Final image IDs and7-check results are committed in [Docker evidence](evidence/docker-validation.json).

This cloud machine has nested Docker DNS and a TLS-intercepting proxy. Unmodified build initially failed DNS, then certificate verification after adding proxy DNS mapping. Corrected using supported Docker `--add-host` for the already configured proxy hostname, predefined `--build-arg HTTP_PROXY --build-arg HTTPS_PROXY --build-arg NO_PROXY`, and optional BuildKit secret `--secret id=build_ca,src=<existing trusted CA bundle>`. Dockerfiles use that ephemeral CA for pip/npm only. No credentials or CA values were committed, no trust verification disabled, and no changed artifact checksums. `DOCKER_CONFIG=/tmp/agentverse-docker` avoided the unwritable default buildx cache. These are environment-specific build prerequisites; the ordinary documented dev command was validated directly. Do not claim the unmodified Compose build ran successfully in this proxied cloud machine.

## Scope and limitations

- MockBrain is deterministic and explicitly labeled. It runs real orchestration, tools/context, handoff and durable output; it does not claim an external model generated/executed code. No live OpenAI account or installed Ollama model was used. Adapter HTTP mock tests do not prove live provider access.
- Shell/file-write/network tools cannot execute side effects; denied requests are audited. No approval-grant executor or unsafe CLI bridge is shipped.
- SQLite aggregate JSON resources embed role/brain/skill config for the modular-monolith MVP; schema versioning, actual FKs and event indexes exist. No distributed queue, normalized CRUD for every logical table, or multi-process worker claim.
- Furniture uses one-tile collision footprints. No keyboard movement, advanced sprite generation, town, SaaS or public deployment.
- Security is scoped to a trusted single user on localhost. Do not expose publicly without a separate security/design task.
- Cloud `install_script` and `start_skill` were saved as a draft; this does not execute, publish, push Git commits, or establish fresh-task restoration. Application commits are local. Preserve branches/worktrees and use Git export/push only when authorized; local-only commit restoration is not independently verified.
