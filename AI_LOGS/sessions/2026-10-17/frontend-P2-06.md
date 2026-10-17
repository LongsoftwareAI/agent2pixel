# P2-06 Frontend session
Owner: Frontend. Status: IN_PROGRESS. Branch: agent/frontend/P2-06.
Scope: apps/web excluding src/office; own logs. Goal: Habblaud-themed control UI with real AgentSpec registry and run evidence.
Inputs: docs/contracts/phase2/IMPLEMENTATION.md, accepted phase2 plan; upstream Habblaud styles reviewed (MIT). No upstream artwork copied by this task.
Decisions: keep existing React CRUD/workflow editor and workspace isolation. Control base is configurable, office remains separate upstream renderer. No new dependencies. Never expose secret values.
Validation: pending build/lint/unit and independent QA. Risks: backend registry contract evolving; coordinate directly.

Milestone: Agent Studio now loads backend catalog and edits pinned role/skills, actual grants, engine/profile readiness, memory scope and appearance seed. Registry forms create versioned skill/role manifests. Workflow supports explicit allowlisted coding demo actions; Run Monitor polls exact approval records and sends decisions, shows backend checkpoint/engine/artifact/test JSON without synthetic usage. Hash routes agents/workflows/runs/settings preserve workspace remount isolation.
Validation: npm ci (frozen lock) PASS; tsc/Vite build PASS; original9 tests +4 phase2 success/failure tests PASS; eslint PASS. No new deps or upstream source copied. Independent QA/screenshots remain required. Bundle-size warning inherited; no suppressed checks.
Handoff update: backend confirmed integer versions; aligned registry/Role/Skill bindings and tests. Final unit count14; hash navigation test added. READY_FOR_REVIEW; no self-approval. QA source + browser screenshots pending.
Additional failure coverage: registry successful creation verifies integer version and payload; expired approval remains explicit error with no artifact/execution claim. All16 tests PASS and lint PASS after final policy-copy correction.
