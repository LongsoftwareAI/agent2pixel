# Phase 4 validation and acceptance limits

Implemented localhost production slice independently **APPROVED at bcd1ff4**. [Production review](../AI_LOGS/reviews/P4-FINAL-review.md) and [Integrator review of QA tests](../AI_LOGS/reviews/P4-INT-review.md) are separate. Later commits contain evidence/docs only. This is not complete acceptance of live external services.

## Delivered

- Scoped text/Markdown/CSV sources with immutable hash, source ID and timestamps. Actual Decimal CSV summaries and grouping; bounded rows/columns/cells and inert formula strings.
- Registered read tools shared by native explicit tool nodes and the actual Harness plugin. Durable outputs/citations, timing and failure records are viewable after reconnect. Grants and workspace ownership remain enforced.
- Human review nodes, explicit validated ancestor rework segment, revision limit1..3, fresh task/output identities and versioned artifact filenames. Actual process restart at a gate does not regenerate saved outputs or charge twice. Original brief/criteria and reviewer comments reach assignments.
- Actual concurrency for adjacent independent readtool batches, maximum4, deterministic joins. Agent/model/write/review steps stay serialized. Base graph remains a bounded32-node DAG; rework is a bounded linear agent/tool segment, not arbitrary cycles.
- Work priorities/deadlines/accountable owner, explicit manual queue dispatch, atomic active-work checks, real task/tool workload counts. Text artifact reader checks path/hash/size; linked completed runs have unified diff and criteria/review history.
- Memory source provenance, human edit/delete with retained audit history and tombstone filtering. Office reflects actual readtool working/failure states, not fabricated animation.
- Frontend new Sources/flow/gates/queue/memory/artifact/diff controls; historical event timelines do not depend on the500-event live buffer. Vitest upgraded to exact5.0.5; lazy legacy office loading reduces main bundle to approximately472kB. Habblaud renderer and MIT/OFL notices preserved.

## Executed checks

| Check | Result |
|---|---|
| Full Python suite: backend +P2/P3 runtime +P4 +backup +mounted integration +Harness +projection +layout | **165 PASS**, no skips,84.08s |
| New independent actual SDK source/CSV/foreign denial, rerun by root after its commit | **1 PASS**,4.20s; **166 aggregate Python checks** |
| Control unit tests / lint / TypeScript+production build | **48 PASS**, lint/build PASS |
| Office typecheck / unit tests / production build | PASS / **10 PASS** / PASS |
| Python correctness Ruff; pip dependency consistency; Compose config | PASS; no broken requirements |
| npm audit, both apps including development dependencies | **0 findings** at verification time |
| Independent HTTP workflows research/CSV/content revision | PASS actual API/LangGraph/SQLite/files/tool execution, inference fixture explicitly labeled |
| Real gate restart, cancellation and delayed provider | PASS; unchanged request accounting; actual timeout approximately20s |
| Independent actual browser,1366/1920 | PASS all7 groups,0page errors/0HTTP failures;8PNG hashes/dimensions verified |
| Actual official Harness SDK/runtime newdata calls | PASS real Cordis/broker/shared dispatcher; provider response remains local fixture |
| Backup/restore original application data | PASS42files, original220resource IDs/27terminalruns/340events; relocated17workspace roots and real restored API healthy |
| Docker API/web builds and isolated runtime | PASS verifiedTLS/frozen installs; proxy/control/catalog/sourceAPI +actualCSV sum0.30; final control module contains tool-workload UI |

Original data is preserved; [migration result](evidence/phase4/migration-results.json) records additive test data separately. Recovery requires a stopped application, rejects active runs/symlinks/overwrite/tamper, verifies SQLite integrity/FK and file hashes. It does not claim hot backup or an atomic transaction spanning filesystem writes. Uncertain consumed writes require reconciliation; a separate surrogate test proves no overwrite/regeneration.

## Evidence

- [Three workflow execution/restart/cancel/timeout](../tests/phase4/evidence/fab2e29/acceptance/live-acceptance.json)
- [Actual queue, provenance and diff](../tests/phase4/evidence/fab2e29/operations/live-operations.json)
- [Final browser result](../tests/phase4/evidence/bcd1ff4/browser/live-browser.json) and [screenshot manifest](../tests/phase4/evidence/bcd1ff4/browser/screenshots.json)
- [Sources screen](../tests/phase4/evidence/bcd1ff4/browser/sources-csv-provenance-1366.png), [human tool/review flow](../tests/phase4/evidence/bcd1ff4/browser/actual-tool-review-gate-1366.png), [artifact diff](../tests/phase4/evidence/bcd1ff4/browser/actual-artifact-diff-1920.png)
- [Docker smoke](evidence/phase4/docker-smoke.json), [restore](evidence/phase4/restore-results.json), [external check outcomes](evidence/phase4/external-checks.json)

Browser helper failures are retained: API-seeded workflow catalog required reload; offscreen graph node required actual Fit View. Assertions were preserved, no forced click or threshold relaxation. Runtime correctness fixes reject revision identity collisions, account rework steps against max_steps and serialize actual API dispatch on the event loop.

## Not yet accepted

**Live model inference: UNRUN.** No DeepSeek/OpenAI credential was present; no local Ollama service. Fixture output proves orchestration, not factual quality, reasoning, live token billing or business acceptance. User-supplied secure DeepSeek requirement was saved in the environment draft; no secret values printed or committed.

**Actual public HTTPS retrieval: FAILED environment DNS.** Both python.org and raw.githubusercontent.com were attempted in default and escalated execution; public name resolution failed before TLS/HTTP. Web URL policy, private/DNS/redirect denial, pinned IP with original-host TLS, body limits and response handling have30passing controlled tool/source tests; these do not establish live network success. No pin/TLS validation was weakened. Server defaults allow exact en/vi.wikipedia.org,www.python.org,docs.python.org,raw.githubusercontent.com; AGENTVERSE_WEB_ALLOWED_HOSTS can replace the list. No search engine, query-string URLs, arbitrary web browser or external writes supported. DNS resolver itself is OS-bound; socket/read deadlines are bounded but not a hard preemption of system DNS.

Also outside this slice: automatic background queue workers, unrestricted parallel agents, arbitrary graph cycles, arbitrary-code execution, external messaging/publishing, complete selected Harness binary SBOM and large production-load certification. The retained SDK third-party notice limitation and upstream AnyIO warning remain. Node audit findings from Phase3 have been resolved, not silently ignored.

Install/start configuration saved as draft. Review/save environment settings and publish to apply the snapshot; publication is not a verified fix for DNS, nor proof of restoration in a fresh cloud task. Fresh Docker startup and local stopped-data restore were actually exercised.
