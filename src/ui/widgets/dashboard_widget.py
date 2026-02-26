"""
Dashboard Widget for KDTPS Error Manager
Provides a high-level overview of error statistics using custom charts.
"""
import logging
from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QScrollArea, QComboBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import Qt, QRect, QSize, QDate
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

logger = logging.getLogger(__name__)

class KPICard(QFrame):
    """A card showing a single metric with a label and icon."""
    def __init__(self, title: str, value: str, color: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("kpiCard")
        self.setStyleSheet(f"""
            #kpiCard {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
                padding: 15px;
            }}
            QLabel {{
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel(f"{icon} {title}")
        self.lbl_title.setStyleSheet("color: #757575; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.lbl_title)
        
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 900; margin-top: 5px;")
        layout.addWidget(self.lbl_value)
        
    def update_value(self, value: str):
        self.lbl_value.setText(value)

class SimpleBarChart(QWidget):
    """A simple custom bar chart component."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.data: Dict[str, int] = {}
        self.setMinimumHeight(250)
        
    def set_data(self, data: Dict[str, int]):
        self.data = data
        self.update()
        
    def paintEvent(self, event):
        if not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        padding = 40
        
        # Draw title
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRect(0, 0, width, 25), Qt.AlignmentFlag.AlignLeft, self.title)
        
        # Drawing area
        chart_rect = QRect(padding, 30, width - padding * 2, height - padding - 40)
        
        # Find max value
        max_val = max(self.data.values()) if self.data else 1
        if max_val == 0: max_val = 1
        
        # Draw bars
        bar_count = len(self.data)
        if bar_count == 0: return
        
        bar_spacing = 10
        total_spacing = bar_spacing * (bar_count + 1)
        bar_width = (chart_rect.width() - total_spacing) // bar_count
        
        keys = list(self.data.keys())
        for i, key in enumerate(keys):
            val = self.data[key]
            bar_height = int((val / max_val) * chart_rect.height())
            
            x = chart_rect.left() + bar_spacing + i * (bar_width + bar_spacing)
            y = chart_rect.bottom() - bar_height
            
            bar_rect = QRect(x, y, bar_width, bar_height)
            
            # Color (alternate or gradient)
            painter.setBrush(QBrush(QColor("#42A5F5")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_rect, 4, 4)
            
            # Label
            painter.setPen(QPen(QColor("#757575")))
            painter.setFont(QFont("Segoe UI", 8))
            
            # Key label (rotated if too many)
            label_rect = QRect(x, chart_rect.bottom() + 5, bar_width, 15)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, key)
            
            # Value label
            value_rect = QRect(x, y - 20, bar_width, 15)
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, str(val))

class DashboardWidget(QWidget):
    """Main dashboard view."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Scroll area for entire dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        
        # 1. Header
        header_layout = QHBoxLayout()
        title = QLabel("📊 Hệ thống Bảng điều khiển")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        btn_refresh = QLabel("🔄 Cập nhật tự động (15p)")
        btn_refresh.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        header_layout.addWidget(btn_refresh)
        
        layout.addLayout(header_layout)

        # 1.5 Filters Row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Phòng ban:"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("Tất cả", None)
        self.cmb_dept.setMinimumWidth(150)
        filter_layout.addWidget(self.cmb_dept)
        
        filter_layout.addWidget(QLabel("Từ ngày:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("Đến ngày:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)
        
        self.btn_refetch = QPushButton("🔍 Lọc")
        filter_layout.addWidget(self.btn_refetch)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # 2. KPI Cards Row
        kpi_layout = QGridLayout()
        self.card_total = KPICard("TỔNG LỖỊ", "0", "#2196F3", "📁")
        self.card_pending = KPICard("ĐANG CHỜ", "0", "#FFA726", "🕒")
        self.card_completed = KPICard("HOÀN THÀNH", "0", "#66BB6A", "✅")
        self.card_jp = KPICard("CẦN JP HỖ TRỢ", "0", "#EF5350", "🇯🇵")
        
        kpi_layout.addWidget(self.card_total, 0, 0)
        kpi_layout.addWidget(self.card_pending, 0, 1)
        kpi_layout.addWidget(self.card_completed, 0, 2)
        kpi_layout.addWidget(self.card_jp, 0, 3)
        
        layout.addLayout(kpi_layout)
        
        # 3. Charts Area
        charts_layout = QHBoxLayout()
        
        # By Machine Chart
        self.chart_machine = SimpleBarChart("📈 Thống kê theo Loại máy")
        charts_layout.addWidget(self.chart_machine, 1)
        
        # By Dept Chart
        self.chart_dept = SimpleBarChart("🏢 Thống kê theo Phòng ban")
        charts_layout.addWidget(self.chart_dept, 1)
        
        layout.addLayout(charts_layout)
        
        # 4. Recent Activity placeholder (Optional future feature)
        layout.addStretch()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
    def refresh_data(self):
        """Fetch statistics and update UI."""
        try:
            from core.database import get_database
            db = get_database()
            stats = db.get_dashboard_stats()
            
            # Update cards
            self.card_total.update_value(str(stats['total']))
            self.card_pending.update_value(str(stats['pending']))
            self.card_completed.update_value(str(stats['completed']))
            self.card_jp.update_value(str(stats['jp_support']))
            
            # Update charts
            self.chart_machine.set_data(stats['by_machine'])
            self.chart_dept.set_data(stats['by_dept'])
            
            logger.info("Dashboard stats refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh dashboard: {e}")

    def on_sync_data_received(self, results: dict):
        """Signal handler to refresh when data is synced."""
        self.refresh_data()

    def set_departments(self, depts: List[Dict[str, Any]]):
        """Populate department combo box."""
        current = self.cmb_dept.currentData()
        self.cmb_dept.clear()
        self.cmb_dept.addItem("Tất cả", None)
        for dept in depts:
            self.cmb_dept.addItem(dept['name'], dept['id'])
        
        # Restore selection if possible
        index = self.cmb_dept.findData(current)
        if index >= 0:
            self.cmb_dept.setCurrentIndex(index)

    def update_dashboard(self, stats: Dict[str, Any]):
        """Update UI with provided stats."""
        # Update cards
        self.card_total.update_value(str(stats.get('total', 0)))
        self.card_pending.update_value(str(stats.get('pending', 0)))
        self.card_completed.update_value(str(stats.get('completed', 0)))
        self.card_jp.update_value(str(stats.get('jp_support', 0)))
        
        # Update charts
        self.chart_machine.set_data(stats.get('by_machine', {}))
        self.chart_dept.set_data(stats.get('by_dept', {}))
        
    def on_refresh_clicked(self):
        """Refresh using current filters. Called by MainWindow."""
        self.refresh_data()
