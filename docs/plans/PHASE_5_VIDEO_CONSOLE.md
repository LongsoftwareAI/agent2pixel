# Phase 5 — kế hoạch AI Operations Console

Ngày 2026-10-18. Trạng thái cập nhật: local core đã tích hợp và được review độc lập; toàn bộ Phase 5 còn OPEN. Xem [kiểm chứng và phần còn thiếu](../PHASE_5_VALIDATION.md). Các milestone bên dưới giữ lại phạm vi đầy đủ, không phải tuyên bố tất cả đã xong. Phạm vi được người dùng chọn: console vận hành đầy đủ trước, CRM sau. [Requirement chuẩn v0.5](../requirements/AGENTVERSE_REQUIREMENTS_v0.5.md); [video evidence board](../references/VIDEO_CONSOLE_REFERENCE_BOARD.md). Không thay bằng một dashboard trang trí; mọi action phải nối runtime có thật.

## 1. Baseline và tái sử dụng

| Phần | Tái sử dụng | Phải làm mới / giới hạn |
|---|---|---|
| Agent/runtime | AgentSpec role/brain/skills/tools/memory, LangGraph, Harness, checkpoints, approval/rework | Chat/session bridge, SOUL revision UI; không đổi sang Hermes vì nhãn video |
| Công việc/flow | Work board, DAG/editor, manual priority dispatch, tool nodes, artifact review/diff | Console QC layout, inbox, chat-created work, typed result cards; không giả background worker đã có |
| Dữ liệu/tool | Sources/CSV/Decimal/provenance, bounded web reader | Upload/message attachments, capability registry; web public baseline đang lỗi DNS |
| Memory/events | History/tombstones, replay events | Logical MEMORY/USER view, session explorer, diagnostics/audit separation, usage aggregation |
| Office | Renderer/art/layout Habblaud, MIT/OFL notices | Shell entry/profile links/lazy load; không dựng 3D mới |
| UI | React/API client/validation patterns hiện có | Shell, dashboard, room/chat, graph, cost, schedule monitor, skills lifecycle, settings |
| Integrations | Native + official Harness/Cordis adapter | Health/schedule observation interfaces, pricing and optional STT adapters; không hứa Telegram/Meta CRM |

Baseline live provider UNRUN (thiếu credentials), public web FAILED DNS; phải giải quyết và test lại riêng trước claim live. Tài liệu này không thêm dependency. Trước khi chọn graph/chart/upload/STT/XLSX library, ghi ADR về nhu cầu, license, compatibility, security và lockfile.

## 2. Milestone và phụ thuộc

| Milestone | Tasks / requirement IDs | Điều kiện ra |
|---|---|---|
| M0 — contract/design | P5-01…19: API schemas, migrations, capability matrix, chat→run lifecycle, redaction/skill policies; normalized visual layouts | Contract/ownership duyệt, không còn mơ hồ schedule monitor vs scheduler, xác định package local và STT adapter test được |
| M1 — shell/visual gate | P5-01,02,17,18; route skeleton có trạng thái trung thực; synthetic visual fixtures chỉ trong test | Sidebar/header/card bounds/font reviewed ở1108×636; keyboard/settings persistence và office regression PASS. Không tuyên bố screen skeleton hoàn thành chức năng |
| M2 — làm việc thật | P5-03…08,11,15; conversations, sessions, revision documents, structured results, QC | Một task mới từ chat tạo run, dùng source/CSV thật, artifact có hash, review/rework/accept; retry/cancel/restart và cách ly workspace PASS |
| M3 — vận hành | P5-09,10,12…14,16; health/topology/usage/audit/cron observer/skill lifecycle | Đối soát số liệu với DB, unknown/stale đúng, schedule observer thật hoặc local adapter có nhãn, skill apply/rollback/restart state thật; không để fake telemetry |
| M4 — media/hoàn thiện | P5-19 và rà đủ mọi ID | Attachment end-to-end, STT permission/transcript review + fixture và live status riêng, responsive/a11y, không còn nút giả; dependency bị thiếu phải ghi OPEN |
| M5 — independent acceptance | Toàn scope | Fresh install/build/tests, migration/backup/restore, localhost screenshots, independent review đúng SHA, GitHub review branch; chỉ đánh dấu slice nếu live gates chưa đạt |

M0 trước sửa shared contracts; M1 visual gate trước nhân rộng component. Backend M2 và frontend M1 có thể tiến song song sau contract. M3 adapter interfaces có thể tách song song; chốt integration theo milestone, không merge một lần cuối. Chưa ấn định deadline khi chưa xong M0; mỗi PR nên một vertical slice có test thay vì hứa số ngày thiếu căn cứ.

## 3. Task độc lập và file ownership khi bắt đầu code

Root giữ quyền ghi docs/contracts/root config và integration. Mỗi agent coding dùng branch/worktree riêng theo AGENTS.md; không cho hai writer cùng path. Bảng là phân công vai trò cho phase tới, chưa khởi chạy coding agents trong task tài liệu này.

| Task | Owner | Paths dự kiến độc quyền | Dependencies / handoff |
|---|---|---|---|
| P5-ARCH | Architect/Integrator | docs/, config root, migrations contract coordination | M0 API/ownership; migration source do Backend viết, root review |
| P5-BE | Backend | services/, tests/backend/, tests/phase5/backend/ | M0; domain/migration/chat/session/metrics/skill/health; nếu tách runtime và tools phải chia file cụ thể trước |
| P5-FE | Frontend | apps/web/ trừ subtree office đã giao Pixel; tests UI colocated | M0 schemas + M1 design; shell và toàn console; request API change qua root |
| P5-PIX | Pixel/Game | apps/web/src/office/ và assets office được audit | Giữ Habblaud, office/profile integration; subtree Habblaud khác cần root chuyển ownership trước khi sửa |
| P5-QA | QA độc lập | tests/phase5/e2e/, tests/phase5/evidence/, AI_LOGS/reviews/P5-* | Black-box success/failure, actual local browser screenshots, license/privacy check; không approve code mình viết |

Mỗi agent chỉ ghi log/session và handoff của mình. Root duyệt thay đổi QA test/evidence; reviewer khác duyệt root integration. AI logs dùng schema `AI_LOGS/schemas/log-entry.schema.json`: goal/inputs/assumptions/constraints/paths/decisions/changes/commands/tests/risks/blockers/next steps/commit/review. Không ghi chain-of-thought, secret hoặc toàn văn dữ liệu khách hàng. Lifecycle BACKLOG→READY→IN_PROGRESS→SELF_TESTED→READY_FOR_REVIEW→APPROVED/CHANGES_REQUESTED→INTEGRATED→DONE. Review findings phải được đóng bằng evidence, không self-approval.

## 4. Test và evidence cần chuẩn bị

- Backend contract/integration: migration giữ IDs/history; chat idempotency, stream reconnect cursor/dedupe, cancellation/restart; workspace isolation; revision conflict và stale approval; skill package validate/apply/failure rollback/pending activation; schedule observations stale/error/timezone; pricing unknown vs estimate vs actual; secret redaction và payload injection.
- Browser vertical journeys: room/direct chat→giao việc→workflow→tool→artifact→QC→accept; request rework và lỗi tool; sessions/audit deep-link; theme/keyboard/search/filter/density/reload; không console error. Mock fixtures ghi rõ fixture; production dữ liệu thật local ở acceptance DB riêng.
- Office regression: layout persistence, state chỉ từ backend, click agent mở đúng profile; control legacy links không gãy. Test CSV/source hiện có và backup/restore không bị mất khi đổi shell.
- Visual: chụp từng màn hình và trạng thái quan trọng ở1108×636,1366×768,1920×1080; compare với thiết kế đã review, user review với video local. Ảnh synthetic/no PII, manifest path/hash/viewport/route/commit/data mode; mở ảnh kiểm tra nội dung trước giao. Bảng reference không được thay bằng screenshot placeholder.
- Live evidence riêng: model thật cho một task noncoding; source public sau khi fix DNS; STT thật khi adapter configured. Thiếu credentials/capability = UNRUN, lỗi = FAILED; không gọi provider stub là live. Không cần credential để làm M0/M1/local-runtime work.

Root duy trì bảng `P5-ID | commit | success test | failure test | screenshots | independent review | state` trong acceptance report khi code bắt đầu; tất cả19IDs phải có dòng. Không tạo test giả chỉ để checklist xanh.

## 5. Giao hàng và điều kiện không được tuyên bố hoàn thành

Bàn giao mỗi milestone qua review branch, không merge main/deploy public tự động. Release note phân biệt implemented/local-tested/live-tested/deferred/open. CRM là deferred theo quyết định người dùng; thiếu console feature vẫn OPEN, không tự đổi thành CRM hoặc giảm scope. Video không chứng minh voice/send/install/billing chạy thật: Phase5 cần evidence riêng cho những điều đó.

Trước code, root phải chốt `docs/contracts/phase5/IMPLEMENTATION.md` gồm exact routes/schema, event mapping, migration version, skill package format và path ownership. Đây là deliverable M0, chưa có trong task lập requirement. Trước DONE sản phẩm phải có independent QA APPROVE pinned SHA và screenshot localhost. Task chuẩn bị hiện tại chỉ tạo requirement/board/plan, không tự nhận đã nâng cấp app.
