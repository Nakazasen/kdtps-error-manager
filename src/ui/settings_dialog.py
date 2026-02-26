"""
Settings Dialog for KDTPS Error Manager
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QGroupBox, QFormLayout,
    QFileDialog, QListWidget, QComboBox, QMessageBox, QInputDialog,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressDialog,
    QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from utils.config import config
import json
import time

class TestModelWorker(QThread):
    progress = pyqtSignal(str, str) # model_id, status_text (e.g. "✅ OK (0.5s)")
    finished = pyqtSignal(str) # Report summary

    def __init__(self, models, api_key):
        super().__init__()
        self.models = models # List of dicts {id, timeout}
        self.api_key = api_key
        self.is_running = True

    def run(self):
        # GLOBAL SSL FIX FOR CORPORATE PROXY
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            # Patch both private and public methods to cover urllib and httpx/requests
            ssl._create_default_https_context = _create_unverified_https_context
            ssl.create_default_context = _create_unverified_https_context

        try:
            from google import genai
            total = len(self.models)
            success_count = 0
            
            for i, model in enumerate(self.models):
                if not self.is_running: break
                
                mid = model["model_id"]
                timeout = model.get("timeout", 10)
                
                # Signal: Testing...
                self.progress.emit(mid, "🔄 Testing...")
                
                try:
                    start_t = time.time()
                    # Simple client init - matching CLI script pattern that works
                    client = genai.Client(api_key=self.api_key)
                    prompt = "Translate to Vietnamese: Hello"
                    # Simple call
                    response = client.models.generate_content(
                        model=mid,
                        contents=prompt,
                    )
                    end_t = time.time()
                    duration = end_t - start_t
                    
                    if response.text:
                        self.progress.emit(mid, f"✅ OK ({duration:.1f}s)")
                        success_count += 1
                    else:
                        self.progress.emit(mid, "❌ No Data")
                        
                except Exception as e:
                    err_msg = str(e).lower()
                    err_display = str(e)
                    logger.error(f"Test failed for {mid}: {err_display}")
                    
                    # Check for common error patterns (case insensitive)
                    if "404" in err_msg or "not found" in err_msg:
                        self.progress.emit(mid, "❌ Model Not Found (404)")
                    elif "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "rate" in err_msg:
                        self.progress.emit(mid, "❌ Hết Quota (429)")
                    elif "401" in err_msg or "invalid" in err_msg or "api_key" in err_msg:
                        self.progress.emit(mid, "❌ Key không hợp lệ")
                    elif "timeout" in err_msg:
                        self.progress.emit(mid, "❌ Timeout")
                    elif "ssl" in err_msg or "handshake" in err_msg or "certificate" in err_msg:
                        self.progress.emit(mid, "❌ Lỗi SSL/Mạng")
                    elif "unexpected keyword argument" in err_msg:
                        # Fallback try without timeout if http_options failed
                        try:
                            # Retry without http_options
                            client = genai.Client(api_key=self.api_key)
                            response = client.models.generate_content(
                                model=mid, contents=prompt
                            )
                            if response.text:
                                self.progress.emit(mid, "⚠️ OK (No Timeout)")
                                success_count += 1
                                continue
                        except Exception as e2:
                             self.progress.emit(mid, f"❌ {str(e2)[:25]}...")
                    else:
                        # Show more meaningful short error
                        short_err = err_display[:40].replace('\n', ' ')
                        self.progress.emit(mid, f"❌ {short_err}...")
            
            self.finished.emit(f"Đã kiểm tra xong {total} mô hình.\nThành công: {success_count}/{total}")
            
        except ImportError:
            self.finished.emit("Lỗi: Chưa cài đặt thư viện google-genai")
        except Exception as e:
            self.finished.emit(f"Lỗi không xác định: {e}")

    def stop(self):
        self.is_running = False
from pathlib import Path

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Application settings dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt")
        self.resize(900, 700)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup UI components."""
        main_layout = QVBoxLayout(self)
        
        # Tabs
        self.tabs = QTabWidget()
        
        self.setup_general_tab()
        self.setup_departments_tab()
        self.setup_email_tab()
        self.setup_sync_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("Đóng")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        main_layout.addLayout(btn_layout)
        
    def setup_general_tab(self):
        """Setup General settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Paths
        group_paths = QGroupBox("Đường dẫn hệ thống")
        form_paths = QFormLayout(group_paths)
        
        # KDTPS Source
        path_layout = QHBoxLayout()
        self.txt_kdtps_source = QLineEdit()
        btn_browse = QPushButton("📂")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(lambda: self.browse_folder(self.txt_kdtps_source))
        
        path_layout.addWidget(self.txt_kdtps_source)
        path_layout.addWidget(btn_browse)
        
        form_paths.addRow("KDTPS Source Folder:", path_layout)
        layout.addWidget(group_paths)
        
        # Translation
        group_trans = QGroupBox("Dịch thuật")
        form_trans = QFormLayout(group_trans)
        
        self.cmb_trans_service = QComboBox()
        self.cmb_trans_service.addItems(["gemini", "google"])
        form_trans.addRow("Dịch vụ dịch:", self.cmb_trans_service)
        
        layout.addWidget(group_trans)
        
        # API Key Pool
        group_keys = QGroupBox("Danh sách API Key (Xoay tua tự động)")
        keys_layout = QVBoxLayout(group_keys)
        
        # Key List
        self.list_api_keys = QListWidget()
        keys_layout.addWidget(self.list_api_keys)
        
        # Add Key Controls
        add_key_layout = QHBoxLayout()
        self.txt_new_key = QLineEdit()
        self.txt_new_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_key.setPlaceholderText("Nhập API Key mới...")
        
        btn_add_key = QPushButton("➕ Thêm")
        btn_add_key.clicked.connect(self.add_api_key)
        
        btn_remove_key = QPushButton("➖ Xóa")
        btn_remove_key.clicked.connect(self.remove_api_key)
        
        add_key_layout.addWidget(self.txt_new_key)
        add_key_layout.addWidget(btn_add_key)
        add_key_layout.addWidget(btn_remove_key)
        
        keys_layout.addLayout(add_key_layout)
        
        # Note
        lbl_note = QLabel("ℹ️ Tip: Thêm nhiều Key để tự động chuyển Key khác khi hết giới hạn.")
        lbl_note.setStyleSheet("color: gray; font-style: italic;")
        keys_layout.addWidget(lbl_note)
        
        layout.addWidget(group_keys)
        
        # Model Priority (Waterfall)
        group_models = QGroupBox("Cấu hình Model (Thứ tự ưu tiên)")
        models_layout = QVBoxLayout(group_models)
        
        models_main_layout = QHBoxLayout()
        models_layout.addLayout(models_main_layout)
        
        # Model Tree
        self.tree_models = QTreeWidget()
        self.tree_models.setHeaderLabels(["Model ID", "Trạng thái", "Timeout (s)"])
        self.tree_models.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_models.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree_models.setMinimumHeight(150)
        models_main_layout.addWidget(self.tree_models)
        
        # Model Actions (Right Side)
        action_layout = QVBoxLayout()
        
        btn_up = QPushButton("⬆️ Lên")
        btn_up.clicked.connect(self.move_model_up)
        
        btn_down = QPushButton("⬇️ Xuống")
        btn_down.clicked.connect(self.move_model_down)
        
        btn_toggle = QPushButton("✅/❌ Bật/Tắt")
        btn_toggle.clicked.connect(self.toggle_model_active)
        
        btn_reset = QPushButton("⟲ Nạp gốc")
        btn_reset.setToolTip("Reset về danh sách mặc định")
        btn_reset.clicked.connect(self.reset_models_to_default)
        
        
        btn_test = QPushButton("🧪 Kiểm tra Toàn bộ")
        btn_test.setToolTip("Kiểm tra kết nối của TẤT CẢ model trong danh sách")
        btn_test.clicked.connect(self.run_batch_test)
        
        action_layout.addWidget(btn_up)
        action_layout.addWidget(btn_down)
        action_layout.addWidget(btn_toggle)
        action_layout.addWidget(btn_test)
        action_layout.addWidget(btn_reset)
        action_layout.addStretch()
        
        models_main_layout.addLayout(action_layout)
        
        # Add/Remove
        add_layout = QHBoxLayout()
        self.txt_new_model = QLineEdit()
        self.txt_new_model.setPlaceholderText("Model ID...")
        self.txt_new_timeout = QLineEdit()
        self.txt_new_timeout.setPlaceholderText("Timeout (s)...")
        self.txt_new_timeout.setFixedWidth(80)
        self.txt_new_timeout.setText("10")
        
        btn_add_model = QPushButton("➕ Thêm")
        btn_add_model.clicked.connect(self.add_model)
        
        btn_del_model = QPushButton("🗑️ Xóa")
        btn_del_model.clicked.connect(self.delete_model)
        
        add_layout.addWidget(self.txt_new_model)
        add_layout.addWidget(self.txt_new_timeout)
        add_layout.addWidget(btn_add_model)
        add_layout.addWidget(btn_del_model)
        
        models_layout.addLayout(add_layout)
        
        layout.addWidget(group_models)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "⚙️ Chung")
        
    def setup_departments_tab(self):
        """Setup Departments settings tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Dept List
        self.list_depts = QListWidget()
        self.list_depts.setMaximumWidth(150)
        self.list_depts.currentRowChanged.connect(self.on_dept_selected)
        layout.addWidget(self.list_depts)
        
        # Dept Details
        dept_group = QGroupBox("Cấu hình phòng ban")
        dept_layout = QFormLayout(dept_group)
        
        # Path
        path_layout = QHBoxLayout()
        self.txt_dept_path = QLineEdit()
        btn_browse = QPushButton("📂")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(lambda: self.browse_folder(self.txt_dept_path))
        
        path_layout.addWidget(self.txt_dept_path)
        path_layout.addWidget(btn_browse)
        
        dept_layout.addRow("Thư mục tổng hợp:", path_layout)
        
        self.dept_config_data = {} # Temporary storage for dept changes
        
        layout.addWidget(dept_group)
        self.tabs.addTab(tab, "🏢 Phòng ban")
        
    def setup_email_tab(self):
        """Setup Email settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # General Info
        form = QFormLayout()
        self.txt_email_subject = QLineEdit()
        form.addRow("Tiêu đề Email mặc định:", self.txt_email_subject)
        layout.addLayout(form)
        
        # Recipients
        group_recipients = QGroupBox("Danh sách người nhận (To)")
        rec_layout = QVBoxLayout(group_recipients)
        
        self.list_emails = QListWidget()
        rec_layout.addWidget(self.list_emails)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Thêm")
        btn_add.clicked.connect(self.add_email)
        btn_remove = QPushButton("➖ Xóa")
        btn_remove.clicked.connect(self.remove_email)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addStretch()
        
        rec_layout.addLayout(btn_layout)
        
        layout.addWidget(group_recipients)
        self.tabs.addTab(tab, "📧 Email")

    def setup_sync_tab(self):
        """Setup Sync settings tab (Phase 7.1)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Cấu hình Tự động Đồng bộ")
        form = QFormLayout(group)
        
        self.chk_sync_enabled = QCheckBox("Bật tự động quét file server (Network Path)")
        form.addRow(self.chk_sync_enabled)
        
        self.spin_sync_interval = QSpinBox()
        self.spin_sync_interval.setRange(5, 120)
        self.spin_sync_interval.setSuffix(" phút")
        form.addRow("Khoảng thời gian quét:", self.spin_sync_interval)
        
        layout.addWidget(group)
        
        lbl_info = QLabel(
            "ℹ️ Khi bật tính năng này, ứng dụng sẽ định kỳ kiểm tra các file Excel\n"
            "tổng hợp trên server và tự động nạp dữ liệu mới nếu có."
        )
        lbl_info.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(lbl_info)
        
        layout.addStretch()
        self.tabs.addTab(tab, "🔄 Đồng bộ")

        
    def load_settings(self):
        """Load settings from global config."""
        # General
        self.txt_kdtps_source.setText(config.kdtps_source_path)
        index = self.cmb_trans_service.findText(config.translation_service)
        if index >= 0:
            self.cmb_trans_service.setCurrentIndex(index)
            
        # AI Settings
        try:
            self.list_api_keys.clear()
            if config.ai_settings_path.exists():
                with open(config.ai_settings_path, 'r', encoding='utf-8') as f:
                    ai_config = json.load(f)
                    
                    # Load key pool if exists, otherwise load legacy single key
                    api_keys = ai_config.get("api_keys", [])
                    if not api_keys and ai_config.get("api_key"):
                        api_keys = [ai_config.get("api_key")]
                    
                    # Add all keys to the list widget
                    for key in api_keys:
                        self.add_key_to_list(key)
            
            # Load Models
            waterfall = ai_config.get("waterfall_strategy", [])
            # Defaults if empty
            if not waterfall:
                waterfall = [
                    {"model_id": "gemini-2.5-flash", "is_active": True, "timeout": 12},
                    {"model_id": "gemini-3-flash-preview", "is_active": True, "timeout": 60},
                    {"model_id": "gemini-robotics-er-1.5-preview", "is_active": True, "timeout": 28},
                    {"model_id": "gemma-3-27b-it", "is_active": True, "timeout": 17},
                    {"model_id": "gemma-3-12b-it", "is_active": True, "timeout": 18},
                    {"model_id": "gemma-3-4b-it", "is_active": True, "timeout": 14},
                    {"model_id": "gemma-3n-e2b-it", "is_active": True, "timeout": 9},
                    {"model_id": "gemini-2.5-flash-lite", "is_active": True, "timeout": 7},
                    {"model_id": "gemini-2.5-computer-use-preview-10-2025", "is_active": False, "timeout": 10},
                    {"model_id": "gemma-3-1b-it", "is_active": True, "timeout": 10}
                ]
            
            self.tree_models.clear()
            for m in waterfall:
                self.add_model_to_tree(m["model_id"], m.get("is_active", True), m.get("timeout", 10))
                
        except Exception as e:
            logger.error(f"Error loading AI settings: {e}")
            
        # Departments
        self.list_depts.clear()
        self.dept_config_data = {}
        for name, data in config.departments.items():
            self.list_depts.addItem(name)
            self.dept_config_data[name] = data.copy() # Deep copy if nested? data is dict with 'path', 'lines'
            
        if self.list_depts.count() > 0:
            self.list_depts.setCurrentRow(0)
            
        # Email
        self.txt_email_subject.setText(config.email_subject)
        self.list_emails.clear()
        for email in config.kdtps_email_to:
            self.list_emails.addItem(email)

        # Sync (Phase 7.1)
        self.chk_sync_enabled.setChecked(config.sync_enabled)
        self.spin_sync_interval.setValue(config.sync_interval)

    def on_dept_selected(self, row):
        """Handle department selection."""
        if row < 0: return
        
        # Save previous selection (if any) to temp dict? 
        # Actually better to update temp dict immediately on text change.
        
        current_item = self.list_depts.currentItem()
        if not current_item: return
        
        dept_name = current_item.text()
        data = self.dept_config_data.get(dept_name, {})
        self.txt_dept_path.setText(data.get("path", ""))
        
        # Disconnect old signals to prevent overwriting wrong dept
        try: self.txt_dept_path.textChanged.disconnect()
        except: pass
        
        self.txt_dept_path.textChanged.connect(lambda text: self.update_dept_path(dept_name, text))

    def update_dept_path(self, dept_name, text):
        if dept_name in self.dept_config_data:
            self.dept_config_data[dept_name]["path"] = text

    def browse_folder(self, line_edit):
        """Open folder browser."""
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder:
            line_edit.setText(folder)

    def add_email(self):
        email, ok = QInputDialog.getText(self, "Thêm Email", "Nhập địa chỉ email:")
        if ok and email:
            self.list_emails.addItem(email)
            
    def remove_email(self):
        row = self.list_emails.currentRow()
        if row >= 0:
            self.list_emails.takeItem(row)

    def add_api_key(self):
        """Add new API key to list."""
        key = self.txt_new_key.text().strip()
        if not key:
            return
            
        # Check duplicates
        for i in range(self.list_api_keys.count()):
            # To perform exact duplicate check we might need hidden user data, 
            # but for simple UI let's just add it.
            # Ideally store full key in item data and masked in text.
            pass

        self.add_key_to_list(key)
        self.txt_new_key.clear()
        
    def add_key_to_list(self, key):
        """Helper to add key item with mask."""
        masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        item = QListWidget() # Wait, need item class or text
        # QListWidgetItem
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(f"🔑 {masked}")
        item.setData(Qt.ItemDataRole.UserRole, key) # Store full key
        self.list_api_keys.addItem(item)

    def remove_api_key(self):
        """Remove selected key."""
        row = self.list_api_keys.currentRow()
        if row >= 0:
            self.list_api_keys.takeItem(row)

    # Model Management Methods
    def add_model_to_tree(self, model_id, is_active=True, timeout=10):
        item = QTreeWidgetItem([model_id, "✅ Active" if is_active else "❌ Inactive", str(timeout)])
        item.setData(1, Qt.ItemDataRole.UserRole, is_active)
        # Allow editing timeout
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if not is_active:
            item.setForeground(0, Qt.GlobalColor.gray)
            item.setForeground(1, Qt.GlobalColor.gray)
            item.setForeground(2, Qt.GlobalColor.gray)
        self.tree_models.addTopLevelItem(item)

    def add_model(self):
        mid = self.txt_new_model.text().strip()
        if not mid: return
        
        try:
            timeout = int(self.txt_new_timeout.text().strip())
        except:
            timeout = 10
            
        self.add_model_to_tree(mid, True, timeout)
        self.txt_new_model.clear()
        self.txt_new_timeout.setText("10")

    def delete_model(self):
        item = self.tree_models.currentItem()
        if not item: return
        index = self.tree_models.indexOfTopLevelItem(item)
        self.tree_models.takeTopLevelItem(index)

    def toggle_model_active(self):
        item = self.tree_models.currentItem()
        if not item: return
        current_active = item.data(1, Qt.ItemDataRole.UserRole)
        new_active = not current_active
        
        item.setText(1, "✅ Active" if new_active else "❌ Inactive")
        item.setData(1, Qt.ItemDataRole.UserRole, new_active)
        # Need config check for theme, but gray is safe
        if not new_active:
             item.setForeground(0, Qt.GlobalColor.gray)
             item.setForeground(1, Qt.GlobalColor.gray)
             item.setForeground(2, Qt.GlobalColor.gray)
        else:
             # Reset color (use default)
             item.setData(0, Qt.ItemDataRole.ForegroundRole, None)
             item.setData(1, Qt.ItemDataRole.ForegroundRole, None)
             item.setData(2, Qt.ItemDataRole.ForegroundRole, None)

    def move_model_up(self):
        item = self.tree_models.currentItem()
        if not item: return
        idx = self.tree_models.indexOfTopLevelItem(item)
        if idx > 0:
            self.tree_models.takeTopLevelItem(idx)
            self.tree_models.insertTopLevelItem(idx - 1, item)
            self.tree_models.setCurrentItem(item)

    def move_model_down(self):
        item = self.tree_models.currentItem()
        if not item: return
        idx = self.tree_models.indexOfTopLevelItem(item)
        if idx < self.tree_models.topLevelItemCount() - 1:
            self.tree_models.takeTopLevelItem(idx)
            self.tree_models.insertTopLevelItem(idx + 1, item)
            self.tree_models.setCurrentItem(item)

    def reset_models_to_default(self):
        """Reset models to hardcoded default list."""
        reply = QMessageBox.question(
            self, "Reset Models", 
            "Bạn có chắc muốn reset danh sách model về mặc định không?\nCác thay đổi hiện tại sẽ bị mất.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            waterfall = [
                {"model_id": "gemini-2.5-flash", "is_active": True, "timeout": 12},
                {"model_id": "gemini-3-flash-preview", "is_active": True, "timeout": 60},
                {"model_id": "gemini-robotics-er-1.5-preview", "is_active": True, "timeout": 28},
                {"model_id": "gemma-3-27b-it", "is_active": True, "timeout": 17},
                {"model_id": "gemma-3-12b-it", "is_active": True, "timeout": 18},
                {"model_id": "gemma-3-4b-it", "is_active": True, "timeout": 14},
                {"model_id": "gemma-3n-e2b-it", "is_active": True, "timeout": 9},
                {"model_id": "gemini-2.5-flash-lite", "is_active": True, "timeout": 7},
                {"model_id": "gemini-2.5-computer-use-preview-10-2025", "is_active": False, "timeout": 10},
                {"model_id": "gemma-3-1b-it", "is_active": True, "timeout": 10}
            ]
            self.tree_models.clear()
            for m in waterfall:
                self.add_model_to_tree(m["model_id"], m.get("is_active", True), m.get("timeout", 10))

    def run_batch_test(self):
        """Run batch test for all models."""
        # 1. Get Key
        keys = []
        for i in range(self.list_api_keys.count()):
            litem = self.list_api_keys.item(i)
            keys.append(litem.data(Qt.ItemDataRole.UserRole))
            
        if not keys:
            QMessageBox.warning(self, "Chưa có Key", "Vui lòng nhập API Key trước khi test.")
            return
        
        api_key = keys[0] # Try first key
        
        # 2. Get Models
        models = []
        for i in range(self.tree_models.topLevelItemCount()):
            item = self.tree_models.topLevelItem(i)
            mid = item.text(0)
            try:
                t_val = int(item.text(2))
            except:
                t_val = 10
            models.append({"model_id": mid, "timeout": t_val})
            
        if not models:
            QMessageBox.warning(self, "Chưa có Model", "Danh sách model trống.")
            return

        # 3. Setup Worker
        self.test_worker = TestModelWorker(models, api_key)
        self.test_worker.progress.connect(self.update_model_status)
        self.test_worker.finished.connect(self.on_test_finished)
        
        # 4. Show Progress Dialog (Modal)
        # Note: We don't block UI completely, but show a dialog that user can cancel
        self.progress_dialog = QProgressDialog("Đang kiểm tra các model...", "Hủy", 0, len(models), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.canceled.connect(self.test_worker.stop)
        self.progress_dialog.show()
        
        self.test_worker.start()

    def update_model_status(self, model_id, status_text):
        """Update tree item status text."""
        # Find item
        items = self.tree_models.findItems(model_id, Qt.MatchFlag.MatchExactly, 0)
        if items:
            item = items[0]
            item.setText(1, status_text)
            
            # Color coding
            if "OK" in status_text:
                item.setForeground(1, Qt.GlobalColor.green)
            elif "Error" in status_text or "❌" in status_text:
                item.setForeground(1, Qt.GlobalColor.red)
            elif "Testing" in status_text:
                item.setForeground(1, Qt.GlobalColor.blue)
                
        # Update progress dialog
        self.progress_dialog.setValue(self.progress_dialog.value() + 1)

    def on_test_finished(self, report):
        self.progress_dialog.close()
        QMessageBox.information(self, "Kết quả Kiểm tra", report)

    def save_settings(self):
        """Save settings to config file."""
        try:
            # Update global config object
            config.kdtps_source_path = self.txt_kdtps_source.text()
            config.translation_service = self.cmb_trans_service.currentText()
            
            # Update departments
            # Ensure current editing path is saved
            current_item = self.list_depts.currentItem()
            if current_item:
                dept_name = current_item.text()
                # TextChanged signal handles update to self.dept_config_data
            
            config.departments = self.dept_config_data
            
            # Update emails
            emails = []
            for i in range(self.list_emails.count()):
                emails.append(self.list_emails.item(i).text())
            config.kdtps_email_to = emails
            
            config.email_subject = self.txt_email_subject.text()
            # Sync (Phase 7.1)
            config.sync_enabled = self.chk_sync_enabled.isChecked()
            config.sync_interval = self.spin_sync_interval.value()
            
            # Save to disk
            config.save_to_file()
            
            # Refresh Auto-sync (Phase 7)
            try:
                from core.sync_manager import SyncManager
                SyncManager.get_instance().update_config()
            except Exception as e:
                logger.error(f"Failed to refresh SyncManager: {e}")
            
            # Save AI Settings
            try:
                ai_config = {}
                if config.ai_settings_path.exists():
                    with open(config.ai_settings_path, 'r', encoding='utf-8') as f:
                        ai_config = json.load(f)
                
                ai_config["translation_service"] = self.cmb_trans_service.currentText()
                
                # Save API Key Pool
                keys = []
                for i in range(self.list_api_keys.count()):
                    item = self.list_api_keys.item(i)
                    keys.append(item.data(Qt.ItemDataRole.UserRole))
                
                ai_config["api_keys"] = keys
                # Set legacy 'api_key' to first available key for backward compatibility
                ai_config["api_key"] = keys[0] if keys else ""
                
                # Save Models (Waterfall)
                models = []
                for i in range(self.tree_models.topLevelItemCount()):
                    item = self.tree_models.topLevelItem(i)
                    try:
                        t_val = int(item.text(2))
                    except:
                        t_val = 10
                    models.append({
                        "model_id": item.text(0),
                        "is_active": item.data(1, Qt.ItemDataRole.UserRole),
                        "timeout": t_val
                    })
                ai_config["waterfall_strategy"] = models
                
                with open(config.ai_settings_path, 'w', encoding='utf-8') as f:
                    json.dump(ai_config, f, indent=4, ensure_ascii=False)
                    
            except Exception as e:
                logger.error(f"Failed to save AI settings: {e}")
                QMessageBox.warning(self, "Lỗi", f"Không thể lưu setting AI: {e}")

            
            QMessageBox.information(self, "Thành công", "Đã lưu cài đặt!")
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cài đặt:\n{e}")
