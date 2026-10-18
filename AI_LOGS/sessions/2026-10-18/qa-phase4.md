# Phase 4 independent QA

- timestamp: 2026-10-18T09:00:00Z
- session_id: qa-phase4-20261018
- agent_id / agent_role: resume_harness / independent QA
- task_id: P4-QA
- goal: Independently verify real data tools, source trust boundary, bounded human rework, company queue/evidence/memory operations and localhost UI.
- status: IN_PROGRESS
- branch / base_commit / workspace: agent/qa/P2-08 /1d88bcc dependency sync / /workspace/worktrees/p2-qa
- owned_paths: tests/phase4 excluding runtime/tools/operations; AI_LOGS/reviews/P4-*; own session log. Production read-only.
- inputs: docs/contracts/phase4/IMPLEMENTATION.md, Integrator assignment, prior source77a1db8/evidence.
- assumptions: Native API/tool/model adapter must run for integration; local provider explicitly test-only. Live provider only if Integrator confirms usable credentials.
- constraints: Preserve old data/notices/evidence; no production edits, no selfapproval of prior own Harness tests; no parallel claim without observed overlapping work.
- plan: Establish independent acceptance fixtures and exact calculations; coordinate owner API contracts; sync owned dependency commits; test positive/negative domain/runtime/security paths; real localhost pointer screenshot and production review.
- changes: QA test plan with three real workflows and security/operations/runtime gates. Clean dependency merge1d88bcc completed without overwriting user files.
- decisions: Prioritize meaningful actual results and failclosed boundaries. Distinguish real parser/tool calculations from deterministic provider text; report missing capabilities honestly.
- commands / tests: Initial repository status and phase4 contract inspection; no implementation acceptance run before owner commits available.
- risks: Existing runtime sequential until proven otherwise; optional live credentials/network; API refinements pending owners. No blocker to independent preparation.
- blockers: Integration gates await owner commits.
- next_steps / handoff_to: Coordinate p4_runtime/p4_tools/p4_operations/p4_frontend, then Integrator for independent test review.
- commit_sha: Pending QA source commit.
- review_status: Pending; no approval yet.
- reference_repository/version/license: Existing Habblaud/Harness notices retained unchanged; no new dependency or upstream copied code/art.

Preparation milestone: Actual HTTP acceptance harness prepared for supplied-source research, hostile source grant immutability, real Decimal CSV summary/grouping/missing/formula classification, bounded human rework and post-generation versioned exports. Optional actual API process restart handshake at pending review gate; no false claim restart was run before handshake. Exact API contracts coordinated with Runtime/Tools/Operations owners. Static F checks and Python compilation PASS. Integration execution awaits owner commits.
Recovery independent milestone: `python -m pytest -q tests/phase4/test_recovery_acceptance.py`1PASS0.17s using actual CLI backup/restore, source+provenance+memoryhistory+events/runoutput/checkpoint SQLite+Unicodeartifact bytes and workspacepath relocation, no overwrite. Root3backup tests freshly3PASS. Reviewed backup source with no blocker in explicitly stopped-app bounded localdirectory scope; no hotbackup claim. Synced85c5d22/8c939fa/642e293/47adea4 as dependencies only.
