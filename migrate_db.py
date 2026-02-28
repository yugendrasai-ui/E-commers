import sqlite3
import config

conn = sqlite3.connect(config.DB_PATH)
c = conn.cursor()

# Add is_seen to admin table if it doesn't exist
try:
    c.execute("ALTER TABLE admin ADD COLUMN is_seen INTEGER DEFAULT 0")
    print("Added is_seen column to admin table.")
except Exception as e:
    print(f"(admin.is_seen already exists or error: {e})")

conn.commit()
conn.close()
print("Done.")
