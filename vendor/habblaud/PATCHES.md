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

- client/src/ui/composer.ts: query optional dictation only when message composition is ready and messages access is allowed; avoids unsupported API calls in disabled AgentVerse composer.

- world/api.ts, world/index.ts, world/sim/sim.ts: optional room layout transform/signature and tile-coordinate access. Host injects persisted additive decorations; omitted transform preserves upstream original layout exactly. Layout refresh rebuilds native collision/path grid. Structural fixtures remain fixed.
- shared/types.ts, ui/drawer.ts: explicit failed/cancelled task marks, error agent status text, unknown token/cost usage N/A. Native kanban only has three columns; failed/cancelled cards remain pending there while drawer retains actual terminal status.
- ui/widgets.ts: persistent main-agent role badge includes explicit Failed marker for domainStatus=error, including sidebar and drawer; upstream agents without extension unchanged.

- client/src/ui/drawer.ts: render failed/cancelled terminal task marks and labels, domain execution error status, and N/A for token/cost statistics when usageKnown is false; preserve original upstream presentation when additive flags are absent.
