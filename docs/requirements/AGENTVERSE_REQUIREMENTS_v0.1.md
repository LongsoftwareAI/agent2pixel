# AGENTVERSE — LOCALHOST MVP REQUIREMENTS v0.1

Status: Proposed baseline | Scope: Single-user, localhost-only | Language: Vietnamese | Date: 2026-10-17

## 0. Mục tiêu và nguyên tắc
Xây dựng web app chạy trên máy cá nhân, mô phỏng một văn phòng pixel-art có các AI agent thực sự nhận việc, dùng model/tool, trao đổi thông điệp và hoàn thành workflow. Một agent có Identity, Role, Brain, Skills, Tools, Memory và Skin. Người dùng xem và điều khiển qua trình duyệt. Tách phần game renderer khỏi agent runtime. Mọi trạng thái `working`, `completed`, `failed` phải bắt nguồn từ sự kiện backend, không phải hoạt ảnh giả.

### Thành công của v0.1
- `docker compose up --build` (hoặc một lệnh dev được tài liệu hóa) khởi động hệ thống, mở được tại `http://localhost:3000`.
- Tạo ít nhất 3 agent, đổi role/brain/skin, phân công bàn và workspace.
- Kết nối một OpenAI-compatible API và một Ollama local adapter (test bằng mock nếu chưa có credentials/model).
- Chạy workflow mẫu `Planner -> Developer -> Reviewer` với output lưu được, log truy vết đầy đủ, có thể retry lỗi.
- Giao diện pixel có idle/walk/work/wait/error/done phản ánh backend events; refresh trang không mất layout, agent hay lịch sử.
- Một người dùng có thể tạo 2 workspace độc lập trong cùng một tòa nhà (ví dụ Coding và Research).
- Có log phát triển và review của từng coding agent để cộng tác không đè code.

## 1. Phạm vi
### IN SCOPE (P0)
Single-user localhost; Agent CRUD; Role/Brain/Skills/Tools/Memory basic; sprite preset và animation; 1 tòa nhà, 1 tầng, tối thiểu 2 phòng/workspace; kéo thả bàn/ghế/cây, lưu layout; workflow editor đơn giản với start/agent/condition/end; agent-to-agent messages thông qua orchestration; API provider adapters; realtime updates; task history, logs, approvals; Docker Compose; automated tests.

### NICE-TO-HAVE (P1, sau khi P0 chạy ổn)
Codex CLI và Claude Code bridge qua local process adapter có capability detection; MCP tools; basic file sandbox; human approval node; export/import workflow; sprite layered customization; đa tầng.

### OUT OF SCOPE
Multi-user authentication, SaaS, billing, marketplace thanh toán, bản đồ thành phố, nhiều tòa nhà, online multiplayer, cloud deployment, remote runner, tự động tích hợp Antigravity khi không có API/bridge được hỗ trợ, AI sprite generation production-grade, mobile optimization.

## 2. User stories và acceptance criteria
**US-01 Setup:** người dùng clone repo, cấu hình `.env`, chạy Docker Compose, xem healthcheck và demo data. Không có key vẫn chạy demo với MockBrain. Khi key thiếu, UI hiển thị lỗi cấu hình rõ ràng, không crash.

**US-02 Agent Builder:** tạo agent tên, avatar preset, role, system instructions, brain provider/model, allowed tools, skills, memory policy; chỉnh sửa và vô hiệu hóa agent. Form validation; agent ID bất biến; secret không xuất hiện trong response.

**US-03 Workspace:** tạo 2 workspace, mỗi workspace có task list, agent membership, documents/memory namespace và project directory riêng. Không đọc/ghi chéo workspace nếu chưa cho phép.

**US-04 Pixel Office:** tile grid, sprite nhân vật, furniture placement, save/load layout; mỗi agent gắn với workstation. Di chuyển hợp lệ theo collision; mất websocket thì hiện disconnected, không tự báo task thành công.

**US-05 Workflow:** người dùng tạo `Start -> Planner -> Developer -> Reviewer -> End`, save JSON, validate graph, execute, inspect each node input/output. Cho phép conditional branching và retry với giới hạn. Không hỗ trợ arbitrary cycles ở P0.

**US-06 Collaboration:** output Planner thành input Developer; output Developer thành input Reviewer; message envelope chứa run_id, sender, recipient, payload, timestamp, correlation_id; không gửi vô hạn; có maximum steps và token budget.

**US-07 Observability:** timeline run/task/tool events; logs được lọc theo agent, run và workspace; cost/tokens chỉ hiển thị nếu provider cung cấp hoặc ghi rõ estimated.

**US-08 Human safety:** thao tác file write, shell, network cần policy; command nguy hiểm và external side effects yêu cầu explicit approval. MVP có thể mặc định read-only tools và mock executor.

## 3. Data model (logical)
- `workspaces(id, name, root_path, created_at)`
- `agents(id, workspace_id, name, role_id, brain_config_id, skin_id, status, created_at)`
- `roles(id, name, system_prompt, responsibilities_json)`
- `brain_configs(id, provider, model, endpoint, secret_ref, capabilities_json)`
- `skills(id, name, version, manifest_json)` and `agent_skills(agent_id, skill_id)`
- `tools(id, name, type, config_json, permissions_json)` and `agent_tools(agent_id, tool_id)`
- `memories(id, workspace_id, agent_id_nullable, kind, content, metadata_json, created_at)`
- `rooms(id, workspace_id, floor_id, tilemap_json)`; `furniture(id, room_id, asset_id, x, y, rotation)`
- `skins(id, asset_manifest_path, animation_manifest_json, license_info)`
- `workflows(id, workspace_id, name, version, graph_json)`
- `workflow_runs(id, workflow_id, state, started_at, ended_at, error)`
- `task_runs(id, run_id, node_id, agent_id, state, input_json, output_json, retry_count)`
- `agent_messages(id, run_id, from_agent_id, to_agent_id, kind, payload_json, correlation_id, timestamp)`
- `runtime_events(id, seq, workspace_id, run_id_nullable, agent_id_nullable, event_type, payload_json, created_at)`
- `audit_logs(id, actor, action, target, decision, metadata_json, created_at)`

Schema cần migrations, FK, indexes cho run_id/agent_id/time, soft-delete hoặc archival phù hợp. Không lưu API key plaintext trong DB hay Git.

## 4. Architecture
- `apps/web`: React + TypeScript + Vite; PixiJS office canvas; React Flow workflow editor; Zustand client state.
- `services/api`: FastAPI REST + WebSocket; config, CRUD, run management, event stream.
- `services/worker`: background workflow execution, agent adapters, cancellation/retry.
- `packages/contracts`: OpenAPI/JSON Schema hoặc TS types generated từ API; event schema versioned.
- `packages/brain-adapters`: mock, OpenAI-compatible, Ollama; future Codex/Claude bridges.
- `infra`: Docker Compose; PostgreSQL (có thể dùng SQLite ở prototype nhưng phải migration-ready), Redis chỉ khi worker queue cần thiết; local asset storage.

Nguyên tắc: modular monolith, không microservices sớm. API không chạy shell trực tiếp; worker/sandbox chịu trách nhiệm thực thi. Backend là source of truth; game chỉ consume events.

## 5. Core contracts
### BrainAdapter
```ts
interface BrainAdapter {
  capabilities(): BrainCapabilities;
  run(request: BrainRequest, signal?: AbortSignal): AsyncIterable<BrainEvent>;
}
```
BrainRequest có agent_id, run_id, messages, system_prompt, allowed_tools, budget, workspace context. Event có `type`, `timestamp`, `run_id`, `agent_id`, `payload`, `schema_version`.

### Runtime events
`agent.created`, `agent.idle`, `task.queued`, `task.started`, `task.progress`, `tool.requested`, `approval.required`, `task.completed`, `task.failed`, `task.cancelled`, `workflow.completed`, `workflow.failed`.

Event phải có monotonically increasing `seq` (theo stream hoặc global) để reconnect/replay. UI không suy diễn completed từ animation.

### REST API (baseline)
- `GET /health`, `GET /api/workspaces`, `POST /api/workspaces`
- `GET/POST /api/agents`, `GET/PATCH/DELETE /api/agents/{id}`
- `GET/POST /api/workflows`, `POST /api/workflows/{id}/validate`
- `POST /api/workflows/{id}/runs`, `GET /api/runs/{id}`, `POST /api/runs/{id}/cancel`
- `GET /api/runs/{id}/messages`, `GET /api/runs/{id}/events`
- `GET/PUT /api/rooms/{id}/layout`, `GET /api/assets`
- `WS /ws/workspaces/{id}/events`

## 6. Frontend screens
1. Home / Workspace picker.
2. Office view: pixel map, agents, furniture, task indicators, inspector panel.
3. Agent Studio: Identity, Role, Brain, Skills, Tools, Memory, Skin, Run History.
4. Workflow Builder: nodes/edges, validation, run, step inspector.
5. Run Monitor: live event timeline, errors, outputs, retry/cancel.
6. Settings: provider connection tests, local paths, budget and security.

Design: desktop-first; clean white/light UI surrounding pixel canvas; no copyrighted game sprites; assets must have license manifest. Use consistent tile sizes, pixel-perfect scaling, nearest-neighbor textures, fixed animation FPS and deterministic coordinate transforms.

## 7. Security & reliability
- Bind services to 127.0.0.1 by default; do not expose publicly without security review.
- `.env.example` only; `.env`, credentials, token dumps excluded from Git and logs.
- Restrict workspace filesystem roots; normalize paths, block `../` traversal and symlink escape.
- Shell execution disabled by default or sandboxed with allowlist and explicit approval.
- Timeouts, cancellation, max workflow steps, concurrency limit, per-run budget.
- Backend event persistence before broadcast when possible; reconnect and snapshot recovery.
- Do not put sensitive full prompts, credentials, personal files into dev logs; redact and store only necessary debug metadata.
- Unit/integration tests for workspace isolation, approval bypass, cancellation and event ordering.

## 8. GitHub reuse policy
Candidate references: `marmottajr/habblaud`, `pixel-agents-hq/pixel-agents`, `OpenBMB/ChatDev`, `basriayaz/pixel-office`, `bignutchanon/pixel-office`, `paulrobello/claude-office`.

Before reusing source: inspect current commit, LICENSE, dependencies, asset rights, architecture, maintainability; document decision in `docs/reuse/REUSE_AUDIT.md` including repo URL, commit SHA, files, license, modifications, attribution and tests. Prefer inspiration/adapters to bulk copy. Do not claim a feature is available without verifying repository code. Keep attribution and notices required by licenses.

## 9. AI MULTI-AGENT DEVELOPMENT PROTOCOL (BẮT BUỘC)
### 9.1 Roles
- **Architect Agent:** architecture, contracts, ADRs, task breakdown; no large implementation without approval.
- **Backend Agent:** API, DB, workflow runtime, adapters, backend tests.
- **Frontend Agent:** React screens, state, API integration, frontend tests.
- **Pixel/Game Agent:** PixiJS canvas, sprites, movement, office layout.
- **QA/Reviewer Agent:** independent review, security, integration tests, reproducible bugs; does not silently fix files assigned to another agent.
- **Integrator Agent:** merges approved branches, resolves conflicts, runs end-to-end acceptance, maintains release notes.

### 9.2 Ownership and branching
Every task must define owner, branch/worktree, file ownership, dependencies, API contract, acceptance criteria. One active writer per file at a time. Each coding agent works in a dedicated git worktree and branch named `agent/<role>/<task-id>`. Cross-module edits require a coordination note and explicit approval. Reviewer works read-only or submits a separate patch branch.

### 9.3 Required repository files
```
AGENTS.md                         # Global coding and coordination instructions
README.md                         # Localhost setup and demo
.env.example                      # Non-secret configuration template
TASKS.md                          # Task board with ownership and dependencies
CHANGELOG.md                      # User-facing changes
AI_LOGS/
  INDEX.md                        # Sessions, owners, task links
  sessions/YYYY-MM-DD/<agent-id>-<session-id>.md
  handoffs/<task-id>.md
  reviews/<task-id>-review.md
  decisions/ADR-0001-*.md
  incidents/<incident-id>.md
  schemas/log-entry.schema.json
  machine/events.jsonl            # Structured sanitized events (optional, rotated)
docs/contracts/                   # API and event schemas
```

### 9.4 Mandatory AI session log
Each agent writes a session log at task start, at meaningful milestones and before handoff. Required fields:
- `timestamp` (ISO-8601), `session_id`, `agent_id`, `agent_role`, `model/provider` (if known)
- `task_id`, `goal`, `status`, `branch`, `base_commit`, `workspace`, `owned_paths`
- `inputs` (references only), `assumptions`, `constraints`, `plan`
- `changes` (paths + summary), `decisions` (why + alternatives), `commands` (sanitized)
- `tests` (exact command + PASS/FAIL/SKIPPED + reason), `risks`, `blockers`
- `next_steps`, `handoff_to`, `commit_sha`, `review_status`

Do NOT log chain-of-thought/private reasoning, secrets, full raw model transcripts or personal content. Log decisions, concise rationale, actions and evidence only.

### 9.5 Log example
```yaml
session_id: session-20261017-backend-001
agent_id: backend-01
agent_role: backend
provider: codex
task_id: TASK-012
status: ready_for_review
branch: agent/backend/TASK-012
base_commit: abc1234
owned_paths: [services/api/agents/, tests/api/test_agents.py]
summary: "Implemented agent CRUD with validation"
changes:
  - path: services/api/agents/routes.py
    reason: "Expose CRUD endpoints"
commands:
  - "pytest tests/api/test_agents.py -q"
tests:
  - command: "pytest tests/api/test_agents.py -q"
    result: PASS
    evidence: "12 passed"
risks: ["Provider validation deferred to TASK-019"]
commit_sha: def5678
handoff_to: reviewer-01
review_status: pending
```

### 9.6 Task lifecycle
`BACKLOG -> READY -> IN_PROGRESS -> SELF_TESTED -> READY_FOR_REVIEW -> CHANGES_REQUESTED / APPROVED -> INTEGRATED -> DONE`.
A task cannot become DONE without: code committed, tests documented, AI session log, reviewer approval and integrator verification. Review must link to commit SHA and test evidence. Failed/skipped tests cannot be presented as passed.

### 9.7 Handoff contract
Each handoff must include: task ID, branch/commit, changed paths, API/schema changes, migration requirements, how to run, test evidence, known limitations, open questions, recommended reviewer focus. Reviewer documents severity (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`), file/line, reproduction, expected vs actual, suggested fix and verdict (`APPROVE`/`REQUEST_CHANGES`). Reviewer cannot approve their own implementation.

### 9.8 Conflict and change control
- Contract changes require Architect approval and update to schema + affected tasks before implementation.
- If two agents need the same file, Integrator serializes work or refactors ownership.
- New dependency requires ADR or dependency decision record (license, size, maintenance, security).
- No agent may remove tests or suppress lint to make CI pass without an explicit review note.
- Every new feature requires at least one success test and one failure-path test.

## 10. Delivery phases and gates
**Sprint 0 — Foundation:** monorepo, Docker Compose, healthchecks, migrations, AGENTS.md, AI_LOGS, lint/test CI, mock brain. Gate: clean install works.

**Sprint 1 — Agents and workspaces:** CRUD, provider adapters, workspace isolation, agent studio. Gate: create 3 agents and switch brains; mock and provider tests.

**Sprint 2 — Workflow runtime:** graph editor, orchestration, messaging, event stream, retry/cancel. Gate: Planner→Developer→Reviewer end-to-end, persisted trace.

**Sprint 3 — Pixel office:** sprite presets, room editor, furniture, movement, realtime mapping. Gate: actual agent events animate correctly; refresh recovers layout.

**Sprint 4 — Hardening:** approvals, security, regression, docs, audit/review. Gate: all P0 acceptance tests pass from clean clone.

## 11. Definition of Done
- Feature matches acceptance criteria and does not exceed approved scope.
- Types, lint, unit tests, integration tests pass; E2E smoke test where applicable.
- No hardcoded secrets, no unsafe path access, no unrestricted shell.
- API schema and docs updated; migrations reversible or rollback documented.
- AI session log + handoff + independent review exist.
- Reviewer has approved; integrator has verified on clean local environment.
- No `TODO` masquerading as implemented behavior; limitations visible in UI and release notes.

## 12. Instructions for the first agent
1. Read this requirements document and create `AGENTS.md`, `TASKS.md`, `AI_LOGS/INDEX.md`.
2. Inspect candidate repositories and produce `docs/reuse/REUSE_AUDIT.md`; do not copy code before license review.
3. Draft architecture ADR and contracts before parallel implementation.
4. Bootstrap a minimal running skeleton with mock agents and an office canvas.
5. Split tasks by ownership and git worktrees; require logs and review on every PR.
6. Never claim a feature works without running and recording the exact tests.

---
## 13. SOURCE REFERENCES & VISUAL DESIGN REFERENCES (BẮT BUỘC CHO AI AGENTS)

### 13.1 Nguyên tắc sử dụng
Các URL sau là **nguồn tham chiếu**, không phải bằng chứng rằng code đã được tích hợp. Trước khi triển khai, Architect/Research Agent phải mở README, kiểm tra cấu trúc source ở commit cụ thể, LICENSE của code và từng asset, rồi ghi kết quả vào `docs/reuse/REUSE_AUDIT.md`. Không tự ý sao chép nguyên repo hoặc sprite nếu chưa kiểm tra quyền sử dụng. Ghi SHA và ngày truy cập; không phụ thuộc nhánh `main` thay đổi theo thời gian.

| ID | Repository | Mục đích tham khảo | Vị trí cần khảo sát | Ưu tiên |
|---|---|---|---|---|
| REF-01 | https://github.com/marmottajr/habblaud | Bố cục pixel office, chuyển động nhân vật, trạng thái agent, phòng/hành lang, realtime feed | `client/`, `server/`, `shared/`, `docs/screenshots/`, `README.md` | P0 visual |
| REF-02 | https://github.com/pixel-agents-hq/pixel-agents | Sprite/animation, office editor, agent visualization | `webview-ui/`, `core/`, `server/`, `README.md` | P0 visual |
| REF-03 | https://github.com/OpenBMB/ChatDev | Workflow multi-agent, runtime, tool, mẫu YAML, handoff | `runtime/`, `workflow/`, `server/`, `yaml_instance/`, `docs/` | P0 backend |
| REF-04 | https://github.com/basriayaz/pixel-office | Agent profile, quản lý nhân viên AI, memory/skill (xác minh implementation) | README và source thực tế | P1 |
| REF-05 | https://github.com/bignutchanon/pixel-office | Codex/Claude integration và trạng thái CLI (xác minh implementation) | README và source thực tế | P1 |
| REF-06 | https://github.com/paulrobello/claude-office | Bảng activity, task và trạng thái agent (xác minh implementation) | README và source thực tế | P1 |
| REF-07 | https://github.com/OpenBMB/ChatDev/tree/chatdev1.0 | Mô hình công ty ảo CEO/CTO/Programmer, phân vai và trao đổi | README và source nhánh legacy | Concept |

### 13.2 Link hình ảnh và UI thực tế để agent quan sát
- **Habblaud — ảnh chụp giao diện chính thức:** https://github.com/marmottajr/habblaud/tree/main/docs/screenshots
- **Habblaud — README chứa hình tổng quan, agent detail, day/night, collaboration:** https://github.com/marmottajr/habblaud#what-it-looks-like
- **Pixel Agents — README với minh họa sản phẩm:** https://github.com/pixel-agents-hq/pixel-agents#readme
- **ChatDev — hình workflow và demo:** https://github.com/OpenBMB/ChatDev#readme
- **ChatDev — thư mục GIF demo:** https://github.com/OpenBMB/ChatDev/tree/main/assets/cases
- **Pixel Office (basriayaz) — README và hình minh họa nếu có:** https://github.com/basriayaz/pixel-office
- **Pixel Office (bignutchanon) — README và hình minh họa nếu có:** https://github.com/bignutchanon/pixel-office
- **Claude Office — README và hình minh họa nếu có:** https://github.com/paulrobello/claude-office

Các liên kết README/thư mục là **visual reference links**, không phải file ảnh đã tải về. AI phải kiểm tra đường dẫn và chọn ảnh phù hợp; không tự giả định ảnh tồn tại trong mọi repo. Nếu có quyền sử dụng, lưu bản copy được phép vào `docs/references/visual/` và ghi nguồn + license + commit SHA trong `ATTRIBUTION.md`. Nếu chưa rõ quyền, chỉ giữ URL, không đưa ảnh vào ứng dụng.

### 13.3 Visual design specification — bắt buộc khi làm UI
- Style: pixel-art 2D top-down / 3/4 view đồng nhất, nét pixel sắc, không làm mờ do interpolation; background UI sáng, bố cục dashboard hiện đại.
- Màn hình P0: (1) Office canvas có nhiều bàn và agent; (2) Agent detail panel gồm Role/Brain/Skills/Tools/Memory/Skin; (3) Workflow editor kéo-thả; (4) Furniture editor có grid và lưu layout; (5) Task activity feed và logs.
- Canvas hỗ trợ pan/zoom, grid, collision và chọn nhân vật; zoom integer khi có thể, render pixelated; không dùng ảnh tĩnh giả làm canvas tương tác.
- Avatar states: idle, walk, working, waiting, error, completed. Backend events là nguồn sự thật; animation không tự quyết định task thành công.
- Bản đầu chỉ dùng asset preset hợp lệ; AI skin generation, town map, nhiều tầng, marketplace là phase sau.
- Responsive tối thiểu desktop 1366×768 và 1920×1080; sidebar không che canvas, popup có thể đóng, text tiếng Việt rõ ràng.

### 13.4 Visual acceptance & evidence
Mỗi màn hình phải có: (a) screenshot chạy localhost ở 1366×768; (b) video/GIF ngắn hoặc Playwright test chứng minh thao tác thật; (c) checklist so sánh với reference và giải thích khác biệt; (d) kiểm tra không có lỗi console; (e) link tới commit và task log. Reviewer không chấp nhận chỉ có mockup đẹp nhưng chức năng không chạy.

### 13.5 Reference investigation task template
```yaml
id: REF-AUDIT-001
owner: research-agent
sources: [REF-01, REF-02, REF-03]
outputs:
  - docs/reuse/REUSE_AUDIT.md
  - docs/references/VISUAL_REFERENCE_BOARD.md
  - docs/references/ATTRIBUTION.md
required_fields:
  - repository_url
  - commit_sha
  - license_code_and_assets
  - relevant_source_paths
  - screenshots_or_demo_links
  - adaptation_strategy
  - risks_and_tests
review_gate: independent_reviewer_approval
```

### 13.6 AI log bổ sung cho mọi task tái sử dụng code / thiết kế
Bổ sung vào mỗi `AI_LOGS/<task-id>.md`: `Reference IDs`, `Source URL`, `Commit SHA`, `Files inspected`, `Asset rights`, `Copied/Adapted/Inspiration-only`, `Visual evidence`, `Deviation from reference`, `Reviewer decision`. Không được ghi "đã tái sử dụng" nếu mới chỉ đọc README.
