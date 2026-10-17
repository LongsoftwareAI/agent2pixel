# P2-08 independent acceptance matrix

No Phase2 approval follows from v0.1 screenshots or tests. Every executed result records application SHA and fixture settings. Tests with mock transport, real Harness runtime with local provider stub, and live provider are separate evidence categories.

| Gate | Success evidence | Failure evidence |
|---|---|---|
| License/provenance | pinned upstream tree, MIT notices, source/asset SHA256 inventory and patch ledger | unknown asset rights, undeclared source delta block reuse |
| Renderer parity | same browser/DPR, seed, wall-clock, camera, scene and animation frame; exact raw-art pixel equality; unmasked sprite/furniture/floor/wall; 1366x768 and1920x1080 upstream/app/diff PNG contact sheets | mismatch fails original threshold; no threshold tuning or screenshot background |
| Office interaction | real canvas pan/zoom, hit-test agent, appearance change, furniture edit/persistence/collision; two rooms | disconnected visible; no fake completion or mocked live feed |
| Agent Studio | create/update Role/Brain/Skills/Tools/Memory/Skin; capability reason and runtime availability | unavailable engine fails explicitly, no silent MockBrain fallback |
| Mixed execution | fresh run native Planner -> official Harness Developer -> Reviewer; skill activation, scoped memory, approved sandbox file write/test, artifact hash and structured reviewer verdict | model/tool failure, rejected/reused/cross-workspace approval, forbidden path/symlink/network/shell and unknown tools rejected |
| Durability | v1 IDs/history survive migration; restart persists spec/layout/memory/run; reconnect replays exact fresh run event/seq | duplicate/out-of-order engine events dedup; interrupted process cannot emit late success |
| Isolation | per-agent Harness homes/session and checkpoint namespace; scrubbed env; browser responses no secrets | cross-workspace memory/run/approval denied; skill text cannot grant tools |
| Browser release | localhost screenshots all screens1366 and office1920; console/network clean; actual interaction trace | errors recorded and sent to owner; prior failures retained |
| Independent review | source SHA + executed command/results + limitations + separate Integrator review QA contribution | no selfapproval; no PASS for blocked live provider |

Current status: UNRUN pending implementation handoffs. Visual gate precedes default switch; runtime work may proceed independently.
