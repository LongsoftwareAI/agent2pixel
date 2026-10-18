# P5-BE handoff

Task P5-BE; branch `agent/p5-backend`; base `cf25d46`. Status READY_FOR_REVIEW, not independently approved yet. Commit: see branch HEAD (this handoff is included in that commit).

Changed paths: services/api/{console,console_extensions,main,store,company,operations}.py; services/api/console_skills/; tests/phase5/backend/; own AI logs. No new dependencies or copied upstream assets.

## API/schema

Fixed `/api/console` contract implemented. All scoped console reads/mutations require `workspace_id` query except workspace-bearing conversation/attachment creation JSON. Missing or foreign resources404. Chat requires idempotency key; changed payload409; message/run/work persisted atomically, real runtime scheduled afterwards. Room requires explicit workflow; direct chat uses one-agent workflow. GET conversation reconciles stable response IDs from actual run state/output, never a generated success. Existing run events/cancel and work acceptance APIs remain authoritative.

Usage `total_tokens`/requests derive actual recorded model.completed events, their existing accounting may be estimated (including MockBrain). Input/output/cache and costs null when not recorded; no copied numbers. Health provider metadata includes agent_id, secret names/presence only, live readiness unknown until probed. Sessions agent_ids derive frozen run specs. Shared runtime/sqlite capability items lack agent_id.

Preferences PATCH requires expected `revision` (422missing,409stale). start_page supports current nav bots/preferences plus legacy aliases. Mutable SOUL/config paths preserve versioned history across old agent studio edits and skill activations; active run snapshots unchanged.

Skill catalog original declarative packages: `{id:'console-evidence-v1',registry_id:'console-evidence',version:1,...}` and `{id:'console-evidence',registry_id:'console-evidence',version:2,...}`. Bindings package_id is stable registry_id. Exact manifest preview + apply supports installv1→updatev2→updatev1 rollback→remove. No dependencies/tool grants/scripts. Replay current exact approval200; superseded historical approval409. Activation for future runs immediately, not fake pending restart. Transactions retain original binding snapshots.

Additive extension endpoints (root must copy into root-owned implementation contract):
- GET/PATCH `/budget`: PATCH `{revision,monthly_token_threshold?:positiveint|null,monthly_cost_threshold?:positivefinitefloat|null,currency?:'USD'}` preserves omitted values; GET `{policy,period,total_tokens,actual_cost:null,enforcement:'monitor-only',alerts,cost_state:'unknown',cost_reason}`. GET `/budget/history`.
- POST `/work-items/{id}/archive` `{archived:boolean,revision:archive_revision||1}`; GET same `/archive/history`. Archived item preserves all prior fields/IDs/history, dispatch/edit/enqueue guarded; active/queued archive409.
- GET `/agents/{id}/soul/history`; POST `/soul/rollback` `{revision:current,target_revision}` -> SOUL shape.
- GET `/agents/{id}/config/history`; POST `/config/rollback` `{revision:agent_config_revision||1,target_revision}` -> `{agent_id,revision,config}`. Current validated AgentInput schema + grants/workspace policies apply, workspace never restored across scope.
- GET `/logs/export` same `kind,limit,before` as logs, bounded200, returns schema/version/metadata + redacted allowlisted items/cursor.

Migration3 additive resource kinds only, preserved IDs and backed-up prior DB (`pre-schema-v3.sqlite3`). Existing schema migrations1/2 remain. Root backup tests passed. No user data wipe/reset.

## Run / validation

Use existing venv from root repository, `PYTHONPATH=$PWD`. 89 focused tests PASS and92 additional compatibility tests PASS (181 total, no skips). Exact commands in session log. Ruff newmodules/tests PASS. Covered real mock-labeled dispatch/output and acceptance separation, failed providerfixture, cancellation, duplicate key, changed payload, restart persistence, migration, scoped attachments, secret/log redaction, settings/SOUL/config stale revision, reviewed skills cycle/rollback, archive guards, budget unknowncost, logs export.

Temporary localhost QA backend running 127.0.0.1:13001 PID80400 with isolated `/tmp/agentverse-p5-backend-qa13001`, not baseline user DB. Frontend agent13000 proxies to it. Startup command `AGENTVERSE_DATA_DIR=/tmp/agentverse-p5-backend-qa13001 PYTHONPATH=$PWD /workspace/agent2pixel/.venv/bin/uvicorn services.api.main:app --host 127.0.0.1 --port 13001`.

Independent review focus: transaction restart boundaries, cross-workspace IDs/cursors/attachmentrefs, superseded approvals, old studio metadata preservation, config rollback validation, archived queue filtering, no fake service/provider readiness or billing. QA reviewer independent; parent root reviews QA contribution separately.

## Limits / open

Live model, live STT, image/audio adapter, external scheduler observations/connectors and provider cost/split accounting are not delivered capabilities; unconfigured/unknown explicitly reported. No CRM, Hermes engine migration, shell installer, external publication or additional dependency. Text attachment budget capped1MiB and combined chatinput20000chars; oversize composition422. No screenshot/visual completion claim from backend tests. Root must accept API addendum and integrate independent QA/evidence before product DONE.
