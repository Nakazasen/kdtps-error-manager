"""
Excel Handler for KDTPS Error Manager
Handles reading KDTPS files and writing to department summary files.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from openpyxl import load_workbook, Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Skip color RGB (light green - cells with this color won't be overwritten)
SKIP_COLOR_RGB = (146, 208, 80)


class ExcelHandler:
    """Handles Excel file operations for KDTPS data."""
    
    def __init__(self):
        self.skip_color_rgb = SKIP_COLOR_RGB
    
    # =========================================================================
    # READING KDTPS SOURCE FILE
    # =========================================================================
    
    def read_kdtps_file(
        self,
        file_path: str,
        sheet_name: str = None,
        start_row: int = 3,
        header_row: int = 2,
        end_col: str = "P",
        date_filter: Tuple[Any, Any] = None  # (start_date, end_date)
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Read KDTPS source file.
        
        Args:
            file_path: Path to KDTPS Excel file
            sheet_name: Sheet name to read (None = active sheet)
            start_row: First data row (default 3)
            header_row: Header row (default 2)
            end_col: Last column to read (default P)
            date_filter: Optional tuple (start_date, end_date) to filter rows
        
        Returns:
            Tuple of (headers, data_rows)
        """
        # TRY 1: openpyxl (Fast, supports network files, no Excel required)
        try:
            wb = load_workbook(file_path, read_only=True, data_only=True)
            
            # Log available sheet names
            logger.debug(f"Available sheets: {wb.sheetnames}")
            
            # Find and select worksheett
            ws = self._find_worksheet(wb, sheet_name)
            
            # Get headers from header_row
            headers = []
            col_idx = 1
            end_col_idx = self._col_letter_to_idx(end_col)
            
            # Read headers efficiently
            for row in ws.iter_rows(min_row=header_row, max_row=header_row, min_col=1, max_col=end_col_idx, values_only=True):
                for cell_value in row:
                    headers.append(str(cell_value) if cell_value else f"Col{len(headers)+1}")
            
            # Get data rows efficiently with iter_rows
            data_rows = []
            rows_scanned = 0
            
            for row in ws.iter_rows(min_row=start_row, min_col=1, max_col=end_col_idx, values_only=True):
                rows_scanned += 1
                
                # Check identifying column (col 1) to stop if empty
                if row[0] is None:
                    # Look ahead logic isn't easy with iter_rows, but usually empty row 1 means end
                    # Let's check if entire row is empty
                    if all(c is None for c in row):
                        break
                    # If just col 1 is empty but others not, maybe continue? 
                    # KDTPS structure usually implies col 1 (No.) is present.
                    continue
                
                # Date Filtering Logic
                if date_filter:
                    date_val = row[1] # Column B (index 1) is Production Date
                    keep_row = False
                    
                    if date_val:
                        row_date = self._parse_date_value(date_val)
                        
                        if row_date:
                            start_date, end_date = date_filter
                            if start_date <= row_date <= end_date:
                                keep_row = True
                    
                    if not keep_row:
                        continue
                
                data_rows.append(list(row))
                
                if rows_scanned > 10000:
                    logger.warning("Reached row limit 10000")
                    break
            
            wb.close()
            logger.info(f"Read {len(data_rows)} rows from {file_path} using openpyxl")
            return headers, data_rows

        except Exception as e:
            error_msg = str(e).lower()
            logger.warning(f"openpyxl failed: {e}")
            
            # TRY 2: win32com (Slow, but handles password protected files)
            # Only try if it looks like a password/encryption error, OR if it was a file access error
            # But win32com is really slow on network, so only use as last resort.
            
            is_password = "password" in error_msg or "encrypted" in error_msg
            
            logger.info("Falling back to win32com...")
            try:
                return self._read_with_excel_com(
                    file_path, sheet_name, start_row, header_row, end_col
                )
            except Exception as e_com:
                logger.error(f"win32com also failed: {e_com}")
                # If it was a password error initially, raise that for clarity
                if is_password:
                    raise e
                raise e_com
    
    
    def _find_worksheet(self, wb: Workbook, sheet_name: Optional[str]) -> Worksheet:
        """Helper to find worksheet with flexible name matching."""
        if not sheet_name:
            ws = wb.active
            logger.info(f"Using active sheet: {ws.title}")
            return ws

        # 1. Exact match
        if sheet_name in wb.sheetnames:
            return wb[sheet_name]
        
        # 2. Case-insensitive
        sheet_lower = sheet_name.lower().strip()
        for name in wb.sheetnames:
            if name.lower().strip() == sheet_lower:
                logger.info(f"Sheet matched (case-insensitive): '{sheet_name}' -> '{name}'")
                return wb[name]
        
        # 3. Partial match
        for name in wb.sheetnames:
            if sheet_lower in name.lower() or name.lower() in sheet_lower:
                logger.info(f"Sheet matched (partial): '{sheet_name}' -> '{name}'")
                return wb[name]
                
        raise KeyError(f"Worksheet '{sheet_name}' does not exist. Available: {wb.sheetnames}")

    def _parse_date_value(self, date_val: Any) -> Optional[Any]:
        """Helper to parse various date formats from Excel."""
        if isinstance(date_val, datetime):
            return date_val.date()
        elif hasattr(date_val, 'date'): # support date objects
                return date_val
        elif isinstance(date_val, str):
            # Try parsing common formats
            # Common formats in KDTPS: 2025-10-01 00:00:00 or 2025/10/01
            s_val = str(date_val).strip().split(' ')[0] # Remove time part if string
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(s_val, fmt).date()
                except ValueError:
                    pass
        return None


    def read_handlers(self, file_path: str) -> List[Dict[str, str]]:
        """
        Read handlers from DS KDTVN sheet.
        Returns [{'name': '...', 'email': '...'}, ...]
        """
        try:
            from openpyxl import load_workbook
            from utils.config import config
            
            logger.debug(f"Opening workbook: {file_path}")
            wb = load_workbook(file_path, read_only=True, data_only=True)
            
            logger.debug(f"Available sheets: {wb.sheetnames}")
            if config.handler_sheet not in wb.sheetnames:
                logger.warning(f"Handler sheet '{config.handler_sheet}' not found in {wb.sheetnames}")
                wb.close()
                return []
            
            ws = wb[config.handler_sheet]
            handlers = []
            
            # Config settings
            start_row = config.handler_start_row  # e.g., 5
            name_col_idx = config.handler_name_column + 1  # 0-based to 1-based: 6 -> 7 (Col G)
            email_col_idx = config.handler_email_column + 1  # 7 -> 8 (Col H)
            
            logger.debug(f"Reading from row {start_row}, name_col={name_col_idx}, email_col={email_col_idx}")
            
            # Use iter_rows for efficiency in read_only mode
            # Only read the columns we need (name and email)
            max_rows_to_read = 200  # Safety limit
            rows_read = 0
            
            for row in ws.iter_rows(min_row=start_row, min_col=name_col_idx, 
                                     max_col=email_col_idx, values_only=True):
                rows_read += 1
                if rows_read > max_rows_to_read:
                    logger.warning(f"Reached max rows limit ({max_rows_to_read})")
                    break
                
                # row[0] = name (Col G), row[1] = email (Col H) if exists
                name = str(row[0] or "").strip() if row and len(row) > 0 else ""
                email = str(row[1] or "").strip() if row and len(row) > 1 else ""
                
                if name:
                    handlers.append({
                        "name": name,
                        "email": email
                    })
            
            wb.close()
            logger.info(f"Read {len(handlers)} handlers from Excel (scanned {rows_read} rows)")
            return handlers
            
        except Exception as e:
            logger.error(f"Failed to read handlers: {e}")
            return []


    def _read_with_excel_com(
        self,
        file_path: str,
        sheet_name: str,
        start_row: int,
        header_row: int,
        end_col: str
    ) -> Tuple[List[str], List[List[Any]]]:
        """
        Read password-protected Excel file using win32com.
        Opens file in read-only mode via Excel application.
        """
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        excel = None
        wb = None
        
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            # Open in read-only mode (ReadOnly=True, no password needed for read)
            wb = excel.Workbooks.Open(
                str(Path(file_path).resolve()),
                ReadOnly=True,
                UpdateLinks=False
            )
            
            # Get sheet
            if sheet_name:
                ws = wb.Worksheets(sheet_name)
            else:
                ws = wb.ActiveSheet
            
            end_col_idx = self._col_letter_to_idx(end_col)
            
            # Get headers from header_row
            headers = []
            for col_idx in range(1, end_col_idx + 1):
                cell_value = ws.Cells(header_row, col_idx).Value
                headers.append(str(cell_value) if cell_value else f"Col{col_idx}")
            
            # Get data rows
            data_rows = []
            row_idx = start_row
            empty_count = 0
            
            while empty_count < 2:  # Stop after 2 consecutive empty rows
                first_cell = ws.Cells(row_idx, 1).Value
                if first_cell is None:
                    empty_count += 1
                    row_idx += 1
                    continue
                
                empty_count = 0
                row_data = []
                for col_idx in range(1, end_col_idx + 1):
                    cell_value = ws.Cells(row_idx, col_idx).Value
                    row_data.append(cell_value)
                
                if any(v is not None for v in row_data):
                    data_rows.append(row_data)
                
                row_idx += 1
                
                if row_idx > 10000:
                    logger.warning("Reached row limit 10000")
                    break
            
            logger.info(f"Read {len(data_rows)} rows via Excel COM from {file_path}")
            return headers, data_rows
            
        finally:
            # Đảm bảo giải phóng tài nguyên COM đúng cách
            # Sử dụng try-except riêng cho từng thao tác để tránh exception làm gián đoạn cleanup
            if wb:
                try:
                    wb.Close(SaveChanges=False)
                except Exception as e:
                    logger.warning(f"Lỗi khi đóng workbook: {e}")
            if excel:
                try:
                    excel.Quit()
                except Exception as e:
                    logger.warning(f"Lỗi khi thoát Excel: {e}")
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"Lỗi khi uninitialize COM: {e}")
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names in an Excel file."""
        try:
            wb = load_workbook(file_path, read_only=True)
            names = wb.sheetnames
            wb.close()
            return names
        except Exception as e:
            logger.error(f"Failed to get sheet names: {e}")
            return []
    
    def filter_rows_by_line(
        self,
        data_rows: List[List[Any]],
        line_column_idx: int,
        allowed_lines: List[str]
    ) -> List[List[Any]]:
        """
        Filter data rows by production line (column D).
        
        Args:
            data_rows: All data rows
            line_column_idx: Column index for Line (0-based, typically 3 for column D)
            allowed_lines: List of line names this department handles
        
        Returns:
            Filtered rows
        """
        # Nếu không có danh sách line nào được chỉ định, trả về tất cả
        if not allowed_lines:
            return data_rows
        
        filtered = []
        for row in data_rows:
            line_value = str(row[line_column_idx] or "").strip()
            # Chỉ kiểm tra nếu line_value có trong danh sách allowed_lines
            if line_value in allowed_lines:
                filtered.append(row)
        
        return filtered
    
    def filter_rows_by_value(
        self,
        data_rows: List[List[Any]],
        column_idx: int,
        allowed_values: List[str]
    ) -> List[List[Any]]:
        """
        Filter data rows by specific column value (exact match after strip).
        
        Args:
            data_rows: All data rows
            column_idx: Column index to check
            allowed_values: List of allowed values
        
        Returns:
            Filtered rows
        """
        if not allowed_values:
            return data_rows
        
        filtered = []
        for row in data_rows:
            # Safe access to column
            if column_idx < len(row):
                val = str(row[column_idx] or "").strip()
                # Also try first line only if newline exists (for department names)
                val_first_line = val.split('\n')[0].strip()
                
                if val_first_line in allowed_values:
                    filtered.append(row)
            else:
                # Column index out of range - keep or skip? Skip is safer for filter.
                pass
        
        return filtered
    
    # =========================================================================
    # WRITING TO DEPARTMENT SUMMARY FILE
    # =========================================================================
    
    def write_to_summary_file(
        self,
        file_path: str,
        sheet_name: str,
        data_rows: List[List[Any]],
        start_row: int = 2,
        key_column_idx: int = 0
    ) -> Dict[str, Any]:
        """
        Write data to department summary file.
        Respects cells with skip color (won't overwrite them).
        
        Args:
            file_path: Path to summary Excel file
            sheet_name: Target sheet name ('Máy in' or 'KIT')
            data_rows: Data to write (columns A-P)
            start_row: First data row
            key_column_idx: Column used as unique key (default 0 = column A)
        
        Returns:
            Dict with stats: {'inserted': N, 'updated': N, 'skipped_cells': N}
        """
        try:
            # Try to open existing file or create new
            if Path(file_path).exists():
                # Important: keep_vba=True is required for .xlsm files to avoid corruption on save
                is_xlsm = str(file_path).lower().endswith('.xlsm')
                wb = load_workbook(file_path, keep_vba=is_xlsm)
            else:
                wb = Workbook()
            
            # Get or create sheet
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                ws = wb.create_sheet(sheet_name)
            
            stats = {'inserted': 0, 'updated': 0, 'skipped_cells': 0}
            
            # Build map of existing keys to row numbers
            existing_keys = {}
            for row_idx in range(start_row, ws.max_row + 1):
                key_value = ws.cell(row=row_idx, column=key_column_idx + 1).value
                if key_value:
                    existing_keys[str(key_value)] = row_idx
            
            # Find initial next empty row (to fill gaps instead of appending)
            next_empty_row = start_row
            while ws.cell(row=next_empty_row, column=key_column_idx + 1).value is not None:
                next_empty_row += 1
            
            # Process each data row
            for data_row in data_rows:
                key_value = str(data_row[key_column_idx] or "")
                
                if key_value in existing_keys:
                    # Update existing row
                    target_row = existing_keys[key_value]
                    self._update_row(ws, target_row, data_row, stats)
                    stats['updated'] += 1
                else:
                    # Insert new row at next available position
                    self._write_row(ws, next_empty_row, data_row)
                    existing_keys[key_value] = next_empty_row
                    stats['inserted'] += 1
                    
                    # Advance to next empty row
                    next_empty_row += 1
                    while ws.cell(row=next_empty_row, column=key_column_idx + 1).value is not None:
                        next_empty_row += 1
            
            wb.save(file_path)
            wb.close()
            
            logger.info(f"Wrote to {file_path}/{sheet_name}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to write to summary file: {e}")
            raise
    
    def _update_row(
        self,
        ws: Worksheet,
        row_idx: int,
        data: List[Any],
        stats: Dict[str, int]
    ):
        """Update a row, respecting skip color cells."""
        for col_idx, value in enumerate(data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            
            # Check if cell has skip color
            if self._cell_has_skip_color(cell):
                stats['skipped_cells'] += 1
                continue
            
            cell.value = value
    
    def _write_row(self, ws: Worksheet, row_idx: int, data: List[Any]):
        """Write a new row."""
        for col_idx, value in enumerate(data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    def _cell_has_skip_color(self, cell) -> bool:
        """Check if cell has the skip color (light green RGB 146,208,80)."""
        try:
            fill = cell.fill
            if fill and fill.patternType == 'solid':
                fg_color = fill.fgColor
                if fg_color and fg_color.type == 'rgb':
                    # RGB string format: AARRGGBB or RRGGBB
                    rgb_str = fg_color.rgb
                    if rgb_str and len(rgb_str) >= 6:
                        # Extract RGB values
                        if len(rgb_str) == 8:
                            r = int(rgb_str[2:4], 16)
                            g = int(rgb_str[4:6], 16)
                            b = int(rgb_str[6:8], 16)
                        else:
                            r = int(rgb_str[0:2], 16)
                            g = int(rgb_str[2:4], 16)
                            b = int(rgb_str[4:6], 16)
                        
                        # Allow some tolerance (±5)
                        target_r, target_g, target_b = self.skip_color_rgb
                        if (abs(r - target_r) <= 5 and 
                            abs(g - target_g) <= 5 and 
                            abs(b - target_b) <= 5):
                            return True
        except Exception:
            pass
        return False
    
    

    # =========================================================================
    # EXPORT REPLY FILE
    # =========================================================================
    
    def create_reply_file(
        self,
        source_file_path: str,
        source_sheet: str,
        no_dvd: str,
        output_path: str
    ) -> bool:
        """
        Create reply file for KDTPS with data from specific No điểm vấn đề.
        
        Args:
            source_file_path: Path to summary file
            source_sheet: Sheet name ('Máy in' or 'KIT')
            no_dvd: No điểm vấn đề to extract
            output_path: Path for output file
        
        Returns:
            True if successful
        """
        try:
            wb_source = load_workbook(source_file_path, data_only=True)
            ws_source = wb_source[source_sheet]
            
            # Find row with matching No
            target_row = None
            for row_idx in range(2, ws_source.max_row + 1):
                if str(ws_source.cell(row=row_idx, column=1).value) == str(no_dvd):
                    target_row = row_idx
                    break
            
            if not target_row:
                logger.error(f"No điểm vấn đề {no_dvd} not found")
                return False
            
            # Create new workbook with extracted data
            wb_new = Workbook()
            ws_new = wb_new.active
            ws_new.title = "Reply"
            
            # Copy headers (row 1)
            for col_idx in range(1, 17):  # A to P
                ws_new.cell(row=1, column=col_idx, value=ws_source.cell(row=1, column=col_idx).value)
            
            # Copy data row
            for col_idx in range(1, 17):  # A to P
                ws_new.cell(row=2, column=col_idx, value=ws_source.cell(row=target_row, column=col_idx).value)
            
            # Adjust column widths
            for col_idx in range(1, 17):
                ws_new.column_dimensions[get_column_letter(col_idx)].width = 15
            
            wb_new.save(output_path)
            wb_new.close()
            wb_source.close()
            
            logger.info(f"Created reply file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create reply file: {e}")
            return False
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    @staticmethod
    def _col_letter_to_idx(col_letter: str) -> int:
        """Convert column letter to 1-based index (A=1, B=2, etc.)"""
        if not col_letter:
            return 1
        
        col_letter = col_letter.upper()
        result = 0
        for char in col_letter:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result
    
    def get_extended_data(
        self,
        file_path: str,
        sheet_name: str,
        start_row: int = 3,
        header_row: int = 2,
        end_col: str = "Y"
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Read extended data (columns A-Y) with column mapping.
        
        Returns:
            Tuple of (headers, list of row dicts with column keys)
        """
        headers, raw_data = self.read_kdtps_file(
            file_path, sheet_name, start_row, header_row, end_col
        )
        
        # Convert to list of dicts
        data_dicts = []
        for row in raw_data:
            row_dict = {}
            for idx, value in enumerate(row):
                col_letter = get_column_letter(idx + 1).lower()
                row_dict[f'col_{col_letter}'] = value
            data_dicts.append(row_dict)
        
        return headers, data_dicts


    # =========================================================================
    # UPDATE SINGLE RECORD (SYNC)
    # =========================================================================
    
    def update_single_record(
        self,
        file_path: str,
        sheet_name: str,
        no_dvd: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific columns of a single record in Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name ('Máy in' or 'KIT')
            no_dvd: The identifying 'No.' to find the row
            updates: Dictionary of column letters and values to update
                     Example: {'N': 'Investigation content', 'O': 'Handler Name'}
        
        Returns:
            True if successful, False if record not found
        """
        try:
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return False

            is_xlsm = str(file_path).lower().endswith('.xlsm')
            wb = load_workbook(file_path, keep_vba=is_xlsm)
            
            if sheet_name not in wb.sheetnames:
                logger.error(f"Sheet '{sheet_name}' not found in {file_path}")
                wb.close()
                return False
            
            ws = wb[sheet_name]
            
            # Find row
            target_row = None
            for row_idx in range(2, ws.max_row + 1):
                # Column A is usually No
                cell_val = ws.cell(row=row_idx, column=1).value
                if str(cell_val).strip() == str(no_dvd).strip():
                    target_row = row_idx
                    break
            
            if not target_row:
                logger.warning(f"Record No {no_dvd} not found in {file_path}")
                wb.close()
                return False
            
            # Apply updates
            for col_letter, value in updates.items():
                col_idx = self._col_letter_to_idx(col_letter)
                cell = ws.cell(row=target_row, column=col_idx)
                
                # Check skip color
                if self._cell_has_skip_color(cell):
                    logger.warning(f"Skipping update for locked cell {col_letter}{target_row}")
                    continue
                
                cell.value = value
            
            wb.save(file_path)
            wb.close()
            logger.info(f"Updated record [{no_dvd}] in {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update record: {e}")
            raise

# Singleton instance
_handler_instance: Optional[ExcelHandler] = None

def get_excel_handler() -> ExcelHandler:
    """Get or create ExcelHandler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = ExcelHandler()
    return _handler_instance
