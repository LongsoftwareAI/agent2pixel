# Phase 3 — company workspace validation

Candidate application77a1db8: backend452763f+978c0f5; frontendffafb98+113ffe0+ae8ae43; officee11cb6a; Harness28a37b5+3b88757. Subsequent docs/tests do not alter application behavior. Independent production verdict **APPROVE** at77a1db8: [P3 final review](../AI_LOGS/reviews/P3-FINAL-review.md). Root independently reviewed QA/Harness tests in [P3 Integrator review](../AI_LOGS/reviews/P3-INT-review.md). Phase2 approval is historical.

## Delivered foundation

- Work board and durable multi-purpose briefs, criteria, workflow/run linkage, versioned edits and human review. Complete run means review; only explicit human acceptance means done. Revised brief requires new evidence.
- Four editable role-mapped templates: research, content, operations and coding review. Existing drag/connect/branch graph retained; each agent node gets its own objective and optional text deliverable. Existing agents/roles/grants are not silently replaced.
- Every assignment gets original brief/criteria, upstream handoff, node instructions and granted source context. Output is generated and persisted before exact-content export approval. Text file bytes/hash/size and node/agent/run provenance are recorded.
- Both native LangChain and official Harness engines support the same noncoding orchestration. Actual Harness plugin premature write is denied; after final generation the orchestrator exports approved content. No arbitrary generated code execution.

## Integrator commands

| Check | Outcome |
|---|---|
| `.venv/bin/python -m pytest tests/backend tests/phase2/runtime tests/phase3/runtime tests/harness tests/projection tests/office_layout -q` | **109 PASS**, no skips; one upstream AnyIO deprecation warning |
| `npm --prefix apps/web test` | **27 PASS** |
| Control lint and production build | PASS, existing ~749kB chunk warning retained |
| Office typecheck, tests, production build | PASS, **10 tests** |
| Selected Python correctness Ruff | PASS final source |
| Actual default launcher restart against preserved data | PASS; same waiting task/output/token_spent across coordinated restart |

Fresh source correction was required after QA found that downstream assignments could miss original brief/criteria when prior output did not repeat them. Original failed evidence is retained. Corrected code adds immutable context every assignment rather than weakening the test.

## Evidence and known limits

Independent [actual HTTP/restart/multi-role evidence](../tests/phase3/evidence/77a1db8/live-acceptance.json), [final pointer browser](../tests/phase3/evidence/77a1db8/review-browser/live-browser.json), [template/flow edit persistence](../tests/phase3/evidence/77a1db8/review-editor/live-editor.json) and [root fresh browser](evidence/phase3/browser/live-browser.json) all PASS. [Migration inventory](evidence/phase3/migration-results.json) preserves129 original resources,19 terminal runs and225 events. Stub-generated output proves orchestration/export/provenance, not factual quality or live model availability. Credentials were checked by presence only and are absent.

Flow is bounded DAG, max32nodes, sequential scheduling of activated branches, one active run per workspace and scheduler concurrency2. It does not yet support arbitrary cycles or unlimited parallel departments. Current tools provide scoped local sources/memory and approved text artifacts; web search, email, spreadsheets, external publishing and arbitrary-code sandbox need additional integrations. A template does not grant these capabilities. Markdown/text/JSON/CSV files are data, not executable actions; JSON/CSV extensions alone do not guarantee schema validity.

Existing development-only npm advisories, Harness selected-binary notice/SBOM limitation and bundle/deprecation warnings from Phase2 remain documented in PHASE_2_VALIDATION.md. No new dependency/artwork copied. Habblaud MIT and font OFL attribution retained; renderer unchanged except office header navigation.

Cloud start instructions updated as a draft, not published or restored in a fresh task. Review/save environment settings and publish through the product to apply that snapshot. Docker Phase3 rebuild not part of these checks; Phase2 container evidence is historical.
