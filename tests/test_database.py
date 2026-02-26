"""
Unit Tests for DatabaseManager
"""
import unittest
import tempfile
import os
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test DatabaseManager functionality."""
    
    def setUp(self):
        """Create temporary database for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        if self.db_path.exists():
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_database_creation(self):
        """Test database and tables are created."""
        self.assertTrue(self.db_path.exists())
    
    def test_get_departments(self):
        """Test getting department list."""
        departments = self.db.get_departments()
        self.assertIsInstance(departments, list)
        self.assertGreater(len(departments), 0)
        
        # Check department structure
        dept = departments[0]
        self.assertIn('id', dept)
        self.assertIn('name', dept)
    
    def test_add_handler(self):
        """Test adding a new handler."""
        handler_id = self.db.add_handler(
            name="Test Handler",
            email="test@example.com"
        )
        self.assertIsNotNone(handler_id)
        self.assertGreater(handler_id, 0)
        
        # Verify handler was added
        handlers = self.db.get_handlers()
        handler_names = [h['name'] for h in handlers]
        self.assertIn("Test Handler", handler_names)
    
    def test_get_handlers(self):
        """Test getting handler list."""
        handlers = self.db.get_handlers()
        self.assertIsInstance(handlers, list)
    
    def test_add_error_record(self):
        """Test adding error record."""
        record_data = {
            'no_dvd': 'TEST-001',
            'col_b': '2026-02-02',
            'col_c': 'Máy A',
            'col_d': 'Line 01',
            'col_e': 5,
            'col_g': 'C001',
            'col_h': 'J001',
            'col_i': 'ERR001',
            'col_j': 'Test error content',
            'col_n': 'Test investigation',
            'sheet_type': 'Máy in',
            'department_id': 1
        }
        
        record_id = self.db.upsert_error_record(record_data)
        self.assertIsNotNone(record_id)
    
    def test_get_error_records(self):
        """Test getting error records."""
        # Add a record first
        self.db.upsert_error_record({
            'no_dvd': 'TEST-002',
            'sheet_type': 'Máy in',
            'department_id': 1
        })
        
        records = self.db.get_error_records()
        self.assertIsInstance(records, list)
        self.assertGreater(len(records), 0)
    
    def test_update_error_field(self):
        """Test updating error record field."""
        # Add a record
        self.db.upsert_error_record({
            'no_dvd': 'TEST-003',
            'col_n': 'Original investigation',
            'sheet_type': 'Máy in',
            'department_id': 1
        })
        
        # Get the record ID
        records = self.db.get_error_records()
        record = next((r for r in records if r['no_dvd'] == 'TEST-003'), None)
        self.assertIsNotNone(record)
        record_id = record['id']
        
        # Update field
        self.db.update_error_field(record_id, 'col_n', 'Updated investigation')
        
        # Verify update
        records = self.db.get_error_records()
        test_record = next((r for r in records if r['id'] == record_id), None)
        self.assertIsNotNone(test_record)
        self.assertEqual(test_record['col_n'], 'Updated investigation')
    
    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.db.get_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('total', stats)
        self.assertIn('total_pending', stats)
        self.assertIn('total_completed', stats)
    
    def test_filter_by_sheet_type(self):
        """Test filtering by sheet type."""
        # Add records with different sheet types
        self.db.upsert_error_record({
            'no_dvd': 'MAYIN-001',
            'sheet_type': 'Máy in',
            'department_id': 1
        })
        self.db.upsert_error_record({
            'no_dvd': 'KIT-001',
            'sheet_type': 'KIT',
            'department_id': 1
        })
        
        # Filter by Máy in
        mayin_records = self.db.get_error_records(sheet_type='Máy in')
        self.assertTrue(all(r['sheet_type'] == 'Máy in' for r in mayin_records))
        
        # Filter by KIT
        kit_records = self.db.get_error_records(sheet_type='KIT')
        self.assertTrue(all(r['sheet_type'] == 'KIT' for r in kit_records))
    


class TestDatabaseSingleton(unittest.TestCase):
    """Test database singleton pattern."""
    
    def test_get_database_returns_same_instance(self):
        """Test get_database returns same instance."""
        from core.database import get_database
        
        temp_path = Path(tempfile.mktemp(suffix='.db'))
        
        try:
            db1 = get_database(temp_path)
            db2 = get_database(temp_path)
            
            # Should be same instance
            self.assertIs(db1, db2)
        finally:
            if temp_path.exists():
                os.remove(temp_path)


if __name__ == '__main__':
    unittest.main()
