# Phase 07.2: Network Scanner Engine

Status: ⬜ Pending

## Objective

Xây dựng "trái tim" của tính năng Auto-sync: Bộ quét định kỳ file server.

## Requirements

- [ ] Tạo `SyncManager` (Singleton) quản lý vòng lặp quét.
- [ ] Logic: Duyệt qua danh sách `network_path` của các phòng ban trong database.
- [ ] Nhận diện file mới nhất: Tìm file có `Last Modified` mới hơn thời điểm quét gần nhất.

## Implementation Steps

1. [ ] Tạo file mới `src/core/sync_manager.py`.
2. [ ] Sử dụng `QTimer` để kích hoạt việc quét.
3. [ ] Lưu "Last Sync Time" cho từng department để tránh import lặp lại dữ liệu cũ.

## Test Criteria

- [ ] App không bị treo khi timer kích hoạt việc quét (chạy trong thread riêng).
