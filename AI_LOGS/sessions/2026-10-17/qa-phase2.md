# P2-08 independent QA

timestamp: 2026-10-17T00:00:00Z
session_id: qa-phase2
agent_id: p2_qa
agent_role: independent QA/reviewer
model/provider: Codex host-provided
task_id: P2-08
goal: independently review pinned Phase2 source, Habblaud visual parity, real execution and failure controls
status: IN_PROGRESS
branch: agent/qa/P2-08
base_commit: 6d5d1fe
workspace: /workspace/worktrees/p2-qa
owned_paths: tests/phase2/ except runtime/; AI_LOGS/reviews/P2-*; own session/handoff
inputs: AGENTS.md; docs/contracts/phase2/IMPLEMENTATION.md; complete Phase2 plan; requirements sections8/9/13
assumptions: external provider key may be unavailable; actual Harness runtime with stub is distinct from live-model evidence
constraints: read-only app review; never approve own tests; existing system Chromium; no secrets/raw reasoning in evidence
plan: establish acceptance matrix; independently hash upstream provenance; capture deterministic upstream/app visual parity; exercise actual browser and sandbox workflow; review source and pin verdict SHA
changes: tests/phase2/TEST_PLAN.md; own session
commands: read instructions/plan/requirements; inspect reference checkout and prior browser helper
Tests: preparation only; app validation UNRUN pending implementation handoff
risks: source/runtime in progress, no visual or execution verdict yet
blockers: awaiting implementation handoff
next_steps: coordinate fixture API with Pixel and runtime endpoints with Backend
handoff_to: Integrator
commit_sha: pending
review_status: PENDING
Reference IDs: REF-01; DeepSeek Harness
Source URL: https://github.com/marmottajr/habblaud; https://github.com/deepseek-ai/deepseek-harness
Commit SHA: Habblaud faa1a012b5fbf632c66dc6801c5383e53a542406; Harness687f282e8625c6b8d11ff58211a90524be2e4317
Files inspected: plan/contracts/requirements; prior QA browser helper
Asset rights: QA copies no assets; inspect MIT notices/provenance on vendor handoff
Copied/Adapted/Inspiration-only: no application changes; test-only source comparisons
Visual evidence: UNRUN
Deviation from reference: pending independent capture
Reviewer decision: PENDING

## Comparator preparation milestone
- Added strict zero-tolerance visual comparator/contact-sheet writer with SHA256 input evidence and exact dimensions. No masks or adjustable threshold. Its regression checks reject one-pixel deltas and viewport mismatch.
- PASS `python tests/phase2/test_compare_visual.py`:2 checks using existing host Pillow12.3.0. No dependency installed.
- Initial `/workspace/agent2pixel/.venv/bin/python -m pytest ...` collection FAIL: that venv lacks Pillow. Host Python has Pillow but lacks pytest; helper regression uses standard-library unittest to avoid changing shared dependencies.
- Application visual gate remains UNRUN; comparator tests are test-tool validation only. Integrator must review QA code separately.

## First independent visual milestone
- Candidate Pixel commit b9892de961d92671752e28bea2f95cbed402d3b5, upstream faa1a012b5fbf632c66dc6801c5383e53a542406. Raw upstream host3102 imports original checkout, candidate3103 imports vendor. Source/assets fixture only, no backend claim.
- PASS `python tests/phase2/capture_visual.py`: fullcanvas0pixel difference1366x768 and1920x1080, no masks, threshold0, exactcamera/insets and cleanHTTP/page errors. Contactsheet+upstream/app/fullpage PNG and JSON evidence saved. First capture with global seeded RNG differed only172/415px exteriorcar because UI consumes randomness differently; fixed global entropy to0.5 equally on both hosts while room/character seeded RNG unchanged, no threshold relaxation.
- Actual canvas character hit, zoom and pan function; browsercleanHTTP gate FAIL `/api/dictation`404 and fixture `/api/agents/agent-0`404; sent Pixel for unsupported endpoint gating. First interaction interrupted by HMR; stable rerun identified HTTP issue.
- Provenance independent audit334 upstream+currentfileSHA256 andMITnotice match; FAIL2 patchledger paths abbreviated (world/index.ts andworld/sim/sim.ts); requested fullpath enumeration.
- Frontend staticreview found responsibilities textarea splits literal backslash+n instead of newlines; owner correcting. Livebrowser pending integration.
- No application APPROVE yet. Integrator reviews QA test code separately.

## Corrected incremental checkpoint
- Candidate5006e2e: provenance audit PASS334files,14 modifiedpaths ledger complete; MIT notice unchanged.
- `python tests/phase2/office_interaction.py` PASS actualcanvas selection/zoom/pan, noHTTP/pageerrors after owner fixes. Fixture-only evidence labeled.
- Initial visual checkpoint scoped APPROVE permits backend integration; finalacceptance pending furniture/appearance/runtime/control/safety/migration checks. Review report names source pin and limits.
- Removed accidentally staged/generated reference/.vite cache and added ignoredcache rule; no application files modified.

## Review correction
- Frontend responsibilities textarea concern was a false positive from escaped tool JSON rendering. Independent raw-byte check confirms delimiter [39,92,110,39], valid JS newline; no application fix needed. Owner added multiline regression cc2d84d. Earlier concern withdrawn.

## Resumed independent QA 2026-10-18
- Task P2-08 remains READY_FOR_REVIEW only for prior visual checkpoint; final Phase2 acceptance pending integrated source SHA and live stack. Role QA; branch agent/qa/P2-08; ownership tests/phase2 except runtime and independent review logs.
- Added live localhost browser capture runner for actual office + Agent Studio/Workflows/Runs/Settings at1366/1920, recording source SHA, nonfixture projection metadata, room/agent counts, HTTP/page errors. Screenshots do not assert model execution.
- PASS comparator regressions2 using host Python. No application code modified, no dependency changes, no assets copied. Existing evidence preserved.
- Handoff Integrator: review QA runner separately; live acceptance UNRUN until startup handoff. Reference remains Habblaud MIT pinned faa1a012 and Harness pin per original log. Visual deviations/final decision pending captures.

## Live release milestone c4933ac (intermediate before furniture integration)
- PASS actual office+four control screens at1366/1920, ten PNGs and contactsheets; no pageerrors/HTTPfailures. Fixturefalse/meta.demofalse and original v1 Coding/Research+existing QA workspaces. Initial state JSON connection was read before wait although screenshot visiblyConnected; final runner now requires connectionopen.
- PASS independent realHTTP LangGraph sandbox workflow a09b9794: Planner memory.read1, Reviewer skillactivation1, tools6, three payloadapprovals, two artifactSHA256 verified against actual files, pytest2passed and Reviewer actualreport. Deterministic Brain is explicitly labeled, no live model inference claim.
- SSE exact fresh run158..184 equals persisted27events; other workspace hasnone. Memorycrossworkspace403, usedapproval409 and remoteOriginPOST/SSE403.
- Earlier e1626a63 run memorycount0 retained honestly; strengthened plannergrant proves actualmemorycall. First helper expected422 but legitimate403 denial; corrected to accept either deniedHTTP result, not relaxed any successfulaccess.
- v1 migration evidence supplied by Integrator copied unchanged:63resources/11terminalruns/116events retain IDs/ownership/historysha. Additive6registryrecords. QA direct readonly verification next final.
- Final review PENDING latest furniture/harness and owner adversarial corrections. QA code requires independent Integrator review.

## Independent latest-source checkpoint01f8f80
- PASS livebrowser10captures actualoffice/control at1366/1920 with explicitSSEconnectionopen and noHTTP/pageerrors.
- PASS nativeUI furniture add/move/reload/delete; collision rejected withoutservermutation. PASS actualcanvascharacterhit+name/randomize/save/reload; restored originalname/appearance and removed testdecoration afterward.
- PASS officialHarness integration2variants independently using rootvenv:8.93s. ActualSDK/runtime/Cordis+Store+LangGraph; localstubprovideronly. Toolbridge reads ownscopedmemory/documents and retrieves previouslyapprovedpytest result; deniedtraversal/mutatedtestpayload/foreignmemory cannotwrite. Doesnot prove modeloriginarbitrarycoding.
- PASS QA directreadonly migrationverify old63resources/11terminalruns/116events untouched; new115resources/15terminalruns/201events additive.
- CHANGES_REQUESTED MEDIUM: stats unknownusageflag is onagent whereasdrawerrendersa.stats.usageKnown. ActualfailedHarness missingkeyrun d37269bb drawerExecutionfailed visible; N/Anotvisible andfake0tokenvalues. Reported rootprojectionowner; originalfailureJSON/screenshots retained.
- CHANGES_REQUESTED LOW provenanceaudit334files modified15: newclient/src/ui/drawer.ts notdeclaredPATCHESledger. SentPixelownerforcorrection.
- Actualcancel55e9118d fromwaitingapproval appearscancelledtask, no inventedcompletion. Providersecretfailure neverfallbackmock.
- Freshunmaskedupstreamparityrunning; finaldecisionpendingtwofixesandparity. QAcode still requires Integrator review.
