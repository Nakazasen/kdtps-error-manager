# Phase 06.1: UI Shell & Filtering

Status: ⬜ Pending

## Objective

Tạo khung giao diện cho Tab Thống kê mới cùng bộ lọc để người dùng chọn xem dữ liệu theo từng Line/Phòng ban.

## Requirements

- [ ] Thêm Tab mới "Thống kê & Báo cáo" vào `QTabWidget` chính.
- [ ] Thiết kế Header với:
  - ComboBox chọn Phòng ban (Tất cả / Cơ 1.1 / Cơ 1.2...).
  - Date range picker (Từ ngày - Đến ngày).
  - Nút "Cập nhật" và "Xuất báo cáo".

## Implementation Steps

1. [ ] Cập nhật `src/ui/main_window.py` để thêm tab mới.
2. [ ] Tạo file mới `src/ui/dashboard_widget.py` kế thừa `QWidget`.
3. [ ] Layout UI sử dụng `QVBoxLayout` cho tổng thể và `QHBoxLayout` cho thanh filter.

## Files to Create/Modify

- `src/ui/main_window.py` - Đăng ký widget mới.
- `src/ui/dashboard_widget.py` (New) - Core UI của Dashboard.

## Test Criteria

- [ ] Khi chuyển tab, giao diện Dashboard hiển thị đúng.
- [ ] Chọn filter phòng ban không làm đứng app.
