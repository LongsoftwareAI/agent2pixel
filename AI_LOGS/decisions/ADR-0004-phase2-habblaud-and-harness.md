# ADR-0004 — proposed phase 2 architecture

Status: PROPOSED, planning only. User explicitly requests Habblaud-equivalent graphics and full per-agent Role/Skills/Tools/Memory architecture using Python frameworks, clarified exact DeepSeekHarness repository. Phase2 user direction supersedes v0.1 inspiration-only/originalart preference and light-dashboard choice; preserve historical audit/acceptance as v0.1 evidence.

Proposed: reuse MIT Habblaud Canvas2D office slice at faa1a012, not another Pixi recreation; LangGraph team orchestration + LangChain native executor/provider/tool components; official DeepSeekHarness PythonSDK/runtime as selectable per-agent executor with reviewed Cordis plugin bridge for the same AgentVerse tool/skill/memory policy. Keep one team orchestrator and one inner agent loop per assignment. CrewAI alternative, not simultaneous second orchestrator. DeepAgents is not the clarified DeepSeekHarness request.

Reasons: visual fidelity requires reuse of upstream detailed material/rig/renderer, Habblaud runtime primarily observes CLI rather than executes AgentVerse graphs, and Harness already has an official Python subprocessSDK. Framework agents and UI must share domain state/events rather than animation-created completion.

Tradeoffs: vendoring shared UI/world closure; upstream Canvas2D rather than prior Pixi; Harness Node/native runtime despite PythonSDK, preview version drift and native artifact/third-party license closure; SDK sync calls require worker/process lifecycle; multiple persistence stores require outbox/reconciliation. No assumption minimalprofile means read-only, no user-home/env inheritance, no cloud tracing by default. Per-file license manifest and SDK compatibility/policy/cancel spike required before adoption. No source dependency installed/changed by this ADR.

Decision gates: P2-00 rights/reference baseline, P2-01 pixel parity, P2-02 SDK/plugin/policy/cancel GO/NO-GO, P2-03+04 actual domain/runtime, P2-05+07 live projection/Harness, independent visual/source review and real sandbox file/test artifacts. Detailed tasks/criteria in docs/plans/PHASE_2_HABBLAUD_RUNTIME.md. No phase2 implementation task is DONE.
