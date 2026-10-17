# P2-06 Frontend session
Owner: Frontend. Status: IN_PROGRESS. Branch: agent/frontend/P2-06.
Scope: apps/web excluding src/office; own logs. Goal: Habblaud-themed control UI with real AgentSpec registry and run evidence.
Inputs: docs/contracts/phase2/IMPLEMENTATION.md, accepted phase2 plan; upstream Habblaud styles reviewed (MIT). No upstream artwork copied by this task.
Decisions: keep existing React CRUD/workflow editor and workspace isolation. Control base is configurable, office remains separate upstream renderer. No new dependencies. Never expose secret values.
Validation: pending build/lint/unit and independent QA. Risks: backend registry contract evolving; coordinate directly.
