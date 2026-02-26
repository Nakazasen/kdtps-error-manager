"""
Search Dialog for KDTPS Error Manager
Dialog for searching backup records by error code or keyword.
"""
import logging
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class SearchDialog(QDialog):
    """Dialog for searching backup records."""
    
    record_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Tìm kiếm Backup")
        self.setMinimumSize(900, 600)
        self.setModal(False)  # Allow non-modal for reference
        
        self.results = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search criteria
        search_group = QGroupBox("Tiêu chí tìm kiếm")
        search_layout = QFormLayout(search_group)
        
        self.txt_keyword = QLineEdit()
        self.txt_keyword.setPlaceholderText("Nhập mã lỗi (Cxxx, Jxxx, Fxxx) hoặc từ khóa...")
        self.txt_keyword.returnPressed.connect(self.on_search)
        search_layout.addRow("🔑 Mã lỗi / Keyword:", self.txt_keyword)
        
        self.cmb_machine = QComboBox()
        self.cmb_machine.addItem("-- Tất cả loại máy --", None)
        # Will be populated with actual machine types
        search_layout.addRow("🖨️ Loại máy:", self.cmb_machine)
        
        layout.addWidget(search_group)
        
        # Search button
        btn_layout = QHBoxLayout()
        
        self.btn_search = QPushButton("🔍 Tìm kiếm")
        self.btn_search.clicked.connect(self.on_search)
        self.btn_search.setMinimumWidth(120)
        btn_layout.addWidget(self.btn_search)
        
        self.btn_clear = QPushButton("🗑️ Xóa")
        self.btn_clear.clicked.connect(self.on_clear)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        self.lbl_count = QLabel("Kết quả: 0")
        btn_layout.addWidget(self.lbl_count)
        
        layout.addLayout(btn_layout)
        
        # Results table
        self.table_results = QTableWidget()
        self.table_results.setAlternatingRowColors(True)
        self.table_results.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_results.setColumnCount(8)
        self.table_results.setHorizontalHeaderLabels([
            "No.", "Ngày", "Loại máy", "Line", "Cxxx", "Jxxx/Fxxx", 
            "Nội dung lỗi", "Điều tra"
        ])
        
        header = self.table_results.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Set column widths
        widths = [60, 80, 100, 60, 60, 80, 200, 250]
        for i, w in enumerate(widths):
            self.table_results.setColumnWidth(i, w)
        
        self.table_results.cellDoubleClicked.connect(self.on_row_double_clicked)
        
        layout.addWidget(self.table_results)
        
        # Footer buttons
        footer = QHBoxLayout()
        
        self.btn_view = QPushButton("👁️ Xem chi tiết")
        self.btn_view.clicked.connect(self.on_view_detail)
        footer.addWidget(self.btn_view)
        
        self.btn_copy = QPushButton("📋 Copy điều tra")
        self.btn_copy.clicked.connect(self.on_copy_investigation)
        footer.addWidget(self.btn_copy)
        
        footer.addStretch()
        
        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.close)
        footer.addWidget(self.btn_close)
        
        layout.addLayout(footer)
        
        # Load machine types
        self.load_machine_types()
    
    def load_machine_types(self):
        """Load available machine types from database."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            
            # Get distinct machine types from backup
            records = db.search_backup()
            machine_types = set()
            for r in records:
                if r.get('col_c'):
                    machine_types.add(r['col_c'])
            
            for mt in sorted(machine_types):
                self.cmb_machine.addItem(mt, mt)
                
        except Exception as e:
            logger.error(f"Failed to load machine types: {e}")
    
    def on_search(self):
        """Perform search."""
        keyword = self.txt_keyword.text().strip()
        machine_type = self.cmb_machine.currentData()
        
        if not keyword and not machine_type:
            QMessageBox.warning(self, "Tìm kiếm", "Vui lòng nhập từ khóa hoặc chọn loại máy")
            return
        
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            
            self.results = db.search_backup(
                keyword=keyword if keyword else None,
                machine_type=machine_type
            )
            
            self.display_results()
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            QMessageBox.critical(self, "Lỗi", f"Tìm kiếm thất bại: {e}")
    
    def display_results(self):
        """Display search results in table."""
        self.table_results.setRowCount(len(self.results))
        
        for row_idx, record in enumerate(self.results):
            items = [
                str(record.get('no_dvd', '')),
                str(record.get('col_b', '')),
                str(record.get('col_c', '')),
                str(record.get('col_d', '')),
                str(record.get('col_g', '')),
                str(record.get('col_h', '')),
                str(record.get('col_j', ''))[:100],
                str(record.get('col_n', ''))[:100]
            ]
            
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, record)
                self.table_results.setItem(row_idx, col_idx, item)
        
        self.lbl_count.setText(f"Kết quả: {len(self.results)}")
        logger.info(f"Found {len(self.results)} backup records")
    
    def on_clear(self):
        """Clear search form."""
        self.txt_keyword.clear()
        self.cmb_machine.setCurrentIndex(0)
        self.table_results.setRowCount(0)
        self.results = []
        self.lbl_count.setText("Kết quả: 0")
    
    def on_row_double_clicked(self, row: int, col: int):
        """Handle row double click."""
        if row < len(self.results):
            self.record_selected.emit(self.results[row])
    
    def on_view_detail(self):
        """View selected record detail."""
        row = self.table_results.currentRow()
        if row >= 0 and row < len(self.results):
            record = self.results[row]
            
            detail = f"""
No: {record.get('no_dvd', '')}
Ngày: {record.get('col_b', '')}
Loại máy: {record.get('col_c', '')}
Line: {record.get('col_d', '')}
Mã lỗi: {record.get('col_g', '')} {record.get('col_h', '')}

--- Nội dung lỗi (JP) ---
{record.get('col_j', '')}

--- Điều tra ---
{record.get('col_n', '')}
"""
            QMessageBox.information(self, f"Chi tiết No.{record.get('no_dvd', '')}", detail)
    
    def on_copy_investigation(self):
        """Copy investigation text to clipboard."""
        row = self.table_results.currentRow()
        if row >= 0 and row < len(self.results):
            investigation = self.results[row].get('col_n', '')
            
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(investigation)
            
            QMessageBox.information(
                self, "Copy",
                "✅ Đã copy nội dung điều tra vào clipboard!"
            )
