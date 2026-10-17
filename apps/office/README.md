# AgentVerse Habblaud office host

Run `npm ci` then `npm run dev` (127.0.0.1:3000); Python API must be on 8000, React control on 3001. `/control/#agents`, workflows/runs/settings route through the same localhost origin. `npm run build`, `npm run typecheck`, `npm test` validate this host.

Live page uses GET /api/office/snapshot and original OfficeStore SSE reconnection at /api/office/stream (snapshot/feed/notice events). No mock fallback; missing backend is explicitly disconnected/reconnecting. Upstream Canvas2D art/render/layout and detailed UI shell are reused, with AgentVerse boundary adaptations in PATCHES.md. Live data has no generated account quota or fictional social rewards.

Development-only `/?fixture=parity` loads a static, visibly labeled visual fixture with fixed time/seeds. It is not execution evidence, and build excludes the fixture branch. Independent raw upstream comparison uses the same fixture only; it must import original reference checkout renderer, not the local renderer on both sides.

License/provenance: THIRD_PARTY_NOTICES.md and ../../vendor/habblaud/. No server/CLI hooks or cloud/city deployment included.
