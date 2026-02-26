"""
Configuration management for KDTPS Error Manager
"""
from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path
import os
import sys
import json


class Constants:
    """Các hằng số và magic strings được định nghĩa tập trung"""
    
    # Tên các sheet trong Excel
    SHEET_MAY_IN = "Máy in"
    SHEET_KIT = "KIT"
    SHEET_DS_KDTVN = "DS KDTVN"
    
    # Các giá trị trạng thái
    STATUS_COMPLETED = "o"
    STATUS_COMPLETED_UPPER = "O"
    STATUS_NEW = "New"
    
    # Các giá trị lọc
    FILTER_PENDING = "pending"
    FILTER_JP_SUPPORT = "jp_support"
    FILTER_ALL = "all"
    
    # Tên cột trong database mapping với Excel
    COL_NO_DVD = "no_dvd"
    COL_MACHINE_TYPE = "col_c"
    COL_LINE = "col_d"
    COL_ERROR_CODE_G = "col_g"
    COL_ERROR_CODE_H = "col_h"
    COL_INVESTIGATION = "col_n"
    COL_DEPARTMENT = "col_o"
    COL_HANDLER = "col_s"
    COL_COMPLETED = "is_completed"
    COL_JP_SUPPORT = "needs_jp_support"
    
    # Màu sắc skip cell (RGB)
    SKIP_COLOR_RGB = (146, 208, 80)
    
    # Các dịch vụ dịch thuật
    TRANSLATION_GEMINI = "gemini"
    TRANSLATION_GOOGLE = "google"
    
    # Ngôn ngữ
    LANG_JAPANESE = "ja"
    LANG_VIETNAMESE = "vi"
    
    # Patterns tìm kiếm file
    PATTERN_SUMMARY_FILE = "File tổng hợp*.xls*"
    PATTERN_XLSX = "*.xlsx"
    PATTERN_XLSM = "*.xlsm"
    
    # Email
    EMAIL_SUBJECT_DEFAULT = "【KDTPS】不具合状況連絡"


def get_app_data_dir() -> Path:
    """Lấy thư mục dữ liệu ứng dụng"""
    if getattr(sys, 'frozen', False):
        # Chạy như file .exe đã compile
        app_data = os.getenv('APPDATA', os.path.expanduser('~'))
        config_dir = Path(app_data) / 'KDTPSErrorManager'
    else:
        # Development mode - sử dụng thư mục data trong project
        config_dir = Path(__file__).parent.parent.parent / "data"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@dataclass
class AppConfig:
    """Cấu hình ứng dụng"""
    
    # Database
    db_name: str = "kdtps.db"
    
    # Đường dẫn network
    kdtps_source_path: str = r"\fstvn01\Data\00_KDTVN Common(KDTVN共通)\③Process QC(品質管理)\001. Báo cáo hàng ngày KDTPS"
    
    # Cấu hình phòng ban
    departments: Dict[str, Dict] = field(default_factory=lambda: {
        "Cơ 1.1": {
            "path": r"\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 1\Cơ 1.1",
            "lines": []  # Sẽ được populate từ Excel
        },
        "Cơ 1.2": {
            "path": r"\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 1\Cơ 1.2",
            "lines": []
        },
        "Cơ 2.1": {
            "path": r"\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 2\Cơ 2.1",
            "lines": []
        },
        "Cơ 2.2": {
            "path": r"\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 2\Cơ 2.2",
            "lines": []
        }
    })
    
    # Excel mapping
    source_columns: str = "A:P"  # Các cột cần copy từ KDTPS
    target_sheets: List[str] = field(default_factory=lambda: [Constants.SHEET_MAY_IN, Constants.SHEET_KIT])
    handler_sheet: str = Constants.SHEET_DS_KDTVN
    handler_start_row: int = 5
    handler_name_column: int = 6  # Col G (0-indexed) -> 6
    handler_email_column: int = 7  # Col H (0-indexed) -> 7
    
    # Các chỉ số cột (0-based)
    col_no_dvd: int = 0          # A - Số điểm vấn đề
    col_machine_type: int = 2    # C - Loại máy
    col_line: int = 3            # D - Line sản xuất
    col_error_code_g: int = 6    # G - Error code (Cxxx)
    col_error_code_h: int = 7    # H - Error code (Jxxx, Fxxx)
    col_investigation: int = 13  # N - Nội dung điều tra
    col_department: int = 14     # O - Bộ phận phụ trách (Department)
    col_handler: int = 18        # S - Người phụ trách
    col_completed: int = 21      # V - Hoàn thành (o = xong)
    col_jp_support: int = 24     # Y - Cần JP hỗ trợ
    
    # Màu skip cell (RGB)
    skip_color_rgb: tuple = Constants.SKIP_COLOR_RGB  # Xanh lá nhạt
    
    # Email settings
    kdtps_email_to: List[str] = field(default_factory=lambda: [
        "thuy.ltt@dtvn.kyocera.com",
        "ha.dtv@dtvn.kyocera.com"
    ])
    email_subject: str = Constants.EMAIL_SUBJECT_DEFAULT
    
    # Translation settings
    translation_service: str = Constants.TRANSLATION_GEMINI  # "gemini" hoặc "google"
    
    # Auto-sync settings (Phase 7)
    sync_enabled: bool = False
    sync_interval: int = 15  # Minutes
    
    @property
    def data_dir(self) -> Path:
        return get_app_data_dir()
    
    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name
    
    @property
    def ai_settings_path(self) -> Path:
        return self.data_dir / "ai_settings.json"
    
    def get_department_path(self, dept_name: str) -> str:
        """Lấy đường dẫn network cho phòng ban"""
        return self.departments.get(dept_name, {}).get("path", "")
    
    def save_to_file(self, path: Path = None):
        """Lưu cấu hình vào file JSON"""
        if path is None:
            path = self.data_dir / "config.json"
        
        # Chuyển đổi sang dict có thể serialize
        config_dict = {
            "db_name": self.db_name,
            "kdtps_source_path": self.kdtps_source_path,
            "departments": self.departments,
            "translation_service": self.translation_service,
            "kdtps_email_to": self.kdtps_email_to,
            "email_subject": self.email_subject,
            "sync_enabled": self.sync_enabled,
            "sync_interval": self.sync_interval
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, path: Path = None) -> 'AppConfig':
        """Tải cấu hình từ file JSON"""
        config = cls()
        if path is None:
            path = config.data_dir / "config.json"
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception as e:
                print(f"Cảnh báo: Không thể tải config: {e}")
        
        return config


# Instance cấu hình global
config = AppConfig()
