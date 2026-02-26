"""
Data Grid Widget for KDTPS Error Manager
Custom QTableView with model for displaying error records.
"""
import logging
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QStyle, QMenu, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QVariant,
    pyqtSignal
)
from PyQt6.QtGui import QColor, QBrush, QFont, QAction, QKeySequence
from PyQt6.QtWidgets import QApplication, QComboBox
from core.database import get_database

logger = logging.getLogger(__name__)


# Column definitions for the grid
COLUMN_DEFS = [
    {"key": "no_dvd", "header": "No", "width": 50},
    {"key": "col_b", "header": "生産日\nNgày tháng sản xuất", "width": 80},
    {"key": "col_c", "header": "機種/型番\nLoại máy", "width": 100},
    {"key": "col_d", "header": "生産Line\nLine sản xuất", "width": 60},
    {"key": "col_e", "header": "生産工程\nCông đoạn sản xuất", "width": 100},
    {"key": "col_f", "header": "発生シリアル/品目\nSerial/Model phát sinh", "width": 120},
    {"key": "col_g", "header": "不具合分類\nPhân loại lỗi", "width": 100},
    {"key": "col_h", "header": "不具合現象\nHiện trạng lỗi", "width": 150},
    {"key": "col_i", "header": "不具合件数\nSố vụ lỗi", "width": 60},
    {"key": "col_j", "header": "累計件数\nSố vụ \nlũy kế", "width": 60},
    {"key": "col_k", "header": "発生時の作業内容(JP語版)\nNội dung thao tác khi phát sinh", "width": 200},
    {"key": "col_l", "header": "発生時の作業内容（VN語版）\nNội dung thao tác khi phát sinh", "width": 200},
    {"key": "col_m", "header": "調査状況（JP語版）\nTình trạng điều tra", "width": 200},
    {"key": "col_n", "header": "調査状況（VN語版）\nTình trạng điều tra", "width": 200},
    {"key": "col_o", "header": "担当部門\nBộ phận phụ trách", "width": 100},
    {"key": "col_p", "header": "回答期限\nKì hạn trả lời", "width": 100},
    {"key": "col_q", "header": "Đã nhập lên\nShare point chưa?", "width": 80},
    {"key": "col_r", "header": "Đã Close trên\nShare point/ KDTPS hay chưa?", "width": 100},
    {"key": "handler_name", "header": "Phụ trách", "width": 100},
    {"key": "col_t", "header": "Follow", "width": 60},
    {"key": "col_u", "header": "Trạng thái điều tra", "width": 120},
    {"key": "is_completed", "header": "Close", "width": 60},
    {"key": "col_w", "header": "Ngày hoàn thành", "width": 100},
    {"key": "col_x", "header": "New", "width": 50},
    {"key": "needs_jp_support", "header": "Cần JP hỗ trợ", "width": 80},
]


class HandlerDelegate(QStyledItemDelegate):
    """Delegate for editing Handler column with ComboBox."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.handlers_list = []  # List of {'id': int, 'name': str}
        
    def set_handlers(self, handlers: List[Dict]):
        """Set available handlers."""
        self.handlers_list = handlers
        
    def createEditor(self, parent, option, index):
        """Create ComboBox editor with Autocomplete."""
        editor = QComboBox(parent)
        editor.setEditable(True)
        
        # Populate
        editor.addItem("", None)
        for h in self.handlers_list:
            editor.addItem(h['name'], h['id'])
            
        # Setup Completer for "Contains" matching
        from PyQt6.QtWidgets import QCompleter
        completer = QCompleter([h['name'] for h in self.handlers_list], editor)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        editor.setCompleter(completer)
            
        return editor
        
    def setEditorData(self, editor, index):
        """Set current value in editor."""
        current_text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if current_text:
            idx = editor.findText(current_text)
            if idx >= 0:
                editor.setCurrentIndex(idx)
            else:
                editor.setCurrentText(current_text)
                
    def setModelData(self, editor, model, index):
        """Save value to model."""
        new_name = editor.currentText().strip()
        # We pass the name back to model.Model will emit signal to Controller to resolve ID.
        model.setData(index, new_name, Qt.ItemDataRole.EditRole)


class ErrorRecordModel(QAbstractTableModel):
    """Table model for error records."""
    
    record_changed = pyqtSignal(int, str, object)  # record_id, field_key, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._columns = COLUMN_DEFS
        self._handlers: Dict[int, str] = {}  # handler_id -> name mapping
    
    def set_data(self, data: List[Dict[str, Any]], handlers: Dict[int, str] = None):
        """Set the data for the model."""
        self.beginResetModel()
        self._data = data or []
        self._handlers = handlers or {}
        self.endResetModel()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._columns)
    
    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._columns[section]["header"]
            else:
                return str(section + 1)
        return None
    
    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
        
        row_data = self._data[index.row()]
        col_def = self._columns[index.column()]
        key = col_def["key"]
        
        if role == Qt.ItemDataRole.DisplayRole:
            if key == "handler_name":
                handler_id = row_data.get("handler_id")
                return self._handlers.get(handler_id, "")
            
            value = row_data.get(key, "")
            # Format date for col_b
            if key == "col_b" and value and isinstance(value, str):
                try:
                    return str(value).split(" ")[0]
                except:
                    pass
            
            return str(value) if value is not None else ""
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Green background for completed
            if key == "is_completed" and str(row_data.get("is_completed", "")).lower() == "o":
                return QBrush(QColor(200, 255, 200))
            # Yellow for needs JP support
            if key == "needs_jp_support" and str(row_data.get("needs_jp_support", "")).lower() == "o":
                return QBrush(QColor(255, 255, 200))
            # Light red for pending (no handler assigned)
            if not row_data.get("handler_id") and not row_data.get("is_completed"):
                return QBrush(QColor(255, 230, 230))
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            # Use black text ONLY if we have a custom background color (which are light)
            # Otherwise use default theme color (white in dark mode)
            
            # Check conditions that set background color
            has_bg = False
            if key == "is_completed" and str(row_data.get("is_completed", "")).lower() == "o":
                has_bg = True
            elif key == "needs_jp_support" and str(row_data.get("needs_jp_support", "")).lower() == "o":
                has_bg = True
            elif not row_data.get("handler_id") and not row_data.get("is_completed"):
                has_bg = True
            
            if has_bg:
                return QBrush(QColor(Qt.GlobalColor.black))
            return None
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Center dates, numbers, and short status fields
            if key in ("no_dvd", "col_b", "col_d", "col_i", "col_j", "col_w", 
                      "col_q", "col_r", "is_completed", "needs_jp_support", "col_x"):
                return Qt.AlignmentFlag.AlignCenter
        
        elif role == Qt.ItemDataRole.FontRole:
            if key == "no_dvd":
                font = QFont()
                font.setBold(True)
                return font
        
        elif role == Qt.ItemDataRole.UserRole:
            # Return the full row data for user role
            return row_data
        
        return None

    def flags(self, index):
        """Enable editing for specific columns."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
            
        flags = super().flags(index)
        col_def = self._columns[index.column()]
        
        # Enable editing for Handler ('handler_name')
        if col_def["key"] == "handler_name":
            flags |= Qt.ItemFlag.ItemIsEditable
            
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Handle data updates."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
            
        row = index.row()
        col = index.column()
        key = self._columns[col]["key"]
        record = self._data[row]
        record_id = record.get("id")
        
        if key == "handler_name":
            # For handler, we just emit the change request.
            # Logic: View -> Model -> Controller -> DB/Excel -> Model (Refresh)
            # Or optimistic update:
            
            # Here we just emit signal. The controller handles the DB logic.
            self.record_changed.emit(record_id, key, value)
            return True
            
        return False
    
    def get_record(self, row: int) -> Optional[Dict[str, Any]]:
        """Get record data for a row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
    
    def get_record_id(self, row: int) -> Optional[int]:
        """Get record ID for a row."""
        record = self.get_record(row)
        return record.get("id") if record else None


class DataGridView(QTableView):
    """Custom table view for error records."""
    
    record_selected = pyqtSignal(dict)  # Emits selected record data
    record_double_clicked = pyqtSignal(dict)
    record_changed = pyqtSignal(int, str, object) # Relay from model
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ErrorRecordModel(self)
        self.setModel(self._model)
        
        # Store current filters for refresh
        self._current_filters = {
            "department_id": None,
            "sheet_type": None,
            "pending_only": False,
            "jp_support_only": False
        }
        
        self.setup_ui()
        self.setup_signals()
        
        # Setup delegate
        self.handler_delegate = HandlerDelegate(self)
        # Find column index for 'handler_name'
        for i, col in enumerate(COLUMN_DEFS):
            if col['key'] == "handler_name":
                self.setItemDelegateForColumn(i, self.handler_delegate)
                break
    
    def setup_ui(self):
        """Configure table view appearance."""
        # Selection behavior
        # Selection behavior - SelectItems allows individual cell selection
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        
        # Header configuration
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set column widths
        for i, col_def in enumerate(COLUMN_DEFS):
            self.setColumnWidth(i, col_def["width"])
        
        # Vertical header
        self.verticalHeader().setDefaultSectionSize(28)
        self.verticalHeader().setVisible(False)
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def setup_signals(self):
        """Setup signal connections."""
        self.clicked.connect(self._on_row_clicked)
        self.doubleClicked.connect(self._on_row_double_clicked)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self._model.record_changed.connect(self.record_changed)
    
    def _on_row_clicked(self, index: QModelIndex):
        """Handle row click."""
        record = self._model.get_record(index.row())
        if record:
            self.record_selected.emit(record)
    
    def _on_row_double_clicked(self, index: QModelIndex):
        """Handle row double click."""
        record = self._model.get_record(index.row())
        if record:
            self.record_double_clicked.emit(record)

    def load_data(
        self,
        department_id: int = None,
        sheet_type: str = None,
        pending_only: bool = False,
        jp_support_only: bool = False
    ):
        """Load data from database with filters."""
        # Update current filters
        self._current_filters.update({
            "department_id": department_id,
            "sheet_type": sheet_type,
            "pending_only": pending_only,
            "jp_support_only": jp_support_only
        })
        
        try:
            from core.database import get_database
            from utils.config import config
            
            db = get_database(config.db_path)
            
            # Get records
            # Get records
            logger.debug(f"GridView fetching: Dept={department_id}, Sheet={sheet_type}, Pending={pending_only}, JP={jp_support_only}")
            records = db.get_error_records(
                department_id=department_id,
                sheet_type=sheet_type,
                pending_only=pending_only,
                jp_support_only=jp_support_only
            )
            logger.debug(f"GridView fetched: {len(records)} records")
            
            # Get handlers for name mapping
            handlers = db.get_handlers()
            self.handler_delegate.set_handlers(handlers) # Update delegate list
            handler_map = {h["id"]: h["name"] for h in handlers}
            
            self._model.set_data(records, handler_map)
            logger.info(f"Loaded {len(records)} records")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
    
    def refresh(self):
        """Refresh the current data using stored filters."""
        self.load_data(**self._current_filters)
    
    def get_selected_record(self) -> Optional[Dict[str, Any]]:
        """Get currently selected record."""
        indexes = self.selectedIndexes()
        if indexes:
            return self._model.get_record(indexes[0].row())
        return None
    
    def get_selected_record_id(self) -> Optional[int]:
        """Get ID of currently selected record."""
        record = self.get_selected_record()
        return record.get("id") if record else None

    def _on_context_menu(self, pos):
        """Show context menu."""
        # Get unique rows from selected cells
        rows = set(index.row() for index in self.selectedIndexes())
        if not rows:
            return
            
        count = len(rows)
        
        menu = QMenu(self)
        delete_action = menu.addAction(f"🗑️ Xóa {count} dòng tương ứng")
        delete_action.triggered.connect(self._delete_selected_rows)
        
        menu.exec(self.viewport().mapToGlobal(pos))
        
    def _delete_selected_rows(self):
        """Delete selected rows with confirmation."""
        # Get unique selected rows
        rows = set(index.row() for index in self.selectedIndexes())
        if not rows:
            return
            
        count = len(rows)
        
        # Confirm
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa {count} dòng dữ liệu này không?\n\nHành động này không thể hoàn tác!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Collect IDs
            ids = []
            for row_idx in rows:
                # Use model to get record ID
                rid = self._model.get_record_id(row_idx)
                if rid:
                    ids.append(rid)
            
            if ids:
                try:
                    db = get_database()
                    deleted = db.delete_error_records(ids)
                    if deleted > 0:
                        QMessageBox.information(self, "Thành công", f"Đã xóa {deleted} dòng dữ liệu.")
                        self.refresh()
                    else:
                        QMessageBox.warning(self, "Lỗi", "Không thể xóa dữ liệu (DB Error).")
                except Exception as e:
                    logger.error(f"Delete failed: {e}")
                    QMessageBox.warning(self, "Lỗi", f"Lỗi xóa dữ liệu: {e}")

    def keyPressEvent(self, event):
        """Handle copy text."""
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selection()
        else:
            super().keyPressEvent(event)

    def _copy_selection(self):
        """Copy selected cells to clipboard."""
        selection = self.selectedIndexes()
        if not selection:
            return
            
        # Sort by row then column
        selection.sort(key=lambda x: (x.row(), x.column()))
        
        if not selection:
            return
            
        # Get data
        rows = {}
        for index in selection:
            r = index.row()
            c = index.column()
            data = str(self._model.data(index, Qt.ItemDataRole.DisplayRole))
            if r not in rows:
                rows[r] = {}
            rows[r][c] = data
            
        # Build CSV/TSV string
        output = []
        sorted_rows = sorted(rows.keys())
        for r in sorted_rows:
            col_data = rows[r]
            sorted_cols = sorted(col_data.keys())
            line = "\t".join(col_data[c] for c in sorted_cols)
            output.append(line)
            
        text = "\n".join(output)
        QApplication.clipboard().setText(text)
