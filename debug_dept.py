
import sqlite3
import json
import io

try:
    conn = sqlite3.connect('C:/ProgramData/Sandbox/kdtps-error-manager/data/kdtps.db')
    cursor = conn.execute('SELECT * FROM departments')
    rows = [list(row) for row in cursor.fetchall()]
    
    with io.open('dept_dump.txt', 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        
    print("Dump successful")
except Exception as e:
    print(f"Dump failed: {e}")
