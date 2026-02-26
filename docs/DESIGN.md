# 🎨 DESIGN: KDTPS Error Manager

> **Ngày tạo:** 2026-02-02  
> **Dựa trên:** [brain.json](file:///C:/ProgramData/Sandbox/kdtps-error-manager/.brain/brain.json)  
> **Tech Stack:** Python + PyQt6 + SQLite + openpyxl + win32com + Gemini API

---

## 1. 📊 Cách Lưu Thông Tin (Database Schema)

### 1.1. Giải thích đơn giản

> 💡 **Giống như Excel có nhiều Sheet**, database có nhiều "bảng" (table).
> Mỗi bảng lưu một loại thông tin khác nhau.

### 1.2. Sơ đồ quan hệ

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏢 DEPARTMENTS (Phòng ban)                                             │
│  ├── id (mã định danh)                                                  │
│  ├── name (Cơ 1.1, Cơ 1.2, Cơ 2.1, Cơ 2.2)                             │
│  ├── network_path (đường dẫn file tổng hợp)                             │
│  └── lines[] (danh sách Line sản xuất phòng phụ trách)                 │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │ 1 phòng có nhiều lỗi
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🐛 ERROR_RECORDS (Bản ghi lỗi) - BẢNG CHÍNH                            │
│  ├── id (mã định danh nội bộ)                                           │
│  ├── no_dvd (No điểm vấn đề - cột A)                                    │
│  ├── department_id → Phòng phụ trách                                    │
│  ├── sheet_type (Máy in / KIT)                                          │
│  ├── machine_type (cột C: 6th, Polaris, Brazil...)                      │
│  ├── line (cột D: Line sản xuất)                                        │
│  │                                                                       │
│  ├── ──── DỮ LIỆU TỪ KDTPS (cột A-P) ────                              │
│  ├── col_a ... col_p (lưu nguyên 16 cột)                                │
│  │                                                                       │
│  ├── ──── DỮ LIỆU ĐIỀU TRA ────                                        │
│  ├── investigation_content (cột N - nội dung điều tra)                  │
│  ├── handler_id → Người phụ trách (cột S)                               │
│  ├── is_completed (cột V: "o" = xong)                                   │
│  ├── needs_jp_support (cột Y: "o" = cần JP)                             │
│  │                                                                       │
│  ├── ──── METADATA ────                                                 │
│  ├── created_at (ngày import)                                           │
│  ├── updated_at (ngày cập nhật cuối)                                    │
│  ├── is_backed_up (đã chuyển sang Backup chưa)                          │
│  └── source_file (tên file KDTPS gốc)                                   │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  👤 HANDLERS (Người phụ trách)                                          │
│  ├── id (mã định danh)                                                  │
│  ├── name (Tên - từ cột G sheet DS KDTVN)                               │
│  ├── email (Email - để gửi thông báo)                                   │
│  └── is_active (còn làm việc không)                                     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ⚙️ APP_CONFIG (Cấu hình ứng dụng)                                      │
│  ├── id                                                                  │
│  ├── key (tên cấu hình)                                                 │
│  ├── value (giá trị)                                                    │
│  └── updated_at                                                          │
│                                                                          │
│  Ví dụ:                                                                  │
│  - last_kdtps_path: đường dẫn file KDTPS cuối                           │
│  - translation_service: "gemini" hoặc "google"                          │
│  - gemini_api_key: API key (mã hóa)                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3. SQLite Schema (Chi tiết kỹ thuật)

```sql
-- Bảng phòng ban
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- 'Cơ 1.1', 'Cơ 1.2', 'Cơ 2.1', 'Cơ 2.2'
    network_path TEXT NOT NULL,          -- Đường dẫn UNC
    lines TEXT,                           -- JSON array: ["Line1", "Line2"]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bảng người phụ trách
CREATE TABLE handlers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lỗi chính
CREATE TABLE error_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_dvd TEXT NOT NULL,                 -- Số điểm vấn đề (cột A)
    department_id INTEGER REFERENCES departments(id),
    sheet_type TEXT CHECK(sheet_type IN ('Máy in', 'KIT')),
    
    -- Dữ liệu gốc từ KDTPS (cột A-P)
    col_a TEXT, col_b TEXT, col_c TEXT, col_d TEXT,
    col_e TEXT, col_f TEXT, col_g TEXT, col_h TEXT,
    col_i TEXT, col_j TEXT, col_k TEXT, col_l TEXT,
    col_m TEXT, col_n TEXT, col_o TEXT, col_p TEXT,
    
    -- Dữ liệu mở rộng (cột Q-Y)
    col_q TEXT, col_r TEXT,
    handler_id INTEGER REFERENCES handlers(id),  -- Cột S
    col_t TEXT, col_u TEXT,
    is_completed TEXT DEFAULT '',         -- Cột V: 'o' hoặc ''
    col_w TEXT, col_x TEXT,
    needs_jp_support TEXT DEFAULT '',     -- Cột Y: 'o' hoặc ''
    
    -- Metadata
    source_file TEXT,
    is_backed_up INTEGER DEFAULT 0,
    skip_cells TEXT,                      -- JSON: cells có màu xanh lá (bỏ qua)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(no_dvd, sheet_type)
);

-- Bảng cấu hình
CREATE TABLE app_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index để tìm kiếm nhanh
CREATE INDEX idx_error_no ON error_records(no_dvd);
CREATE INDEX idx_error_completed ON error_records(is_completed);
CREATE INDEX idx_error_jp ON error_records(needs_jp_support);
CREATE INDEX idx_error_handler ON error_records(handler_id);
CREATE INDEX idx_error_machine ON error_records(col_c);  -- Loại máy
```

---

## 2. 📱 Danh Sách Màn Hình (UI Screens)

### 2.1. Tổng quan layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📊 KDTPS Error Manager                                    [─] [□] [×]   │
├──────────────────────────────────────────────────────────────────────────┤
│  [Menu Bar: File | Edit | View | Tools | Help]                           │
├──────────────────────────────────────────────────────────────────────────┤
│  [Toolbar: 📥Import | 📧Send | 📊Report | 🔍Search | ⚙️Settings]        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐  ┌────────────────────────────────────────────────────┐│
│  │ SIDEBAR     │  │  MAIN CONTENT AREA                                 ││
│  │             │  │                                                    ││
│  │ 🏢 Phòng    │  │  Tab: [Máy in] [KIT] [Báo cáo] [Tìm kiếm]         ││
│  │  ├ Cơ 1.1   │  │                                                    ││
│  │  ├ Cơ 1.2   │  │  ┌───┬────┬────┬─────┬──────┬──────────┬─────┐   ││
│  │  ├ Cơ 2.1   │  │  │No │Máy │Line│Error│Handler│Completed│JP   │   ││
│  │  └ Cơ 2.2   │  │  ├───┼────┼────┼─────┼──────┼──────────┼─────┤   ││
│  │             │  │  │001│6th │L1  │C123 │Vinh  │   ✓      │     │   ││
│  │ 📋 Filters  │  │  │002│Pol │L2  │J456 │Hùng  │          │  ✓  │   ││
│  │  ☑ Tồn đọng │  │  │...│... │... │...  │...   │   ...    │ ... │   ││
│  │  ☑ Cần JP   │  │  └───┴────┴────┴─────┴──────┴──────────┴─────┘   ││
│  │             │  │                                                    ││
│  │ 📊 Stats    │  │  [Selected: 3 items]                               ││
│  │  Mới: 5     │  │                                                    ││
│  │  Đọng: 12   │  │  ┌──────────────────────────────────────────────┐ ││
│  │  Xong: 45   │  │  │ 📝 DETAIL PANEL (khi chọn 1 dòng)            │ ││
│  │             │  │  │                                              │ ││
│  └─────────────┘  │  │ No: 001  |  Máy: 6th  |  Handler: Vinh ▼    │ ││
│                   │  │                                              │ ││
│                   │  │ Nội dung điều tra:                           │ ││
│                   │  │ ┌────────────────────────────────────────┐   │ ││
│                   │  │ │ (Editable text area)                   │   │ ││
│                   │  │ │                                        │   │ ││
│                   │  │ │ [Right-click: Dịch Nhật/Việt]          │   │ ││
│                   │  │ └────────────────────────────────────────┘   │ ││
│                   │  │                                              │ ││
│                   │  │ [💾 Lưu] [📧 Gửi mail KDTPS] [🔄 Sync Excel] │ ││
│                   │  └──────────────────────────────────────────────┘ ││
│                   └────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────────┤
│  Status: Ready | Last sync: 10:30 | DB: kdtps_co_1.1.db                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Chi tiết từng màn hình

| # | Tên màn hình | Mục đích | Components chính |
|---|--------------|----------|------------------|
| 1 | **Main Window** | Giao diện chính | Sidebar + Tabs + Grid + Detail |
| 2 | **Import Dialog** | Chọn file KDTPS & phòng đích | FileDialog + Combobox + Preview |
| 3 | **Handler Assignment** | Gán người phụ trách | Combobox có tìm kiếm |
| 4 | **Report Dashboard** | Thống kê lỗi | Charts + Filters |
| 5 | **Search Backup** | Tìm lịch sử lỗi | Search form + Result grid |
| 6 | **Settings Dialog** | Cấu hình AI, đường dẫn | Tabs: General, AI, Paths |
| 7 | **Email Preview** | Xem trước mail | Email template + Attachments |

---

## 3. 🚶 Luồng Hoạt Động (User Flows)

### 3.1. 👔 LEADER FLOW: Import & Assign

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 HÀNH TRÌNH: Leader import lỗi mới và phân công
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────┐     ┌──────────────┐     ┌─────────────┐
│ 1. Mở   │────▶│ 2. Bấm       │────▶│ 3. Chọn     │
│ App     │     │ "📥 Import"  │     │ File KDTPS  │
└─────────┘     └──────────────┘     └──────┬──────┘
                                            │
    ┌───────────────────────────────────────┘
    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ 4. Chọn    │────▶│ 5. Chọn     │────▶│ 6. Preview  │
│ Phòng đích │     │ Sheet       │     │ Dữ liệu     │
│ (Cơ 1.1)   │     │ (Máy in/KIT)│     │ sẽ import   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
    ┌───────────────────────────────────────────┘
    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ 7. Bấm     │────▶│ 8. Dữ liệu  │────▶│ 9. Gán      │
│ "Import"   │     │ hiện trên   │     │ Người PT ▼  │
│            │     │ Grid        │     │ (Combobox)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
    ┌───────────────────────────────────────────┘
    ▼
┌─────────────┐     ┌──────────────┐
│ 10. Bấm    │────▶│ 11. Outlook │
│ "Gửi thư"  │     │ tự mở mail   │
│            │     │ với nội dung │
└─────────────┘     └──────────────┘

💡 Quy tắc đặc biệt:
   - Ô có màu xanh lá (RGB: 146,208,80) → KHÔNG ghi đè
   - Cột D dùng để lọc theo Line sản xuất của phòng
```

### 3.2. 👷 NPT FLOW: Investigate & Reply

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 HÀNH TRÌNH: NPT điều tra lỗi và trả lời KDTPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────┐     ┌──────────────┐     ┌─────────────────┐
│ 1. Mở   │────▶│ 2. Thấy      │────▶│ 3. Click vào   │
│ App     │     │ danh sách    │     │ điểm vấn đề    │
│         │     │ lỗi mình PT  │     │ cần điều tra   │
└─────────┘     └──────────────┘     └────────┬────────┘
                                              │
    ┌─────────────────────────────────────────┘
    ▼
┌─────────────────┐     ┌──────────────────────────────────────┐
│ 4. Nhập nội    │────▶│ 5. Bôi chọn text cần dịch           │
│ dung điều tra  │     │    Right-click → "Dịch sang 🇯🇵/🇻🇳" │
│ (cột N)        │     │                                      │
└─────────────────┘     └──────────────────┬───────────────────┘
                                           │
    ┌──────────────────────────────────────┘
    ▼
┌─────────────────┐     ┌──────────────────────────────────────┐
│ 6. Đánh dấu    │────▶│ 7. Bấm "Gửi mail trả lời KDTPS"     │
│ hoàn thành (V) │     │    → Tự tạo file "Trả lời No...xlsx" │
│ hoặc cần JP (Y)│     │    → Mở Outlook với nội dung sẵn     │
└─────────────────┘     └──────────────────┬───────────────────┘
                                           │
    ┌──────────────────────────────────────┘
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. Kiểm tra nội dung mail → Bấm "Send" trong Outlook                │
│                                                                      │
│ To: thuy.ltt@dtvn.kyocera.com, ha.dtv@dtvn.kyocera.com              │
│ Subject: 【KDTPS】不具合状況連絡                                     │
│                                                                      │
│ Dear Ms. Hà, Ms. Thủy.                                              │
│ KTCT xin gửi câu trả lời điểm vấn đề KDTPS No... (JP + VN)          │
│ Nhờ mọi người cập nhật file KDTPS và close điểm vấn đề giúp.        │
│                                                                      │
│ [📎 Trả lời lỗi KDTPS No....xlsx]                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3. 📊 REPORT FLOW: View Statistics

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐
│ Bấm     │────▶│ Chọn loại   │────▶│ Xem biểu đồ │
│ "Báo cáo"│     │ máy/ngày    │     │ thống kê    │
└─────────┘     └──────────────┘     └─────────────┘

Hiển thị:
┌────────────────────────────────────────────────────┐
│  📊 THỐNG KÊ LỖI - Ngày 02/02/2026                │
├────────────────────────────────────────────────────┤
│                                                    │
│  Loại máy    │ Mới │ Đang │ Xong │ Tồn │ Cần JP │
│  ────────────┼─────┼──────┼──────┼─────┼────────│
│  6th         │  3  │  5   │  10  │  2  │   1    │
│  Polaris     │  2  │  3   │   8  │  1  │   0    │
│  Brazil      │  0  │  1   │   5  │  0  │   0    │
│  ────────────┼─────┼──────┼──────┼─────┼────────│
│  TỔNG        │  5  │  9   │  23  │  3  │   1    │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 4. ✅ Checklist Kiểm Tra (Acceptance Criteria)

### 4.1. F001: Import KDTPS Data

| # | Điều kiện | Trạng thái |
|---|-----------|------------|
| 1 | Bấm Import → Mở file dialog | ☐ |
| 2 | Chỉ hiện file .xlsx | ☐ |
| 3 | Có thể browse đến network path `\\fstvn01\...` | ☐ |
| 4 | Preview dữ liệu trước khi import | ☐ |
| 5 | Lọc theo cột D (Line) khớp với phòng | ☐ |
| 6 | Ô màu xanh (146,208,80) → KHÔNG ghi đè | ☐ |
| 7 | Copy cột A-P thành công | ☐ |
| 8 | Ghi log import | ☐ |

### 4.2. F003: Assign Handler

| # | Điều kiện | Trạng thái |
|---|-----------|------------|
| 1 | Combobox load tên từ DS KDTVN | ☐ |
| 2 | Gõ 1 ký tự → Tự filter tên | ☐ |
| 3 | Chọn handler → Lưu vào cột S | ☐ |
| 4 | Handler có email trong DB | ☐ |

### 4.3. F005: Translation

| # | Điều kiện | Trạng thái |
|---|-----------|------------|
| 1 | Bôi chọn text → Right-click | ☐ |
| 2 | Context menu: "Dịch sang 🇯🇵" / "Dịch sang 🇻🇳" | ☐ |
| 3 | Dịch bằng Gemini (nếu có API key) | ☐ |
| 4 | Fallback Google Translate (nếu Gemini fail) | ☐ |
| 5 | Hiện popup với bản dịch | ☐ |
| 6 | Có nút "Copy" để copy bản dịch | ☐ |

### 4.4. F006: Reply KDTPS

| # | Điều kiện | Trạng thái |
|---|-----------|------------|
| 1 | Chọn sheet (Máy in / KIT) + No điểm vấn đề | ☐ |
| 2 | Tự tạo file "Trả lời lỗi KDTPS No....xlsx" | ☐ |
| 3 | File chứa cột A-P của điểm vấn đề | ☐ |
| 4 | Mở Outlook với To, Subject, Body sẵn | ☐ |
| 5 | Đính kèm file đã tạo | ☐ |
| 6 | KHÔNG tự gửi, chờ user confirm | ☐ |

### 4.5. F008: Pending Investigation

| # | Điều kiện | Trạng thái |
|---|-----------|------------|
| 1 | Cột V = "" → Tồn đọng | ☐ |
| 2 | Cột V = "o" (hoa/thường) → Xong | ☐ |
| 3 | Cột V = ký tự khác → Yêu cầu sửa lại | ☐ |
| 4 | Filter chỉ hiện tồn đọng hoạt động | ☐ |

---

## 5. 🧪 Test Cases (Outline)

### TC-01: Import Happy Path

```
Given: User đã mở app, có file KDTPS hợp lệ trên network
When:  Bấm Import → Chọn file → Chọn phòng Cơ 1.1 → Sheet "Máy in" → Import
Then:  ✓ Dữ liệu hiển thị trên Grid
       ✓ Lọc đúng theo Line của Cơ 1.1
       ✓ SQLite có record mới
```

### TC-02: Skip Green Cells

```
Given: File đích có ô A5 bôi màu xanh (146,208,80)
When:  Import file mới có dữ liệu ở A5
Then:  ✓ Ô A5 KHÔNG bị ghi đè
       ✓ Các ô khác được cập nhật bình thường
```

### TC-03: Translation Context Menu

```
Given: User đang xem chi tiết 1 điểm vấn đề
When:  Bôi chọn text tiếng Nhật → Right-click → "Dịch sang 🇻🇳"
Then:  ✓ Popup hiện bản dịch tiếng Việt
       ✓ Có nút Copy
```

### TC-04: Validation cột V

```
Given: User nhập "x" vào cột V (thay vì "o" hoặc để trống)
When:  Bấm Lưu
Then:  ✓ Hiện thông báo lỗi yêu cầu sửa
       ✓ Không lưu dữ liệu
```

---

## 6. 📁 Cấu Trúc Thư Mục Code

```
kdtps-error-manager/
├── .brain/
│   └── brain.json
├── docs/
│   ├── ideas.md
│   └── DESIGN.md          ← BẠN ĐANG Ở ĐÂY
├── src/
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py     # SQLite operations
│   │   ├── excel_handler.py# openpyxl operations
│   │   ├── email_handler.py# win32com Outlook
│   │   └── translator.py   # Gemini/Google Translate
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py  # PyQt6 main window
│   │   ├── import_dialog.py
│   │   ├── report_dialog.py
│   │   ├── search_dialog.py
│   │   └── widgets/
│   │       ├── data_grid.py
│   │       ├── detail_panel.py
│   │       └── sidebar.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── logger.py
├── data/
│   ├── kdtps.db            # SQLite database
│   └── ai_settings.json    # Gemini config
├── tests/
│   ├── test_database.py
│   ├── test_excel.py
│   └── test_translator.py
├── requirements.txt
└── README.md
```

---

## 7. 📦 Dependencies

```txt
# requirements.txt
PyQt6>=6.5.0
openpyxl>=3.1.0
pywin32>=306
google-genai>=0.3.0
deep-translator>=1.11.0
```

---

*Tạo bởi AWF /design - 2026-02-02*
