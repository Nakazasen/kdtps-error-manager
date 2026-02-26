"""
Report Widget for KDTPS Error Manager
Dashboard showing error statistics and charts.
"""
import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class StatCard(QFrame):
    """A styled card for displaying a statistic."""
    
    def __init__(self, title: str, value: str = "0", color: str = "#1976D2", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_value)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title)
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.lbl_value.setText(value)


class ReportWidget(QWidget):
    """Widget for displaying error statistics and reports."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with refresh button
        header = QHBoxLayout()
        
        title = QLabel("📊 Báo cáo tổng hợp")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.cmb_department = QComboBox()
        self.cmb_department.addItem("Tất cả phòng", None)
        self.cmb_department.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.cmb_department)
        
        self.btn_refresh = QPushButton("🔄 Làm mới")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)
        
        layout.addLayout(header)
        
        # Summary cards
        cards_layout = QHBoxLayout()
        
        self.card_total = StatCard("Tổng số lỗi", "0", "#4CAF50")
        cards_layout.addWidget(self.card_total)
        
        self.card_pending = StatCard("Đang điều tra", "0", "#FF9800")
        cards_layout.addWidget(self.card_pending)
        
        self.card_completed = StatCard("Hoàn thành", "0", "#2196F3")
        cards_layout.addWidget(self.card_completed)
        
        self.card_jp = StatCard("Cần JP hỗ trợ", "0", "#F44336")
        cards_layout.addWidget(self.card_jp)
        
        layout.addLayout(cards_layout)
        
        # Statistics by machine type
        machine_group = QGroupBox("📈 Thống kê theo loại máy")
        machine_layout = QVBoxLayout(machine_group)
        
        self.table_machines = QTableWidget()
        self.table_machines.setColumnCount(5)
        self.table_machines.setHorizontalHeaderLabels([
            "Loại máy", "Tổng", "Đang điều tra", "Hoàn thành", "Cần JP"
        ])
        
        header = self.table_machines.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.table_machines.setAlternatingRowColors(True)
        machine_layout.addWidget(self.table_machines)
        
        layout.addWidget(machine_group)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        self.btn_export_excel = QPushButton("📤 Xuất Excel")
        self.btn_export_excel.clicked.connect(self.on_export_excel)
        export_layout.addWidget(self.btn_export_excel)
        
        self.btn_backup = QPushButton("📦 Backup hoàn thành")
        self.btn_backup.clicked.connect(self.on_backup_completed)
        export_layout.addWidget(self.btn_backup)
        
        export_layout.addStretch()
        layout.addLayout(export_layout)
        
        # Load departments
        self.load_departments()
    
    def load_departments(self):
        """Load department list."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            departments = db.get_departments()
            
            for dept in departments:
                self.cmb_department.addItem(dept['name'], dept['id'])
                
        except Exception as e:
            logger.error(f"Failed to load departments: {e}")
    
    def refresh(self):
        """Refresh statistics."""
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            
            department_id = self.cmb_department.currentData()
            stats = db.get_statistics(department_id)
            
            # Update cards
            self.card_total.set_value(str(stats.get('total', 0)))
            self.card_pending.set_value(str(stats.get('total_pending', 0)))
            self.card_completed.set_value(str(stats.get('total_completed', 0)))
            self.card_jp.set_value(str(stats.get('total_needs_jp', 0)))
            
            # Update machine type table
            by_machine = stats.get('by_machine', [])
            self.table_machines.setRowCount(len(by_machine))
            
            for row_idx, item in enumerate(by_machine):
                machine_type = item.get('machine_type', 'Unknown')
                total = item.get('total', 0)
                pending = item.get('pending', 0)
                completed = item.get('completed', 0)
                needs_jp = item.get('needs_jp', 0)
                
                self.table_machines.setItem(row_idx, 0, QTableWidgetItem(str(machine_type)))
                self.table_machines.setItem(row_idx, 1, QTableWidgetItem(str(total)))
                self.table_machines.setItem(row_idx, 2, QTableWidgetItem(str(pending)))
                self.table_machines.setItem(row_idx, 3, QTableWidgetItem(str(completed)))
                self.table_machines.setItem(row_idx, 4, QTableWidgetItem(str(needs_jp)))
            
            logger.info("Report refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh report: {e}")
    
    def on_export_excel(self):
        """Export report to Excel file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo Excel",
            f"KDTPS_Report.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                from openpyxl import Workbook
                
                wb = Workbook()
                ws = wb.active
                ws.title = "Report"
                
                # Write summary
                ws.append(["KDTPS Error Report"])
                ws.append([])
                ws.append(["Tổng số:", self.card_total.lbl_value.text()])
                ws.append(["Đang điều tra:", self.card_pending.lbl_value.text()])
                ws.append(["Hoàn thành:", self.card_completed.lbl_value.text()])
                ws.append(["Cần JP:", self.card_jp.lbl_value.text()])
                ws.append([])
                
                # Write machine type table
                ws.append(["Loại máy", "Tổng", "Đang điều tra", "Hoàn thành", "Cần JP"])
                for row_idx in range(self.table_machines.rowCount()):
                    row_data = []
                    for col_idx in range(self.table_machines.columnCount()):
                        item = self.table_machines.item(row_idx, col_idx)
                        row_data.append(item.text() if item else "")
                    ws.append(row_data)
                
                wb.save(file_path)
                
                QMessageBox.information(self, "Xuất Excel", f"✅ Đã xuất báo cáo:\n{file_path}")
                
            except Exception as e:
                logger.error(f"Export failed: {e}")
                QMessageBox.critical(self, "Lỗi", f"Không thể xuất: {e}")
    
    def on_backup_completed(self):
        """Move completed records to backup."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Backup",
            "Đánh dấu tất cả lỗi 'Hoàn thành' thành Backup?\n\n"
            "Các lỗi này sẽ được chuyển sang mục Tìm kiếm Backup.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from core.database import get_database
                from utils.config import config
                
                db = get_database(config.db_path)
                
                # Get all completed records
                records = db.get_error_records()
                completed_ids = [
                    r['id'] for r in records 
                    if str(r.get('is_completed', '')).lower() == 'o'
                ]
                
                if completed_ids:
                    db.mark_as_backed_up(completed_ids)
                    self.refresh()
                    
                    QMessageBox.information(
                        self, "Backup",
                        f"✅ Đã backup {len(completed_ids)} lỗi hoàn thành!"
                    )
                else:
                    QMessageBox.information(
                        self, "Backup",
                        "Không có lỗi hoàn thành để backup."
                    )
                
            except Exception as e:
                logger.error(f"Backup failed: {e}")
                QMessageBox.critical(self, "Lỗi", f"Backup thất bại: {e}")
