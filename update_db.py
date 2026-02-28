import sqlite3
import config

def update_schema():
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Add status to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        print("Added status to users")
    except Exception as e:
        print(f"Users status already exists or error: {e}")

    # Add status to admin
    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN status TEXT DEFAULT 'active'")
        print("Added status to admin")
    except Exception as e:
        print(f"Admin status already exists or error: {e}")

    # Add stock to products
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 10")
        print("Added stock to products")
    except Exception as e:
        print(f"Products stock already exists or error: {e}")

    # Add address to orders
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN address TEXT")
        print("Added address to orders")
    except Exception as e:
        print(f"Orders address already exists or error: {e}")

    # Add is_seen to order_items for merchant notifications
    try:
        cursor.execute("ALTER TABLE order_items ADD COLUMN is_seen INTEGER DEFAULT 0")
        print("Added is_seen to order_items")
    except Exception as e:
        print(f"OrderItems is_seen already exists or error: {e}")

    # Create feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        merchant_id INTEGER,
        rating INTEGER,
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id),
        FOREIGN KEY (merchant_id) REFERENCES admin (admin_id)
    )
    ''')
    print("Feedback table created or verified")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_schema()
