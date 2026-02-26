"""
Verification script for Email Notification System.
Tests EmailService and Database tracking.
"""
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from core.email_service import EmailService
from core.database import get_database

def test_database_logging():
    print("\nTesting Database Logging...")
    db = get_database()
    
    no_dvd = "TEST-NO-001"
    email = "test@example.com"
    
    print(f"Logging email for {no_dvd}...")
    db.log_email_sent(no_dvd, email, "Sent")
    
    sent = db.has_email_been_sent(no_dvd, email)
    print(f"Has email been sent? {sent}")
    
    # Test auto notification query
    print("\nTesting get_new_records_to_notify...")
    with db.get_connection() as conn:
        # Check if test handler exists
        cursor = conn.execute("SELECT id FROM handlers WHERE name = 'Tester-Email' LIMIT 1")
        handler = cursor.fetchone()
        if not handler:
            conn.execute("INSERT INTO handlers (name, email) VALUES ('Tester-Email', 'tester@example.com')")
            handler_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            handler_id = handler[0]

        # Use a dummy dept
        dept = conn.execute("SELECT id FROM departments LIMIT 1").fetchone()
        if dept:
            dept_id = dept[0]
            test_no = f"AUTO-TEST-{datetime.now().strftime('%H%M%S')}"
            conn.execute("""
                INSERT INTO error_records (no_dvd, department_id, handler_id, col_c, col_d, col_g)
                VALUES (?, ?, ?, 'MOCK-MACHINE', 'MOCK-LINE', 'MOCK-CODE')
            """, (test_no, dept_id, handler_id))
            print(f"Added mock record {test_no} with handler_id {handler_id} for auto-notification test.")
    
    # Check if detected using UTC
    ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)
    new_records = db.get_new_records_to_notify(ten_seconds_ago)
    print(f"Found {len(new_records)} new records to notify.")
    for r in new_records:
        print(f" - {r['no_dvd']} (Handler: {r['handler_name']} <{r['handler_email']}>)")

if __name__ == "__main__":
    try:
        test_database_logging()
    except Exception as e:
        print(f"Error: {e}")
