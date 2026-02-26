# Phase 07.4: Notification System

Status: ⬜ Pending

## Objective

Thông báo cho người dùng biết khi có dữ liệu mới vừa được "âm thầm" nạp vào.

## Requirements

- [ ] Sử dụng `QSystemTrayIcon` hoặc Banner nội bộ ứng dụng.
- [ ] Nội dung: "Phát hiện {N} lỗi mới từ phòng {Department}!".
- [ ] Click vào thông báo sẽ tự động chuyển sang Line tương ứng để xem.

## Implementation Steps

1. [ ] Cấu hình Signal từ `SyncManager` đến `MainWindow`.
2. [ ] Implement hàm hiển thị thông báo.

## Test Criteria

- [ ] Thông báo hiện đúng số lượng record mới vừa import.
