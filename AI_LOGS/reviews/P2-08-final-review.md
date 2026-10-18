# Phase2 independent review — pending corrections

Reviewer: independent QA. Candidate01f8f80. This report does not approve QA's own helpers; Integrator must review those separately.

Decision: **CHANGES_REQUESTED** pending the two concrete corrections below and final parity recheck.

1. MEDIUM — `services/api/office_projection.py` puts `usageKnown:false` on AgentInfo but `vendor/habblaud/client/src/ui/drawer.ts` reads `a.stats.usageKnown`. Actual failed-run drawer displays zero tokens instead of unknown N/A. Reproduced by `tests/phase2/live_office_status.py`; failed evidence kept under `evidence/01f8f80`.
2. LOW — source audit334 files has undeclared adapted `client/src/ui/drawer.ts` in vendor PATCHES ledger. MIT notice intact; provenance ledger must match current modified files.

Executed independently: actual localhost office/four control screens at1366/1920, clean errors/HTTP; native furniture add/move/reload/delete and collision-no-mutation; character canvas hit/randomize/save/reload and restore; actualfailed/cancelledtask projection; actualLangGraph/SQLite/artifactwrite/pytest2passed/threeapprovals/Reviewerreport; artifact file hashes; memory isolation; approval reuse409; exactfresh-runSSE158..184 replay; remoteOriginPOST/SSE403; preserved genuinev1 IDs/history/event hashes. OfficialHarness realSDK/runtime/plugin+sharedStore mixed workflow two variants pass with local provider stub; no live provider credentials asserted.

Limit: current coding action supports reviewed deterministic calculator templates. Harness retrieves native-preapproved results; it does not originate a new model-driven code write. No unrestricted arbitrary coding or live DeepSeek inference validated.
