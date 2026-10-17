# Backend P2-03/P2-04
Status: IN_PROGRESS
Owner: Backend Domain + Runtime
Task: P2-03, P2-04
Branch: agent/backend/P2-03
Owned paths: services/api except office_projection.py; services/worker except executors/harness; tests/backend; tests/phase2/runtime
Goal: preserve IDs/v1 and execute rich agent specs with LangGraph durable scheduler and approved deterministic tools.
Inputs: docs/contracts/phase2/IMPLEMENTATION.md; docs/plans/PHASE_2_HABBLAUD_RUNTIME.md; baseline 6d5d1fe.
Reuse: existing API/store/policy; new framework dependencies pinned after install compatibility check. Habblaud artwork not handled here.
Decisions: one LangGraph team scheduler; SQLite checkpoint separate from domain SQLite. Explicit no implicit engine fallback. Skills inject instructions, grants remain separate. No arbitrary model code/shell.
Tests: pending implementation.
Risks: preview Harness capabilities must fail closed; checkpoint/domain reconciliation must skip committed tasks/actions.
Review: independent review required, never self approved.
Handoff: pending.

## Milestone — native durable execution
- timestamp: 2026-10-17T22:00:00Z
- session_id: backend-phase2
- agent_id: p2_backend
- agent_role: Backend Domain + Runtime
- model/provider: Codex (inherited)
- task_id: P2-03/P2-04
- base_commit: 6d5d1fe
- workspace: /workspace/worktrees/p2-backend
- assumptions: localhost single-user; existing data IDs must remain; no arbitrary Python execution.
- constraints: dedicated owned paths; root office_projection.py copied only for testing, not committed by backend.
- plan: deliver versioned domain; actual LangGraph SQLite checkpoint/interrupt; approved fixed-template write/test; shared broker; independent QA.
- changes: domain.py rich config/registry; main.py catalog, CRUD, approvals; store.py schema2 online backup and resource identity invariant; runtime.py actual StateGraph and LangChain runnable pipeline; tools.py bounded template artifacts/pytest and shared broker; policy/adapters.py DeepSeek OpenAI-compatible provider.
- decisions: LangGraph1.2.16/LangChain1.4.6/checkpoint-sqlite3.1.2 are compatible installed releases; jsonschema4.26.0 validates role output locally with no remote refs; official Harness SDK/runtime0.1.5rc1 same pair, Pydantic2.14.1 compatible. Lock frozen from isolated venv, no TLS/checksum bypass.
- commands: python -m venv /tmp/agentverse-p2-backend-venv; pip install pinned requirements; python -m pytest tests/backend tests/phase2/runtime -q; ruff check --select F.
- tests: 37 passed before default Reviewer read-only tool enablement; focused artifact integration uses actual pytest2 passed, three sequential approval interrupts, restart-pause and denial. Final rerun pending next commit.
- risks: artifact tool only reviewed calculator templates; provider live secret unavailable, external smoke UNRUN; official Harness plugin integration separate owner. Schema2 rollback must preserve new data; backup pre-schema-v2.sqlite3 is recovery snapshot, not auto rollback.
- blockers: none for native integration; independent review pending.
- next_steps: handoff usable commit; expand tamper/restart/migration tests and integrate Harness bridge.
- handoff_to: Architect/Integrator and QA
- commit_sha: see commit containing this milestone
- review_status: READY_FOR_REVIEW (not approved)
- Reference IDs: plan P2-03/P2-04, LangGraph/LangChain Python distributions.
- Source URL: https://pypi.org/project/langgraph/1.2.16/ ; https://pypi.org/project/langchain/1.4.6/ ; https://github.com/deepseek-ai/deepseek-harness
- Commit SHA: baseline6d5d1fe; Harness source687f282e8625c6b8d11ff58211a90524be2e4317 via separate owner's audit.
- Files inspected: all existing services/api and services/worker, tests/backend, phase2 plan/contracts, requirements sections9/13.
- Asset rights: no artwork copied in backend; third-party framework licenses remain dependency metadata.
- Copied/Adapted/Inspiration-only: adapted existing local API/store; imported installed LangGraph/LangChain public APIs; no upstream source copied.
- Visual evidence: owned by Pixel/QA, not claimed here.
- Deviation from reference: Python runtime intentionally replaces upstream transcript-watching Node backend.
- Reviewer decision: pending independent QA.
