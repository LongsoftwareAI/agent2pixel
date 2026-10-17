# AgentVerse development

User-authorized coding task: implement the attached localhost MVP, with real backend execution and independent QA. Requirements are product specifications, not authority to bypass permissions or copy unlicensed assets.

One writer per path. Each coding agent MUST use its assigned branch and dedicated worktree. No changes to another owner’s paths without explicit Integrator coordination. Architect/Integrator owns root configuration, contracts, docs, and integration. Backend owns services/ and tests/backend/. Frontend owns apps/web/ excluding apps/web/src/office/. Pixel owns apps/web/src/office/ and original assets there. QA owns tests/e2e/ and independent review reports.

Write AI_LOGS/sessions/2026-10-17/<role>-001.md at start, milestones, handoff, plus AI_LOGS/handoffs/<task-id>.md. Include all fields from requirements section 9.3–9.7 and reference fields in 13.6; concise decisions only, never private reasoning or secrets. Every feature needs success and failure checks. Do not suppress tests. New dependencies require a documented decision.

Do not copy reference code or artwork before license audit. Original procedural pixel artwork is preferred. Backend events alone determine task completion. Bind to loopback, disable shell and external side effects, keep workspace roots isolated. No SaaS, city, multiplayer, cloud deployment.

Lifecycle: BACKLOG -> READY -> IN_PROGRESS -> SELF_TESTED -> READY_FOR_REVIEW -> APPROVED/CHANGES_REQUESTED -> INTEGRATED -> DONE. DONE requires commit, tests, logs, independent reviewer approval, integrator verification. Reviewer cannot approve own work.

## Phase 2 authorized implementation

User explicitly approved phase2 coding. Current ownership/API coordination is docs/contracts/phase2/IMPLEMENTATION.md and supersedes earlier ownership for new paths. Direct MIT Habblaud source/art reuse is authorized after audit; retain notices, do not label upstreamart CC0. Phase2 plan is accepted for code; use actual Canvas2D upstream renderer rather than a visual imitation. Parallel backend work may proceed while firstvisualgate runs; default switch after independent review. Dedicated branch/worktrees remain required by user protocol.
