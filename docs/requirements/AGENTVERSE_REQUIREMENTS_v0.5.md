# AgentVerse requirements v0.5 — AI Operations Console

Trạng thái: đề xuất chi tiết để review trước Phase 5; chưa triển khai. Ngày 2026-10-18. Baseline mã nguồn: `295f7603f375960dc913cdcf6ec5a49485caa2d9` (Phase 4). Bản này định nghĩa trải nghiệm tiếp theo; giữ [v0.1](AGENTVERSE_REQUIREMENTS_v0.1.md) và lịch sử Phase 2–4 để kiểm chứng, không sửa ngược bằng chứng cũ. Với thay đổi UI/phạm vi mới, v0.5 ưu tiên; quy tắc an toàn, license, logging và review cũ vẫn áp dụng.

## 1. Mục tiêu và quyết định đã chốt

Tạo một công ty agent đa nhiệm: người dùng giao brief, chọn/điều chỉnh flow, agent thực thi bằng model/tool được cấp, bàn giao sản phẩm có nguồn và được người phụ trách duyệt. Không giới hạn vào coding; cũng không tuyên bố làm được mọi nhiệm vụ khi thiếu tool hoặc quyền.

Người dùng chọn: **làm đầy đủ console vận hành AI đã thấy trong video trước; CRM triển khai sau**. Giao diện console bám sát [video reference board](../references/VIDEO_CONSOLE_REFERENCE_BOARD.md) về bố cục, màu, mật độ, phân nhóm và tương tác. Văn phòng Habblaud tiếp tục là view riêng, trạng thái lấy từ backend. Không đổi engine thành Hermes, không yêu cầu macOS/launchd/Tailscale vì tên đó xuất hiện trong video. Localhost, một người dùng, dữ liệu workspace cách ly; không SaaS/city/public deployment.

Loại khỏi Phase 5: khách hàng, đơn hàng, phễu, duyệt tin bán hàng, catalog/cấu hình sản phẩm, checkout; clone landing page ngoài console; Meta Ads/Telegram/Slack connector đầy đủ; dựng scene 3D mới. Không hiển thị menu CRM chết như chức năng đã có. Video có cấu hình sản phẩm ở 45–46s nhưng vẫn hoãn theo quyết định trên.

## 2. Cách đọc bằng chứng

OBSERVED là điều nhìn thấy, NAV_ONLY chỉ có nhãn menu, DERIVED là yêu cầu mới do AgentVerse cần để hoạt động. Backend trong video đều chưa được xác minh. Audio chưa được phiên âm. Các yêu cầu dưới đây là hành vi cần xây dựng/kiểm thử, không phải tuyên bố đã có. Chi tiết nguồn/thời gian và nút chưa được thực thi nằm ở board.

## 3. Yêu cầu theo màn hình và tiêu chí chấp nhận

Mỗi ID phải có success/failure checks, trạng thái loading/empty/error/stale và bằng chứng localhost. Khi chưa có integration, trả về `unconfigured` kèm lý do; không thay bằng số giả. Disabled có lý do là xử lý trung thực nhưng không tự đóng hạng mục yêu cầu chức năng.

| ID | Màn hình / nguồn | Hành vi bắt buộc và acceptance chính |
|---|---|---|
| P5-01 | Shell — OBSERVED xuyên video | Sidebar/header như board, grouped nav, badge thật, avatar/status, global search và command palette Ctrl/Cmd+K, collapse Ctrl/Cmd+B, URL/deep-link/back/forward. Keyboard focus/labels; trạng thái disconnected không xanh giả. Không copy email/logo reference |
| P5-02 | Tổng quan — 10–12s | KPI phân biệt agent configured/busy, gateway connected, công việc chờ duyệt; chart có khoảng thời gian/đơn vị; recent work/activity/background services. Link từ card đến đúng bản ghi; tổng bằng query cùng filter/timezone; dữ liệu không có là — |
| P5-03 | Cần xử lý — NAV_ONLY + DERIVED | Inbox hợp nhất approval payload, review artifact/sản phẩm bàn giao, work acceptance và cảnh báo vận hành; phân biệt từng loại. Mở đúng revision, accept/reject có lý do; double-submit/revision cũ bị chặn; badge phản ánh backend |
| P5-04 | Phòng chung — 13–22s | Hội thoại lưu bền trong workspace, @agent, quick prompts, markdown an toàn, task/result cards, bảng mở rộng, mở việc/hỏi tiếp. Gửi một lần tạo message và workflow thật; nhận stream/cancel/reconnect không trùng. Không tự giao mọi bot hoặc tự cấp tool |
| P5-05 | Chat riêng — 41s | Conversation theo bot/session, history/new, composer. Điều phối đến đúng agent/engine; lưu model/tool/error và task/run IDs. Retry không gửi lặp; sửa agent config không âm thầm đổi revision của run đã tạo |
| P5-06 | Danh sách bot — 31–37s | List/detail, avatar/role/skills/tools/memory/brain/engine; usage có nguồn, chat action. Tabs Overview/SOUL/Skills/Memory/Tasks/Activity/Channels/Cron/Config liên kết cùng dữ liệu, không tạo bản sao lệch. SOUL/role editor có version/diff; config validation và rollback revision |
| P5-07 | Giao việc & QC — 38–40s | Giữ brief/criteria, owner/priority/deadline, filter/search/archive/list-detail; giao workflow tùy chỉnh, dispatch thực tế, xem output. Review/rework bounded và nghiệm thu có quyền/phiên bản; không đổi “tool done” thành “đã nghiệm thu”. Archive không xóa lịch sử |
| P5-08 | Workflow và sản phẩm — kế thừa + DERIVED | Mở builder hiện có từ giao việc, chỉnh agent/tool/review nodes và flow templates đa ngành. Giữ checkpoint, provenance, artifact hash/version/diff. Bảng/CSV/XLSX chỉ tải khi backend tạo đúng format; không đổi đuôi CSV thành XLSX. Report schema generic, không hard-code báo cáo ads trong video |
| P5-09 | Lịch chạy — 42–44s | Console **monitor only**: nhóm bot, search, last/next/timezone, heartbeat, result/error, link task/run. Adapter dữ liệu lịch có nguồn; lịch chưa cấu hình không có fake next-run. Không tạo/sửa/bật/tắt trong console. Yêu cầu thay lịch qua assistant chỉ thực thi khi có tool adapter được cấp quyền; nếu chưa có phải nói rõ không hỗ trợ |
| P5-10 | Kho skill — 47–48s | Chọn bot/search/checkbox/detail/install/update/remove reviewed package. Manifest version/hash/license/dependencies/tool grants; preview diff và approval trước thay đổi. Bind/unbind/cập nhật thực sự, transaction/rollback/backup; pending restart khác active version. Không tải/chạy shell tùy ý, không tự tăng quyền. Unsupported package báo lý do; phải có ít nhất một package local được test trọn vòng |
| P5-11 | Bộ nhớ — 49s + kế thừa | Nhóm bot, MEMORY/USER logical documents, counts/age/expand; ánh xạ vào memory store hiện có, không giả định đường dẫn Hermes. Giữ edit/history/tombstone/provenance và workspace isolation; chống lost update. Nội dung nguồn không tự trở thành lệnh hệ thống |
| P5-12 | Kênh kết nối — 50s | Health registry: provider/tool/gateway/service capabilities, observed_at, last error, dependency status; hiển thị tên biến secret và configured/missing, tuyệt đối không giá trị. Gateway online khác model/tool ready. Không tạo PID/Tailscale/launchd giả; outbound connector chưa có = unconfigured |
| P5-13 | Sơ đồ hệ thống — 01–05s | Read-only topology từ registry/runtime: workspace/user, agent/coordinator, workflow/task, tool/skill, model/service/channel. Search, pan/zoom, fit, node detail, rearrange local, refresh; legend/status. Không sửa grants qua kéo node; trạng thái stale khi backend mất kết nối |
| P5-14 | Chi phí & ngân sách — 06–09s | 7/30/90/all, daily chart, per-agent/model token/request/cache. Tách actual spend có provider record, estimate có pricing version/currency/date, unknown. Không suy actual từ token; không dùng số trong video. Budget thresholds là DERIVED: cấu hình local có validation/audit, cảnh báo, không hứa provider hard cap |
| P5-15 | Phiên làm việc — NAV_ONLY + DERIVED | List/detail sessions theo workspace/agent/run/status/time, search/filter, timeline/messages/tool facts/artifacts; link giữa chat/run/session. Không trộn session khác workspace; phân biệt active/resumable/failed/cancelled |
| P5-16 | Log hệ thống & nhật ký thao tác — NAV_ONLY + DERIVED | Hai view riêng: diagnostics/runtime errors và audit mutation/actor/target/revision/outcome. Filter/time/correlation ID/pagination/export được redaction. Không dump prompt/secret/env; log kỹ thuật không thay audit review. Không gán giao diện chi tiết này là đã xem trong video |
| P5-17 | Cài đặt — 00;51–52s | Theme light/dark/system, blue/black accent, sidebar size, font3levels, density2levels, start page, refresh fast/slow/off. Persist sau reload, system theo prefers-color-scheme. Office enable/disable lazy-load view Habblaud hiện có; label đúng 2D, không gọi giả là 3D. Refresh off không tắt lifecycle events cần cho run |
| P5-18 | Office và tương thích — menu + kế thừa | Nav Văn phòng AI mở Habblaud thực, agent click mở profile/chat; trạng thái backend, đồ đạc/layout lưu như trước. Giữ workflow/source/run pages và deep-link cũ/redirect rõ. Không mất DB, lịch sử, memory, IDs hoặc notices khi migrate |
| P5-19 | Attachment/voice — controls OBSERVED, hành vi DERIVED | Upload có giới hạn size/MIME, kiểm tra nội dung/path/workspace; file là dữ liệu chưa tin cậy. Voice cần permission, recording indicator/stop/cancel, adapter STT có dependency/license review, transcript được người dùng duyệt trước send; không âm thầm gửi mic. Test với adapter fixture và một lần thật khi cấu hình; thiếu adapter báo chưa cấu hình, không giả transcript |

## 4. Kiến trúc và hợp đồng cần khóa trước code

Giữ FastAPI + SQLite, LangGraph/checkpoints và Harness adapter đã audit; không thêm LangChain/CrewAI cùng lúc khi chưa có nhu cầu chứng minh được. React console tái dùng components/store/API hiện có; Habblaud renderer không viết lại. Console là projection của runtime, không tự tạo completion bằng timer/animation.

Mô hình bổ sung dự kiến: Conversation/Message/Attachment; Session; AgentDocumentRevision; SkillPackage/Binding/Activation; IntegrationHealth; ScheduleObservation; UsageRecord/PricingVersion/BudgetPolicy; AuditEntry. Tất cả record có workspace_id, stable ID, version, timestamps và source/correlation IDs phù hợp. API định nghĩa trước bằng OpenAPI/schema, error enum và migration có kiểm tra phục hồi. Chat dispatch nối work item/run/checkpoint hiện có; không làm runtime thứ hai.

Stream có event ID/sequence, resume cursor, dedupe và snapshot reconciliation; chỉ subscribe workspace được chọn. Aggregates có timezone, observed_at, provenance và cửa sổ tính. Adapter trả capability/state/reason thay vì boolean duy nhất; `unknown`, `unconfigured`, `healthy`, `degraded`, `unavailable`, `stale` phân biệt rõ. MockBrain/fixture/live model luôn có nhãn; không dùng test fixture làm data mặc định production.

Trước implementation phải khóa API route/schema, concurrency/idempotency/cancel semantics, retention/redaction, skill activation policy, chat→workflow mapping và adapter scheduling nguồn nào thực sự hỗ trợ. Schedule monitor không đồng nghĩa xây scheduler mới. Không mặc định cần đọc `~/.hermes`, systemprocess hoặc `.env` bất kỳ trên máy.

## 5. Bảo vệ và chất lượng

Giữ loopback, workspace containment, approved exact payload, tool grants, bounded review/rework. Chat/report/skill/memory/web content là dữ liệu không tin cậy; không tự cấp quyền hoặc tắt approvals vì nội dung video nói vậy. Markdown không chạy HTML/script, URL/export/attachment được kiểm tra; secret refs không trả secret. Mọi mutation quan trọng có actor, version, outcome và correlation ID. User “gửi chat nội bộ” không đồng nghĩa cấp quyền gửi email/đăng public.

Font/icon/assets có audit trước reuse; screenshot dùng synthetic nonprivate data và caption “fixture” nếu dùng fixture. Review visual cần screenshot app thực ở ba viewport board; ảnh phải được đọc lại để xác nhận không trống và path/hash đúng. Bằng chứng phải truy xuất được; không chỉ dẫn người dùng mở `/tmp` như một ảnh đã giao thành công. Chuẩn bị ảnh đã làm sạch trong repo và đính kèm chat khi nền tảng hỗ trợ.

## 6. Nghiệm thu Phase 5

Mỗi P5-ID có traceability tới PR/commit, success/failure test và evidence; IDs chưa hoàn tất nằm OPEN, không tự bỏ khỏi scope. Phải chạy chat→workflow đa nhiệm→tool thật local→artifact→QC→accept; thêm failure/retry/cancel/restart/reconnect/duplicate-message và stale-review. Kiểm thử ít nhất research có nguồn, phân tích CSV chính xác và nội dung có review; không phải chỉ bài toán coding.

Cần test migration/backup/restore từ Phase 4, cross-workspace leakage, XSS/path traversal/secrets, skill rollback/pending activation, metrics unknown/estimated/actual, schedule stale/error, keyboard/theme persistence. Live model/STT/remote connector acceptance ghi riêng PASS/FAILED/UNRUN; fixture không thay live. Baseline Phase 4 đã có 166 Python/48 control/10 office checks; chưa chạy lại trong task lập requirement, và không phải Phase 5 evidence.

DONE cho sản phẩm cần test thực đã chạy, screenshot localhost không trống, reviewer độc lập APPROVE đúng SHA, integrator xác nhận, logs/handoff đầy đủ. Với phụ thuộc chưa được cấu hình, chỉ được nghiệm thu rõ “local slice”; không tuyên bố full live console hoàn tất. [Kế hoạch triển khai](../plans/PHASE_5_VIDEO_CONSOLE.md) chia milestone/owner/gate; task hiện tại chỉ hoàn tất tài liệu sau independent review.
