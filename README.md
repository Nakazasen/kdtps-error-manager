# KDTPS Error Manager

**Hệ thống quản lý lỗi KDTPS** - Tổng hợp thông tin lỗi từ nhiều nguồn (Excel), quản lý tiến độ điều tra, hỗ trợ dịch tự động (AI) và xuất báo cáo.

## 🚀 Tính năng nổi bật

- **Centralized Data**: Nhập liệu tại 1 nơi, tự động đồng bộ từ file Excel KDTPS.
- **Auto-sync**: Tự động quét và nạp dữ liệu từ server (Network Path) theo định kỳ.
- **Progress Tracking**: Quản lý trạng thái (Pending, Completed, Needs JP Support).
- **Dashboard Pro**: Biểu đồ trực quan (Matplotlib) về lỗi, tỉ lệ hoàn thành và xu hướng.
- **AI Translation**: Dịch tự động Nhật-Việt/Việt-Nhật sử dụng Gemini API 2.0 (với fallback Google Translate).
- **Report**: Xuất báo cáo Excel, Snapshot Dashboard và gửi email Outlook theo template.

## 🛠️ Yêu cầu cài đặt

- Python 3.11 trở lên
- Windows OS (cho các tính năng Outlook/Excel Automation)

## 📦 Cài đặt

1. Clone dự án:

    ```bash
    git clone https://github.com/vudovn/kdtps-error-manager.git
    cd kdtps-error-manager
    ```

2. Cài đặt thư viện:

    ```bash
    pip install -r requirements.txt
    ```

3. Cấu hình môi trường (`.env`):
    - Copy file `.env.example` thành `.env`:

      ```bash
      copy .env.example .env
      ```

    - Mở file `.env` và điền API Key (nếu dùng tính năng dịch AI):

      ```ini
      GEMINI_API_KEY=your_api_key_here
      ```

## 🖥️ Sử dụng

Chạy ứng dụng:

```bash
python src/main.py
```

### Các bước cơ bản

1. **Import**: Chọn `File -> Import KDTPS` để lấy dữ liệu từ file Excel.
2. **Quản lý**: click vào dòng lỗi để Chỉnh sửa, Dịch, hoặc Gửi mail.
3. **Báo cáo**: Chọn `Tools -> Báo cáo` để xem biểu đồ và xuất file tổng hợp.

## 📂 Cấu trúc dự án

```
kdtps-error-manager/
├── src/
│   ├── core/         # Xử lý Logic (Database, Excel, Translation)
│   ├── ui/           # Giao diện (PyQt6)
│   ├── utils/        # Tiện ích
│   └── main.py       # Entry point
├── data/             # Database SQLite (tự động tạo)
├── docs/             # Tài liệu & Báo cáo Audit
└── tests/            # Unit tests
```

## 🛡️ License

Internal Use Only (PE Dept).
