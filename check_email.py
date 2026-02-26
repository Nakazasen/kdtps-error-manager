
import sqlite3
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_email():
    conn = sqlite3.connect('data/kdtps.db')
    cur = conn.cursor()
    
    # Check specifically for "Vinh PTHTCT"
    cur.execute("SELECT name, email FROM handlers WHERE name LIKE ?", ('%Vinh PTHTCT%',))
    row = cur.fetchone()
    if row:
        print(f"FOUND: Name={row[0]}, Email={row[1]}")
    else:
        # List some handlers to see data
        print("Vinh PTHTCT not found. Listing last 5 handlers:")
        cur.execute("SELECT name, email FROM handlers ORDER BY id DESC LIMIT 5")
        for r in cur.fetchall():
            print(f"Name={r[0]}, Email={r[1]}")
            
    conn.close()

if __name__ == "__main__":
    check_email()
