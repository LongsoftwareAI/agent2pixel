# ADR-0003 — reviewed integration corrections

Architect/Integrator approved these cross-module contract clarifications before owner edits:

- Backend original asset catalog extends desk/chair/plant to bookshelf/sofa, matching original Pixel designs; single-tile collision footprint remains explicit. Existing user layout is never overwritten by richer fresh seed data.
- SQLite aggregate JSON persistence retained for prototype but actual workspace/event FKs, version marker, indexes and transaction-wide RLock required. Embedded role/brain/skill config is a documented deviation from separate logical SQL tables.
- Frontend owns every non-office web path; Pixel owns office subtree. Frontend consumes Pixel committed API, never rewrites renderer. Workspace-keyed state and stale response/socket guards preserve isolation.
- Missing real ASGI WebSocket transport fixed with pinned websockets dependency. Origin limited to localhost UI. HTTP TestClient alone was insufficient readiness evidence.
- Docker optionally accepts BuildKit public CA secret; existing proxy binding and DNS mapping are runtime build prerequisites only. TLS/signature/integrity validation was never disabled.
- Candidate integration cherry-picks precede review solely to run QA; task INTEGRATED/DONE gates require independent verdict and Integrator validation, not merely cherry-pick success.
- Integrator reviewed QA tests separately; tightened reconnect proof to exact newly created run/seq received on real WebSocket rather than a previously visible completion event. QA does not approve its own tests.

No new application source was copied from reference repositories; original procedural visual designs only. All product changes stayed inside trusted single-user localhost scope.
