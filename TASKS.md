# AgentVerse task board

All tasks use requirements v0.1 and docs/contracts/API.md. One active writer per owned path. Root Integrator explicitly approves separate worktrees for this user-requested multi-agent development.

| ID | Owner | Branch/worktree | Owned paths | Dependencies | Acceptance | Status |
|---|---|---|---|---|---|---|
| REF-001 | Research agents / Architect | research outside checkout | docs/reuse/, docs/references/ (root writes) | none | six repositories + legacy exact commits, code/assets rights, actual images inspected | DONE |
| ARCH-001 | Architect/Integrator | work /workspace/agent2pixel | root config, docs/, AI_LOGS root and decisions | REF-001 before code | contracts, ADR, ownership, audit before implementation | DONE |
| BE-001 | Backend | agent/backend/BE-001 /workspace/worktrees/backend | services/, tests/backend/, own logs/handoff | ARCH-001 | CRUD, persistence, DAG worker, adapters, safety, replay, success+failure tests | DONE |
| FE-001 | Frontend | agent/frontend/FE-001 /workspace/worktrees/frontend | apps/web/ except src/office/, own logs/handoff | ARCH-001, API contract | usable six screens, editor, persisted integration, no console errors | DONE |
| PIX-001 | Pixel/Game | agent/pixel/PIX-001 /workspace/worktrees/pixel | apps/web/src/office/, own logs/handoff | REF-001, API contract | original Pixi office, states, pan/zoom, collision, placement | DONE |
| QA-001 | QA/Reviewer | agent/qa/QA-001 /workspace/worktrees/qa | tests/e2e/, own logs, AI_LOGS/reviews/ | implementation handoff | independent tests, screenshots each screen 1366x768, interactions, security review pinned SHAs | DONE |
| INT-001 | Integrator | work /workspace/agent2pixel | root files, integration | QA approval | merge approved commits, clean install, test+screenshots evidence, release notes | DONE |

Cross-module changes require a coordination note and Integrator approval. Shared API changes require Architect approval and updating this contract before code. No agent approves own implementation. No DONE until independent review + integration evidence.

## Final acceptance and integration

All rows above passed their lifecycle gates; candidate cherry-picks were provisional until review. Independent application approval: `AI_LOGS/reviews/QA-001-review.md`, candidate `826c74c311023e62f42df8455171e8bdffeb4ed0`. Final backend original7b8189b, frontend6d82221, pixel47361bc; root integration includes their full preceding owned commits. QA contribution original944f472→470b438→0d0e137 was reviewed separately by Integrator; last commit strengthens actual new-run WebSocket replay, not old completion matching.

Integrator independently ran locked installation,29Python+9frontend+4pixel checks, lint/type/build, actual Docker web-proxy7checks and final tightened browser7interactions; screenshots10 hashes/dimensions verified. No app source changed after approved candidate; subsequent commits contain tests/evidence/docs. Full evidence: docs/VALIDATION.md and docs/evidence/.

## Phase 2 — proposed, not implemented

User requests Habblaud-equivalent visuals and clarifies DeepSeekHarness plug-and-play runtime. Complete plan/owner/branch/path/dependency/acceptance table: [PHASE_2_HABBLAUD_RUNTIME.md](docs/plans/PHASE_2_HABBLAUD_RUNTIME.md). Existing DONE rows apply to v0.1 only.

| Task | Owner | State |
|---|---|---|
| PLAN-P2 | Architect root | READY_FOR_REVIEW (documents only) |
| P2-00 source/license/reference baseline | Architect/Research | BACKLOG |
| P2-01 upstream Habblaud graphics/UI adoption | Pixel/Game | BACKLOG |
| P2-02 official HarnessSDK/plugin/cancel/policy spike | Harness Integration | BACKLOG |
| P2-03 Role/Brain/Skills/Tools/Memory domain v2 | Backend Domain | BACKLOG |
| P2-04 LangGraph/native runtime | Backend Runtime | BACKLOG |
| P2-05 backend-event to Habblaud snapshot/feed adapter | Integrator/Bridge | BACKLOG |
| P2-06 Habblaud-themed AgentStudio/workflow UI | Frontend | BACKLOG |
| P2-07 Harness executor/plugin full integration | Harness Integration | BACKLOG |
| P2-08 independent visual/security/real-artifact acceptance | QA | BACKLOG |
| P2-09 localhost integration/release | Integrator | BACKLOG |

No phase2 code has started; proposedworktrees are not created. New runtime/provider/dependencies are not installed or validated. Keep v0.1 data/history and GitHubmain intact until reviewed phase2 milestones.
