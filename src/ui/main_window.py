"""
KDTPS Error Manager - Main Window (PyQt6)
Cửa sổ chính của ứng dụng quản lý lỗi KDTPS
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Any, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QToolBar, QStatusBar, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableView, QTextEdit,
    QLabel, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog, QMenu
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QAction, QIcon, QDesktopServices

logger = logging.getLogger(__name__)


class SidebarWidget(QWidget):
    """Left sidebar with department tree and filters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Department tree
        dept_group = QGroupBox("🏢 Phòng ban")
        dept_layout = QVBoxLayout(dept_group)
        
        self.dept_tree = QTreeWidget()
        self.dept_tree.setHeaderHidden(True)
        self.dept_tree.setMaximumHeight(150)
        
        # Add department items
        for dept in ["Cơ 1.1", "Cơ 1.2", "Cơ 2.1", "Cơ 2.2"]:
            item = QTreeWidgetItem([dept])
            self.dept_tree.addTopLevelItem(item)
        
        dept_layout.addWidget(self.dept_tree)
        layout.addWidget(dept_group)
        
        # Filters
        filter_group = QGroupBox("📋 Bộ lọc")
        filter_layout = QVBoxLayout(filter_group)
        
        self.chk_pending = QPushButton("☐ Chỉ tồn đọng")
        self.chk_pending.setCheckable(True)
        self.chk_jp = QPushButton("☐ Cần JP hỗ trợ")
        self.chk_jp.setCheckable(True)
        
        filter_layout.addWidget(self.chk_pending)
        filter_layout.addWidget(self.chk_jp)
        layout.addWidget(filter_group)
        
        # Statistics
        stats_group = QGroupBox("📊 Thống kê")
        stats_layout = QFormLayout(stats_group)
        
        self.lbl_new = QLabel("0")
        self.lbl_pending = QLabel("0")
        self.lbl_completed = QLabel("0")
        self.lbl_jp = QLabel("0")
        
        stats_layout.addRow("Mới:", self.lbl_new)
        stats_layout.addRow("Tồn đọng:", self.lbl_pending)
        stats_layout.addRow("Hoàn thành:", self.lbl_completed)
        stats_layout.addRow("Cần JP:", self.lbl_jp)
        
        layout.addWidget(stats_group)
        layout.addStretch()
    
    def update_stats(self, stats: dict):
        """Update statistics display."""
        self.lbl_new.setText(str(stats.get('total', 0)))
        self.lbl_pending.setText(str(stats.get('total_pending', 0)))
        self.lbl_completed.setText(str(stats.get('total_completed', 0)))
        self.lbl_jp.setText(str(stats.get('total_needs_jp', 0)))


class DetailPanel(QWidget):
    """Bottom panel showing selected record details."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with basic info
        header_layout = QHBoxLayout()
        
        self.lbl_no = QLabel("No: ---")
        self.lbl_no.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.lbl_no)
        
        self.lbl_machine = QLabel("Máy: ---")
        header_layout.addWidget(self.lbl_machine)
        
        header_layout.addWidget(QLabel("Phụ trách:"))
        self.cmb_handler = QComboBox()
        self.cmb_handler.setEditable(True)
        self.cmb_handler.setMinimumWidth(150)
        self.cmb_handler.setPlaceholderText("Chọn người...")
        header_layout.addWidget(self.cmb_handler)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Investigation content
        layout.addWidget(QLabel("📝 Nội dung điều tra (cột N):"))
        
        self.txt_investigation = QTextEdit()
        self.txt_investigation.setPlaceholderText(
            "Nhập nội dung điều tra:\n"
            "• Nội dung điều tra của KTCT\n"
            "• Đối sách tạm thời\n"
            "• Đối sách lâu dài\n\n"
            "💡 Bôi chọn text → Chuột phải → Dịch"
        )
        self.txt_investigation.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.txt_investigation.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.txt_investigation)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_save.setMinimumWidth(100)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_reply = QPushButton("📧 Gửi mail trả lời KDTPS")
        self.btn_reply.setMinimumWidth(180)
        btn_layout.addWidget(self.btn_reply)
        
        self.btn_sync = QPushButton("🔄 Sync Excel")
        btn_layout.addWidget(self.btn_sync)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def show_context_menu(self, pos):
        """Show translation context menu."""
        menu = QMenu(self)
        
        action_jp = menu.addAction("🇯🇵 Dịch sang tiếng Nhật")
        action_vn = menu.addAction("🇻🇳 Dịch sang tiếng Việt")
        
        action = menu.exec(self.txt_investigation.mapToGlobal(pos))
        
        if action == action_jp:
            self.translate_selected("ja")
        elif action == action_vn:
            self.translate_selected("vi")
    
    def translate_selected(self, target_lang: str):
        """Translate selected text."""
        cursor = self.txt_investigation.textCursor()
        selected_text = cursor.selectedText()
        
        if not selected_text:
            QMessageBox.information(self, "Dịch", "Vui lòng bôi chọn đoạn text cần dịch.")
            return
        
        # TODO: Implement translation
        QMessageBox.information(
            self, "Dịch", 
            f"Đang dịch sang {'tiếng Nhật' if target_lang == 'ja' else 'tiếng Việt'}:\n\n{selected_text[:100]}..."
        )


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, current_user: str = "Unknown"):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("📊 KDTPS Error Manager")
        self.setMinimumSize(1200, 800)
        
        self.current_dept_id = None
        
        # Initialize Auto-sync (Phase 7) - Must be before setup_ui
        from core.sync_manager import SyncManager
        self.sync_manager = SyncManager.get_instance()
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        
        self.load_data()
        self.sync_manager.data_synced.connect(self.on_data_synced)
    
    def setup_ui(self):
        """Setup main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Main splitter (sidebar | content)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.setMaximumWidth(250)
        # Connect selection
        self.sidebar.dept_tree.itemSelectionChanged.connect(self.on_dept_selected)
        # Connect filters
        self.sidebar.chk_pending.toggled.connect(self.on_filter_changed)
        self.sidebar.chk_jp.toggled.connect(self.on_filter_changed)
        main_splitter.addWidget(self.sidebar)
        
        # Right side (tabs + detail)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Máy in tab - Use DataGridView
        from ui.widgets.data_grid import DataGridView
        self.table_mayin = DataGridView()
        self.table_mayin.record_selected.connect(self.on_record_selected)
        self.table_mayin.record_changed.connect(self.on_record_changed)
        self.tabs.addTab(self.table_mayin, "🖨️ Máy in")
        
        # KIT tab - Use DataGridView
        self.table_kit = DataGridView()
        self.table_kit.record_selected.connect(self.on_record_selected)
        self.table_kit.record_changed.connect(self.on_record_changed)
        self.tabs.addTab(self.table_kit, "📦 KIT")
        
        # Report tab - Use ReportWidget
        from ui.report_widget import ReportWidget
        self.report_widget = ReportWidget()
        self.tabs.addTab(self.report_widget, "📊 Báo cáo")

        # Dashboard tab - NEW (Leadership requirement)
        from ui.widgets.dashboard_widget import DashboardWidget
        self.dashboard_widget = DashboardWidget()
        self.sync_manager.data_synced.connect(self.dashboard_widget.on_sync_data_received)
        self.tabs.insertTab(0, self.dashboard_widget, "📊 Dashboard")
        self.tabs.setCurrentIndex(0)
        
        # Search tab - Use embedded search
        from ui.search_dialog import SearchDialog
        self.search_widget = SearchDialog()
        self.search_widget.record_selected.connect(self.on_record_selected)
        # Remove window frame for embedded mode
        self.search_widget.setWindowFlags(Qt.WindowType.Widget)
        self.tabs.addTab(self.search_widget, "🔍 Tìm kiếm")
        
        # Sync Log tab - NEW (Enterprise requirement)
        from ui.widgets.sync_log_widget import SyncLogWidget
        self.sync_log_widget = SyncLogWidget()
        self.sync_manager.data_synced.connect(self.sync_log_widget.on_sync_data_received)
        self.tabs.addTab(self.sync_log_widget, "🕒 Nhật ký Sync")
        
        right_splitter.addWidget(self.tabs)
        
        # Detail panel - Use enhanced DetailPanelWidget
        from ui.widgets.detail_panel import DetailPanelWidget
        self.detail_panel = DetailPanelWidget()
        self.detail_panel.setMaximumHeight(350)
        self.detail_panel.record_saved.connect(self.on_record_saved)
        # Connect Sync Signal
        self.detail_panel.sync_requested.connect(self.on_sync_excel)
        right_splitter.addWidget(self.detail_panel)
        
        right_splitter.setSizes([500, 250])
        main_splitter.addWidget(right_splitter)
        
        main_splitter.setSizes([200, 900])
        main_layout.addWidget(main_splitter)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        action_import = QAction("📥 Import KDTPS...", self)
        action_import.setShortcut("Ctrl+I")
        action_import.triggered.connect(self.on_import)
        file_menu.addAction(action_import)
        
        file_menu.addSeparator()
        
        action_exit = QAction("❌ Thoát", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        action_pending = QAction("⏳ Lỗi đang điều tra", self)
        action_pending.triggered.connect(self.on_show_pending)
        view_menu.addAction(action_pending)
        
        action_jp = QAction("🇯🇵 Cần JP hỗ trợ", self)
        action_jp.triggered.connect(self.on_show_jp_support)
        view_menu.addAction(action_jp)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        action_report = QAction("📊 Báo cáo", self)
        action_report.triggered.connect(self.on_report)
        tools_menu.addAction(action_report)
        
        action_backup = QAction("📦 Backup hoàn thành", self)
        action_backup.triggered.connect(self.on_backup)
        tools_menu.addAction(action_backup)
        
        action_export = QAction("📄 Xuất file báo cáo lỗi", self)
        action_export.triggered.connect(self.on_export_report)
        tools_menu.addAction(action_export)
        
        tools_menu.addSeparator()
        
        action_settings = QAction("⚙️ Cài đặt...", self)
        action_settings.triggered.connect(self.on_settings)
        tools_menu.addAction(action_settings)
        action_sync_handlers = QAction("👥 Đồng bộ người phụ trách", self)
        action_sync_handlers.triggered.connect(self.on_sync_handlers)
        tools_menu.addAction(action_sync_handlers)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        action_guide = QAction("📖 Hướng dẫn sử dụng", self)
        action_guide.setShortcut("F1")
        action_guide.triggered.connect(self.on_user_guide)
        help_menu.addAction(action_guide)
        
        action_about = QAction("ℹ️ About", self)
        action_about.triggered.connect(self.on_about)
        help_menu.addAction(action_about)
    
    def setup_toolbar(self):
        """Setup main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        btn_import = QPushButton("📥 Import")
        btn_import.clicked.connect(self.on_import)
        toolbar.addWidget(btn_import)
        
        btn_send = QPushButton("📧 Gửi thư")
        btn_send.clicked.connect(self.on_send_mail)
        toolbar.addWidget(btn_send)
        
        toolbar.addSeparator()
        
        btn_report = QPushButton("📊 Báo cáo")
        btn_report.clicked.connect(self.on_report)
        toolbar.addWidget(btn_report)
        
        btn_pending = QPushButton("⏳ Đang điều tra")
        btn_pending.clicked.connect(self.on_show_pending)
        toolbar.addWidget(btn_pending)
        
        btn_jp = QPushButton("🇯🇵 Cần JP")
        btn_jp.clicked.connect(self.on_show_jp_support)
        toolbar.addWidget(btn_jp)
        
        toolbar.addSeparator()
        
        btn_backup = QPushButton("📦 Backup")
        btn_backup.clicked.connect(self.on_backup)
        toolbar.addWidget(btn_backup)
        
        btn_search = QPushButton("🔍 Search")
        btn_search.clicked.connect(self.on_search)
        toolbar.addWidget(btn_search)
        
        from PyQt6.QtWidgets import QWidget, QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        btn_guide = QPushButton("📖 Hướng dẫn")
        btn_guide.clicked.connect(self.on_user_guide)
        toolbar.addWidget(btn_guide)
    
    def setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
        # User status label
        self.lbl_user_status = QLabel(f"👤 User: {self.current_user}")
        self.lbl_user_status.setStyleSheet("font-weight: bold; margin-right: 10px;")
        self.statusbar.addPermanentWidget(self.lbl_user_status)
        
        # DB status label
        self.lbl_db_status = QLabel("DB: Not connected")
        self.statusbar.addPermanentWidget(self.lbl_db_status)
    
    def load_data(self, department_id: int = None):
        """Load data from database."""
        try:
            from core.database import get_database
            from utils.config import config
            
            # Update current Dept ID if provided (or keep existing if None)
            if department_id is not None:
                self.current_dept_id = department_id
            
            # If called without ID (e.g. initial load), use stored ID
            target_dept_id = self.current_dept_id
            
            pending_only = self.sidebar.chk_pending.isChecked()
            jp_support_only = self.sidebar.chk_jp.isChecked()
            
            db = get_database(config.db_path)
            stats = db.get_statistics(department_id=target_dept_id)
            self.sidebar.update_stats(stats)
            
            # Load data into grids
            logger.debug(f"Loading grid data. Dept: {target_dept_id}, Pending: {pending_only}, JP: {jp_support_only}")
            self.table_mayin.load_data(
                sheet_type="Máy in", 
                department_id=target_dept_id,
                pending_only=pending_only,
                jp_support_only=jp_support_only
            )
            self.table_kit.load_data(
                sheet_type="KIT", 
                department_id=target_dept_id,
                pending_only=pending_only,
                jp_support_only=jp_support_only
            )
            
            # Update Dashboard (Phase 6)
            depts = db.get_departments()
            self.dashboard_widget.set_departments(depts)
            
            # Get advanced stats for Dashboard Pro
            dash_dept_id = self.dashboard_widget.cmb_dept.currentData()
            date_from = self.dashboard_widget.date_from.date().toPyDate().isoformat()
            date_to = self.dashboard_widget.date_to.date().toPyDate().isoformat()
            
            dash_stats = db.get_dashboard_stats(
                department_id=dash_dept_id,
                date_from=date_from,
                date_to=date_to
            )
            self.dashboard_widget.update_dashboard(dash_stats)
            
            self.lbl_db_status.setText(f"DB: {config.db_path.name}")
            self.statusbar.showMessage("Data loaded successfully")
            logger.info("Data loaded from database")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            self.statusbar.showMessage(f"Error: {e}")
    
    def on_record_selected(self, record: dict):
        """Handle record selection from data grid."""
        self.detail_panel.set_record(record)
        self.statusbar.showMessage(f"Selected: No. {record.get('no_dvd', '')}")
    
    def on_filter_changed(self):
        """Handle filter checkbox toggled."""
        self.load_data()
    
    def on_dept_selected(self):
        """Handle department selection from sidebar."""
        items = self.sidebar.dept_tree.selectedItems()
        target_id = None
        
        if items:
            dept_name = items[0].text(0)
            try:
                from core.database import get_database
                from utils.config import config
                db = get_database(config.db_path)
                dept = db.get_department_by_name(dept_name)
                if dept:
                    target_id = dept['id']
                    self.statusbar.showMessage(f"Đang lọc theo phòng: {dept_name}")
            except Exception as e:
                logger.error(f"Error getting department: {e}")
        else:
             self.statusbar.showMessage("Đang hiển thị tất cả phòng ban")
        
        # Reload with new filter
        self.load_data(department_id=target_id)
    
    def on_sync_excel(self, record: dict):
        """Handle Sync Excel request from DetailPanel."""
        try:
            from core.excel_handler import get_excel_handler
            from core.database import get_database
            from utils.config import config
            
            # 1. Get Department File Path
            dept_id = record.get('department_id')
            if not dept_id:
                QMessageBox.warning(self, "Lỗi Sync", "Record này không thuộc phòng ban nào (thiếu Department ID).")
                return

            db = get_database(config.db_path)
            
            # Get department path by ID
            path = None
            with db.get_connection() as conn:
                row = conn.execute("SELECT network_path FROM departments WHERE id = ?", (dept_id,)).fetchone()
                if row:
                    path = row[0]
            
            if not path or not Path(path).exists():
                QMessageBox.warning(self, "Lỗi Sync", f"Không tìm thấy file Excel của phòng ban.\nPath: {path}")
                return

            # 2. Prepare Updates
            no_dvd = record.get('no_dvd')
            sheet_name = record.get('sheet_type')
            
            updates = {}
            # Update Investigation (Col N)
            updates['N'] = record.get('col_n', '')
            
            # Update Handler (Col O) -> Need Handler Name
            handler_id = record.get('handler_id')
            if handler_id:
                # Get handler name from handlers list
                handlers = db.get_handlers()
                h_name = next((h['name'] for h in handlers if h['id'] == handler_id), None)
                if h_name:
                    updates['O'] = h_name
            
            # 3. Execute Update
            handler = get_excel_handler()
            success = handler.update_single_record(path, sheet_name, no_dvd, updates)
            
            if success:
                QMessageBox.information(self, "Sync Excel", f"✅ Đã cập nhật thành công record {no_dvd} vào file Excel.")
                logger.info(f"Synced record {no_dvd} to {path}")
            else:
                QMessageBox.warning(self, "Sync Excel", "⚠️ Không tìm thấy dòng tương ứng trong file Excel hoặc lỗi file.")
                
        except FileNotFoundError as e:
            logger.error(f"File không tồn tại: {e}")
            QMessageBox.critical(self, "Lỗi Sync", f"Không tìm thấy file Excel:\n{e}")
        except PermissionError as e:
            logger.error(f"Không có quyền truy cập file: {e}")
            QMessageBox.critical(self, "Lỗi Sync", f"Không có quyền ghi file Excel.\nKiểm tra xem file có đang mở không.\n{e}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi database: {e}")
            QMessageBox.critical(self, "Lỗi Sync", f"Lỗi truy vấn database:\n{e}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            QMessageBox.critical(self, "Lỗi Sync", f"Đã xảy ra lỗi không mong muốn: {e}")

    def on_record_saved(self, record: dict):
        """Handle record save from detail panel."""
        # Refresh the current tab
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            self.table_mayin.refresh()
        elif current_tab == 1:
            self.table_kit.refresh()
        self.load_data()  # Refresh stats
    
    # =========================================================================
    # ACTION HANDLERS
    # =========================================================================
    
    def on_import(self):
        """Handle import action."""
        from ui.import_dialog import ImportDialog
        
        dialog = ImportDialog(self)
        dialog.import_completed.connect(self.on_import_completed)
        dialog.exec()
    
    def on_import_completed(self, stats: dict):
        """Handle import completion."""
        self.load_data()  # Refresh data
        self.statusbar.showMessage(
            f"Import hoàn tất: +{stats.get('inserted', 0)} mới, "
            f"~{stats.get('updated', 0)} cập nhật"
        )
    
    def on_send_mail(self):
        """Handle send mail action - create KDTPS reply email."""
        record = self.detail_panel.current_record
        if not record:
            QMessageBox.warning(self, "Gửi thư", "Vui lòng chọn một lỗi trước.")
            return
        
        try:
            from core.email_handler import get_email_handler
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            handler_id = record.get('handler_id')
            
            # Check if handler assigned
            should_offer_batch = False
            pending_records = []
            handler_name = ""
            handler_email = ""
            
            if handler_id:
                # Get handler info
                handlers = db.get_handlers()
                h_data = next((h for h in handlers if h['id'] == handler_id), None)
                if h_data:
                    handler_name = h_data['name']
                    handler_email = h_data.get('email', '')
                    
                    # Check for pending records
                    pending_records = db.get_pending_records_by_handler(handler_id)
                    # Filter out current record to see if there are OTHERS
                    other_records = [r for r in pending_records if str(r['id']) != str(record.get('id'))]
                    
                    if len(other_records) > 0:
                        should_offer_batch = True
            
            email_handler = get_email_handler()
            
            # Case 1: Batch Offer
            if should_offer_batch:
                count = len(pending_records)
                reply = QMessageBox.question(
                    self,
                    "Gửi Email",
                    f"Người phụ trách **{handler_name}** đang có **{count}** lỗi chưa xử lý.\n\n"
                    "Anh/Chị muốn gửi mail tổng hợp không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Send Batch
                    if not handler_email:
                        # Try to prompt for email if missing? Or just warn
                        QMessageBox.warning(self, "Thiếu Email", f"Chưa có email cho {handler_name}. Vui lòng cập nhật trong file DS KDTVN.")
                        return
                        
                    if email_handler.create_aggr_notification(handler_email, handler_name, pending_records):
                         self.statusbar.showMessage(f"Đã tạo email tổng hợp cho {handler_name}")
                    else:
                         QMessageBox.warning(self, "Lỗi", "Không thể tạo email (Outlook Error).")
                    return

            # Case 2: Specific Reply (Default)
            # Find destination emails
            to_emails = []
            if handler_email:
                to_emails.append(handler_email)
            
            # Always reply using default KDTPS template for single item
            if email_handler.create_kdtps_reply(record, to_emails=to_emails):
                self.statusbar.showMessage(f"Đã tạo email cho No.{record.get('no_dvd', '')}")
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể kết nối Outlook. Hãy đảm bảo Outlook đang chạy.")
                
        except Exception as e:
            logger.error(f"Send mail failed: {e}")
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {e}")
    
    def on_report(self):
        """Show report dashboard."""
        self.tabs.setCurrentIndex(2)  # Switch to Report tab
    
    def on_show_pending(self):
        """Show pending investigations."""
        self.sidebar.chk_pending.setChecked(True)
        # load_data will be triggered by toggled signal
    
    def on_show_jp_support(self):
        """Show errors needing JP support."""
        self.sidebar.chk_jp.setChecked(True)
        # load_data will be triggered by toggled signal
    
    def on_backup(self):
        """Backup completed records."""
        self.tabs.setCurrentIndex(2)  # Switch to Report tab
        self.report_widget.on_backup_completed()
    
    def on_search(self):
        """Show search dialog."""
        self.tabs.setCurrentIndex(3)  # Switch to Search tab
    
    def on_export_report(self):
        """Export error report file."""
        self.tabs.setCurrentIndex(2)  # Switch to Report tab
        self.report_widget.on_export_excel()
    
    def on_settings(self):
        """Show settings dialog."""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def on_user_guide(self):
        """Open internal user guide viewer (Phase 7 Fix)."""
        try:
            from ui.guide_dialog import GuideDialog
            
            # resolve() helps to get absolute path accurately
            base_dir = Path(__file__).resolve().parent.parent.parent
            guide_path = base_dir / "docs" / "USER_GUIDE.md"
            
            if guide_path.exists():
                dialog = GuideDialog(str(guide_path.absolute()), self)
                dialog.exec()
                self.statusbar.showMessage("Đã mở tài liệu hướng dẫn nội bộ.", 3000)
            else:
                logger.error(f"Guide not found at: {guide_path}")
                QMessageBox.warning(self, "Lỗi", f"Không tìm thấy file hướng dẫn tại:\n{guide_path}")
        except Exception as e:
            logger.exception(f"Failed to open guide: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể hiển thị tài liệu: {e}")

    def on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About KDTPS Error Manager",
            "📊 KDTPS Error Manager v0.1.0\n\n"
            "Hệ thống quản lý lỗi KDTPS\n"
            "Tổng hợp thông tin lỗi, quản lý tiến độ điều tra,\n"
            "hỗ trợ dịch tự động và xuất báo cáo.\n\n"
            "© 2026 PE Dept - KDTVN"
        )
    
    def on_record_changed(self, record_id: int, key: str, value: Any):
        """Handle inline edits from grid."""
        logger.debug(f"Record changed: ID={record_id}, Key={key}, Value={value}")
        
        try:
            from core.database import get_database
            from utils.config import config
            db = get_database(config.db_path)
            
            # 1. Update Database
            if key == "handler_name":
                # Resolve Handler Name -> ID
                handler_name = str(value).strip()
                handler_id = None
                if handler_name:
                    h_data = db.get_handler_by_name(handler_name)
                    if h_data:
                        handler_id = h_data['id']
                    else:
                        # Auto-create new handler if allowed
                        handler_id = db.add_handler(handler_name)
                
                # Update DB
                db.update_error_field(record_id, "handler_id", handler_id)
                self.statusbar.showMessage(f"Đang cập nhật '{handler_name}'...")
                
                # 2. Get Record Info for Excel Sync
                # We need the full record to get No, Sheet, DeptID
                # Since we don't have the full record passed here, we query it or use selected
                # But querying DB is safer
                with db.get_connection() as conn:
                    row = conn.execute("SELECT * FROM error_records WHERE id = ?", (record_id,)).fetchone()
                    if not row:
                        return
                    record_data = dict(row)
                
                # 3. Trigger Excel Sync
                self.start_excel_sync(record_data, {'O': handler_name})
                
                # Refresh UI to show update (and re-map ID to Name)
                # reload_data is heavy, maybe just refresh current item if possible?
                # But we need to refresh to get the ID->Name mapping correct for the Delegate
                # Current tab refresh
                current_tab = self.tabs.currentIndex()
                if current_tab == 0:
                    self.table_mayin.refresh()
                elif current_tab == 1:
                    self.table_kit.refresh()

        except Exception as e:
            logger.error(f"Failed to update record: {e}")
            QMessageBox.warning(self, "Lỗi cập nhật", f"Không thể lưu thay đổi: {e}")

    def start_excel_sync(self, record: dict, updates: dict):
        """Start background Excel sync."""
        try:
            dept_id = record.get('department_id')
            if not dept_id:
                return

            path = self._get_department_path(dept_id)
            if not path or not Path(path).exists():
                logger.warning(f"Excel file not found for Dept {dept_id}: {path}")
                return

            # Start worker
            self.sync_worker = SyncWorker(
                file_path=path,
                sheet_name=record.get('sheet_type'),
                no_dvd=record.get('no_dvd'),
                updates=updates
            )
            self.sync_worker.finished.connect(self.on_sync_finished)
            self.sync_worker.start()
            
        except Exception as e:
            logger.error(f"Failed to start sync: {e}")

    def _get_department_path(self, dept_id: int) -> Optional[str]:
        """Helper to get department network path (resolves to Excel file)."""
        try:
            from core.database import get_database
            from utils.config import config
            db = get_database(config.db_path)
            
            path_str = None
            with db.get_connection() as conn:
                row = conn.execute("SELECT network_path FROM departments WHERE id = ?", (dept_id,)).fetchone()
                if row:
                    path_str = row[0]
            
            if not path_str:
                return None
                
            # If path is a directory, try to find the summary file
            # This fixes the issue where DB has folder path ending in .2 (e.g. "Cơ 2.2")
            # causing openpyxl to fail.
            path = Path(path_str)
            if path.exists() and path.is_dir():
                # Logic: look for File tổng hợp*.xl*
                for ext in ["*.xlsm", "*.xlsx"]:
                    for f in path.glob(f"File tổng hợp*{ext}"):
                        return str(f)
            
            return path_str
        except Exception as e:
            logger.error(f"Error resolving department path: {e}")
            return None

    def on_sync_finished(self, success: bool, message: str):
        """Handle sync completion."""
        if success:
            self.statusbar.showMessage(f"✅ {message}", 5000)
        else:
            self.statusbar.showMessage(f"⚠️ {message}", 5000)

    def on_sync_handlers(self):
        """Handle Sync Handlers action."""
        self.statusbar.showMessage("⏳ Đang đồng bộ danh sách phụ trách...")
        
        self.handlers_worker = SyncHandlersWorker()
        self.handlers_worker.finished.connect(self.on_sync_handlers_finished)
        self.handlers_worker.start()
        
    def on_sync_handlers_finished(self, count: int, message: str):
        """Handle sync handlers completion."""
        if count > 0:
            self.statusbar.showMessage(f"✅ {message}", 5000)
            QMessageBox.information(self, "Đồng bộ hoàn tất", message)
            
            # Refresh delegate in grids to show new names
            try:
                from core.database import get_database
                from utils.config import config
                db = get_database(config.db_path)
                handlers = db.get_handlers()
                
                self.table_mayin.handler_delegate.set_handlers(handlers)
                self.table_kit.handler_delegate.set_handlers(handlers)
            except Exception as e:
                logger.error(f"Failed to refresh delegates: {e}")

    def on_data_synced(self, results: dict):
        """Handle background auto-sync completion (Phase 7.4)."""
        total_new = sum(results.values())
        if total_new == 0:
            return
            
        dept_info = ", ".join([f"{name} (+{count})" for name, count in results.items()])
        msg = f"PHÁT HIỆN LỖI MỚI!\n\nĐã tự động nạp {total_new} lỗi mới từ server:\n{dept_info}"
        
        self.statusbar.showMessage(f"📢 {msg.replace('\\n', ' ')}", 20000)
        
        # Trigger UI refresh
        self.on_import_completed({"inserted": total_new, "updated": 0})
        
        # Auto refresh Dashboard if active
        if self.tabs.currentIndex() == self.tabs.indexOf(self.dashboard_widget):
            self.dashboard_widget.on_refresh_clicked()
                
        else:
            self.statusbar.showMessage(f"⚠️ {message}", 5000)
            if "Lỗi" in message:
                QMessageBox.warning(self, "Lỗi đồng bộ", message)


from PyQt6.QtCore import QThread, pyqtSignal

class SyncWorker(QThread):
    """Background worker for Excel Sync."""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, file_path, sheet_name, no_dvd, updates):
        super().__init__()
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.no_dvd = no_dvd
        self.updates = updates
        
    def run(self):
        try:
            from core.excel_handler import get_excel_handler
            handler = get_excel_handler()
            
            # Simple wrapper around update_single_record
            success = handler.update_single_record(
                self.file_path, 
                self.sheet_name, 
                self.no_dvd, 
                self.updates
            )
            
            msg = "Cập nhật Excel thành công" if success else "Không tìm thấy dòng tương ứng"
            self.finished.emit(success, msg)
            
        except Exception as e:
            self.finished.emit(False, str(e))


class SyncHandlersWorker(QThread):
    """Background worker for Syncing Handlers from Excel."""
    finished = pyqtSignal(int, str)  # count, message
    
    def run(self):
        try:
            from core.excel_handler import get_excel_handler
            from core.database import get_database
            from utils.config import config
            
            logger.info("=== SyncHandlersWorker START ===")
            
            excel_handler = get_excel_handler()
            db = get_database(config.db_path)
            
            total_synced = 0
            errors = []
            
            # Iterate through all configured departments to find "DS KDTVN"
            departments = db.get_departments()
            logger.info(f"Found {len(departments)} departments")
            
            visited_paths = set()
            
            for dept in departments:
                dept_name = dept.get('name', 'Unknown')
                path = dept.get('network_path')
                logger.debug(f"Processing dept: {dept_name}, path: {path}")
                
                if not path:
                    logger.warning(f"  No path for {dept_name}")
                    continue
                    
                # Resolve file path
                file_path = None
                p = Path(path)
                
                if not p.exists():
                    logger.warning(f"  Path not accessible: {path}")
                    errors.append(f"{dept_name}: Path không tồn tại")
                    continue
                    
                if p.is_file():
                    file_path = str(p)
                elif p.is_dir():
                    # Find summary file
                    for ext in ["*.xlsm", "*.xlsx"]:
                        for f in p.glob(f"File tổng hợp*{ext}"):
                            file_path = str(f)
                            logger.debug(f"  Found file: {f.name}")
                            break
                        if file_path: 
                            break
                    
                    if not file_path:
                        logger.warning(f"  No summary file found in {path}")
                        errors.append(f"{dept_name}: Không tìm thấy file tổng hợp")
                        continue
                
                if file_path and file_path not in visited_paths:
                    visited_paths.add(file_path)
                    logger.info(f"  Reading handlers from: {file_path}")
                    
                    # Read handlers
                    handlers = excel_handler.read_handlers(file_path)
                    logger.info(f"  Found {len(handlers)} handlers")
                    
                    if handlers:
                        db.sync_handlers(handlers)
                        total_synced += len(handlers)
                        logger.info(f"  Synced {len(handlers)} handlers from {dept_name}")
                    else:
                        logger.warning(f"  No handlers found in {file_path}")
                        errors.append(f"{dept_name}: Sheet 'DS KDTVN' trống hoặc không tồn tại")
            
            logger.info(f"=== SyncHandlersWorker END: {total_synced} handlers ===")
            
            if total_synced > 0:
                self.finished.emit(total_synced, f"Đã đồng bộ {total_synced} người phụ trách.")
            elif errors:
                self.finished.emit(0, f"Lỗi: {'; '.join(errors[:3])}")
            else:
                self.finished.emit(0, "Không tìm thấy dữ liệu phụ trách (kiểm tra sheet DS KDTVN)")
            
        except Exception as e:
            logger.exception(f"SyncHandlersWorker error: {e}")
            self.finished.emit(0, f"Lỗi: {str(e)}")
