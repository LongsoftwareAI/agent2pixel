# P4-03 Company operations

- Task / owner: P4-03, Operations Agent; branch agent/operations/P4-03, dedicated /workspace/worktrees/p2-harness.
- Authorization: Phase 4 user instruction; docs/contracts/phase4/IMPLEMENTATION.md at 1d88bcc; AGENTS.md one-writer protocol.
- Scope: company brief metadata, manual work queue, observed workload, verified artifact retrieval/comparison, memory edit/delete provenance history. No external actions, automatic dispatcher, provider claims, or new dependencies.
- Inputs / references: existing company/store/tool artifact schema, Phase 4 contract. No new copied external source/assets.
- Decisions: dispatch uses shared Store RLock and existing start_run atomic linked persistence; queued item removed only with successfully linked run. Priority then timezone-aware deadline then deterministic creation/id order. Owner indicates accountability, does not silently change workflow actors.
- Evidence handling: UTF-8 artifact content limited 1MiB, linked run directory, no symlink/traversal, SHA256+size integrity checked; comparisons require completed linked same-workspace runs. Human memory edits store before snapshots and provenance hash; deletion is audited tombstone, requires reader filtering by other owners.
- Coordination: Runtime mounts operations router and handles memory creation/list tombstones; Tools source kind source and excludes tombstones; FE and independent QA received wire schemas.
- Validation: 4 focused tests passed (actual SQLite persistence, two simultaneous dispatches, priority/deadline/foreign owner, artifact corruption/symlink/foreign comparison, memory provenance+history+tombstone). Ruff critical checks passed. Broader baseline backend/Phase 3 regression pending at writing.
- Status: IN_PROGRESS -> SELF_TESTED for focused scope; independent review required, no self-approval.
- Risks / limitations: manual dispatch only, owner field does not reschedule workflow actors; no advertised background dispatch or cross-process multi-instance queue support.
- Milestone: focused operations + baseline backend + Phase 3: 49 passed in 18.55s, one upstream Starlette deprecation warning; no failures suppressed.
- Follow-up self-review: dispatch endpoint now async wrapper with synchronous locked mutation, matching real Runtime.schedule event-loop requirement. Added regression assertion that launcher executes on running API asyncio loop; 4 focused tests PASS. Initial synchronous-route implementation could schedule in worker thread; corrected before integration acceptance.
- Integrator review follow-up: real create_app + actual LangGraph Runtime dispatch integration now completes workflow and item enters review; no mocked launcher in this smoke. Added strict create metadata booleans/ISO strings and epoch-zero deadline ordering regression. 6 focused tests PASS; critical Ruff PASS. Async scheduling issue independently identified by integrator too; addressed before acceptance.
