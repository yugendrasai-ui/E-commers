import sqlite3

def find_watch():
    conn = sqlite3.connect('ecommerce.db')
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, name, price FROM products WHERE name LIKE '%watch%';")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Price: {row[2]}")
    conn.close()

if __name__ == "__main__":
    find_watch()
