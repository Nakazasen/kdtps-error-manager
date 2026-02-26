import sys
import logging
from pathlib import Path

# Setup logging to console
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append('src')

from core.database import get_database
from utils.config import config
from core.excel_handler import get_excel_handler

def debug_sync():
    logger.info("Starting Sync Debug...")
    db = get_database(config.db_path)
    excel_handler = get_excel_handler()
    
    departments = db.get_departments()
    logger.info(f"Found {len(departments)} departments in DB")
    
    for dept in departments:
        name = dept['name']
        path_str = dept['network_path']
        logger.info(f"Checking Dept: {name}, Path: {path_str}")
        
        if not path_str:
            logger.warning("  -> Path is empty")
            continue
            
        p = Path(path_str)
        if not p.exists():
            logger.warning(f"  -> Path does not exist: {p.absolute()}")
            continue
            
        file_path = None
        if p.is_file():
            file_path = str(p)
            logger.info("  -> Is a file")
        elif p.is_dir():
            logger.info("  -> Is a directory, searching for summary file...")
            for ext in ["*.xlsm", "*.xlsx"]:
                found = list(p.glob(f"File tổng hợp*{ext}"))
                logger.info(f"     pattern 'File tổng hợp*{ext}' matched: {found}")
                if found:
                    file_path = str(found[0])
                    break
        
        if file_path:
            logger.info(f"  -> Target File: {file_path}")
            # Try Reading
            try:
                from openpyxl import load_workbook
                wb = load_workbook(file_path, read_only=True, keep_vba=True)
                if "DS KDTVN" in wb.sheetnames:
                    logger.info("  -> Sheet 'DS KDTVN' FOUND!")
                    ws = wb["DS KDTVN"]
                    count = 0
                    for row in range(2, 20): # Check first 20 rows
                        val = ws.cell(row=row, column=7).value # Col G
                        if val:
                            count += 1
                            logger.info(f"     Row {row}: {val}")
                    logger.info(f"  -> Found approx {count} entries in first 20 rows")
                else:
                    logger.error(f"  -> Sheet 'DS KDTVN' NOT FOUND in {wb.sheetnames}")
            except Exception as e:
                logger.error(f"  -> Failed to read excel: {e}")
        else:
            logger.error("  -> No matching file found in directory")

if __name__ == "__main__":
    debug_sync()
