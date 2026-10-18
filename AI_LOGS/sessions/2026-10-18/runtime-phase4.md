# P4 runtime implementation

- timestamp: 2026-10-18; session_id: runtime-phase4; agent_id: p4_runtime; agent_role: Runtime Backend; model/provider: inherited Codex.
- task_id: P4 runtime/tool/review; branch: agent/runtime/P4; worktree: /workspace/worktrees/p2-backend; input: contract1d88bcc merged into clean prior backend branch without reset.
- goal: actual read-tool nodes, durable bounded human rework, observed timing, safe limited parallel reads; preserve all legacy data/APIs.
- plan/actions: inspect full contract/AGENTS; coordinate exact wire fields with FE, QA, Tools and Operations; implement checkpoint-resumable gates and immutable revision outputs; adversarial tests and full backend regression.
- changes: runtime validates tools/grants and ancestor linear rework segments; tool results persisted with binding before checkpoint; replay failclosed for uncertain/failed execution; review gates persist revision/input/allowed decisions and require human decision; revised task/output identities and export filenames never overwrite. Model context labels upstream/tool/source data UNTRUSTED and includes human rework comment. Actual request/tool milliseconds and unknown monetary cost recorded; no fabricated model toolcall.
- parallel semantics: only independent adjacent readonly tool nodes concurrently (up to4); deterministic topological output merge. Agents, mutation actions and human checkpoints remain serialized; no claim of arbitrary parallel agents.
- validation: legacy tests/backend + tests/phase2/runtime + tests/phase3/runtime 61PASS; new tests/phase4/runtime 5PASS before final guards; Ruff relevant checksPASS. Concurrency test uses two-entry barrier so serialized execution would fail; actual dispatcher still executes both reads. Actual SQLite restart, once-only decisions, bounded rework, denial and cancellation used; deterministic brain, not live model.
- risks/limits: source/model quality cannot be proven by deterministic tests; live-provider tests owned QA/root. Only linear agent/tool ancestor segments can rework; branching segments reject instead of silently guessing. Tool interrupted before completed-record commit requires reconciliation/newrun (no implicit replay). Existing provider in-flight crash remains uncertain remote charge. No dependency changes or upstream copied assets.
- sources/reuse: existing LangGraph/persistence/runtime APIs; contract phase4/IMPLEMENTATION.md; existing MIT/OFL assets untouched.
- review status: IN_PROGRESS; own tests before commit, independent QA/root pending. No DONE/selfapproval.

## Core handoff
- validation final:66 combined testsPASS (61 legacy+5firstP4); expanded7P4PASS includes twoactual approved revisionexports with distinctpaths and commentreceived by actualmodeladapter, plus failedtool resume neverreexecutes. Ruff E9/F63/F7/F82 PASS.
- exact APIs: GET runs/{id}/gates returns history+pending; POST gates/{id}/decision exact decision/comment, statusbound, once-only, autoschedule samecheckpoint. Pending uses waiting_approval for backward-compatible active-work locks. Newtasks revisionnode IDs original~review~rN, export stem-review-rN.ext.
- subsequent integration: Data/Operations routers and DATA_TOOLS catalogue require owner handoffs; core commit intentionally does not import unavailable modules. Human approval/render depends FE branchintegration. READY_FOR_REVIEW core, no final approval claim.

## Step-budget correction
- Rework runs are real graph work: count every repeated agent/tool toward max_steps and carry count into later checkpoints/downstream nodes. Prevalidate safe revision export names. New actual max_steps denial regression verifies no extra model task executes after budget denial.
- Validation8P4PASS, including7corecases; first local run during tuple-return refactor caught mismatched return unpack, corrected before commit and reran8PASS. No suppressed tests.
- Additional replay regression9P4PASS: process restart after actual rework reaches revision1 pendinggate; approve afterrestart preserves exact taskrecords and token_spent (no duplicate model request/charge).

## Operations integration
- Cherry-picked owner Operations commits8c939fa/642e293/47adea4 as dependencies only (root already has corresponding commits); mounted create_operations_router(app,start_run,RunInput). Existing main memorycreation validates source sameworkspace + provenance snapshot and GET excludes tombstone. Shared tool readers handled Tools owner.
- Actual15 tests runtime+operations PASS after mount, including queue dispatch through actual Runtime. Router mount commit changes only main+ownlog.

## Inspectable durable tool evidence
- Added GET /api/runs/{id}/tool-results, filtered both workspace and exact run, returning actual persisted result body/provenance plus observed timing. Failed record persists observed duration, no raw potentially sensitive exception text. FE informed of wire shape and JSON envelope.
- Validation9runtimePASS; scoped test injects foreignworkspace record with same run ID and sameworkspace other-run record, verifies only exact owned result is exposed. Actual readtool result classification and duration asserted.

## Revision identity validation
- Explicit base node IDs must not collide with generated revision node IDs; otherwise a malicious/custom graph could reuse cached revision output in a later base node. Reject at graph validation. Additional malformed review targets/revision booleans/out-of-range/tool IDs return400 rather than500.
- Validation10P4PASS. Source/data router integration remains pending Tools handoff, not silently omitted.
