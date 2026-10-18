# Phase 2 independent review

Reviewer: independent QA. Candidate: `01f8f80`. QA did not modify application code. Integrator must independently review QA helpers and evidence.

**Decision: CHANGES_REQUESTED** for the two findings below. Fresh visual comparison passes.

| Severity | Finding | Reproduction |
|---|---|---|
| Medium | Projection puts `usageKnown:false` on the agent, while the drawer reads `a.stats.usageKnown`. Unknown token usage therefore appears as zero instead of N/A. | `live_office_status.py`; retained failed JSON and drawer PNG under `evidence/01f8f80`. |
| Low | Adapted `client/src/ui/drawer.ts` is missing its full path in the vendor patch ledger. MIT notice remains intact. | `audit_vendor.py`: 334 files checked, 15 adapted files, one undeclared path. |

## Independently executed checks

- Visual parity: raw upstream Habblaud versus current fixture, full unmasked canvas at 1366×768 and 1920×1080, **zero differing pixels**, equal PNG hashes, identical camera/DPR/seed/time. No HTTP or browser errors. Fixture evidence does not prove runtime execution.
- Actual localhost: office, Agent Studio, Workflows, Run Monitor and Settings at both sizes, ten screenshots and contact sheets. Live projection and SSE connection are explicit; no demo fallback or browser/HTTP errors.
- Native furniture editor: add, move, reload persistence, delete; collision rejection leaves backend layout unchanged. Native canvas character selection, edit/randomize/save, reload persistence. Original name/appearance restored and test decoration removed.
- Actual execution: fresh LangGraph/SQLite workflow `a09b9794-ef8a-46df-81ce-5da83c1f4693`, three distinct approvals, two file hashes checked against disk, real pytest subprocess with two passes, Reviewer consumes the actual report. One skill activation, one memory read and six completed tool calls. Brain is explicitly deterministic.
- Replay/isolation: exact fresh-run SSE sequence 158–184 equals all 27 persisted events; another workspace receives none. Cross-workspace memory denied, approval reuse returns 409, remote Origin mutation and SSE return 403.
- Failure/cancel: actual Harness missing-key failure remains explicit, with failed task and visible Execution failed badge; a different run cancelled during approval wait appears as cancelled, without fabricated completion.
- Harness: independently reran both official SDK/runtime/Cordis plus shared Store/LangGraph integration variants: **2 passed**, 8.93 seconds. Only the provider is a local stub. Own memory/document reads and previously approved pytest retrieval succeed; traversal, changed test payload and foreign memory scope fail without extra artifacts.
- Migration: direct read-only inventory verifies all original 63 resources, 11 terminal runs and 116 events retain IDs, ownership and terminal history/event hashes; new records are additive.

## Scope and limitations

Reviewed coding actions support fixed, reviewed calculator templates. LangGraph commits approved native writes/tests before the Harness turn; Harness retrieves those results. Model-originated new code writes and arbitrary authored coding are not implemented. No live DeepSeek/OpenAI inference is validated. Real SDK/runtime integration with a local provider stub and deterministic native Brain evidence are separate categories.

Integrator reports 88 Python checks, 10 office checks and 17 control checks passing; these are not presented as independently rerun by QA. QA independently ran the specific browser, API, migration, parity and two Harness integration checks above.

Evidence: `tests/phase2/evidence/01f8f80/`, with earlier live API evidence in `tests/phase2/evidence/final/`. Existing failures are retained; no threshold was relaxed or test suppressed.
