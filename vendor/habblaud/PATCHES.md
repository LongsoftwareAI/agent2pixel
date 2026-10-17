# Local patch ledger

Upstream pin: faa1a012b5fbf632c66dc6801c5383e53a542406. Original copyright/license retained. UPSTREAM.json records upstream and current file SHA256.

- client/src/net/store.ts: public applySnapshot seam and AgentVerse SSE route; original revision, indexes, feed and reconnect logic retained. DemoSimulator never enabled by live host.
- shared/types.ts, client/src/ui/provider.ts, shared/world/office-from-world.ts: additive agentverse provider identity; no false Claude/Codex quota. City account map type compatibility only; no city scene mounted.
- client/src/ui/index.ts: additive integration option hides unsupported session history, deliveries, day stats and timelapse; disables rename keyboard/context; routes help to control UI. Original sidebar, feed, drawer, settings and camera viewport code retained.
- client/src/ui/topbar.ts: hide unavailable timelapse for AgentVerse agents.
- client/src/ui/settings.ts: omit server demo toggle in AgentVerse integration. Appearance, daylight, language, sound remain original.
- client/src/ui/widgets.ts: show actual main-agent role, not generic Principal badge.
- client/src/world/api.ts, client/src/world/sim/sim.ts, client/src/world/index.ts: additive ambientSocial option (upstream default unchanged); live host disables fictional conversations, wallet/rewards/gatherings and social drawer data, while preserving idle walking/coffee animation. Explicit test fixture retains upstream default.

Renderer/art/layout geometry are unchanged. Node server, CLI, deployment and hooks were not vendored. Entire client/shared closure is retained because UI imports pure shared world contract helpers; unused city view is never mounted by AgentVerse.

- client/src/ui/overlays.ts: additive AgentVerse empty/offline text; hide unsupported demo action. Default upstream behavior unchanged.

- client/src/ui/character-editor.ts: AgentVerse character editing uses confirmed local access independently of unavailable upstream PTY/terminal feature. Original saveCharacter/resetCharacter HTTP methods remain unchanged; Python API validates and persists these requests.
