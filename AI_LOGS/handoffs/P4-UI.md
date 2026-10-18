# P4-UI handoff
Owner Frontend; branch agent/frontend/P4-01; base1d88bcc. READY_FOR_REVIEW. Owned apps/web excluding oldoffice; ownlogs. Contract docs/contracts/phase4/IMPLEMENTATION.md; peercoordination Runtime7876a0f, Operations8c939fa, Tools fieldresponseconfirmation.

Routes: /control/#sources (Nguồn dữ liệu), #workboard manualqueue/priority/deadline/owner/workload/diff, #agents Memory có nguồn gốc, #workflows tool/review controls, #runs gates/artifacts/timing. Browser globals and all earlierP2/P3 controls preserved. Habblaud source/art unchanged. New read/export/memory calls render text, never execute HTML or CSV formulas.

Source GET includes workspace_id; source content used only as data. Manual dispatch opens server run; no background scheduler claim. Human review decision requires nonempty comment and binds exact gate. Graphreview semantics supported single ancestor segment only, server validation authoritative. Parallel engine claim intentionally absent. CSVanalysis is through actual toolnode/output, not fabricated client arithmetic/search.

Checks: dedicated frozen npmci; lint/type/build PASS;41unit tests PASS. Vitest exact5.0.5 approved peer-compatible upgrade resolves all npm audit findings (fullgraph0). Legacy office lazychunk split main469kB vs763kB. Integration must stop root Vite before npmci; no new frontendframework. Independent QA actual browser required, screenshots and APIintegration still pending; root must review tests. User/data migration unaffected.
