# Phase 5 independent implementation review

Status: CHANGES_REQUESTED (interim source review; final acceptance pending).

Reviewer: p5_independent_review. Production read-only; QA owns acceptance scripts/evidence only. Reviewed production at `bb9d07fdc1be690c681486d27c4cb2cb730bbaad`; uncommitted root launcher/config changes are not pinned evidence.

## Findings requiring correction

1. **MAJOR — P5-16, log export always fails.** `ConsoleOperations.tsx` requests `limit=500` while `console_extensions.py` permits only 1–200. Actual UI download must be exercised against the backend, including workspace/redaction assertions.
2. **MAJOR — P5-06, configuration rollback uses a stale revision.** Config-tab `RevisionHistory` receives no current revision, then infers current from latest historical revision. Backend history contains prior snapshots only, so rollback sends current−1 and receives409. Both config and SOUL current-side diffs use the historical list to find the current record, producing an empty current comparison. SOUL save does not trigger history reload because currentRevision is absent from effect dependencies. Existing mocked fixture incorrectly includes the current record in history.
3. **MAJOR — P5-05, changing the direct-chat bot selector retains the previous conversation binding.** After selecting another bot, the UI displays the new bot but submits the old selected conversation; server correctly runs the original conversation agent. Clear/rebind conversation or lock the selector to the immutable conversation target.
4. **MAJOR — P5-14, estimated token provenance is discarded.** Runtime events distinguish estimated tokens from provider-reported totals. Console aggregation drops this distinction and describes all totals as runtime-recorded usage. Preserve and display accounting provenance in usage/budget projections; unknown cost handling is already correct.
5. **MINOR — P5-14, threshold validation copy diverges.** Frontend accepts zero as nonnegative but backend requires positive values. Align validation/message or intentionally model zero semantics.

## Source review observations

Durable chat dispatch atomically commits message/work/run through put_many before scheduling. Idempotency keys bind the exact payload. Agent/runtime snapshots remain immutable; SOUL/skill edits affect future runs only. Scoped conversation/attachment resolution, exact skill manifest approval with stale-binding checks, code-owned declarative skills, and log allowlist projection are present. No production files were edited by this reviewer.

These observations are not a final security certification or runtime acceptance. Final independent review must pin the corrected integrated SHA and reference actual HTTP, browser, restart and manually inspected screenshot evidence. Live provider/STT/image/scheduler capabilities must remain OPEN/UNRUN when unavailable; UI screenshots cannot establish those capabilities.
