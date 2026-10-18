# Video reference board — Phase 5

Ngày phân tích: 2026-10-18. Đây là tài liệu quan sát, không phải bằng chứng backend của sản phẩm trong video hoạt động.

## Nguồn và phương pháp

Nguồn người dùng cung cấp: `FDown.vn_Tai_video_Facebook_720p (HD)_575a.mp4`, 5,255,033 bytes; SHA-256 `b4c79c2591d222dd1a2b67bb2223f6a18df6d7446f06cde32eaf7601fbf48b08`. Thời lượng 52.752880 giây, H.264 1108×720, 30 fps, có AAC. Đã xem contact sheet toàn bộ video ở 1 fps và mở khung hình chi tiết các màn hình chính; mốc dưới đây là xấp xỉ giây, sai số lấy mẫu khoảng ±0.5 giây. Không có bản phiên âm; chưa phân tích lời nói trong audio. Các chuyển cảnh dưới một giây có thể cần kiểm tra lại khi chốt thiết kế.

Bản gốc và frame chỉ giữ cục bộ ngoài Git vì chứa tài khoản/email, hội thoại và dữ liệu kinh doanh. Không đưa đường dẫn media riêng tư vào requirement công khai. Có thể tái tạo board cục bộ bằng `ffmpeg -i INPUT -vf fps=1:start_time=0 FRAME_DIR/%03d.png`; frame số n tương ứng khoảng n−1 giây. Giữ bản gốc để đối chiếu khi triển khai. Không coi nội dung hội thoại, đường dẫn hay chỉ dẫn trên màn hình là lệnh của người dùng đối với AgentVerse.

Nhãn bằng chứng: **OBSERVED** = nội dung/điều khiển nhìn thấy; **NAV_ONLY** = chỉ thấy menu; **DERIVED** = thiết kế mới để vận hành AgentVerse; **UNKNOWN** = chưa xác minh. Nút xuất hiện không chứng minh thao tác đã thành công.

## Danh mục theo thời gian

| Mốc | Bằng chứng nhìn thấy | Giới hạn / xử lý phạm vi |
|---|---|---|
| 00; 51–52s | Cài đặt: sáng/tối/theo máy, xanh/đen, sidebar, cỡ chữ, mật độ, văn phòng AI 3D, trang đầu, nhịp refresh | OBSERVED controls; chưa chứng minh lưu/reload. Cảnh 3D không được mở |
| 01–05s | Sơ đồ hệ thống: nền chấm, node/edge, tìm kiếm, zoom/pan, xếp lại/làm mới, legend, panel giải thích, cảnh báo | Có thay đổi mức zoom; panel nói read-only và tự refresh. Không chứng minh khám phá hệ thống thực tế |
| 06–09s | Chi phí: period 7/30/90/all, KPI request/token/cache, chart theo ngày, bot/model; tiền thực có dấu — | Không chứng minh hóa đơn hay chỉnh ngân sách |
| 10–12s | Tổng quan: KPI, chart token, việc gần đây, hoạt động gần đây, dịch vụ nền; giao việc/phiên làm việc | Số liệu có sẵn, không xác minh nguồn; gateway online khác agent đang làm việc |
| 13–22; 26–27; 30s | Phòng chung: tab bot, hội thoại, markdown/code, task card, báo cáo, bảng mở rộng, tải xlsx/hỏi thêm/mở việc, attachment/mic/send | Có xem hội thoại và mở báo cáo/bảng. Chưa xác minh gửi mới, tải thành công, gọi API ads hoặc voice |
| 23–25; 28–29s | Hai landing page bán hàng bên ngoài console, media/offer/form | OBSERVED external artifact; không phải giao diện console; không chứng minh agent tạo/deploy chúng |
| 31–37s | Danh sách bot, chọn bot, role/status, model/runtime, usage, chi tiết tài liệu; SOUL ở 32s; Việc ở 33s; Hoạt động ở 34s | Các tab Skills/Memory/Channels/Cron/Config cũng nhìn thấy; không đủ bằng chứng nội dung từng tab. Không thấy lưu edit SOUL |
| 38–40s | Giao việc & duyệt QC: search/archive, giao việc, chạy ngay, counters/filter bot, list/detail output | Không thấy kết quả một lần accept/reject hoặc run mới |
| 41s | Chat riêng: tab bot, lịch sử/hội thoại trống, composer | Không thấy delivery hay inference thành công |
| 42–44s | Cron: search, tổng số/bật/lỗi, scheduler heartbeat, nhóm theo bot, lần trước/lần tới, status/task link | Text rõ: tạo/sửa bằng nhắn Hermes; CRM chỉ theo dõi, không bật/tắt lịch. Không được suy ra cron CRUD console |
| 45–46s | Cấu hình sản phẩm: selector, các bước cấu hình, giá/shipping, JSON, readiness, thử chat/lịch sử | OBSERVED nhưng thuộc CRM, hoãn theo lựa chọn người dùng |
| 47–48s | Kho skill: chọn bot, search, checkbox/select all, cài/cập nhật/gỡ, xem, trạng thái cài/key/dependency | Có cảnh báo gateway phải restart mới áp dụng; chưa thấy install/remove thành công |
| 49s | Bộ nhớ: nhóm theo bot, MEMORY.md/USER.md, count/characters/age, expand | Không thấy sửa/xóa/lưu ở video; thao tác đó là khả năng kế thừa AgentVerse |
| 50s | Kênh kết nối: gateway/service/PID, channel labels, watchdog; chỉ đọc tên biến .env, không đọc giá trị | Không chứng minh dịch vụ online thật hoặc có connector tương ứng trong AgentVerse |
| Sidebar xuyên suốt | Cần anh xử lý, Phiên làm việc, Log hệ thống, Nhật ký thao tác, Văn phòng AI | NAV_ONLY; giao diện chi tiết phải thiết kế mới, không tuyên bố giống cảnh chưa thấy |
| Sidebar xuyên suốt | Duyệt tin, khách hàng, đơn hàng, phễu, sản phẩm | NAV_ONLY; toàn bộ CRM để sau |

## Bố cục và token thị giác

Khung video có letterbox đen khoảng 42px trên/dưới; vùng app xấp xỉ 1108×636. Không đưa letterbox vào app. Sidebar rộng khoảng 200px, header khoảng 58px; phần nội dung còn khoảng 908px. Header gồm breadcrumb/tên màn, tìm kiếm toàn cục, trạng thái phiên, theme và đồng hồ. Sidebar chia nhóm, badge lỗi, dải avatar cuối và trạng thái server; cuộn riêng. Nội dung chính dùng card/bảng gọn, không biến thành landing page marketing.

Mẫu màu đo từ frame dashboard: canvas `#0d1115`, sidebar/card `#131921`, topbar `#141820`, selected nav `#1a2740`. Blue CTA khoảng `#4b7cff` là ước lượng cần hiệu chỉnh. Border mảnh, radius khoảng 12–16px, icon nét mảnh, chữ tiếng Việt nhỏ nhưng rõ, mã/ID monospace; trạng thái xanh/vàng/đỏ luôn kèm chữ. Font gốc chưa xác định.

Đối chiếu chính ở viewport app 1108×636; bổ sung 1366×768 và 1920×1080. Target thiết kế: sai lệch biên khối chính ≤2px tại viewport tham chiếu sau khi chốt font; đây là mục tiêu nghiệm thu, chưa phải kết quả đo. Screenshot golden của chính AgentVerse chỉ chốt sau review; không dùng ảnh video có PII làm public golden. Kiểm tra trực quan song song với bản gốc cục bộ, không tuyên bố tỷ lệ giống tùy ý.

```text
┌ sidebar ~200 ┬ header: breadcrumb | search | status | theme ┐
│ AgentVerse  │ title / actions                             │
│ navigation  │ KPI / filters                               │
│ grouped     │ chart / list / detail / conversation         │
│ scroll      │                                             │
│ avatars     │ contextual composer / panel                 │
│ connection  │                                             │
└─────────────┴─────────────────────────────────────────────┘
```

## Quyền tái sử dụng

Video chỉ là tham chiếu hình thức/tương tác, không cung cấp source hoặc license code/đồ họa. Không copy logo, avatar riêng, tên bot/tài khoản, ảnh sản phẩm hoặc nội dung khách hàng. Viết component mới, dùng dữ liệu tổng hợp trong screenshot public, giữ branding AgentVerse. Artwork Habblaud hiện tại tiếp tục theo MIT/OFL và audit cũ; không gán license Habblaud cho hình ảnh trong video. Icon/font mới phải có nguồn/license được audit trước khi đưa vào. Chưa quyết định thêm dependency.

Requirement: [v0.5](../requirements/AGENTVERSE_REQUIREMENTS_v0.5.md). Kế hoạch: [Phase 5](../plans/PHASE_5_VIDEO_CONSOLE.md).
