# Visual reference board

Observed actual source images on 2026-10-17; no upstream images shipped.

## REF-01 Habblaud
Commit faa1a012b5fbf632c66dc6801c5383e53a542406. Viewed `docs/screenshots/overview.png`; research agent also inspects detail references. [Pinned overview](https://github.com/marmottajr/habblaud/blob/faa1a012b5fbf632c66dc6801c5383e53a542406/docs/screenshots/overview.png). Actual visual: multiple rooms separated by a corridor, tiled floors, small pixel people at desks, room labels, sidebar agent list, bottom timestamped activity feed. Adopt room zoning, desk/state association, character selection and activity context. Depart from dark game chrome to required clean light dashboard; omit outdoor world/city.

## REF-02 Pixel Agents
Commit b1bafd02896d90d83457266575a1e8e5011ce997. Viewed `webview-ui/public/office.png`. [Pinned office](https://github.com/pixel-agents-hq/pixel-agents/blob/b1bafd02896d90d83457266575a1e8e5011ce997/webview-ui/public/office.png). Actual visual: orthographic/three-quarter top-down office, crisp pixel edges, warm wooden desks/floors, monitors, chairs, plants, bookshelves and separate lounge. Adopt coherent 32px tile system, original desk/monitor/plant primitives, compact characters and room palette contrast. Do not copy Metro City characters or external furniture packs.

## AgentVerse implementation direction
1366x768 desktop: narrow light navigation, workspace selector, office central canvas, agent inspector at right, task/event area below; cream room floor, lavender/teal accents, dark ink text. One building, two independent workspaces (Coding/Research). Canvas is actual PixiJS with pan/zoom, grid, selection and layout editing, never a screenshot backdrop. Original procedural pixel characters and furniture licensed CC0.

Backend status -> visual: idle stationary; walk path travel; working keyboard movement; waiting speech ellipsis; error red mark; completed green check, triggered only by persisted backend events. Connection loss visibly disconnected. No optimistic task completion.

## Acceptance evidence — independently reviewed
For Office, Agent Studio, Workflow Builder, Furniture Editor, Run Monitor and Settings: capture localhost at 1366x768, interaction Playwright test, no-console-error check, commit/task/log links and comparison deviations. Actual screenshots and functional evidence are now committed in `tests/e2e/evidence/` at application candidate `826c74c`; see `AI_LOGS/reviews/QA-001-review.md` for independent visual comparison, exact commands, resolved findings and APPROVE verdict. Research images above remain reference-only. Each screen has real localhost capture at1366×768; office also1920×1080. Capability and event detail supplemental captures cover below-fold controls. Final console/HTTP errors are empty; initial failing evidence is retained separately.
