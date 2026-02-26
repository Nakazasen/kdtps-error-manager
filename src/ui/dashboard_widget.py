"""
Dashboard Widget for KDTPS Error Manager
Advanced visualization and alerts.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QFrame, QGridLayout,
    QScrollArea, QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate

# Import matplotlib for charts
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

class AlertBanner(QFrame):
    """Red alert banner shown when pending errors exceed threshold."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AlertBanner")
        self.setStyleSheet("""
            #AlertBanner {
                background-color: #f44336;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.setVisible(False)
        
        layout = QHBoxLayout(self)
        self.lbl_icon = QLabel("⚠️")
        self.lbl_msg = QLabel("BÁO ĐỘNG: CÓ QUÁ NHIỀU LỖI CHƯA XỬ LÝ!")
        
        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_msg)
        layout.addStretch()
        
    def show_alert(self, count: int):
        self.lbl_msg.setText(f"⚠️ BÁO ĐỘNG: CÒN {count} LỖI CHƯA XỬ LÝ (Vượt ngưỡng 10)!")
        self.setVisible(True)
        
    def hide_alert(self):
        self.setVisible(False)

class ChartCanvas(FigureCanvas):
    """Canvas for matplotlib charts."""
    
    def __init__(self, title: str, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.set_title(title)
        super().__init__(fig)
        self.setParent(parent)

class DashboardWidget(QWidget):
    """Main Dashboard with filters, alerts and charts."""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 1. Alert Banner
        self.alert_banner = AlertBanner()
        main_layout.addWidget(self.alert_banner)
        
        # 2. Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border-radius: 5px; }")
        filter_layout = QHBoxLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("🏢 Phòng ban:"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("Tất cả phòng", None)
        self.cmb_dept.setMinimumWidth(120)
        filter_layout.addWidget(self.cmb_dept)
        
        filter_layout.addWidget(QLabel("📅 Từ:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("Đến:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)
        
        self.btn_refresh = QPushButton("🔄 Cập nhật")
        self.btn_refresh.setMinimumWidth(100)
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)
        filter_layout.addWidget(self.btn_refresh)
        
        self.btn_export = QPushButton("📤 Xuất báo cáo")
        self.btn_export.clicked.connect(self.on_export_clicked)
        filter_layout.addWidget(self.btn_export)
        
        filter_layout.addStretch()
        main_layout.addWidget(filter_frame)
        
        # 3. Content Area (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(15)
        
        # Placeholder for charts (Phase 6.3)
        self.canvas_top_machines = ChartCanvas("Top 5 Máy lỗi nhiều nhất")
        self.grid_layout.addWidget(self.canvas_top_machines, 0, 0)
        
        self.canvas_completion = ChartCanvas("Tỉ lệ Hoàn thành")
        self.grid_layout.addWidget(self.canvas_completion, 0, 1)
        
        self.canvas_trend = ChartCanvas("Xu hướng Lỗi theo thời gian")
        self.grid_layout.addWidget(self.canvas_trend, 1, 0, 1, 2) # Span 2 columns
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)
        
    def on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_requested.emit()
        
    def on_export_clicked(self):
        """Export current dashboard view as an image (Phase 6.5)."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Xuất báo cáo Dashboard", 
            f"KDTPS_Dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            "Images (*.png *.jpg)"
        )
        
        if file_path:
            pixmap = self.container.grab()
            if pixmap.save(file_path):
                QMessageBox.information(self, "Xuất thành công", f"✅ Đã lưu ảnh báo cáo tại:\n{file_path}")
                # Open the file
                import os
                os.startfile(os.path.dirname(file_path))
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể lưu file. Vui lòng kiểm tra quyền ghi.")
        
    def set_departments(self, departments: List[Dict[str, Any]]):
        """Populate department combobox."""
        self.cmb_dept.clear()
        self.cmb_dept.addItem("Tất cả phòng", None)
        for dept in departments:
            self.cmb_dept.addItem(dept['name'], dept['id'])
            
    def update_dashboard(self, stats: Dict[str, Any]):
        """Update dashboard data and charts (Phase 6.3)."""
        # Update alert
        pending_count = stats.get('total_pending', 0)
        if pending_count > 10:
            self.alert_banner.show_alert(pending_count)
        else:
            self.alert_banner.hide_alert()
            
        # 1. Plot Top Machines (Bar Chart)
        self.plot_top_machines(stats.get('top_machines', []))
        
        # 2. Plot Completion Rate (Pie Chart)
        self.plot_completion_rate(stats.get('summary', {}))
        
        # 3. Plot Trend (Line Chart)
        self.plot_trend(stats.get('trend', []))
        
    def plot_top_machines(self, data: List[Dict[str, Any]]):
        """Draw bar chart for top 5 machine types with most errors."""
        ax = self.canvas_top_machines.axes
        ax.clear()
        
        if not data:
            ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center')
        else:
            labels = [d['machine_type'] for d in data]
            counts = [d['count'] for d in data]
            
            bars = ax.bar(labels, counts, color='#1976D2')
            ax.set_title("Top 5 Máy lỗi nhiều nhất")
            ax.set_ylabel("Số lượng lỗi")
            
            # Rotate labels if too many
            if len(labels) > 3:
                ax.tick_params(axis='x', rotation=45)
                
            # Add labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), 
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        self.canvas_top_machines.draw()

    def plot_completion_rate(self, summary: Dict[str, Any]):
        """Draw pie chart for investigation completion rate."""
        ax = self.canvas_completion.axes
        ax.clear()
        
        pending = summary.get('pending', 0)
        completed = summary.get('completed', 0)
        
        if pending == 0 and completed == 0:
            ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center')
        else:
            labels = ['Đang điều tra', 'Hoàn thành']
            sizes = [pending, completed]
            colors = ['#FF9800', '#4CAF50']
            
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
            ax.set_title("Tỉ lệ Hoàn thành điều tra")
        
        self.canvas_completion.draw()

    def plot_trend(self, trend_data: List[Dict[str, Any]]):
        """Draw line chart for error trend over time."""
        ax = self.canvas_trend.axes
        ax.clear()
        
        if not trend_data:
            ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center')
        else:
            dates = [d['date'] for d in trend_data]
            counts = [d['count'] for d in trend_data]
            
            ax.plot(dates, counts, marker='o', linestyle='-', color='#f44336', linewidth=2)
            ax.fill_between(dates, counts, color='#f44336', alpha=0.1)
            
            ax.set_title("Xu hướng Lỗi mới theo thời gian")
            ax.set_ylabel("Số lượng")
            
            # Formatting X-axis
            if len(dates) > 5:
                # Show every nth label to avoid crowding
                n = len(dates) // 5
                ax.set_xticks(dates[::n])
                ax.tick_params(axis='x', rotation=30)
                
        self.canvas_trend.draw()
