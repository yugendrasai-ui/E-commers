import sqlite3
import config

try:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, name, price FROM products")
    products = cursor.fetchall()
    for p in products:
        print(f"ID: {p['product_id']} | Name: {p['name']} | Price: {p['price']}")
    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
