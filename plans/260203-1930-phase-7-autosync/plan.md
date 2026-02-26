# Plan: Phase 7 - Auto-sync từ Network Path 🤖

Created: 2026-02-03T19:30:00+07:00
Status: 🟡 In Progress

## Overview

Tự động hóa việc cập nhật dữ liệu từ các file Excel trên server (Network Path). Ứng dụng sẽ tự động quét và import lỗi mới mà không cần người dùng thao tác thủ công.

## Tech Stack

- Logic: `QTimer` (cho quét định kỳ) hoặc `QFileSystemWatcher`
- Background: `QThread` (để không làm treo UI khi đọc file server chậm)
- Storage: `app_config` table (lưu cài đặt sync)

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 07.1 | Sync Configuration UI | ⬜ Pending | 0% |
| 07.2 | Network Scanner Engine | ⬜ Pending | 0% |
| 07.3 | Auto-Import Logic | ⬜ Pending | 0% |
| 07.4 | Notification System | ⬜ Pending | 0% |
| 07.5 | Error Resilience | ⬜ Pending | 0% |

## Quick Commands

- Start: `/code phase-07-01`
- Next: `/next`
- Save: `/save-brain`
