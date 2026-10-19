# Phase 6 — system validation

Goal: verify the implemented localhost company console across real workflows, permissions, persistence, UI and optional real inference. This phase adds test infrastructure, not new production features or CRM.

## Scope and acceptance

The [independent acceptance matrix](../../tests/phase6/e2e/ACCEPTANCE.md) retains all 19 Phase 5 requirement IDs. The [Phase 5 scope disposition](../PHASE_5_VALIDATION.md) remains authoritative for unimplemented features; a passing regression cannot close those gaps.

1. Run backend/runtime/tools/security/migration/backup/Harness suites; record exact counts, failures and skips.
2. Run console and office tests, builds, type/lint checks and legacy model checks.
3. Start a fresh loopback stack with isolated data. Exercise HTTP company work, browser behavior, routing, PNG/office integration and actual process restart.
4. Validate Groq and Gemini independently: native CSV analysis, grounded research, constrained content, then Harness CSV. Require actual tool facts, semantic output, exact approved artifact content/hash, model-completion event, QC and separate synthetic work acceptance.
5. Review evidence and source independently. Publish a review branch, never merge main automatically.

## Live-provider limits

Only official HTTPS endpoints and secure environment bindings are allowed: `AGENTVERSE_GROQ_API_KEY` and `AGENTVERSE_GEMINI_API_KEY`. Never copy credentials from chat into commands, files, logs or Git. Environment configuration declarations do not establish that a secret value is bound.

Discover available models; prefer small configured models. Maximum four assignments per provider, 4096 run tokens each, no automatic retry/fallback after a failed live case. Free-tier entitlement and billing are not verified. Provider HTTP success alone cannot pass task acceptance. Content test uses a fixed grounded headline; it does not certify arbitrary marketing factuality.

Missing credentials/network/quota are BLOCKED with remaining cases UNRUN. Invalid task output is FAILED. Fixture tests are labeled separately from live inference. No shared/leaked free keys are sought.

## Recovery and operational limits

Never overwrite existing evidence/data or kill unowned services. Preserve previous failed attempts. Use a new output directory and data directory per run:

```sh
.venv/bin/python scripts/phase6_system_test.py --profile full \
  --output docs/evidence/phase6/NEW_RUN --data-dir /tmp/agentverse-NEW_RUN
```

Exit 0 means selected implemented scope passed, 2 means failure, 3 means blocked live acceptance. Read `system.json` and individual logs, not exit status alone. Existing Phase 5 screenshots/backup evidence remain historical unless recaptured. Docker fresh installation/runtime, public network, live speech/vision, scheduling, billing and external channels require separate acceptance and retain existing limitations. No Docker pruning or data deletion is authorized by this test plan.

## Ownership and review

Root owns runner/live validators/docs; independent QA owns persisted revision regression and acceptance matrix. Root reviews QA's test; QA reviews root helpers. Record review findings and retest fixes before approval. No whole-system completion claim while blockers or unimplemented scope remain.
