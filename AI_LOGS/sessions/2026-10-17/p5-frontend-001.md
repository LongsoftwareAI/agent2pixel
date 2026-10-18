# P5 Frontend
- Agent: P5-FE; scope apps/web except src/office; dedicated branch agent/p5-frontend.
- Status: IN_PROGRESS; input Phase5 contract, v0.5 requirements and video reference board.
- Goal: actual API-backed operations console, preserve existing workflows/data and office.
- References: uploaded video visual analysis only; original graphics/code, no third-party artwork copied.
- Decisions: no dependencies added; retain legacy App for tooling and tests; new console entry.
- Validation: pending build, tests and independent review; no live model claims.
- Risks: backend integration and unavailable STT/provider connections must remain explicit.
- Handoff: AI_LOGS/handoffs/P5-FE.md; reviewer Integrator/independent QA.

## SELF_TESTED milestone
- Implemented original dense console shell and full operations navigation, actual scoped API-backed chat/run cards, safe report markdown/tables, real topology, skills preview/apply, versioned SOUL/config history/rollback, budgets, redacted log export, scoped memory, archive/search and persistent preferences.
- Preserved legacy workflow/source/workboard/run/provider UI inside console; deep links now select run/work item. Office proxy uses /office/ at3002; /control/ redirects supported.
- Verification: npm run test --prefix apps/web 61 PASS (48 prior +13 new); production build PASS; ESLint PASS. No new dependencies. Vite warns main bundle >500kB, retained existing engine/editor chunk surface.
- Reference evidence inspected: original video frame011, independent QA precommit localhost overview1108x636; nonblank, sidebar200px/header58px. Refined inherited global CSS, chart width, original monochrome SVG symbols. No private video frames copied into repo.
- Open: independent pinned review, final screenshots and integration; live browser STT/model/provider UNRUN without actual configured runtime.
