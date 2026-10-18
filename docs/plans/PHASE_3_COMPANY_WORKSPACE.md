# Phase 3 — công ty agent đa nhiệm

Mục tiêu người dùng: giao việc cho một công ty agent có thể tùy chỉnh vai trò, kỹ năng, công cụ, bộ nhớ và flow; không đóng khung thành công cụ viết code. Giữ office Habblaud, localhost một người dùng và dữ liệu hiện hữu.

## Luồng làm việc

Người dùng tạo công việc với mục tiêu, tài liệu/ngữ cảnh và tiêu chí nghiệm thu; chọn hoặc chỉnh flow; ánh xạ các bước vào nhân sự hiện có. Mỗi bước có hướng dẫn riêng dù cùng một agent thực hiện nhiều bước. Agent bàn giao kết quả qua graph, lưu checkpoint và tạo sản phẩm từ output thực tế. Người dùng duyệt nội dung ghi file; hoàn thành workflow đưa công việc sang chờ review. Chỉ quyết định nghiệm thu của người dùng mới đánh dấu Done. Từ chối review đưa về backlog để giao lại.

## Lát cắt triển khai

1. Work board: backlog → running → waiting approval → review → done; failed/cancelled riêng. Brief, tiêu chí nghiệm thu, workflow, lịch sử run và quyết định review được lưu.
2. Flow đa mục đích: giữ kéo nối node, agent tùy chọn và điều kiện rẽ nhánh; thêm hướng dẫn/mục tiêu và tên sản phẩm từng bước. Graph DAG tối đa32node; chưa hứa vòng lặp vô hạn hoặc chạy mọi topology.
3. Mẫu nghiên cứu từ nguồn cung cấp, sản xuất nội dung, vận hành/báo cáo và review code. Mẫu chỉ tạo graph chỉnh được, không giả lập kết quả nghiên cứu hay tự cấp tool.
4. Sản phẩm tổng quát: Markdown/text/JSON/CSV từ output agent thực sự, không calculator template. Approval gắn đúng nội dung/agent/node/run; persist output trước khi pause, resume không gọi model lại. Không tự chạy nội dung thành code.
5. Kiểm chứng nhiều nghiệp vụ, cả thành công/thất bại, không phá dữ liệu Phase2, screenshotlocalhost và review QA độc lập.

## Mở rộng sau nền tảng này

Tool plugin/connectors mới cung cấp khả năng thực tế: tìm web có trích nguồn, bảng tính, tài liệu, ticket, lịch, email; quyền đọc/ghi và duyệt trước external sideeffect theo tool. Cần thêm provider credential/connector tương ứng trước khi tuyên bố chạy được. Không tự gửi mail, đăng bài hay chi tiền vì có template. Model có thể đề xuất công cụ nhưng không tự cấp quyền.

Tiếp theo: memory có provenance/biên tập/xóa; sandbox container task chạy code tùy ý có giới hạn; human-approval nodes chuyên biệt; loop/rework/fanout rõ semantics và quản lý ngân sách; thiết kế phòng ban/nhân sự có workload, thư viện skill cóversion và capability discovery. Giữ một scheduler LangGraph, không ghép thêmframework khôngcầnthiết.

## Nguyên tắc nghiệm thu

Test/stub được ghi nhãn, không nhầm với model thật. Kết quả lưu file cóhash và nguồn node/run, không chỉ animation. UI không đánh dấu Done thay người review. Tránh hứa “bất kỳ việc gì”: khả năng phụ thuộc tool/quyền/model và tài liệu có sẵn. Các phần chưa có được ghi rõ, không bỏ qua rồi tự nhận hoàn thành toàn bộ tầm nhìn.

Ownership và wire contract: ../contracts/phase3/IMPLEMENTATION.md. User đã yêu cầu thực hiện; không cần thêm blanketapproval. Source/codeđangtriểnkhai và QAđộc lập là cácgate riêng.
