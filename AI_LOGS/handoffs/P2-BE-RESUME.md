# P2 Backend resumed handoff

Status: READY_FOR_REVIEW (independent approval pending)
Owner: resume_backend, branch agent/backend/P2-03, worktree /workspace/worktrees/p2-backend
Base: ecb8e3c (root integrated equivalent299570f). Handoff SHA: commit containing this file.

Changes: nested config422 validation, stricter localhost Origin, remote dynamic schema references denied; shared broker result identity binding; exhausted budgets stop further provider attempts. No dependency changes or another owner's source edits.

Executed validation: `/workspace/agent2pixel/.venv/bin/python -m pytest tests/backend tests/phase2/runtime -q`: **43 passed**, one upstream Starlette deprecation warning. `ruff check --select F` selected changed owned Python: PASS. Six additional tests cover malicious nested input, malformed Origin, approval tamper, restart without repeated actions, token exhaustion retry prevention, v1 migration/backup integrity.

Integration: cherry-pick after baseline runtime. API signatures and catalog unchanged. office_projection.py is untracked root-provided fixture here, untouched/uncommitted. Harness owner should maintain `dispatch_tool(store,run,agent,tool_id,payload)` signature.

Limitations: no live model credentials exercised; no visual evidence claimed by backend; deterministic template calculator is the only writable Python action; consume-before-write crash fails closed and needs reconciliation. Independent reviewer approval required before DONE.
