# P2-05 authoritative room furniture

Owner: Bridge; branch agent/bridge/P2-05. Status READY_FOR_REVIEW.

API mount: import `create_office_layout_router` from `services.api.office_layout`; `app.include_router(create_office_layout_router(app))` after `app.state.store` initialization. GET/PUT `/api/office/rooms/{workspace_id}/furniture`; GET returns `{items,version,seed}`; PUT accepts only `{items,expected_version}`. Each item `{id,kind,x,y,variant?}`, kinds plant_tall/bookshelf/floor_lamp. Coordinates are room-relative. Invalid placement 422, stale/concurrent write 409, missing workspace 404.

Projection helpers: `seed_for_room(workspace_id)` is SHA256 first four bytes big-endian modulo8+1. `slot_for_room(store,workspace_id)` is workspace insertion index modulo2. `room_furniture(store,id)` returns full state; `custom_furniture(store,id)` returns item list. Renderer prefix `agentverse:custom:` avoids base furniture ID collision. Do not enable custom workstation/seat kinds without updating server validation.

Trust: server reads pinned sixteen native 16x12 layouts and footprint definitions; caller cannot provide geometry/seed. Preserves all base furniture, native spots, doors and existing reachable workstation paths. SQLite writes use shared Store lock, version check and reserved resource-kind collision check. Workspaces/base layouts untouched.

Validation: `/workspace/agent2pixel/.venv/bin/python -m pytest tests/office_layout -q` => 21 passed. No new dependencies. Source derived from Habblaud MIT faa1a012b5fbf632c66dc6801c5383e53a542406; full notice included. Remaining: Pixel generator reproducibility cross-check; independent QA and integrated UI review. No completion claim.
