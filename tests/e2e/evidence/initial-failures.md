# Initial real browser failures — 2026-10-17

Candidate root347ca8d. `python tests/e2e/browser_acceptance.py --base http://127.0.0.1:3000 --output tests/e2e/evidence` FAIL at realtime connection assertion. Office loaded but badge stays Disconnected. Actual browser console: WS `/ws/workspaces/{id}/events?after=0` handshake404 repeatedly. API requirements.lock lacks websockets/wsproto required by uvicorn runtime, although TestClient WS test passes. Reported BLOCKER to backend/integrator; awaiting pinned protocol dependency and server restart.

Initial browser also reports missing resource404, suspected favicon; reported frontend to resolve no-console-errors gate. Screenshot suite cannot pass until corrected. Failed initial attempt is not acceptance evidence.
