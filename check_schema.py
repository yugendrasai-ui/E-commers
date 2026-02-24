import sqlite3
import config

def check_schema():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Admin Table ---")
    cursor.execute("PRAGMA table_info(admin)")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Products Table ---")
    cursor.execute("PRAGMA table_info(products)")
    for row in cursor.fetchall():
        print(row)

        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
