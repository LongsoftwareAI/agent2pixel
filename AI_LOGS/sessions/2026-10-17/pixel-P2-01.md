# P2-01 Pixel / Office host
Status: IN_PROGRESS
Owner: Pixel agent; branch agent/pixel/P2-01; worktree /workspace/worktrees/p2-pixel.
User request: actual Habblaud visuals and real workflow-driven agents, localhost only.
Inputs: docs/contracts/phase2/IMPLEMENTATION.md; full reuse audit; upstream faa1a012b5fbf632c66dc6801c5383e53a542406.
Ownership: vendor/habblaud, apps/office, own logs.
Decisions: reuse MIT client/shared (including original Canvas2D createWorld, art, CSS/UI), preserve notices and per-file hashes. No Node server/CLI. Pinned Vite/TS/Pixelify dependencies needed for exact upstream rendering; no new model calls or secrets.
Reference: inspected actual overview.png source screenshot with image tool; corridor, kitchen, reception, lounge and workspace rooms are original upstream geometry, not new simplified scene.
Validation planned: build/typecheck, adapter success/failure tests; independent QA localhost screenshots and parity fixture.
Risks: upstream extra controls must be disabled or routed to real control UI; no mocked agents on live route.
Handoff: pending. No completion claim before independent QA.

## Milestone 2
- Commit b9892de: usable host, exact renderer/art/layout, MIT/OFL provenance.
- Self checks PASS: Vite production build, TypeScript7 typecheck, 8 tests (live projection/revision/error/replay plus snapshot-driven working/waiting/persistent-idle and no fake social coins/rewards).
- Independent QA reported canvas zero pixel differences at1366x768 and1920x1080 against original pinned checkout with shared deterministic fixture; verdict pending full handoff.
- Live character editor now uses Python-backed local access and inherited save/reset endpoints independently of unavailable upstream terminal. No fake demo, history, city or PTY calls exposed.
- Followup acceptance furniture editor under investigation; upstream has art/layout/collision but no editor. Root coordinating persisted layout contract.
