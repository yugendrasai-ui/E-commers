import sqlite3

def update_watch_price():
    conn = sqlite3.connect('ecommerce.db')
    cursor = conn.cursor()
    # Update price for product ID 12
    cursor.execute("UPDATE products SET price = 1.00 WHERE product_id = 12;")
    conn.commit()
    print("Price updated successfully to 1.00 rupee for product ID 12.")
    conn.close()

if __name__ == "__main__":
    update_watch_price()
