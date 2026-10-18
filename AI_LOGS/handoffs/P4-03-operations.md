# P4-03 Operations handoff

Owner Operations; READY_FOR_REVIEW. Baseline 1d88bcc; no dependencies/new packages/external assets. Files owned: services/api/company.py, services/api/operations.py, tests/phase4/operations, own logs.

Runtime integrator MUST mount `create_operations_router(app, start_run, RunInput)` and exclude memory tombstones in old list/shared tool routes. Memory creation source provenance is runtime-owned. Source resource kind is `source` with top-level sha256.

Implemented explicit enqueue/dequeue/manual dispatch sorted priority/deadline, same-workspace owner validation, observed active task/run load, linked artifact text retrieval with hash/path checks, completed linked-run unified diffs, and human memory content/source edits plus tombstone deletion with retained audit snapshots. Owner is accountability metadata; it does not replace workflow actors. Queue is single local app process, not distributed background scheduler.

Verification: `python -m pytest tests/phase4/operations tests/backend tests/phase3 -q`: 49 PASS. Ruff critical rule check PASS. Independent QA must review implementation and integrated API behavior before approval. No model/provider claim from these tests; all queue/evidence/memory persistence is actual SQLite/file behavior.
