"""
Sync Log Widget for KDTPS Error Manager
Hiển thị nhật ký đồng bộ dữ liệu.
"""
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)

class SyncLogWidget(QWidget):
    """Widget to display sync logs in a table."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_logs()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header area
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("🕒 Nhật ký đồng bộ gần đây (100 bản ghi):"))
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Làm mới")
        self.btn_refresh.clicked.connect(self.refresh_logs)
        header_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(header_layout)
        
        # Log table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Thời gian bắt đầu", "Thời gian kết thúc", "Trạng thái", "Chi tiết", "Thông báo"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.table)
        
    def refresh_logs(self):
        """Fetch logs from database and update table."""
        try:
            from core.database import get_database
            db = get_database()
            logs = db.get_sync_logs(limit=100)
            
            self.table.setRowCount(len(logs))
            
            for row, log in enumerate(logs):
                # 0. Start Time
                self.table.setItem(row, 0, QTableWidgetItem(self._format_dt(log['start_time'])))
                # 1. End Time
                self.table.setItem(row, 1, QTableWidgetItem(self._format_dt(log['end_time'])))
                
                # 2. Status
                status = log['status']
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Colors based on status
                if status == "Success":
                    status_item.setBackground(QColor("#C8E6C9")) # Light Green
                elif status == "Warning":
                    status_item.setBackground(QColor("#FFF9C4")) # Light Yellow
                elif status == "Error":
                    status_item.setBackground(QColor("#FFCDD2")) # Light Red
                    status_item.setForeground(QColor("#B71C1C"))
                
                self.table.setItem(row, 2, status_item)
                
                # 3. Results (JSON summary)
                results_text = self._format_results(log['results'])
                self.table.setItem(row, 3, QTableWidgetItem(results_text))
                
                # 4. Message
                self.table.setItem(row, 4, QTableWidgetItem(log['message'] or ""))
                
            logger.info(f"Refreshed {len(logs)} sync logs")
        except Exception as e:
            logger.error(f"Failed to refresh sync logs: {e}")

    def _format_dt(self, dt_str: str) -> str:
        """Format ISO datetime string for display."""
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return dt_str

    def _format_results(self, results_json: str) -> str:
        """Format results JSON into a readable string."""
        try:
            results = json.loads(results_json)
            if not results:
                return "Không có dữ liệu mới"
            
            parts = []
            for dept, count in results.items():
                if count > 0:
                    parts.append(f"{dept}: +{count}")
            
            return ", ".join(parts) if parts else "Không có lỗi mới"
        except:
            return results_json

    @pyqtSlot(dict)
    def on_sync_data_received(self, results: dict):
        """Signal handler for auto-sync results."""
        self.refresh_logs()
