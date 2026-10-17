# QA-001 independent review — APPROVE

Reviewer: qa-01 (independent of Backend/Frontend/Pixel/Integrator application authors). Reviewed application candidate **826c74c311023e62f42df8455171e8bdffeb4ed0**; subsequent documentation-only 9be205b and ae43cd5 reviewed separately. Task: QA-001; session: AI_LOGS/sessions/2026-10-17/qa-001.md. Date: 2026-10-17. Application verdict APPROVE for the documented trusted single-user localhost MVP. No remaining BLOCKER/MAJOR finding. This does not independently approve QA's own test implementation; Integrator reviews that contribution.

## Executed evidence

All browser screenshots below were captured by real Chromium at exact viewport dimensions on localhost, not assembled mockups. Main acceptance used root's documented dev launcher with fresh ignored data root `var/acceptance-final`. No user data was removed.

| Exact command | Result |
|---|---|
| `/workspace/agent2pixel/.venv/bin/python -m pytest tests/backend tests/e2e/runtime_security.py -q` (QA checkout at candidate) | PASS 29 (27 backend + 2 QA); upstream AnyIO deprecation warning |
| `npm --prefix apps/web test` (candidate application source) | PASS 9, independently rerun |
| `node --test apps/web/src/office/model.check.ts` | PASS 4, independently rerun |
| `python tests/e2e/api_acceptance.py --base http://127.0.0.1:8000` | PASS 7 independent HTTP checks; evidence/api-results.json |
| `python tests/e2e/browser_acceptance.py --output tests/e2e/evidence` | PASS 7 real interactions; console errors [], HTTP failures []; evidence/browser-results.json |
| `python tests/e2e/canvas_interaction.py` | PASS 7 real pointer/layout controls; page errors []; evidence/canvas-results.json |
| `python tests/e2e/workspace_interaction.py` | PASS UI-created workspace + 3 agents (role/brain/skin), memory persistence, rapid switches, soft-disable; console errors []; evidence/workspace-results.json |
| `python tests/e2e/capture_details.py` | PASS capabilities and event trace screenshots; console errors [] |
| `python tests/e2e/api_acceptance.py --base http://127.0.0.1:13000` | PASS same 7 checks through actual Docker web proxy; independently rerun |

The run assertions verify actual Planner output becomes Developer input, then Reviewer input; durable task output/message envelopes; ordered persisted event replay. Browser closes the actual runtime WebSocket, sees Disconnected, starts a run while disconnected, reconnects and receives missed workflow.completed. Pixi test moves desk via pointer, assigns selected agent, saves/reloads layout, zooms, toggles grid and pans. QA's local HTTP server blocks an actual Ollama adapter call, cancellation occurs, late response cannot complete the run. Additional checks exercise condition true, foreign workspace agents, max steps and memory isolation. Backend suite covers condition false, provider HTTP success/failure, missing secret, bounded retries/token budget, approval denial, traversal/symlink escape, malformed inputs, restart recovery, concurrency/FKs and actual uvicorn WebSocket Origin rejection. Tests did not use real external API credentials or a real installed Ollama model.

## Resolved findings

| Severity | File/line at final candidate | Reproduction / expected vs initial actual | Fix and verification |
|---|---|---|---|
| BLOCKER | services/api/requirements.lock:22 | Real uvicorn WS should connect; initial TestClient passed but browser handshake404 and permanent Disconnected | Pinned websockets15.0.1; actual subprocess regression + clean browser reconnect PASS |
| MAJOR | services/api/main.py:170 | Foreign Origin WS should reject; initial socket accepted arbitrary Origin | Explicit localhost origin allowlist; live regression rejects foreign Origin |
| MAJOR | services/api/main.py:111; services/api/policy.py:19 | Invalid agent patch/nested brain types/null model should return4xx; initially500 | Explicit nested types/model validation and ValidationError translation; POST/PATCH regressions PASS |
| MAJOR | services/worker/runtime.py:8 | Malformed edge source[]/mixed label types should reject graph; initially500 | Typed graph validation; regressions PASS |
| MAJOR | services/api/main.py:188 | Bad assignment shape/id[]/out-of-bounds workstation should reject; initially500 or invalid position | Type/bounds checks and regressions PASS |
| MAJOR | services/api/store.py:28 | Process restart should terminate interrupted tasks/agent status and recover trace; initial run-only fail left working task | Failed tasks, agent error and persisted recovery events; restart tests PASS; serialized store access regression PASS |
| MAJOR | apps/web/src/App.tsx:4 | Rapid workspace switches must not display previous workspace doc/memory/response/socket state | Keyed workspace-local tree and stale callback guards; unit test + real rapid-switch PASS |
| MAJOR | apps/web/src/office/OfficeCanvas.tsx:14 | CSS-scaled canvas hit-testing should select intended tile; initial event coords unscaled | CSS/backing normalization; real drag/assignment/reload PASS |
| MINOR | services/api/main.py:14 | Furniture selector bookshelf/sofa should save; initial API unknown-asset rejection | Catalog extended for original assets; backend roundtrip/collision tests PASS |
| MINOR | apps/web/index.html:1 | No console errors; initial favicon404 | Original inline SVG favicon; final browser console [] |
| MINOR | apps/web/src/office/OfficeCanvas.tsx:25; apps/web/src/style.css:2 | Advertised wheel zoom and readable office viewport | Integer wheel zoom, compact office chrome, separate wall labels and original decor; screenshots/pointer tests reviewed |
| MINOR | apps/web/src/AgentForm.tsx:3; apps/web/src/App.tsx:21 | Tools hint/filter/audit should reflect runtime policy; initial mismatched tool names and missing filter/audit view | Correct allowlisted names, agent event filter and policy audit view present |

Initial failures remain in evidence/initial-failures.md and initial-office-failed.png. The integrator's concurrent npm reinstall briefly broke running Vite; that attempt is INVALID and excluded. Clean dependency install and launcher restart preceded final passing run. QA selector mistakes were corrected in tests; they were not reported as application defects.

## Source/reuse review and visual comparison

Read full requirement, particularly8/9/13, AGENTS, API contract, audit/board/attribution, implementation source, manifests, logs/handoffs and root install/dev/Compose/Dockerfiles. Independently verified all seven reference checkout SHAs and top-level licenses: Habblaud/Pixel Agents/basriayaz/claude-office MIT; ChatDev current/legacy Apache; bignutchanon no top-level LICENSE. Third-party sprite/data caveats in audit are retained. No upstream code/images/sprites are included in application; graphics are original procedural primitives with CC0 manifest. Inspiration-only decisions and new-module boundary are documented. No unverified upstream feature is claimed integrated.

Independently viewed pinned Habblaud overview faa1a012b5fbf632c66dc6801c5383e53a542406 and Pixel Agents office b1bafd02896d90d83457266575a1e8e5011ce997. Comparison:

| Reference property | AgentVerse evidence / deliberate deviation |
|---|---|
| Habblaud room zoning, workstation/agent association, roster and event context | Warm work zone + cool lounge, named agents at desks, sidebar workspace/roster and real activity feed. One room per independently selected workspace; no world/city/roads. |
| Pixel Agents top-down furniture grouping and sharp pixel silhouettes | Original tile-floor, desks/monitors/chairs, plants/shelves/sofa and small characters rendered by Pixi; simpler silhouettes and lower art detail, not copied sprite identities. |
| Interactive office and editor | Actual canvas drag, workstation assignment, collision/path checks, pan/zoom/grid and backend layout persistence pass. No screenshot backdrop or animation-generated task completion. |
| Dashboard readability | Intentional light/lavender desktop chrome, distinct from dark references. Six screens and normal vertical page scroll; full room exploration supports pan/zoom. No sidebar overlaps canvas. |

## Screenshot index (all inspected)

Paths below relative repository root. Each links to application candidate826c74c and QA task/session above via this review.

- tests/e2e/evidence/01-office-1366.png — Office/Home workspace picker, actual original seeded room.
- tests/e2e/evidence/02-agent-studio-1366.png and02b-agent-capabilities-1366.png — Role/Brain + Skills/Tools/Memory/Skin details.
- tests/e2e/evidence/03-workflow-1366.png — real React Flow graph saved after node drag.
- tests/e2e/evidence/04-run-monitor-1366.png and04b-run-events-1366.png — actual persisted output, handoff and trace.
- tests/e2e/evidence/05-furniture-1366.png and08-furniture-interaction-1366.png — actual editor/grid and manipulated layout.
- tests/e2e/evidence/06-settings-1366.png — actual provider test/policy view.
- tests/e2e/evidence/07-office-1920.png — larger desktop office.

## Remaining limits / review boundary

No live OpenAI/Ollama account/model validation; deterministic MockBrain visibly labeled, actual execution does not imply generated code was executed. Side-effect tools remain denied with audit; no approval-grant executor. SQLite single-process prototype uses aggregate JSON entities and one-tile furniture footprints. Chunk-size and upstream deprecation warnings remain disclosed. Art is simpler than reference projects; long forms/trace use scrolling and room uses pan/zoom. Security assumes trusted single-user loopback and is not SaaS/public deployment approval. Docker trust/network prerequisites and actual image/proxy results reviewed in docs/VALIDATION.md and docs/evidence/docker-validation.json; optional CA injection preserves TLS verification. Cloud draft is not publication or Git push. Integrator still owns final merge, QA-test review and delivery verification.
