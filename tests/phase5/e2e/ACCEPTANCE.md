# Phase 5 independent acceptance

Status: PREPARED, not executed. Production remains read-only to QA. Root reviews QA code; QA independently reviews integrated application commit. All screenshots use newly generated synthetic workspaces, never video frames or accounts. Historical Phase4 tests remain regression evidence only.

| ID | Positive | Failure / adverse condition |
|---|---|---|
| P5-01 | All navigation/deep links, command palette, keyboard collapse, three viewports | API disconnected state, back/forward, no invisible focused controls |
| P5-02 | Counts reconcile actual created records and UTC period query | Missing usage remains unknown; no fake services |
| P5-03 | Actual artifact approval, checkpoint review and final acceptance distinct | Stale/double approval rejects, denial records reason |
| P5-04 | Persistent common-room message creates exactly one real run/work item | Duplicate request stable; changed payload conflicts; reconnect/restart retains IDs |
| P5-05 | Private conversation reaches selected actual adapter and correct run | Foreign workspace/agent denied; immutable active-run context |
| P5-06 | Agent tabs agree with source records, SOUL revision changes future prompts | Stale revision409; config rollback and validation must be evidenced |
| P5-07 | Real queue dispatch, review/rework, accept, archive/search | Stale review, overlapping dispatch, bounded rework and archived history |
| P5-08 | Real Decimal CSV tool→artifact→QC→accept, saved editable flow | Changed source/foreign source denied; exact artifact hash; no disguised XLSX |
| P5-09 | Monitor shows true observations or explicit unconfigured state | No CRUD controls or fabricated next runs |
| P5-10 | Reviewed local package preview/install/update/remove and audit | Expired/replayed preview, stale binding, grant escalation, unsupported package |
| P5-11 | Edit/history/tombstone/source provenance persist | Lost update and cross-workspace documents denied |
| P5-12 | Actual adapter/secret-name presence with timestamps | Missing config and disconnected service never green; no secret values |
| P5-13 | Registry topology, search/pan/zoom/fit/details | Disconnect becomes stale; dragging cannot change grants |
| P5-14 | Period queries reconcile fixture token usage, unknown cost | Invalid period rejects; actual/estimated unknown distinct; budget validation/audit |
| P5-15 | Real run-derived session detail and correlation links | Cross-workspace IDs do not disclose session/message/artifact |
| P5-16 | Distinct system/audit queries with filters/cursor/export | Bad cursor/limit rejects, redact token/password/environment values |
| P5-17 | All settings persist reload; keyboard/theme/system behavior | Invalid values/stale revision reject; refresh off preserves run events |
| P5-18 | Actual upstream office renderer, navigation/profile bridge and notices | Office disabled lazy loading, old data/IDs/deep links survive migration |
| P5-19 | Bounded text/CSV attachment source/hash and draft handling | Unsupported image/audio/path/size rejected; voice unconfigured explicit; real STT OPEN |

## Execution gates

1. Start fresh isolated localhost stack at pinned application SHA. Record commands and provider identity. Never use paid/live credentials from environment without explicit configuration.
2. Run backend and frontend owner tests, then independent HTTP acceptance against actual app. Provider fixture replaces inference only, never workflow/store/tools.
3. Capture each newly introduced console screen at1108×636,1366×768,1920×1080. Hash images, validate decoded size/nonblank and manually inspect representative images. Screenshot presence alone proves no interactions.
4. Execute actual chat→CSV tool→artifact approval→QC→human work acceptance. Restart between durable message/review reads, recheck exact IDs. Capture failure/disconnect/reconnect and keyboard flows separately.
5. Independent production review at pinned integrated SHA. PASS/PARTIAL/OPEN/UNRUN must not be conflated. Live model, microphone/STT and outbound integration remain UNRUN unless actually configured and exercised. No full phase completion with missing required capabilities.
