"""
SQLite Database operations for KDTPS Error Manager
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            self._create_tables(conn)
            self._seed_departments(conn)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create all required tables."""
        cursor = conn.cursor()
        
        # Departments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                network_path TEXT NOT NULL,
                lines TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Handlers table (người phụ trách)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS handlers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Error records - main table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_dvd TEXT NOT NULL,
                department_id INTEGER REFERENCES departments(id),
                sheet_type TEXT CHECK(sheet_type IN ('Máy in', 'KIT')),
                
                -- Source data columns A-P
                col_a TEXT, col_b TEXT, col_c TEXT, col_d TEXT,
                col_e TEXT, col_f TEXT, col_g TEXT, col_h TEXT,
                col_i TEXT, col_j TEXT, col_k TEXT, col_l TEXT,
                col_m TEXT, col_n TEXT, col_o TEXT, col_p TEXT,
                
                -- Extended columns Q-Y
                col_q TEXT, col_r TEXT,
                handler_id INTEGER REFERENCES handlers(id),
                col_t TEXT, col_u TEXT,
                is_completed TEXT DEFAULT '',
                col_w TEXT, col_x TEXT,
                needs_jp_support TEXT DEFAULT '',
                
                -- Metadata
                source_file TEXT,
                is_backed_up INTEGER DEFAULT 0,
                skip_cells TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(no_dvd, sheet_type, department_id)
            )
        """)
        
        # App configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sync logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                status TEXT NOT NULL,
                results TEXT,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Email logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_dvd TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                status TEXT NOT NULL, -- Sent, Failed
                error_message TEXT,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_no ON error_records(no_dvd)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_completed ON error_records(is_completed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_jp ON error_records(needs_jp_support)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_handler ON error_records(handler_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_machine ON error_records(col_c)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_backed_up ON error_records(is_backed_up)")
        
        logger.info("Database tables created successfully")
    
    def _seed_departments(self, conn: sqlite3.Connection):
        """Seed initial department data."""
        cursor = conn.cursor()
        
        departments = [
            ("Cơ 1.1", r"\\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 1\Cơ 1.1"),
            ("Cơ 1.2", r"\\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 1\Cơ 1.2"),
            ("Cơ 2.1", r"\\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 2\Cơ 2.1"),
            ("Cơ 2.2", r"\\fstvn01\Data\10_Production Engineering Department(製造技術部)\02.製造技術課\PE Dept\30. Lỗi phát sinh -不具合発生\Tổng hợp lỗi KDTPS của Phòng\Cơ 2\Cơ 2.2"),
        ]
        
        for name, path in departments:
            cursor.execute("""
                INSERT OR IGNORE INTO departments (name, network_path)
                VALUES (?, ?)
            """, (name, path))
    
    # =========================================================================
    # DEPARTMENT OPERATIONS
    # =========================================================================
    
    def get_departments(self) -> List[Dict]:
        """Get all departments."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM departments ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_department_by_name(self, name: str) -> Optional[Dict]:
        """Get department by name."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM departments WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # =========================================================================
    # HANDLER OPERATIONS
    # =========================================================================
    
    def get_handlers(self, active_only: bool = True) -> List[Dict]:
        """Get all handlers."""
        with self.get_connection() as conn:
            query = "SELECT * FROM handlers"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_handler(self, name: str, email: str = None) -> int:
        """Add a new handler. Returns handler ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO handlers (name, email) VALUES (?, ?)",
                (name, email)
            )
            return cursor.lastrowid
    
    def get_handler_by_name(self, name: str) -> Optional[Dict]:
        """Get handler by name."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM handlers WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def sync_handlers(self, handlers: List[Dict[str, str]]):
        """
        Sync handlers from list (Name, Email).
        Updates email if name exists, inserts if not.
        """
        with self.get_connection() as conn:
            for h in handlers:
                name = h['name']
                email = h['email']
                
                # Check exist
                cursor = conn.execute("SELECT id FROM handlers WHERE name = ?", (name,))
                row = cursor.fetchone()
                
                if row:
                    # Update email if changed
                    # (In future we could check if email changed to avoid writes)
                    if email:
                        conn.execute(
                            "UPDATE handlers SET email = ? WHERE id = ?",
                            (email, row[0])
                        )
                else:
                    # Insert
                    conn.execute(
                        "INSERT INTO handlers (name, email) VALUES (?, ?)",
                        (name, email)
                    )
    
    # =========================================================================
    # ERROR RECORD OPERATIONS
    # =========================================================================
    
    def upsert_error_record(self, record: Dict[str, Any]) -> int:
        """Insert or update an error record."""
        with self.get_connection() as conn:
            # Build column list dynamically
            columns = [
                'no_dvd', 'department_id', 'sheet_type',
                'col_a', 'col_b', 'col_c', 'col_d', 'col_e', 'col_f',
                'col_g', 'col_h', 'col_i', 'col_j', 'col_k', 'col_l',
                'col_m', 'col_n', 'col_o', 'col_p',
                'col_q', 'col_r', 'handler_id', 'col_t', 'col_u',
                'is_completed', 'col_w', 'col_x', 'needs_jp_support',
                'source_file', 'skip_cells'
            ]
            
            values = [record.get(col) for col in columns]
            placeholders = ', '.join(['?' for _ in columns])
            columns_str = ', '.join(columns)
            
            # Create update clause for ON CONFLICT
            update_cols = [c for c in columns if c not in ['no_dvd', 'sheet_type', 'department_id']]
            update_clause = ', '.join([f"{c} = excluded.{c}" for c in update_cols])
            
            sql = f"""
                INSERT INTO error_records ({columns_str}, updated_at)
                VALUES ({placeholders}, CURRENT_TIMESTAMP)
                ON CONFLICT(no_dvd, sheet_type, department_id)
                DO UPDATE SET {update_clause}, updated_at = CURRENT_TIMESTAMP
            """
            
            cursor = conn.execute(sql, values)
            return cursor.lastrowid
    
    def get_error_records(
        self,
        department_id: int = None,
        sheet_type: str = None,
        pending_only: bool = False,
        jp_support_only: bool = False,
        backed_up: bool = False
    ) -> List[Dict]:
        """Get error records with filters."""
        with self.get_connection() as conn:
            query = "SELECT * FROM error_records WHERE is_backed_up = ?"
            params: List[Any] = [1 if backed_up else 0]
            
            if department_id:
                query += " AND department_id = ?"
                params.append(department_id)
            
            if sheet_type:
                query += " AND sheet_type = ?"
                params.append(sheet_type)
            
            if pending_only:
                query += " AND (is_completed = '' OR is_completed IS NULL)"
            
            if jp_support_only:
                query += " AND LOWER(needs_jp_support) = 'o'"
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_records_by_handler(self, handler_id: int) -> List[Dict]:
        """Get all pending records for a specific handler."""
        with self.get_connection() as conn:
            query = """
                SELECT * FROM error_records 
                WHERE handler_id = ? 
                AND (is_completed IS NULL OR is_completed = '')
                ORDER BY created_at DESC
            """
            cursor = conn.execute(query, (handler_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    
    def update_error_field(self, record_id: int, field: str, value: Any):
        """Update a specific field of an error record."""
        allowed_fields = [
            'col_n', 'handler_id', 'is_completed', 'needs_jp_support',
            'col_q', 'col_r', 'col_t', 'col_u', 'col_w', 'col_x'
        ]
        if field not in allowed_fields:
            raise ValueError(f"Field '{field}' is not updatable")
        
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE error_records SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, record_id)
            )
    

    def delete_error_records(self, record_ids: List[int]) -> int:
        """Delete multiple error records by ID. Returns number of deleted rows."""
        if not record_ids:
            return 0
            
        with self.get_connection() as conn:
            try:
                # Prepare placeholder string ?,?,?
                placeholders = ",".join("?" * len(record_ids))
                query = f"DELETE FROM error_records WHERE id IN ({placeholders})"
                
                cursor = conn.execute(query, record_ids)
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} records.")
                return deleted_count
            except sqlite3.Error as e:
                logger.error(f"Error deleting records: {e}")
                return 0

    def mark_as_backed_up(self, record_ids: List[int]):
        """Mark records as backed up."""
        with self.get_connection() as conn:
            placeholders = ', '.join(['?' for _ in record_ids])
            conn.execute(
                f"UPDATE error_records SET is_backed_up = 1 WHERE id IN ({placeholders})",
                record_ids
            )
    
    def search_backup(
        self,
        keyword: str = None,
        machine_type: str = None
    ) -> List[Dict]:
        """Search in backed up records."""
        with self.get_connection() as conn:
            query = "SELECT * FROM error_records WHERE is_backed_up = 1"
            params: List[Any] = []
            
            if keyword:
                query += " AND (col_g LIKE ? OR col_h LIKE ?)"
                like_pattern = f"%{keyword}%"
                params.extend([like_pattern, like_pattern])
            
            if machine_type:
                query += " AND col_c LIKE ?"
                params.append(f"%{machine_type}%")
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self, department_id: int = None) -> Dict[str, Any]:
        """Get error statistics grouped by machine type."""
        with self.get_connection() as conn:
            base_query = """
                SELECT 
                    col_c as machine_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_completed = '' OR is_completed IS NULL THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN LOWER(is_completed) = 'o' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN LOWER(needs_jp_support) = 'o' THEN 1 ELSE 0 END) as needs_jp
                FROM error_records
                WHERE is_backed_up = 0
            """
            params: List[Any] = []
            
            if department_id:
                base_query += " AND department_id = ?"
                params.append(department_id)
            
            base_query += " GROUP BY col_c"
            
            cursor = conn.execute(base_query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            return {
                "by_machine": results,
                "total": sum(r['total'] for r in results),
                "total_pending": sum(r['pending'] for r in results),
                "total_completed": sum(r['completed'] for r in results),
                "total_needs_jp": sum(r['needs_jp'] for r in results)
            }
    



    def get_dashboard_stats(self, department_id: int = None, date_from: str = None, date_to: str = None) -> dict:
        """Get comprehensive stats for dashboard charts (Phase 6.2)."""
        with self.get_connection() as conn:
            filters = ["is_backed_up = 0"]
            params = []
            if department_id:
                filters.append("department_id = ?")
                params.append(department_id)
            if date_from:
                filters.append("created_at >= ?")
                params.append(date_from)
            if date_to:
                filters.append("created_at <= ?")
                params.append(date_to)
            
            where_clause = " WHERE " + " AND ".join(filters)
            
            query_totals = f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_completed = '' OR is_completed IS NULL THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN LOWER(is_completed) = 'o' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN LOWER(needs_jp_support) = 'o' THEN 1 ELSE 0 END) as needs_jp
                FROM error_records
                {where_clause}
            """
            row = conn.execute(query_totals, params).fetchone()
            summary = dict(row) if row else {"total": 0, "pending": 0, "completed": 0, "needs_jp": 0}
            
            query_machines = f"""
                SELECT col_c as machine_type, COUNT(*) as count
                FROM error_records
                {where_clause}
                GROUP BY col_c
                ORDER BY count DESC
                LIMIT 5
            """
            top_machines = [dict(r) for r in conn.execute(query_machines, params).fetchall()]
            
            query_trend = f"""
                SELECT strftime('%Y-%m-%d', created_at) as date, COUNT(*) as count
                FROM error_records
                {where_clause}
                GROUP BY date
                ORDER BY date ASC
            """
            trend = [dict(r) for r in conn.execute(query_trend, params).fetchall()]
            
            return {
                "summary": summary,
                "top_machines": top_machines,
                "trend": trend,
                "total_pending": summary.get('pending', 0)
            }

    # =========================================================================
    # SYNC LOG OPERATIONS
    # =========================================================================
    
    def add_sync_log(self, start_time: datetime, end_time: datetime, status: str, results: dict, message: str = ""):
        """Add a new sync log entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO sync_logs (start_time, end_time, status, results, message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                start_time.isoformat(),
                end_time.isoformat(),
                status,
                json.dumps(results, ensure_ascii=False),
                message
            ))

    def get_sync_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent sync logs."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sync_logs ORDER BY start_time DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # EMAIL LOG OPERATIONS
    # =========================================================================

    def log_email_sent(self, no_dvd: str, email: str, status: str, error: str = ""):
        """Log an email sending attempt."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO email_logs (no_dvd, recipient_email, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (no_dvd, email, status, error))

    def has_email_been_sent(self, no_dvd: str, email: str) -> bool:
        """Check if an email has already been successfully sent for this record."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id FROM email_logs 
                WHERE no_dvd = ? AND recipient_email = ? AND status = 'Sent'
            """, (no_dvd, email)).fetchone()
            return row is not None

    def get_new_records_to_notify(self, after_time: datetime) -> List[Dict]:
        """Get records added after a certain time that have a handler assigned."""
        # SQLite CURRENT_TIMESTAMP is UTC, ensure after_time is also UTC
        if after_time.tzinfo is None:
            # Assume local if no tz, convert to UTC
            # For simplicity in this env, we can just use the provided time 
            # but ideally we should be consistent.
            pass
            
        with self.get_connection() as conn:
            # Querying with >= string comparison on ISO format
            cursor = conn.execute("""
                SELECT e.*, h.name as handler_name, h.email as handler_email 
                FROM error_records e
                JOIN handlers h ON e.handler_id = h.id
                WHERE e.created_at >= ? AND h.email IS NOT NULL AND h.email != ''
            """, (after_time.strftime('%Y-%m-%d %H:%M:%S'),))
            return [dict(row) for row in cursor.fetchall()]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics for the dashboard."""
        stats = {
            'total': 0,
            'pending': 0,
            'completed': 0,
            'jp_support': 0,
            'by_machine': {},
            'by_dept': {}
        }
        
        with self.get_connection() as conn:
            # 1. KPI Counts
            # Total
            stats['total'] = conn.execute("SELECT COUNT(*) FROM error_records").fetchone()[0]
            # Completed (is_completed = 'o')
            stats['completed'] = conn.execute(
                "SELECT COUNT(*) FROM error_records WHERE LOWER(is_completed) = 'o'"
            ).fetchone()[0]
            # JP Support (needs_jp_support = 'o')
            stats['jp_support'] = conn.execute(
                "SELECT COUNT(*) FROM error_records WHERE LOWER(needs_jp_support) = 'o'"
            ).fetchone()[0]
            # Pending (not completed)
            stats['pending'] = stats['total'] - stats['completed']
            
            # 2. By Machine Type (col_c)
            cursor = conn.execute(
                "SELECT col_c, COUNT(*) as count FROM error_records GROUP BY col_c"
            )
            stats['by_machine'] = {row['col_c'] or 'Unknown': row['count'] for row in cursor.fetchall()}
            
            # 3. By Department (via department_id)
            cursor = conn.execute("""
                SELECT d.name, COUNT(e.id) as count 
                FROM error_records e 
                JOIN departments d ON e.department_id = d.id 
                GROUP BY d.name
            """)
            stats['by_dept'] = {row['name']: row['count'] for row in cursor.fetchall()}
            
        return stats


# Factory function
_db_instance: Optional[DatabaseManager] = None

def get_database(db_path: Path = None) -> DatabaseManager:
    """Get or create database manager instance."""
    global _db_instance
    if _db_instance is None:
        if db_path is None:
            from utils.config import config
            db_path = config.db_path
        _db_instance = DatabaseManager(db_path)
    return _db_instance
