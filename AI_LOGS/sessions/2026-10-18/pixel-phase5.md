# P5-PIX — Office / console integration
Status: IN_PROGRESS
Owner: Pixel; branch agent/p5-pixel; dedicated worktree /workspace/worktrees/p5-pixel.
Authorized request: implement Phase 5 console while retaining original Habblaud office; localhost only.
Inputs: AGENTS.md; docs/contracts/phase5/IMPLEMENTATION.md; v0.5 requirements.
Ownership: apps/office/, apps/web/src/office/, own session and handoff only.
Reference: prior audited Habblaud MIT renderer/art, existing notices retained. No new reference media/art or dependencies.
Plan: base-aware Vite host at port3002 /office/, console selection links carrying actual projected agent/workspace identity, preserve furniture/state and actual execution projection.
Safety: selected workspace derives actual projection roomId; no fixture fallback in production, no new permissions or external actions.
Validation: existing office tests/typecheck/build, base/URL success and rejection checks; root independent integration QA required.
Limitations: no 3D rewrite, no backend implementation claimed.

## Self-tested milestone
- Base /office/, office3002, console3000 agreed with Integrator and Frontend. Registry roomId maps actual workspace; #agents alias supported by FE.
- Added same-origin encoded selected-agent link; selection removal hides it. Existing world, projection and furniture persistence untouched.
- Audited vendor public assets adapted at Vite transform time; no vendor source/art/license files changed.
- PASS: 14 Vitest tests (10 existing + 4 host/navigation integration cases), TypeScript check and production build. PASS: Chromium fixture browser smoke, no JS errors/art404, selected link and deselection verified.
- Evidence: /tmp/agentverse-p5-office-host.png explicitly dev fixture, not live runtime proof. Browser smoke source apps/office/tests/browser_smoke.py.
- npm ci default cache failed /home/agent permissions; success using --cache /tmp/agentverse-p5-pixel-npm. No new dependencies or lock changes.
- Status READY_FOR_REVIEW, not DONE. Independent integrated console/proxy review and live execution evidence remain root/QA gates.
