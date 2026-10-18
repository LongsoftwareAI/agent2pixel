# Phase3 Frontend handoff
Owner Frontend (reassigned Bridge), dedicated agent/bridge/P2-05 worktree. READY_FOR_REVIEW, not DONE. Backend contract coordinated with backend agent; root docs/contracts/phase3/IMPLEMENTATION.md.

New /control/#workboard route/nav Công việc. WorkBoard consumes authoritative work items, creates scope/brief/criteria/workflow, edits brief only, starts with backend-generated brief and opens Run Monitor. Review state remains distinct from done; explicit human accept/changes request with comment; linked runs/evidence and review history. API failure visible and no optimistic completion. Workflow link navigates existing graph/templates screen.

WorkflowTemplates GET /api/workflow-templates; roles mapped to existing enabled agents only; creates normal editable workflow, preserves actual instructions/output filename, no role/grant mutation. Explicit supplied-source-only guidance and artifacts.write_text grant warning. WorkflowEditor serializes per-node instructions/deliverable; retains branches/condition controls. All existing screens retained. No new dependencies/artwork.

Checks: `npm --prefix apps/web test` 25 PASS; `npm --prefix apps/web run lint` PASS; `npm --prefix apps/web run build` PASS (largechunk advisory). Initial npm cache path failure corrected using --cache /tmp/agentverse-p3-fe-npm without bypassing integrity. Changes limited apps/web except office + own logs. QA/root own integrated localhost screenshots/review; those remain acceptance prerequisites.

Follow-up: standalone WorkBoard workspace isolation/unmount response guard; delayed list and launch callback regression checks. App was already keyed, so this hardens component reuse and outstanding callback handling. 27 tests PASS, lint PASS; no scope expansion.
