# AgentVerse task board

All tasks use requirements v0.1 and docs/contracts/API.md. One active writer per owned path. Root Integrator explicitly approves separate worktrees for this user-requested multi-agent development.

| ID | Owner | Branch/worktree | Owned paths | Dependencies | Acceptance | Status |
|---|---|---|---|---|---|---|
| REF-001 | Research agents / Architect | research outside checkout | docs/reuse/, docs/references/ (root writes) | none | six repositories + legacy exact commits, code/assets rights, actual images inspected | IN_PROGRESS |
| ARCH-001 | Architect/Integrator | work /workspace/agent2pixel | root config, docs/, AI_LOGS root and decisions | REF-001 before code | contracts, ADR, ownership, audit before implementation | IN_PROGRESS |
| BE-001 | Backend | agent/backend/BE-001 /workspace/worktrees/backend | services/, tests/backend/, own logs/handoff | ARCH-001 | CRUD, persistence, DAG worker, adapters, safety, replay, success+failure tests | READY |
| FE-001 | Frontend | agent/frontend/FE-001 /workspace/worktrees/frontend | apps/web/ except src/office/, own logs/handoff | ARCH-001, API contract | usable six screens, editor, persisted integration, no console errors | READY |
| PIX-001 | Pixel/Game | agent/pixel/PIX-001 /workspace/worktrees/pixel | apps/web/src/office/, own logs/handoff | REF-001, API contract | original Pixi office, states, pan/zoom, collision, placement | READY |
| QA-001 | QA/Reviewer | agent/qa/QA-001 /workspace/worktrees/qa | tests/e2e/, own logs, AI_LOGS/reviews/ | implementation handoff | independent tests, screenshots each screen 1366x768, interactions, security review pinned SHAs | READY |
| INT-001 | Integrator | work /workspace/agent2pixel | root files, integration | QA approval | merge approved commits, clean install, test+screenshots evidence, release notes | BACKLOG |

Cross-module changes require a coordination note and Integrator approval. Shared API changes require Architect approval and updating this contract before code. No agent approves own implementation. No DONE until independent review + integration evidence.
