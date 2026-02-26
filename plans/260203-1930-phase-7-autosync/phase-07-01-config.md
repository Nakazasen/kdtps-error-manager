# Phase 07.1: Sync Configuration UI

Status: ⬜ Pending

## Objective

Cho phép người dùng bật/tắt tính năng tự động đồng bộ và chỉnh thời gian quét (ví dụ: mỗi 15 phút).

## Requirements

- [ ] Cập nhật `SettingsDialog` để thêm mục "Đồng bộ tự động".
- [ ] Các field:
  - Checkbox: [x] Bật tự động quét file server.
  - SpinBox: Khoảng thời gian quét (15 - 120 phút).
- [ ] Lưu cài đặt vào bảng `app_config` trong Database.

## Implementation Steps

1. [ ] Sửa `src/ui/settings_dialog.py` (nếu có) hoặc thêm vào Menu Settings.
2. [ ] Thêm các key `sync_enabled`, `sync_interval` vào logic load/save config.

## Test Criteria

- [ ] Thay đổi interval và lưu lại, giá trị phải được giữ nguyên khi mở lại app.
