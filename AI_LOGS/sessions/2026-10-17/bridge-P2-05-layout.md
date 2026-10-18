# P2-05 additive furniture persistence
Owner: Frontend reassigned Bridge. Branch agent/bridge/P2-05. Status IN_PROGRESS.
Authorization: root Architect assigned new office_layout module + trusted generated blueprints + isolated tests; no edits to other owners.
Contract: additive actual Habblaud plant_tall/bookshelf/floor_lamp; base layout/seats unchanged. GET/PUT /api/office/rooms/{workspace_id}/furniture; optimistic expected_version. Server owns geometry, bounds, collision/path validation. No client footprints.
References: accepted Phase2 plan, Habblaud MIT pinned upstream, Pixel generator outputs pending. No execution of untrusted uploaded blueprints. No new dependencies.
Checks pending: valid move/persist, invalid bounds/base collision/custom overlap/door/path block/unknown kind/seed tamper/stale version. Independent QA required.

2026-10-18 resume milestone: SELF_TESTED -> READY_FOR_REVIEW. Files owned: services/api/office_layout.py; packages/office-layout/blueprints.json and LICENSE-HABBLAUD; tests/office_layout/. All tracked baseline files preserved. Dependency additions: none. Blueprint provenance pinned MIT Habblaud faa1a012b5fbf632c66dc6801c5383e53a542406; Pixel owns reproducible generator, pending cross-check.
Checks: `/workspace/agent2pixel/.venv/bin/python -m pytest tests/office_layout -q` => 21 passed (Starlette/AnyIO deprecation warning only). Verified sixteen native seed/slot layouts, create/move/delete/reopen persistence, kind/variant/ID/geometry validation, walls/base/custom collision, doors, disconnected path, workspace missing, immutable seed, concurrent 409 optimistic version, HTTP contract, and resource-kind upsert collision protection. No credentials or model calls. Review: independent QA and integrated browser validation remain required; not DONE.
