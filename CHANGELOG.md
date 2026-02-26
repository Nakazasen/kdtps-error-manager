# Changelog

All notable changes to KDTPS Error Manager.

## [1.3.0] - 2026-02-04

### Added

- **User Access & Security**
  - New `LoginDialog` for user selection on startup.
  - Integration with `handlers` table for whitelisted user access.
- **System Monitoring (Sync Log Viewer)**
  - Dedicated "Nhật ký Sync" tab to track background synchronization history.
  - New `sync_logs` table in SQLite for persistent history tracking.
- **Collaboration (Email Notification System)**
  - Automatic email alerts for new records with assigned handlers.
  - Manual email trigger in Detail Panel with personalized prompts.
  - Sent email tracking in `email_logs` to prevent notification spam.
- **Reporting (Enterprise Dashboard)**
  - Premium Dashboard landing page with KPI cards and interactive charts.
  - Real-time statistics for record statuses, machine types, and departments.
  - Built-in charting engine using custom QPainter logic (no external dependencies).

### Fixed

- **System Stability**: Resolved module import errors in database factory functions.
- **Data Integrity**: Standardized timestamp handling using UTC for cross-timezone record detection.
- **Verification**: Improved automated verification scripts for email and notification logic.

### Fixed

- **UI Crash**: Sửa lỗi ứng dụng tự đóng do lệnh `addStretch` sai trên thanh công cụ.
- **Documentation**: Tích hợp trình xem hướng dẫn trực tiếp vào ứng dụng để tránh việc mở bằng các phần mềm lập trình (IDE).
- **Usability**: Viết lại toàn bộ hướng dẫn sử dụng bằng ngôn ngữ dễ hiểu, tập trung vào thao tác thực tế cho người dùng không chuyên kỹ thuật.

## [1.2.0] - 2026-02-03

### Added

- **Phase 6: Advanced Visualization (Dashboard Pro)**
  - Interactive Dashboard with Bar, Pie, and Line charts using Matplotlib.
  - Interactive filters by Department and Date Range.
  - Proactive Alert Banner triggered when pending errors > 10.
  - PNG Snapshot Export for quick report sharing.
- **Phase 7: Automation (Auto-sync Engine)**
  - Background Network Scanner for automatic Excel data import.
  - Change detection using file mtime to optimize network usage.
  - Real-time status bar notifications for new data discovery.
  - Automated UI refreshing when new data is synced.
  - New "Sync" tab in Settings for configuration.

### Improved

- **Database Performance**: Added `get_dashboard_stats` with optimized SQL for complex aggregations.
- **UI Responsiveness**: Integrated specialized background workers for all I/O bound tasks.

## [1.1.0] - 2026-02-03

### Added

- **Documentation & UI Integration**
  - Created Visual User Guide with Mermaid diagrams and Mind Maps (`docs/USER_GUIDE.md`).
  - Integrated User Guide into Main Window (Help menu F1 & Toolbar button).
  - Added logic to open local documentation using system default applications.
- **Code Hardening**
  - Refactored `ExcelHandler` to extract helper methods (`_find_worksheet`, `_parse_date_value`).
  - Added Integration Tests for Handler Sync flow (Excel -> DB).
  - Improved error handling for network path resolution.

### Fixed

- Fixed UI freeze during Excel synchronization by moving logic to background workers.
- Improved validation for record updates to prevent data loss.

## [1.0.0] - 2026-02-02

### Added

- **Phase 1: Core Setup**
  - SQLite database with departments, handlers, error_records tables
  - PyQt6 main window with sidebar, tabs, detail panel
  - Application configuration system

- **Phase 2: Excel Integration**
  - Read KDTPS files (supports password-protected via win32com)
  - Write to department summary files
  - Skip color detection (RGB 146,208,80)
  - Import dialog with preview and progress

- **Phase 3: Data Display & Translation**
  - Data grid with color-coded rows (green=completed, yellow=pending, red=needs JP)
  - Translation service (Gemini API + Google Translate fallback)
  - Detail panel with handler assignment and status checkboxes

- **Phase 4: Email & Reports**
  - Outlook email integration for KDTPS replies (Japanese template)
  - Statistics dashboard with summary cards
  - Machine type breakdown table
  - Excel export for reports
  - Backup manager for completed records
  - Search dialog for backup records

- **Phase 5: Testing & Packaging**
  - Unit tests for database (11 tests)
  - Unit tests for Excel handler (8 tests)
  - PyInstaller spec file for Windows EXE build
  - Build script (build.bat)

### Technical Notes

- KDTPS file format: Header at row 2, data from row 3
- Uses win32com for password-protected Excel files
- All async operations run in QThread to keep UI responsive
