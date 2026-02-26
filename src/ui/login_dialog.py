"""
Login Dialog for KDTPS Error Manager
Cửa sổ đăng nhập chọn tên từ danh sách whitelist.
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

class LoginDialog(QDialog):
    """Dialog for user to select their name from the whitelist."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_user = None
        self.setWindowTitle("Đăng nhập - KDTPS Error Manager")
        self.setFixedSize(350, 150)
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Welcome message
        lbl_welcome = QLabel("Vui lòng chọn tên của bạn để bắt đầu:")
        lbl_welcome.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_welcome)
        
        # User selection combobox
        self.cmb_user = QComboBox()
        self.cmb_user.setEditable(True)
        self.cmb_user.setPlaceholderText("Chọn hoặc nhập tên...")
        layout.addWidget(self.cmb_user)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Đăng nhập")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setDefault(True)
        
        self.btn_cancel = QPushButton("Thoát")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def load_users(self):
        """Load handler names from database."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            handlers = db.get_handlers(active_only=True)
            
            names = sorted([h['name'] for h in handlers])
            self.cmb_user.addItems(names)
            
            logger.info(f"Loaded {len(names)} users into LoginDialog")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách người dùng:\n{e}")

    def accept(self):
        """Override accept to capture selected user."""
        user = self.cmb_user.currentText().strip()
        if not user:
            QMessageBox.warning(self, "Đăng nhập", "Vui lòng chọn hoặc nhập tên của bạn.")
            return
            
        self.selected_user = user
        logger.info(f"User selected: {self.selected_user}")
        super().accept()

    def get_user(self) -> str:
        """Return the selected username."""
        return self.selected_user
