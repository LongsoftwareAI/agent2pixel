# Reuse audit — AgentVerse v0.1

Accessed 2026-10-17. Research completed before application implementation. Decisions below authorize **inspiration-only**, not source/asset copying. External repositories are isolated under /workspace/reference-checkouts and excluded from project/dependencies. Detailed evidence follows as research agents finalize notes.

| Ref | Repository | Commit | License / rights | Decision |
|---|---|---|---|---|
| REF-01 | https://github.com/marmottajr/habblaud | `faa1a012b5fbf632c66dc6801c5383e53a542406` | MIT | Reference room zoning, workstation assignment and state feed; original implementation only. |
| REF-02 | https://github.com/pixel-agents-hq/pixel-agents | `b1bafd02896d90d83457266575a1e8e5011ce997` | MIT code; third-party Metro City characters / Donarg packs separately licensed | Reference office editor and pixel scaling; no character or furniture copying. |
| REF-03 | https://github.com/OpenBMB/ChatDev | `a2ea4a263cebe9a7abd01ee3b5b0bf95698ed328` | Apache-2.0 | Reference DAG scheduling, adapters, cancellation; no bulk reuse or dependencies. |
| REF-04 | https://github.com/basriayaz/pixel-office | `4ebfdc7e4538eb68ea987f57ccf2810bc488a39c` | MIT code; logo/trademark rights separate | Reference agent identity and profile only. |
| REF-05 | https://github.com/bignutchanon/pixel-office | `bacbf2157adf5882daf79171245356697c15c296` | No LICENSE located: rights unconfirmed | No source or asset reuse. Concepts only. |
| REF-06 | https://github.com/paulrobello/claude-office | `11e5011d7dba3d0ddc7db6704c8d2e356756f01f` | MIT code; asset-specific provenance must be checked | Reference activity/task feed; original implementation. |
| REF-07 | https://github.com/OpenBMB/ChatDev/tree/chatdev1.0 | `31fd994416a251ecdeb1f0a73c329271743bfb56` | Apache-2.0 source; related DATA CC BY-NC 4.0 | Conceptual role handoff only; do not redistribute legacy media/data. |

## Reuse boundary

No upstream application source, sprites, screenshots, fonts, logos or packs will be shipped. Reusable elements are architectural patterns and dependencies selected separately in ADR-0001. Fresh modules: FastAPI CRUD/persistence, isolated workspace access, DAG worker, adapters, event store/replay, React screens, workflow builder, procedural Pixi office and tests. Adapter protocol and message envelope follow our own documented contract.

## Validation requirements

Each adapter needs success and provider-failure tests; DAG needs branching, cycles, retry, budget and cancellation tests. Validate workspace traversal and symlink escape, no secret responses, event ordering/reconnect. Office needs real event mapping, collision/layout persistence, sprite interaction and integer zoom. Independent QA must inspect source at implementation commits and capture localhost screenshots; no feature is verified solely from upstream README.

## License obligations if future copying is proposed

MIT copying requires copyright/license notices; Apache-2.0 copying requires license, applicable notices and modification notices. Unknown asset rights block copying; code license does not automatically cover external art. REF-05 has no permission grant. Legacy ChatDev data noncommercial restriction is incompatible with treating all assets as Apache-2.0. No copying approved in this MVP.

---

# ChatDev runtime audit — 2026-10-17

Read complete AgentVerse requirements, including sections 8, 9 and 13. Research only; no source or assets copied into AgentVerse.

## REF-03 current
- Repository: https://github.com/OpenBMB/ChatDev
- Commit: `a2ea4a263cebe9a7abd01ee3b5b0bf95698ed328` (default branch clone).
- Code license: Apache-2.0 (`LICENSE`; pyproject metadata agrees). No NOTICE file found with rg. Preserve license, copyright and applicable attribution; mark modified files if source adapted. License does not grant trademark rights. Asset-specific provenance was not established; keep logo/demo images URL-only and do not ship them in app.
- Inspected: README.md, LICENSE, pyproject.toml, workflow/executor/dag_executor.py, runtime/node/executor/agent_executor.py, runtime/node/agent/tool/tool_manager.py, runtime/node/agent/providers/base.py, entity/messages.py, server/services/session_store.py, utils/code_execution.py, utils/workspace_paths.py, yaml_instance/ChatDev_v1.yaml; tree/search of runtime, workflow, server, yaml_instance and tests.
- Verified behavior: DAG executes topological layers using ParallelExecutor, node trigger filtering; actual agent executor selects provider, builds prompt/messages, retrieves memory, invokes model, calls real tools, persists attachment refs, updates memory and returns source-tagged messages. ToolManager implements function, MCP HTTP and stdio tool discovery/execution. Provider ABC separates client/invocation/token extraction. Cancellation is cooperatively checked in runtime and propagated from run service.
- Important incompatibilities: UI is Vue 3/Vite, not required React. pyproject pins Python >=3.12,<3.13; dependency surface includes FAISS, cartopy, pygame, plotting, mem0, PDF and MCP, too large for AgentVerse MVP. Session store is explicitly in-memory with bounded 1000-message replay buffer, unsuitable as durable backend event store.
- Error handling caveat: AgentNodeExecutor.execute catches generic provider failures and returns an assistant error message, potentially allowing downstream work on an error. AgentVerse must instead persist task.failed and prevent workflow.completed on failures.
- Security evidence: utils/code_execution.py gates workflow-supplied code on server-only MAC_ALLOW_UNSAFE_CODE_EXECUTION and explicitly states execution is NOT sandboxed. Do not enable/copy unsafe executor. utils/workspace_paths.py rejects path separators and resolves containment; useful policy pattern, but needs workspace authorization and TOCTOU awareness.
- Actual tests found (not run; upstream stack not installed): tests/test_code_execution_security.py, test_session_workspace_security.py, test_attachment_boundary_security.py, test_attachment_upload_filename.py, test_websocket_send_message_sync.py.
- Visual references: commit-pinned `frontend/public/media/logo.png`, `assets/workflow.gif`; README uses product images. Requirement `assets/cases` directory has no files in current checkout; do not claim demo GIFs there were inspected.
- Decision: INSPIRATION ONLY. Reimplement a small typed DAG coordinator, adapter registry, typed message envelope, allowlisted read-only tool dispatcher and cooperative cancellation. No copied files, no integration claim, no attribution obligations triggered by copying yet.

## REF-07 legacy
- Repository: https://github.com/OpenBMB/ChatDev/tree/chatdev1.0
- Commit: `31fd994416a251ecdeb1f0a73c329271743bfb56`.
- Code license: Apache-2.0. README license section lines 265–268 explicitly assigns related DATA CC BY-NC 4.0. Legacy assets/data must not be blanket-classified Apache; no app asset reuse approved. If data reuse later considered, attribution and NC restriction need item-specific review.
- Inspected README license section, LICENSE, chatdev/chat_chain.py; source search chatdev/chat_env.py and chatdev/phase.py; tree CompanyConfig and camel.
- Actual structure: CompanyConfig/Default/{ChatChainConfig,PhaseConfig,RoleConfig}.json; chatdev/chat_chain.py recruits roles and sequentially executes simple/composed phases; camel/agents/role_playing.py supports pairwise role conversations. Max chat turns and configured cycle counts exist. Shared ChatEnv carries outputs; this is a conversational software company pipeline, not the requested persisted event/workspace runtime.
- Risk: chat_env.py installs model-selected modules through shell=True subprocess; chat_chain.py uses interpolated os.system Git commands and shell=True subprocess. Do not import these execution paths into localhost MVP.
- assets/cases does not exist in legacy checkout.
- Decision: CONCEPT ONLY. Planner/Developer/Reviewer role specialization and explicit bounded handoffs; new implementation and original prompts. No files/assets copied.

## Practical AgentVerse design and tests
Use FastAPI modular monolith plus worker module, SQLite with migrations/FKs for prototype; event rows committed before broadcast, monotonic seq cursor; snapshots/replay after refresh/reconnect. Validate DAG has exactly one start/end, known node types/agent IDs, same-workspace references, bounded steps, deterministic condition branches; reject cycles. Each node receives actual predecessor output; persist each task input/output and message envelope with run_id, sender, recipient, timestamp, correlation_id. Mock adapter must compute deterministic task-dependent outputs and execute real orchestration/persistence; label provider=mock clearly, never pretend model calls occurred. OpenAI-compatible and Ollama use HTTP adapters, environment secret refs only, bounded timeout/token budget, cancellation checks around calls and terminal state transaction guards. Read-only tools may list/read only authorized resolved workspace roots; shell/write/network blocked or explicit approval in worker, never arbitrary browser-supplied command execution. Provider endpoint configuration requires controlled trusted-local policy and redacted error handling.

Required meaningful tests: planner output reaches developer/reviewer; outputs survive refresh/process restart; wrong-workspace IDs and path traversal/symlink escape denied; provider missing key/failure becomes failed state; timeout/token/step budget; retries bounded; cancellation cannot later turn completed; condition chooses one branch and invalid/cyclic graph rejected; seq monotonic and replay excludes duplicate events; secret not returned/logged; denied tools cannot bypass through workflow payload. Adapter contract tests with stub HTTP servers assert request/body and failure handling for OpenAI and Ollama. E2E run must show backend task events drive office statuses and final output, with independent reviewer evidence.
