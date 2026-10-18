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

## Phase 2 — implemented localhost slice, independent final review

User authorized coding. Ownership/contracts: docs/contracts/phase2/IMPLEMENTATION.md. Actual scope and remaining limitations: docs/PHASE_2_VALIDATION.md. Historical v0.1 DONE/approval is unchanged and does not approve Phase 2.

| Task | Owner | State / evidence |
|---|---|---|
| PLAN-P2 | Architect | INTEGRATED, user authorized coding |
| P2-00 source/license/reference baseline | Architect/Pixel/QA | READY_FOR_REVIEW; MIT/OFL notices, 334-file manifest; Harness binary notice closure limitation documented |
| P2-01 Habblaud renderer/UI/graphics | Pixel | READY_FOR_REVIEW; actual upstream reuse, parity0pixels both sizes; furniture and appearance persistence |
| P2-02 official Harness SDK/plugin policy | Harness | READY_FOR_REVIEW; actual SDK/runtime0.1.5rc1, sanitized process and reviewed Cordis bridge |
| P2-03 full AgentSpec domain | Backend | READY_FOR_REVIEW; role/brain/skills/tools/memory, migration and isolation |
| P2-04 LangGraph runtime | Backend | READY_FOR_REVIEW; SQLite checkpoints, approval interrupts, budgets/restart |
| P2-05 projection/layout adapter | Integrator/Layout | READY_FOR_REVIEW; persistent custom decor, authoritative snapshots, exact SSE replay |
| P2-06 control interface | Frontend | READY_FOR_REVIEW; 17 tests, full agent editor and approval UI |
| P2-07 Harness domain integration | Harness | READY_FOR_REVIEW; actual SDK/provider-stub mixed workflows; arbitrary model-authored writes remain outside implemented slice |
| P2-08 independent acceptance | QA | APPROVED implemented localhost slice at3b7b138; final review P2-08, corrected stats/ledger retested |
| P2-09 localhost integration/review branch | Integrator | INTEGRATED; 88 Python +10 office +17 control pass; scoped independent APPROVE, GitHub review branch pending |

No SaaS/city/public deployment. Live paid model verification UNRUN without credentials. Native approved fixed calculator actions execute before Harness retrieves results; do not report autonomous general coding complete.
