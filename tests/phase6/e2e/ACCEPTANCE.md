# Phase 6 independent system acceptance

Target: application e9f5465756ad1ed6607d2fc8c032ef3387c43812; baseline checkout25df32e. All current-run outcomes below start **UNRUN**. Historical Phase5 PASS is regression context only. Root's current manifest must supply exact command, target SHA, exit code, counts, duration, artifact paths/hashes and provider mode; update verdicts only from that evidence. FAIL means observed failing assertion; unavailable/unsupported/unconfigured behavior stays UNRUN with explicit scope limitation. A requirement may have passing checks and unresolved subrequirements.

| ID | Required positive checks | Required failure checks | Current |
|---|---|---|---|
| P5-01 |18 routes/deep links, history, keyboard palette/sidebar;1108/1366/1920 screenshots and dimensions/hash/nonblank/manual inspection |disconnect/retry; API failures explicit; keyboard focus |UNRUN|
| P5-02 |overview counts reconcile actual workspace records |unknown remote billing/services remain unknown |UNRUN|
| P5-03 |payload approval, QC gate, human acceptance distinct |stale/duplicate denial; rejection reason persisted |UNRUN|
| P5-04 |room→durable message/work/run; lifecycle replay |idempotent same payload; changed payload409; cancel/reconnect/restart IDs |UNRUN|
| P5-05 |A→B selection reaches correct agent adapter and history |foreign room/agent denied; concurrent run context immutable |UNRUN|
| P5-06 |SOUL/config history/diff/rollback and future prompt binding |stale409; invalid/foreign rollback rejected |UNRUN|
| P5-07 |queue→dispatch→rework→QC→accept→archive/search; retained history |overlap/stale review/active archive guards; bounded rework |UNRUN|
| P5-08 |actual CSV Decimal calculations→artifact/hash→review; editable graph |changed/foreign source; denied tools; approval binds exact payload |UNRUN|
| P5-09 |monitor true observations or explicit unconfigured state |no invented next run or unsupported cron CRUD |UNRUN|
| P5-10 |reviewed local declarative package lifecycle and audit |expired/replayed/stale preview; escalation/executable installer denied |UNRUN|
| P5-11 |memory scope/history/tombstone/provenance; legacy writer compatibility |persisted lost-update/delete conflict; foreign writes denied |UNRUN|
| P5-12 |actual adapter/services; secret names/status only |missing config cannot be healthy; no credential values in evidence |UNRUN|
| P5-13 |actual registry search/zoom/fit/details/rearrange |layout does not grant tools; disconnected topology stale |UNRUN|
| P5-14 |usage period/provider versus estimated provenance; revision budget alerts |invalid periods/budgets; stale update after reopen; unknown actual cost |UNRUN|
| P5-15 |run-derived sessions/correlation links |foreign session/message/artifact not disclosed |UNRUN|
| P5-16 |distinct diagnostic/audit; bounded export/download |bad cursor/limit; redaction; unsupported filters remain gap |UNRUN|
| P5-17 |preferences persist reload/reopen; light/dark/system; refresh-off lifecycle |stale panel writes409; invalid values422; contrast/manual browser |UNRUN|
| P5-18 |actual Habblaud renderer+agent bridge+notices; migrated IDs |lazy disabled office; old data retained; real container separately |UNRUN|
| P5-19 |actual bounded text/CSV/Markdown/PNG hashes/decoded preview; voice draft |foreign preview/oversize/path/invalid media denied; live STT separate |UNRUN|

## Company work and recovery scenarios

| Scenario | Required observed result | Evidence source | Current |
|---|---|---|---|
| Finance analyst |CSV values actually executed with Decimal; exact totals and named source in artifact; explicit human accept |phase5 console_acceptance; phase4 live_acceptance and data tools tests |UNRUN|
| Research/operations |read approved local documents, preserve source citations; no invented external facts |phase3/4 runtime+tools+operations suites; current root live scenario |UNRUN|
| Writing/content |actual text artifact with task constraints; review/rework changes revision; acceptance separately recorded |phase3 runtime+phase4 operations; live source/artifact comparison |UNRUN|
| Software work |Harness compatibility, real denied/allowed tools, generated artifact tests; side effects require approval |tests/harness and phase2 runtime suites |UNRUN|
| Multi-agent isolation |parallel workspaces/agents don't share private memory/grants/source records |backend/runtime/harness suites; bot-switch browser |UNRUN|
| Persisted panel recovery |memory legacy edit invalidates old CAS across reopen; budget+preferences stale panels409; reload/retry retains values |new test_revision_reopen.py (app reopen only) |UNRUN|
| Actual process recovery |stop/restart isolated stack between prepare/verify; exact durable message/run/work/gate IDs and hashes; dedupe; resume QC/accept |phase5 restart_probe two commands + root process log |UNRUN|
| Backup/disaster recovery |stopped-source backup+restore file hashes/IDs and relocated roots; WAL/symlink guards |tests/backup plus actual stopped backup manifest |UNRUN|
| Provider failure/recovery |timeout/invalid response/rate-limit/cancel transitions honest; no completion synthesized |backend/runtime/provider tests; live failures separately labeled |UNRUN|
| Security boundary |path traversal/symlink/foreign IDs denied; tool permissions immutable; malicious source treated as data |backend/tools/harness/security tests |UNRUN|

## Root runner and live review gates

- Preserve each child command's exit status. No `|| true`, assertion removal, retry-until-pass, missing-count success, stale result reuse or renamed old screenshots. Record failed attempts separately.
- Execute existing test sources directly, with current counts/skips. Do not copy old tests into wrappers or count skipped Harness tests as passing. Official Harness unavailable means compatibility UNRUN.
- Identify application source SHA separately from evidence-only commits. Hash unchanged dependency locks and images if reusing cache; cache is not fresh install/container acceptance.
- Live inference must identify the actual provider/model and run IDs. A provider200 or fluent text alone does not prove company task success. Assert required semantic facts against actual tool source, exact computed numbers, artifact hash/content and task constraints. Distinguish inference, tool execution, workflow completion and human acceptance.
- Keep credentials in runtime environment only; never CLI arguments, JSON manifests, fixtures, reports, Git or provider request dumps. Do not pass secrets to QA. Redact sensitive exception bodies/headers before writing evidence. Scan tracked changes and generated evidence for credential-shaped strings before commit, without printing matches.
- Provider inference does not establish live speech, vision/OCR, public web, external sending, billing, scheduling or universal task execution. Retain unsupported/partial parity gaps from Phase5.
- Screen file existence/hash is integrity evidence. Independent image inspection and actual interactions remain separate checks. Review all expected screen entries and dimensions, no selected subset advertised as54 screens.

Run new regression with the same tested backend interpreter from repository root:

```sh
.venv/bin/python -m pytest tests/phase6/e2e/test_revision_reopen.py -q
```

No dependencies added. This new case verifies persisted cross-panel conflict handling and legacy/new client interoperability; it does not claim an actual subprocess restart or simultaneous process lock safety.
