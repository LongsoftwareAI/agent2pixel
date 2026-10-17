# P2-02/P2-07 Harness
Status: IN_PROGRESS. Owner: Harness Integration. Branch: agent/harness/P2-02.
Scope: official SDK/runtime compatibility, isolated executor, reviewed plugin policy; no upstream unguarded shell.
Inputs: IMPLEMENTATION.md, phase2 plan/reuse delta; upstream687f282e8625c6b8d11ff58211a90524be2e4317 MIT.
Changes: owned executor/bridge/tests only. Dependencies: testing official SDK/runtime0.1.5rc1 pair. Secrets: none copied or logged.
Validation: pending release API/profile inspection, runtime smoke, cancellation/session/policy regressions. Review: independent required; not complete.

Milestone: official0.1.5rc1 wheel installed with normal TLS/signature defaults; actual bundled runtime sdk-minimal + disabling overlay provider-stub smoke completed HARNESS_REAL_RUNTIME_OK. Release protocol /chat/completions differs inspected HEAD; recorded actual profile/hash closure/notices. Implemented sanitized outer SDK worker, explicit identities, profile attestation, typed completion/token check/cancel. Full plugin broker remains gated; text adapter never claims tools. Own tests running. Review pending.
