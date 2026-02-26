from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class GuideDialog(QDialog):
    """Cửa sổ hiển thị hướng dẫn sử dụng chuyên nghiệp (Phase 7 Fix)."""
    
    def __init__(self, guide_path, parent=None):
        super().__init__(parent)
        self.guide_path = guide_path
        self.setWindowTitle("📖 Hướng dẫn sử dụng KDTPS Manager")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_guide()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Trình duyệt văn bản nội bộ
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True) # Cho phép bấm link web nếu có
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: 'Segoe UI', Arial;
                font-size: 14px;
                padding: 20px;
                border: 1px solid #dcdde1;
            }
        """)
        layout.addWidget(self.browser)
        
        # Nút đóng
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Đã hiểu")
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("padding: 8px; background-color: #3498db; color: white; border-radius: 4px;")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def load_guide(self):
        try:
            from PyQt6.QtCore import QUrl
            import os
            
            # Set search path so images in Markdown work
            guide_dir = os.path.dirname(self.guide_path)
            self.browser.setSearchPaths([guide_dir])
            
            with open(self.guide_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # PyQt6 supports Markdown with images if search paths are set
            self.browser.setMarkdown(content)
        except Exception as e:
            logger.error(f"Failed to load guide content: {e}")
            self.browser.setText(f"❌ Không thể tải nội dung hướng dẫn.\nLỗi: {e}")
