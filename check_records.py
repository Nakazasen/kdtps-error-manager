
import sqlite3
import sys
import io
import json

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_records():
    conn = sqlite3.connect('data/kdtps.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    nos = ['4015', '4090', '4110']
    for no in nos:
        print(f"--- Record {no} ---")
        cur.execute("SELECT * FROM error_records WHERE no_dvd = ?", (no,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            # Print only relevant columns to avoid encoding issues with JP text if possible
            # or just print everything and let handle it
            for k, v in d.items():
                print(f"{k}: {v}")
        else:
            print("Not found")
        print()
            
    conn.close()

if __name__ == "__main__":
    check_records()
