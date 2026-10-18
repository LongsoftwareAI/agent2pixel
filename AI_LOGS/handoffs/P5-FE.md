# P5-FE handoff
Status: READY_FOR_REVIEW (not DONE; independent approval/integration pending).

Owner: apps/web excluding src/office. Branch agent/p5-frontend dedicated worktree.

Implemented console entry Console.tsx with original video-inspired dark200px sidebar/58pxheader, grouped navigation, command palette, keyboard sidebar persistence, URLdeep-links, server preferences, real dashboard usage/work and lifecycle metadata. Added commonroom/directchat durable requests, scoped idempotency, attachments text/CSV/MD, draft-preserving errors, configured workflow selection, @agent matching persisted workflow, safeMarkdown/tables/code/links, run/work/artifact references, cancellation. Skills preview→review→apply exact manifest, actual graph topology using existing XYFlow, provider/adapterhealth, schedules monitoronly, inbox/sessions/logs/audit, scoped botmemory/SOUL/configrevision history/rollback, local budget threshold and redacted export. WorkBoard archives preserve records and supports search/filter. Retains App for legacytooling and regressions; main mounts Console. Browser voice optional native adapter requires explicit consent; recording/stop/cancel/transcript review, no automatic send or server-ASR claim.

API: docs/contracts/phase5/IMPLEMENTATION.md and Backend08dd2ca addenda. All console reads/mutations queryworkspace_id where applicable. Fullpreferences include revision; unavailable capabilities visible rather than fakeonline. Unknown input/output/cost remain—; actual total_tokens used. No CRM/new3D/shell/dependencies/assets fromreference.

Self-checks: frontend62tests PASS, buildPASS, lintPASS, diffcheckPASS. New tests cover realrequests/failures/revision conflicts/unknownmetrics/palette/budget validation/rollback/archive/safeMarkdown/XSS and optional voice mockadapter (not live STT). Baseline48 retained. Vite mainchunkwarning remains (>500kB); no warning suppression.

Review environment: BE13001 isolated/tmp DB; frontend13000; office13002. QA owns final evidence. Inspected QA precommit overview1108x636 nonblank; final pinning pending.

Risks/limits: native browser SpeechRecognition often unavailable or networkdependent, live STT UNRUN; no providercredential acceptance. Schedules monitoronly no existing adapterrecords. Backend owns actual state/actions. New agents/configchanges only affect future runtime snapshots. Root must independently integrate/tests and review production setup/proxy. Do not publish originalvideo/screenshots containingprivate reference businessdata; localhost synthetic QA images acceptable.

QA follow-up: actual scoped sessions now authoritatively drive chat run-card state/cancel eligibility; no inferred running state for user messages. Dedicated regression covers completed→active→cancelled.
