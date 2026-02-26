"""
Import Dialog for KDTPS Error Manager
Dialog for selecting KDTPS source file, target department, and sheet.
"""
import logging
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QGroupBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QProgressBar,
    QCheckBox, QHeaderView, QListWidget, QAbstractItemView, QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDate
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class PreviewWorker(QThread):
    """Background worker for loading file preview (avoids UI freeze).
    
    Uses openpyxl directly for fast preview. If file is password-protected,
    shows friendly error instead of blocking.
    """
    
    finished = pyqtSignal(list, list, int)  # headers, preview_rows, total_count
    error = pyqtSignal(str)
    
    # New signal: includes unique_lines from column D
    preview_ready = pyqtSignal(list, list, int, list, list)  # headers, rows, total_rows, unique_lines, unique_depts
    
    def __init__(self, source_file: str, end_col: str = "P"):
        super().__init__()
        self.source_file = source_file
        self.end_col = end_col
        logger.debug(f"[PreviewWorker] Created for file: {source_file}")
    
    def run(self):
        logger.debug("[PreviewWorker] run() STARTED")
        try:
            logger.debug("[PreviewWorker] Importing openpyxl...")
            from openpyxl import load_workbook
            from openpyxl.utils import get_column_letter
            logger.debug("[PreviewWorker] openpyxl imported successfully")
            
            # Try openpyxl first (fast, no COM issues)
            logger.debug(f"[PreviewWorker] Opening file: {self.source_file}")
            try:
                wb = load_workbook(self.source_file, read_only=True, data_only=True)
                logger.debug("[PreviewWorker] File opened successfully with openpyxl")
            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"[PreviewWorker] openpyxl failed: {e}")
                if 'password' in error_str or 'encrypted' in error_str:
                    logger.debug("[PreviewWorker] File is password-protected, emitting preview_ready with -1")
                    # Password protected - emit finished with special marker, NOT error
                    self.preview_ready.emit(
                        ["(File có mật khẩu - không thể xem trước)"],
                        [],
                        -1,  # Special value: -1 means password-protected
                        []   # No line data available
                    )
                    logger.debug("[PreviewWorker] preview_ready emitted for password-protected file")
                    return
                else:
                    raise
            
            ws = wb.active
            logger.debug(f"[PreviewWorker] Active sheet: {ws.title}, max_row={ws.max_row}")
            
            header_row = 2  # KDTPS header at row 2
            start_row = 3   # Data starts at row 3
            line_col = 4    # Column D = Line (index 4)
            dept_col = 15   # Column O = Department (index 15) for openpyxl (1-based)
            
            # Convert end_col to index
            end_col_idx = 0
            for char in self.end_col.upper():
                end_col_idx = end_col_idx * 26 + (ord(char) - ord('A') + 1)
            logger.debug(f"[PreviewWorker] end_col_idx={end_col_idx}")
            
            # Get headers from row 2
            logger.debug("[PreviewWorker] Reading headers from row 2...")
            headers = []
            for row in ws.iter_rows(min_row=header_row, max_row=header_row, min_col=1, max_col=end_col_idx, values_only=True):
                for cell_value in row:
                    headers.append(str(cell_value) if cell_value else f"Col{len(headers)+1}")
            logger.debug(f"[PreviewWorker] Headers count: {len(headers)}")
            
            # STEP 1: Get first 10 rows for preview display (fast)
            logger.debug("[PreviewWorker] Reading first 10 rows for preview...")
            preview_rows = []
            preview_limit = min(start_row + 10, ws.max_row + 1)
            
            for row in ws.iter_rows(min_row=start_row, max_row=preview_limit - 1, min_col=1, max_col=end_col_idx, values_only=True):
                first_cell = row[0] if row else None
                if first_cell is None:
                    continue
                preview_rows.append(list(row))
                if len(preview_rows) >= 10:
                    break
            
            logger.debug(f"[PreviewWorker] Preview rows loaded: {len(preview_rows)}")
            
            # STEP 2: Scan ALL rows for unique Lines (Column D) and Departments (Column O)
            logger.debug("[PreviewWorker] Scanning columns D to O for unique values...")
            unique_lines = set()
            unique_depts = set()
            line_rows_scanned = 0
            
            # Scan from Line (D=4) to Dept (O=15)
            # Row index 0 = Line, Row index 11 = Dept
            for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row, min_col=line_col, max_col=dept_col, values_only=True):
                line_rows_scanned += 1
                
                # Get Line (Column D - index 0 in this slice)
                if row:
                    line_val = row[0]
                    if line_val:
                        raw = str(line_val).split('\n')[0].strip().upper()
                        if raw:
                            unique_lines.add(raw)
                
                    if len(row) > 11:
                        dept_val = row[11]
                        if dept_val:
                            # Normalize: take first line, strip whitespace
                            raw_raw = str(dept_val)
                            # Log potential duplicates (using repr to see hidden chars)
                            if "製造技術" in raw_raw:
                                logger.debug(f"[PreviewWorker] Found Dept: {repr(raw_raw)}")
                                
                            raw_dept = raw_raw.split('\n')[0].strip()
                            
                            if raw_dept:
                                unique_depts.add(raw_dept)
                
                # Log progress every 500 rows
                if line_rows_scanned % 500 == 0:
                    logger.debug(f"[PreviewWorker] Scanned {line_rows_scanned} rows...")
            
            logger.debug(f"[PreviewWorker] Column D scan done: {line_rows_scanned} rows, {len(unique_lines)} unique Lines")
            logger.debug(f"[PreviewWorker] Lines found: {sorted(unique_lines)}")
            
            # Estimate total from max_row (faster than counting)
            estimated_total = ws.max_row - start_row + 1 if ws.max_row >= start_row else 0
            logger.debug(f"[PreviewWorker] Estimated total rows: {estimated_total}")
            
            logger.debug("[PreviewWorker] Closing workbook...")
            wb.close()
            
            # Sort and emit unique lines
            # Sort and emit unique lines and departments
            sorted_lines = sorted(list(unique_lines))
            sorted_depts = sorted(list(unique_depts))
            
            logger.debug(f"[PreviewWorker] Emitting preview_ready: headers={len(headers)}, rows={len(preview_rows)}, total={estimated_total}, lines={len(sorted_lines)}, depts={len(sorted_depts)}")
            self.preview_ready.emit(headers, preview_rows, estimated_total, sorted_lines, sorted_depts)
            logger.debug("[PreviewWorker] preview_ready EMITTED successfully")
            
        except Exception as e:
            logger.exception(f"[PreviewWorker] ERROR: {e}")
            self.error.emit(str(e))
            logger.debug("[PreviewWorker] error signal emitted")


class ImportWorker(QThread):
    """Background worker for import operation."""
    
    progress = pyqtSignal(int, str)  # progress%, message
    finished = pyqtSignal(dict)  # result stats
    error = pyqtSignal(str)
    
    def __init__(
        self,
        source_file: str,
        target_file: str,
        sheet_name: str,
        department_id: int,
        filter_lines: List[str] = None,
        filter_depts: List[str] = None,
        date_range: tuple = None
    ):
        super().__init__()
        self.source_file = source_file
        self.target_file = target_file
        self.sheet_name = sheet_name
        self.department_id = department_id
        self.filter_lines = filter_lines or []
        self.filter_depts = filter_depts or []
        self.date_range = date_range  # (start_date, end_date) or None
    
    def run(self):
        try:
            from core.excel_handler import get_excel_handler
            from core.database import get_database
            from utils.config import config
            
            handler = get_excel_handler()
            db = get_database()
            
            self.progress.emit(10, "Đang đọc danh sách phụ trách (DS KDTVN)...")
            
            # Sync Handlers from TARGET file (File Tổng Hợp)
            # User confirmed DS KDTVN is in the target file
            try:
                target_path_obj = Path(self.target_file)
                logger.info(f"Syncing handlers from: {self.target_file}")
                
                if target_path_obj.exists():
                    handlers_list = handler.read_handlers(self.target_file)
                    if handlers_list:
                        logger.info(f"Found {len(handlers_list)} handlers in target file.")
                        db.sync_handlers(handlers_list)
                        self.progress.emit(15, f"Đã cập nhật {len(handlers_list)} người phụ trách từ file đích")
                    else:
                        logger.warning(f"No handlers found in {self.target_file} (Check sheet name/data)")
                        self.progress.emit(15, "⚠️ Không tìm thấy danh sách phụ trách (sheet DS KDTVN)")
                else:
                    logger.warning(f"Target file does not exist: {self.target_file}")
                    self.progress.emit(15, "⚠️ File đích chưa có - bỏ qua cập nhật phụ trách")
                    
            except Exception as e_h:
                logger.error(f"Failed to sync handlers: {e_h}")
                # Continue anyway, not fatal
            
            self.progress.emit(20, "Đang đọc file KDTPS...")
            
            # Read source file - use active sheet (Sheet1) not target sheet name
            # sheet_name ("Máy in", "KIT") is for TARGET file, not SOURCE file
            # Update: Read up to column S (index 18) to get Handler
            headers, data_rows = handler.read_kdtps_file(
                self.source_file,
                sheet_name=None,  # Use active sheet (typically Sheet1 in KDTPS files)
                end_col="S",      # Read up to S (Phụ trách)
                date_filter=self.date_range
            )
            
            self.progress.emit(30, f"Đọc được {len(data_rows)} dòng")
            
            # Filter by line if specified
            if self.filter_lines:
                data_rows = handler.filter_rows_by_line(
                    data_rows,
                    line_column_idx=config.col_line,
                    allowed_lines=self.filter_lines
                )
                self.progress.emit(40, f"Sau lọc Line: {len(data_rows)} dòng")
            
            # Filter by department if specified
            if self.filter_depts:
                data_rows = handler.filter_rows_by_value(
                    data_rows,
                    column_idx=config.col_department,  # Column O
                    allowed_values=self.filter_depts
                )
                self.progress.emit(45, f"Sau lọc Bộ phận: {len(data_rows)} dòng")
            
            self.progress.emit(50, "Đang ghi vào file tổng hợp...")
            
            # Write to summary file
            stats = handler.write_to_summary_file(
                self.target_file,
                self.sheet_name,
                data_rows
            )
            
            self.progress.emit(70, "Đang đồng bộ vào database...")
            
            # Sync to database
            source_filename = Path(self.source_file).name
            col_handler_idx = 18  # Column S (0-based)
            
            for row in data_rows:
                record = {
                    'no_dvd': str(row[0] or ''),
                    'department_id': self.department_id,
                    'sheet_type': self.sheet_name,
                    'source_file': source_filename
                }
                # Add column data (A-P)
                for i, val in enumerate(row[:16]):  # A-P
                    col_letter = chr(ord('a') + i)
                    record[f'col_{col_letter}'] = val
                
                # Handle Handler (Column S)
                handler_id = None
                if len(row) > col_handler_idx:
                    handler_name = str(row[col_handler_idx] or "").strip()
                    if handler_name:
                        # Find or create handler
                        handler_data = db.get_handler_by_name(handler_name)
                        if handler_data:
                            handler_id = handler_data['id']
                        else:
                            # Create new handler
                            handler_id = db.add_handler(handler_name)
                
                record['handler_id'] = handler_id
                
                if record['no_dvd']:
                    db.upsert_error_record(record)
            
            self.progress.emit(100, "Hoàn tất!")
            self.finished.emit(stats)
            
        except Exception as e:
            logger.exception(f"Import error: {e}")
            self.error.emit(str(e))


class ImportDialog(QDialog):
    """Dialog for importing KDTPS data."""
    
    import_completed = pyqtSignal(dict)  # Emit stats when done
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Import Dữ Liệu KDTPS")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        self.source_file = None
        self.preview_data = []
        self.departments = []
        self.preview_worker = None  # Track preview worker
        
        self.setup_ui()
        self.load_departments()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Step 1: Source file selection
        step1_group = QGroupBox("Bước 1: Chọn File KDTPS Nguồn")
        step1_layout = QHBoxLayout(step1_group)
        
        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("Chọn file KDTPS từ: \\\\fstvn01\\Data\\...")
        self.txt_source.setReadOnly(True)
        step1_layout.addWidget(self.txt_source)
        
        self.btn_browse = QPushButton("📁 Chọn file...")
        self.btn_browse.clicked.connect(self.on_browse_source)
        step1_layout.addWidget(self.btn_browse)
        
        layout.addWidget(step1_group)
        
        # Step 2: Target selection
        step2_group = QGroupBox("Bước 2: Chọn Phòng & Sheet Đích")
        step2_layout = QFormLayout(step2_group)
        
        self.cmb_department = QComboBox()
        self.cmb_department.currentIndexChanged.connect(self.on_department_changed)
        step2_layout.addRow("Phòng:", self.cmb_department)
        
        self.cmb_sheet = QComboBox()
        self.cmb_sheet.addItems(["Máy in", "KIT"])
        step2_layout.addRow("Sheet:", self.cmb_sheet)
        
        self.txt_target_path = QLineEdit()
        self.txt_target_path.setReadOnly(True)
        self.txt_target_path.setStyleSheet("color: gray;")
        step2_layout.addRow("Đường dẫn đích:", self.txt_target_path)
        
        layout.addWidget(step2_group)
        
        # Preview table
        preview_group = QGroupBox("Xem trước dữ liệu (10 dòng đầu)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.table_preview = QTableWidget()
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.table_preview)
        
        self.lbl_preview_info = QLabel("Chưa chọn file")
        preview_layout.addWidget(self.lbl_preview_info)
        
        layout.addWidget(preview_group)
        
        # Options
        options_group = QGroupBox("Tùy chọn")
        options_layout = QVBoxLayout(options_group)
        
        self.chk_sync_handlers = QCheckBox("Đồng bộ danh sách người phụ trách (DS KDTVN)")
        self.chk_sync_handlers.setChecked(True)
        options_layout.addWidget(self.chk_sync_handlers)
        
        # Date filter section
        date_filter_layout = QHBoxLayout()
        self.chk_filter_date = QCheckBox("Lọc theo ngày sản xuất (cột B):")
        self.chk_filter_date.setChecked(True)
        self.chk_filter_date.stateChanged.connect(self.on_filter_date_changed)
        date_filter_layout.addWidget(self.chk_filter_date)
        
        self.dte_start = QDateEdit()
        self.dte_start.setCalendarPopup(True)
        self.dte_start.setDisplayFormat("dd/MM/yyyy")
        # Default: Start of current month
        today = QDate.currentDate()
        self.dte_start.setDate(QDate(today.year(), today.month(), 1))
        date_filter_layout.addWidget(QLabel("Từ:"))
        date_filter_layout.addWidget(self.dte_start)
        
        self.dte_end = QDateEdit()
        self.dte_end.setCalendarPopup(True)
        self.dte_end.setDisplayFormat("dd/MM/yyyy")
        self.dte_end.setDate(today)
        date_filter_layout.addWidget(QLabel("Đến:"))
        date_filter_layout.addWidget(self.dte_end)
        
        date_filter_layout.addStretch()
        options_layout.addLayout(date_filter_layout)
        
        # Line filter section
        line_filter_layout = QHBoxLayout()
        
        self.chk_filter_line = QCheckBox("Lọc theo Line (cột D):")
        self.chk_filter_line.setChecked(False)
        self.chk_filter_line.stateChanged.connect(self.on_filter_line_changed)
        line_filter_layout.addWidget(self.chk_filter_line)
        
        # ListWidget for selecting Lines
        self.list_lines = QListWidget()
        self.list_lines.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_lines.setMaximumHeight(80)
        self.list_lines.setEnabled(False)
        self.list_lines.setToolTip("Chọn các Line muốn import (giữ Ctrl để chọn nhiều)")
        line_filter_layout.addWidget(self.list_lines)
        
        # --- Department Filter (Column O) ---
        dept_filter_layout = QVBoxLayout()
        dept_filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chk_filter_dept = QCheckBox("Lọc theo Bộ phận (cột O)")
        self.chk_filter_dept.setToolTip("Chỉ import các dòng thuộc các bộ phận được chọn")
        self.chk_filter_dept.stateChanged.connect(self.on_filter_dept_changed)
        dept_filter_layout.addWidget(self.chk_filter_dept)
        
        self.list_depts = QListWidget()
        self.list_depts.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_depts.setMaximumHeight(80)
        self.list_depts.setEnabled(False)
        self.list_depts.setToolTip("Chọn các Bộ phận muốn import (giữ Ctrl để chọn nhiều)")
        dept_filter_layout.addWidget(self.list_depts)
        
        # Combine filters horizontally
        filters_hbox = QHBoxLayout()
        filters_hbox.addLayout(line_filter_layout)
        filters_hbox.addLayout(dept_filter_layout)
        
        options_layout.addLayout(filters_hbox)
        
        layout.addWidget(options_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_import = QPushButton("📥 Import")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_import.setMinimumWidth(120)
        btn_layout.addWidget(self.btn_import)
        
        layout.addLayout(btn_layout)
    
    def load_departments(self):
        """Load department list from database."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            self.departments = db.get_departments()
            
            self.cmb_department.clear()
            for dept in self.departments:
                self.cmb_department.addItem(dept['name'], dept['id'])
            
            if self.departments:
                self.on_department_changed(0)
                
        except Exception as e:
            logger.error(f"Failed to load departments: {e}")
    
    def on_department_changed(self, index: int):
        """Handle department selection change."""
        if index >= 0 and index < len(self.departments):
            dept = self.departments[index]
            self.txt_target_path.setText(dept.get('network_path', ''))
    
    def on_browse_source(self):
        """Open file dialog to select KDTPS source file."""
        from utils.config import config
        
        # Start from KDTPS source path if accessible
        start_path = config.kdtps_source_path
        if not Path(start_path).exists():
            start_path = ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn File KDTPS",
            start_path,
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.source_file = file_path
            self.txt_source.setText(file_path)
            self.load_preview()
    
    def load_preview(self):
        """Load preview of source file in background thread."""
        logger.debug("[ImportDialog] load_preview() called")
        if not self.source_file:
            logger.debug("[ImportDialog] No source file, returning")
            return
        
        logger.debug(f"[ImportDialog] Loading preview for: {self.source_file}")
        
        # Show loading state
        self.lbl_preview_info.setText("⏳ Đang đọc file... (vui lòng chờ)")
        self.btn_import.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.table_preview.setRowCount(0)
        
        # Clear line list
        self.list_lines.clear()
        self.chk_filter_line.setChecked(False)
        
        # Start background worker
        logger.debug("[ImportDialog] Creating PreviewWorker...")
        self.preview_worker = PreviewWorker(self.source_file, end_col="P")
        logger.debug("[ImportDialog] Connecting signals...")
        self.preview_worker.preview_ready.connect(self.on_preview_finished)
        self.preview_worker.error.connect(self.on_preview_error)
        logger.debug("[ImportDialog] Starting PreviewWorker thread...")
        self.preview_worker.start()
        logger.debug("[ImportDialog] PreviewWorker.start() called, waiting for signals...")
    
    def on_preview_finished(self, headers: list, preview_rows: list, total_count: int, unique_lines: list = None, unique_depts: list = None):
        """Handle preview load completion."""
        logger.debug(f"[ImportDialog] on_preview_finished() RECEIVED: headers={len(headers)}, rows={len(preview_rows)}, total={total_count}, lines={len(unique_lines) if unique_lines else 0}, depts={len(unique_depts) if unique_depts else 0}")
        self.preview_data = preview_rows
        unique_lines = unique_lines or []
        unique_depts = unique_depts or []
        
        # Handle password-protected file (total_count = -1)
        if total_count == -1:
            self.table_preview.setColumnCount(1)
            self.table_preview.setRowCount(1)
            self.table_preview.setHorizontalHeaderLabels(["Thông báo"])
            item = QTableWidgetItem("🔒 File có mật khẩu - không thể xem trước")
            item.setForeground(QColor(255, 165, 0))  # Orange
            self.table_preview.setItem(0, 0, item)
            
            self.lbl_preview_info.setText(
                "🔒 File có mật khẩu. Nhấn Import để tiếp tục (sẽ mở bằng Excel)."
            )
            # Disable line filter for password-protected files
            self.list_lines.clear()
            self.list_lines.setEnabled(False)
            self.chk_filter_line.setEnabled(False)
            
            self.btn_import.setEnabled(True)
            self.btn_browse.setEnabled(True)
            return
        
        # Update table
        self.table_preview.setColumnCount(len(headers))
        self.table_preview.setRowCount(len(self.preview_data))
        self.table_preview.setHorizontalHeaderLabels(headers)
        
        for row_idx, row_data in enumerate(self.preview_data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value or ""))
                self.table_preview.setItem(row_idx, col_idx, item)
        
        # Adjust columns
        header = self.table_preview.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Populate Line list
        self.list_lines.clear()
        if unique_lines:
            self.list_lines.addItems(unique_lines)
            self.chk_filter_line.setEnabled(True)
        else:
            self.chk_filter_line.setEnabled(False)

        # Populate Dept list
        self.list_depts.clear()
        if unique_depts:
            self.list_depts.addItems(unique_depts)
            self.chk_filter_dept.setEnabled(True)
        else:
            self.chk_filter_dept.setEnabled(False)
            
        self.lbl_preview_info.setText(
            f"✅ Tổng: {total_count} dòng | Lines: {len(unique_lines)} | Depts: {len(unique_depts)}"
        )
        
        self.btn_import.setEnabled(True)
        self.btn_browse.setEnabled(True)
    
    def on_filter_line_changed(self, state: int):
        """Handle filter line checkbox state change."""
        self.list_lines.setEnabled(state == Qt.CheckState.Checked.value)
        
    def on_filter_dept_changed(self, state: int):
        """Handle filter dept checkbox state change."""
        self.list_depts.setEnabled(state == Qt.CheckState.Checked.value)
        
    def on_filter_date_changed(self, state: int):
        """Enable/disable date edits based on checkbox."""
        enabled = (state == Qt.CheckState.Checked.value)
        self.dte_start.setEnabled(enabled)
        self.dte_end.setEnabled(enabled)
    
    def on_preview_error(self, error_msg: str):
        """Handle preview load error."""
        logger.error(f"Failed to load preview: {error_msg}")
        
        # Check if it's a password error - still allow import
        if "mật khẩu" in error_msg.lower() or "password" in error_msg.lower():
            self.lbl_preview_info.setText("🔒 " + error_msg)
            self.btn_import.setEnabled(True)
        else:
            self.lbl_preview_info.setText(f"❌ Lỗi: {error_msg}")
            self.btn_import.setEnabled(False)
        
        self.btn_browse.setEnabled(True)
    
    def on_import(self):
        """Start import process."""
        if not self.source_file:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file nguồn")
            return
        
        dept_idx = self.cmb_department.currentIndex()
        if dept_idx < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn phòng đích")
            return
        
        dept = self.departments[dept_idx]
        target_path = dept.get('network_path', '')
        
        # Check if target path is accessible
        if target_path and not Path(target_path).exists():
            reply = QMessageBox.question(
                self,
                "Cảnh báo",
                f"Đường dẫn không tồn tại hoặc không thể truy cập:\n{target_path}\n\n"
                "Bạn có muốn chọn file khác không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                target_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Chọn file tổng hợp đích",
                    "",
                    "Excel Files (*.xlsx)"
                )
                if not target_path:
                    return
        
        # Get filter lines from user selection in ListWidget
        filter_lines = []
        if self.chk_filter_line.isChecked():
            selected_items = self.list_lines.selectedItems()
            filter_lines = [item.text() for item in selected_items]
            if not filter_lines:
                # User checked filter but didn't select any lines
                QMessageBox.warning(
                    self, "Cảnh báo",
                    "Bạn đã chọn lọc theo Line nhưng chưa chọn Line nào.\n"
                    "Vui lòng chọn ít nhất 1 Line hoặc bỏ chọn ô 'Lọc theo Line'."
                )
                return
        
        # Get filter depts from user selection
        filter_depts = []
        if self.chk_filter_dept.isChecked():
            selected_items = self.list_depts.selectedItems()
            filter_depts = [item.text() for item in selected_items]
            if not filter_depts:
                QMessageBox.warning(
                    self, "Cảnh báo",
                    "Bạn đã chọn lọc theo Bộ phận nhưng chưa chọn Bộ phận nào.\n"
                    "Vui lòng chọn ít nhất 1 Bộ phận hoặc bỏ chọn ô 'Lọc theo Bộ phận'."
                )
                return
        
        # Disable UI during import
        self.btn_import.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Handle if target_path is a directory (e.g. "...\Cơ 2.2")
        if target_path and Path(target_path).exists() and Path(target_path).is_dir():
            dept_name = dept['name']
            # Try to find existing summary file matching pattern
            found_file = None
            try:
                # Check for "File tổng hợp*.xlsm" or "File tổng hợp*.xlsx"
                # Prioritize existing files that match the department name
                for ext in ["*.xlsm", "*.xlsx"]:
                    for f in Path(target_path).glob(f"File tổng hợp*{ext}"):
                        if dept_name in f.name:
                            found_file = str(f)
                            break
                    if found_file: break
            except Exception as e:
                logger.error(f"Error searching directory: {e}")
            
            if found_file:
                target_path = found_file
                logger.info(f"Auto-detected summary file: {target_path}")
            else:
                # Construct default filename
                clean_dept_name = dept_name.replace('/', '_').replace('\\', '_')
                filename = f"File tổng hợp lỗi {clean_dept_name}.xlsm"
                target_path = str(Path(target_path) / filename)
                logger.info(f"Constructed default summary file path: {target_path}")

        # Create and start worker
        # For now, use a simple target file path (will be enhanced later)
        if not target_path or (not Path(target_path).exists() and not Path(target_path).parent.exists()):
            # Use a local default path
            from utils.config import get_app_data_dir
            target_path = str(get_app_data_dir() / f"summary_{dept['name'].replace(' ', '_')}.xlsx")
        
        # Get date filter
        date_range = None
        if self.chk_filter_date.isChecked():
            start_date = self.dte_start.date().toPyDate()
            end_date = self.dte_end.date().toPyDate()
            date_range = (start_date, end_date)

        self.worker = ImportWorker(
            source_file=self.source_file,
            target_file=target_path,
            sheet_name=self.cmb_sheet.currentText(),
            department_id=dept['id'],
            filter_lines=filter_lines,
            filter_depts=filter_depts,
            date_range=date_range
        )
        
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.error.connect(self.on_import_error)
        self.worker.start()
    
    def on_progress(self, value: int, message: str):
        """Handle progress update."""
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)
    
    def on_import_finished(self, stats: dict):
        """Handle import completion."""
        self.progress_bar.setVisible(False)
        
        QMessageBox.information(
            self,
            "Import Thành Công",
            f"✅ Import hoàn tất!\n\n"
            f"• Thêm mới: {stats.get('inserted', 0)} dòng\n"
            f"• Cập nhật: {stats.get('updated', 0)} dòng\n"
            f"• Ô bỏ qua (màu xanh): {stats.get('skipped_cells', 0)}\n"
        )
        
        self.import_completed.emit(stats)
        self.accept()
    
    def on_import_error(self, error_msg: str):
        """Handle import error."""
        self.progress_bar.setVisible(False)
        self.btn_import.setEnabled(True)
        self.btn_browse.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Lỗi Import",
            f"❌ Không thể import dữ liệu:\n{error_msg}"
        )
        
        self.lbl_status.setText(f"Lỗi: {error_msg}")
