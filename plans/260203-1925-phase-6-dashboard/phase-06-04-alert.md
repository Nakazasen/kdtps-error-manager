# Phase 06.4: Alert & Notification Logic

Status: ⬜ Pending

## Objective

Xây dựng cơ chế cảnh báo "Báo động đỏ" khi số lượng lỗi chưa xử lý vượt ngưỡng 10.

## Requirements

- [ ] Logic kiểm tra: `count(error_records WHERE is_completed != 'o')`.
- [ ] Hiển thị Visual Alert:
  - Nếu count > 10: Hiện banner đỏ lớn đầu Dashboard: "⚠️ BÁO ĐỘNG: CÒN {X} LỖI CHƯA XỬ LÝ!".
  - Update icon hoặc màu sắc của tab Thống kê để thu hút sự chú ý.

## Implementation Steps

1. [ ] Thêm method `get_pending_count()` vào `DatabaseManager`.
2. [ ] Tạo widget `AlertBanner` trong Dashboard.
3. [ ] Kết nối signal khi data thay đổi để update banner realtime.

## Test Criteria

- [ ] Khi có 11 lỗi pending, banner đỏ phải hiện lên.
- [ ] Khi xử lý lỗi xuống còn 9, banner tự động ẩn.
