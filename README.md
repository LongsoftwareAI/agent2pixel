# AgentVerse — localhost MVP

Văn phòng pixel cho agent thực thi workflow có lưu lịch sử. Phạm vi: một người dùng trên localhost, một tòa nhà, hai workspace độc lập; không SaaS/thành phố. Requirement gốc: [v0.1](docs/requirements/AGENTVERSE_REQUIREMENTS_v0.1.md).

## Chạy development

Cần Python 3.12+, Node 24 và npm. Từ thư mục repository:

```sh
cp .env.example .env
bash scripts/install.sh
python3 scripts/dev.py
```

Mở localhost port 3000 trong trình duyệt. API port 8000; tất cả port dev bind 127.0.0.1. Ctrl-C dừng hai service. SQLite và workspace files trong `var/`, bị Git bỏ qua. Không xóa `var/` nếu muốn giữ dữ liệu. MockBrain không cần key hoặc model. Nó thực thi workflow thật với output deterministic; không được hiểu là model AI bên ngoài đã được gọi.

## Docker Compose

```sh
docker compose up --build
```

Port publish chỉ trên 127.0.0.1; API trong container nghe trên mạng nội bộ Compose. Dữ liệu lưu volume `agentverse-data`. Web proxy `/api`, `/health`, `/ws` đến API. Compose validation/build/runtime status xem báo cáo evidence, không suy từ sự tồn tại của Dockerfile.

## Workflow demo

Chọn Coding hoặc Research. Chọn ba agent Planner/Developer/Reviewer, dùng MockBrain mặc định; chỉnh role, provider và skin trong Agent Studio. Mở Workflow Builder, kiểm tra graph Start → Planner → Developer → Reviewer → End, lưu rồi chạy với yêu cầu của bạn. Run Monitor hiển thị task inputs/outputs, message handoffs và event sequence. Output từng node trở thành input node tiếp theo. Chạy lại, hủy hoặc retry thông qua backend. State văn phòng phản ánh backend events. Mất kết nối hiển thị disconnected.

Office có chọn agent và chế độ sửa furniture; lưu layout qua API, refresh để xác minh persistence. Các room/workspace có agent, task, memory và project root riêng.

## Provider và an toàn

Không lưu key trong form/DB/Git. Thiết lập credential bằng biến môi trường được mô tả trong `.env.example`; cấu hình provider/model/endpoint trong Agent Studio. Settings kiểm tra khả dụng. API adapter có test HTTP mock cho OpenAI-compatible và Ollama; thành công với mock không chứng minh tài khoản/API/model thật hoạt động. Không có key vẫn dùng MockBrain được. Không gửi secret trong chat hoặc AI logs.

Shell và tool có side effect bị chặn mặc định. Không có auth: giữ bind loopback, không mở public/tunnel. Workspace file reader kiểm tra containment/traversal/symlink; API và UI không cung cấp shell tùy ý. SQLite là lựa chọn prototype với migration schema versioned.

## Kiểm thử

```sh
.venv/bin/python -m pytest tests/backend -q
npm --prefix apps/web test
npm --prefix apps/web run build
```

QA E2E và ảnh chụp: xem `tests/e2e/` cùng báo cáo trong `AI_LOGS/reviews/` sau integration. Kết quả chính xác, SHA được review và các giới hạn được ghi trong `docs/VALIDATION.md`; không coi checklist yêu cầu là kết quả test.

## Nguồn tham khảo và cộng tác

- [Reuse audit](docs/reuse/REUSE_AUDIT.md): commit, source, license và quyết định inspiration-only cho sáu repo + ChatDev legacy.
- [Visual board](docs/references/VISUAL_REFERENCE_BOARD.md): Habblaud và Pixel Agents đã xem ảnh thực tế; artwork ứng dụng được viết mới.
- [Contracts](docs/contracts/API.md), [ownership/task board](TASKS.md), [agent rules](AGENTS.md), [AI logs](AI_LOGS/INDEX.md).

Mỗi coding agent dùng branch/worktree riêng; một writer mỗi path. QA review độc lập, không tự sửa file owner khác. Không task nào DONE nếu thiếu commit, tests, session log, reviewer approval và integrator verification.
