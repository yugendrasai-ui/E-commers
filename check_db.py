import sqlite3
import config

conn = sqlite3.connect(config.DB_PATH)
c = conn.cursor()

print("=== TABLES ===")
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(c.fetchall())

print("\n=== admin columns ===")
c.execute("PRAGMA table_info(admin)")
for row in c.fetchall():
    print(row)

print("\n=== users columns ===")
c.execute("PRAGMA table_info(users)")
for row in c.fetchall():
    print(row)

print("\n=== products columns ===")
c.execute("PRAGMA table_info(products)")
for row in c.fetchall():
    print(row)

conn.close()
