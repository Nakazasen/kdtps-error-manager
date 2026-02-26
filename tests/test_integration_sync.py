import unittest
import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add src to path to match app behavior
sys.path.append(os.path.join(os.getcwd(), 'src'))

from openpyxl import Workbook
from core.database import DatabaseManager
from core.excel_handler import ExcelHandler
from utils.config import config, AppConfig

class TestSyncHandlersIntegration(unittest.TestCase):
    def setUp(self):
        # Create temp dir
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self.excel_path = Path(self.test_dir) / "test_handlers.xlsx"
        
        # Initialize DB
        self.db = DatabaseManager(self.db_path)
        self.excel_handler = ExcelHandler()
        
        # Mock Config to point to our test file structure
        # Assuming config is used to determine start rows/columns in read_handlers
        # We need to ensure we match what read_handlers expects (based on config defaults)
        # Default config: handler_sheet="DS KDTVN", start_row=5, name_col=6 (G), email_col=7 (H)
        
        from utils.config import config
        # Save original values to restore later
        self.orig_handler_sheet = config.handler_sheet
        self.orig_start_row = config.handler_start_row
        self.orig_name_col = config.handler_name_column
        self.orig_email_col = config.handler_email_column
        
        # Set test values (using defaults for now but explicitly)
        config.handler_sheet = "DS KDTVN"
        config.handler_start_row = 2 # Simplify for test
        config.handler_name_column = 0 # Col A
        config.handler_email_column = 1 # Col B

    def tearDown(self):
        # Restore config
        from utils.config import config
        config.handler_sheet = self.orig_handler_sheet
        config.handler_start_row = self.orig_start_row
        config.handler_name_column = self.orig_name_col
        config.handler_email_column = self.orig_email_col
        
        # Cleanup temp dir
        shutil.rmtree(self.test_dir)

    def create_mock_excel(self, data):
        """Helper to create Excel file with handler data."""
        wb = Workbook()
        ws = wb.active
        ws.title = "DS KDTVN"
        
        # Headers
        ws.cell(row=1, column=1, value="Name")
        ws.cell(row=1, column=2, value="Email")
        
        # Data
        for i, (name, email) in enumerate(data, start=2):
            ws.cell(row=i, column=1, value=name)
            ws.cell(row=i, column=2, value=email)
            
        wb.save(self.excel_path)
        wb.close()

    def test_sync_flow_new_handlers(self):
        """Test syncing new handlers from Excel to DB."""
        # 1. Prepare Excel Data
        mock_data = [
            ("Nguyen Van A", "a@example.com"),
            ("Le Thi B", "b@example.com")
        ]
        self.create_mock_excel(mock_data)
        
        # 2. Read from Excel
        handlers_from_excel = self.excel_handler.read_handlers(str(self.excel_path))
        self.assertEqual(len(handlers_from_excel), 2)
        self.assertEqual(handlers_from_excel[0]['name'], "Nguyen Van A")
        
        # 3. Sync to DB
        self.db.sync_handlers(handlers_from_excel)
        
        # 4. Verify in DB
        db_handlers = self.db.get_handlers()
        self.assertEqual(len(db_handlers), 2)
        
        names = [h['name'] for h in db_handlers]
        self.assertIn("Nguyen Van A", names)
        self.assertIn("Le Thi B", names)
        
        # Check email mapping
        handler_a = self.db.get_handler_by_name("Nguyen Van A")
        self.assertEqual(handler_a['email'], "a@example.com")

    def test_sync_flow_update_existing(self):
        """Test ensuring existing handlers are updated, not duplicated."""
        # 1. Pre-seed DB
        self.db.add_handler("Nguyen Van A", "old@example.com")
        
        # 2. Prepare Excel with Update
        mock_data = [
            ("Nguyen Van A", "new@example.com"), # Update email
            ("Tran Van C", "c@example.com")      # New user
        ]
        self.create_mock_excel(mock_data)
        
        # 3. Sync
        handlers = self.excel_handler.read_handlers(str(self.excel_path))
        self.db.sync_handlers(handlers)
        
        # 4. Verify
        all_handlers = self.db.get_handlers()
        self.assertEqual(len(all_handlers), 2) # Should still be 2 total (A and C)
        
        # Check update
        updated_a = self.db.get_handler_by_name("Nguyen Van A")
        self.assertEqual(updated_a['email'], "new@example.com")
        
        # Check insert
        new_c = self.db.get_handler_by_name("Tran Van C")
        self.assertIsNotNone(new_c)

if __name__ == '__main__':
    unittest.main()
