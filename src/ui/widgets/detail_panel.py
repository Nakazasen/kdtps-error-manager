"""
Enhanced Detail Panel Widget for KDTPS Error Manager
Panel showing selected record details with editing and translation.
"""
import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QTextEdit, QPushButton,
    QCheckBox, QMessageBox, QMenu, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QTextCursor

logger = logging.getLogger(__name__)


class TranslationWorker(QThread):
    """Background worker for translation."""
    
    finished = pyqtSignal(str)  # translated text
    error = pyqtSignal(str)
    
    def __init__(self, text: str, target_lang: str):
        super().__init__()
        self.text = text
        self.target_lang = target_lang
    
    def run(self):
        try:
            from core.translator import translate_text
            result = translate_text(self.text, self.target_lang)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Translation failed")
        except Exception as e:
            self.error.emit(str(e))


class DetailPanelWidget(QWidget):
    """Enhanced detail panel for error record editing."""
    
    # Signals
    record_saved = pyqtSignal(dict)  # Emits saved record data
    email_requested = pyqtSignal(dict)  # Emits record for email
    sync_requested = pyqtSignal(dict)  # Emits record for Excel sync
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_record: Optional[Dict[str, Any]] = None
        self.handlers: list = []
        
        self.setup_ui()
        self.load_handlers()
    
    def setup_ui(self):
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header row
        header = QHBoxLayout()
        
        self.lbl_no = QLabel("No: ---")
        self.lbl_no.setStyleSheet("font-weight: bold; font-size: 16px; color: #42A5F5;")
        header.addWidget(self.lbl_no)
        
        self.lbl_machine = QLabel("| Máy: ---")
        self.lbl_machine.setStyleSheet("color: #B0BEC5;")
        header.addWidget(self.lbl_machine)
        
        self.lbl_line = QLabel("| Line: ---")
        self.lbl_line.setStyleSheet("color: #B0BEC5;")
        header.addWidget(self.lbl_line)
        
        header.addStretch()
        
        # Handler selection
        lbl_handler = QLabel("👤 Phụ trách:")
        lbl_handler.setStyleSheet("color: #E0E0E0;")
        header.addWidget(lbl_handler)
        self.cmb_handler = QComboBox()
        self.cmb_handler.setEditable(True)
        self.cmb_handler.setMinimumWidth(150)
        self.cmb_handler.setPlaceholderText("Chọn người...")
        header.addWidget(self.cmb_handler)
        
        # Status checkboxes
        self.chk_completed = QCheckBox("✅ Hoàn thành (V)")
        header.addWidget(self.chk_completed)
        
        self.chk_jp_support = QCheckBox("🇯🇵 Cần JP (Y)")
        header.addWidget(self.chk_jp_support)
        
        layout.addLayout(header)
        
        # Error info row
        info_row = QHBoxLayout()
        
        self.lbl_error_code = QLabel("Mã lỗi: ---")
        self.lbl_error_code.setStyleSheet("background: #FFF3E0; color: #E65100; padding: 4px 8px; border-radius: 4px; font-weight: bold;")
        info_row.addWidget(self.lbl_error_code)
        
        self.lbl_error_content = QLabel("")
        self.lbl_error_content.setStyleSheet("color: #B0BEC5; font-style: italic;")
        self.lbl_error_content.setWordWrap(True)
        info_row.addWidget(self.lbl_error_content, 1)
        
        layout.addLayout(info_row)
        
        # Investigation text area
        lbl_investigation = QLabel("📝 Nội dung điều tra (cột N):")
        lbl_investigation.setStyleSheet("font-weight: bold; color: #E0E0E0; margin-top: 5px;")
        layout.addWidget(lbl_investigation)
        
        self.txt_investigation = QTextEdit()
        self.txt_investigation.setPlaceholderText(
            "Nhập nội dung điều tra:\n\n"
            "• Nội dung điều tra của KTCT\n"
            "• Đối sách tạm thời\n"
            "• Đối sách lâu dài\n\n"
            "💡 Tip: Bôi chọn text → Chuột phải → Dịch JP↔VN"
        )
        self.txt_investigation.setMinimumHeight(120)
        self.txt_investigation.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.txt_investigation.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.txt_investigation)
        
        # Action buttons
        btn_row = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_save.setMinimumWidth(100)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)
        
        self.btn_translate_all = QPushButton("🔄 Dịch tự động")
        self.btn_translate_all.clicked.connect(self._on_translate_all)
        btn_row.addWidget(self.btn_translate_all)
        
        self.btn_reply = QPushButton("📧 Gửi mail KDTPS")
        self.btn_reply.setMinimumWidth(150)
        self.btn_reply.clicked.connect(self._on_send_email)
        btn_row.addWidget(self.btn_reply)
        
        self.btn_sync = QPushButton("📤 Sync Excel")
        self.btn_sync.clicked.connect(self._on_sync)
        btn_row.addWidget(self.btn_sync)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
    
    def load_handlers(self):
        """Load handler list from database."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            self.handlers = db.get_handlers()
            
            self.cmb_handler.clear()
            self.cmb_handler.addItem("", None)  # Empty option
            for handler in self.handlers:
                self.cmb_handler.addItem(handler["name"], handler["id"])
                
        except Exception as e:
            logger.error(f"Failed to load handlers: {e}")
    
    def set_record(self, record: Dict[str, Any]):
        """Display a record in the panel."""
        self.current_record = record
        
        if not record:
            self._clear()
            return
        
        # Update labels
        self.lbl_no.setText(f"No: {record.get('no_dvd', '---')}")
        self.lbl_machine.setText(f"| Máy: {record.get('col_c', '---')}")
        self.lbl_line.setText(f"| Line: {record.get('col_d', '---')}")
        
        # Error codes and content
        error_codes = []
        if record.get('col_g'):
            error_codes.append(str(record['col_g']))
        if record.get('col_h'):
            error_codes.append(str(record['col_h']))
        self.lbl_error_code.setText(f"Mã lỗi: {', '.join(error_codes) or '---'}")
        
        self.lbl_error_content.setText(str(record.get('col_j', ''))[:200])
        
        # Handler selection
        handler_id = record.get('handler_id')
        if handler_id:
            index = self.cmb_handler.findData(handler_id)
            if index >= 0:
                self.cmb_handler.setCurrentIndex(index)
        else:
            self.cmb_handler.setCurrentIndex(0)
        
        # Checkboxes
        self.chk_completed.setChecked(
            str(record.get('is_completed', '')).lower() == 'o'
        )
        self.chk_jp_support.setChecked(
            str(record.get('needs_jp_support', '')).lower() == 'o'
        )
        
        # Investigation text
        self.txt_investigation.setPlainText(str(record.get('col_n', '') or ''))
    
    def _clear(self):
        """Clear the panel."""
        self.lbl_no.setText("No: ---")
        self.lbl_machine.setText("| Máy: ---")
        self.lbl_line.setText("| Line: ---")
        self.lbl_error_code.setText("Mã lỗi: ---")
        self.lbl_error_content.setText("")
        self.cmb_handler.setCurrentIndex(0)
        self.chk_completed.setChecked(False)
        self.chk_jp_support.setChecked(False)
        self.txt_investigation.clear()
    
    def _show_context_menu(self, pos):
        """Show translation context menu."""
        menu = QMenu(self)
        
        cursor = self.txt_investigation.textCursor()
        has_selection = cursor.hasSelection()
        
        if has_selection:
            action_jp = menu.addAction("🇯🇵 Dịch → Tiếng Nhật")
            action_vn = menu.addAction("🇻🇳 Dịch → Tiếng Việt")
            menu.addSeparator()
            action_replace = menu.addAction("🔄 Dịch và thay thế")
        else:
            action_jp = menu.addAction("🇯🇵 Dịch toàn bộ → Tiếng Nhật")
            action_vn = menu.addAction("🇻🇳 Dịch toàn bộ → Tiếng Việt")
            action_replace = None
        
        action = menu.exec(self.txt_investigation.mapToGlobal(pos))
        
        if action == action_jp:
            self._translate_text('ja', replace=False)
        elif action == action_vn:
            self._translate_text('vi', replace=False)
        elif action_replace and action == action_replace:
            self._translate_text(None, replace=True)
    
    def _translate_text(self, target_lang: str = None, replace: bool = False):
        """Translate text using translation service."""
        cursor = self.txt_investigation.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else self.txt_investigation.toPlainText()
        
        if not text.strip():
            QMessageBox.information(self, "Dịch", "Không có text để dịch.")
            return
        
        # Auto-detect language if not specified
        if not target_lang:
            from core.translator import get_translator
            translator = get_translator()
            source = translator.detect_language(text)
            target_lang = 'vi' if source == 'ja' else 'ja'
        
        # Show waiting cursor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        self.worker = TranslationWorker(text, target_lang)
        self.worker.finished.connect(lambda result: self._on_translation_done(result, replace))
        self.worker.error.connect(self._on_translation_error)
        self.worker.start()
    
    def _on_translation_done(self, result: str, replace: bool):
        """Handle translation completion."""
        QApplication.restoreOverrideCursor()
        
        cursor = self.txt_investigation.textCursor()
        
        if replace and cursor.hasSelection():
            # Replace selected text
            cursor.insertText(result)
        else:
            # Show in message box for copy
            QMessageBox.information(
                self,
                "Kết quả dịch",
                f"📝 Bản dịch:\n\n{result}"
            )
    
    def _on_translation_error(self, error: str):
        """Handle translation error."""
        QApplication.restoreOverrideCursor()
        QMessageBox.warning(self, "Lỗi dịch", f"Không thể dịch: {error}")
    
    def _on_translate_all(self):
        """Translate the entire investigation text."""
        self._translate_text(None, replace=False)
    
    def _on_save(self):
        """Save the current record."""
        if not self.current_record:
            return
        
        # Check if handler changed for email prompt
        old_handler_id = self.current_record.get('handler_id')
        new_handler_id = self.cmb_handler.currentData()
        handler_changed = (new_handler_id != old_handler_id) and new_handler_id is not None
        
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            record_id = self.current_record.get('id')
            
            if not record_id:
                QMessageBox.warning(self, "Lỗi", "Không có record để lưu")
                return
            
            # Update fields
            db.update_error_field(record_id, 'col_n', self.txt_investigation.toPlainText())
            
            handler_id = self.cmb_handler.currentData()
            if handler_id:
                db.update_error_field(record_id, 'handler_id', handler_id)
            
            is_completed = 'o' if self.chk_completed.isChecked() else ''
            db.update_error_field(record_id, 'is_completed', is_completed)
            
            needs_jp = 'o' if self.chk_jp_support.isChecked() else ''
            db.update_error_field(record_id, 'needs_jp_support', needs_jp)
            
            # Update local record
            self.current_record['col_n'] = self.txt_investigation.toPlainText()
            self.current_record['handler_id'] = handler_id
            self.current_record['is_completed'] = is_completed
            self.current_record['needs_jp_support'] = needs_jp
            
            self.record_saved.emit(self.current_record)
            
            QMessageBox.information(self, "Thành công", "✅ Đã lưu thay đổi!")
            
            # Email Notification Prompt (Phase 8)
            if handler_changed:
                handler_name = self.cmb_handler.currentText()
                reply = QMessageBox.question(
                    self, "Thông báo",
                    f"Anh có muốn gửi mail thông báo cho **{handler_name}** không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self._send_notification_to_handler(new_handler_id)
                    
        except Exception as e:
            logger.error(f"Failed to save: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {e}")
    
    def _send_notification_to_handler(self, handler_id: int):
        """Send email notification to the selected handler."""
        try:
            from core.email_service import EmailService
            from core.database import get_database
            
            db = get_database()
            # Get handler email
            handler = next((h for h in self.handlers if h['id'] == handler_id), None)
            if not handler or not handler.get('email'):
                QMessageBox.warning(self, "Lỗi", "Người phụ trách này chưa có địa chỉ email!")
                return
            
            email_service = EmailService.get_instance()
            subject = f"【KDTPS】Thông báo lỗi mới - {self.current_record.get('no_dvd')}"
            body = email_service.format_error_notification(self.current_record)
            
            success = email_service.send_notification(handler['email'], subject, body)
            
            if success:
                db.log_email_sent(self.current_record['no_dvd'], handler['email'], "Sent")
                QMessageBox.information(self, "Email", f"✅ Đã gửi mail cho {handler['name']}")
            else:
                db.log_email_sent(self.current_record['no_dvd'], handler['email'], "Failed", "SMTP Error")
                QMessageBox.warning(self, "Lỗi", "Không thể gửi email. Vui lòng kiểm tra lại cấu hình SMTP.")
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            QMessageBox.critical(self, "Lỗi", f"Lỗi hệ thống khi gửi mail: {e}")

    def _on_send_email(self):
        """Request email sending."""
        if self.current_record:
            self.email_requested.emit(self.current_record)
    
    def _on_sync(self):
        """Request Excel sync."""
        if self.current_record:
            self.sync_requested.emit(self.current_record)
