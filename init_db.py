import sqlite3
import config

def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        status TEXT DEFAULT 'active'
    )
    ''')

    # Create admin table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'seller',
        status TEXT DEFAULT 'pending',
        is_seen INTEGER DEFAULT 0
    )
    ''')

    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        price REAL,
        image TEXT,
        admin_id INTEGER,
        stock INTEGER DEFAULT 10,
        FOREIGN KEY (admin_id) REFERENCES admin (admin_id)
    )
    ''')

    # Create orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        amount REAL,
        payment_status TEXT,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # Create order_items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    )
    ''')

    # --- Migration: Add missing columns to existing tables ---
    tables_to_check = {
        "users": [("status", "TEXT DEFAULT 'active'")],
        "products": [("stock", "INTEGER DEFAULT 10")],
        "orders": [("address", "TEXT")],
        "admin": [("status", "TEXT DEFAULT 'pending'"), ("is_seen", "INTEGER DEFAULT 0")]
    }


    for table, columns in tables_to_check.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [col[1] for col in cursor.fetchall()]
        for col_name, col_def in columns:
            if col_name not in existing_columns:
                print(f"Adding column {col_name} to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

    conn.commit()


    # Seed initial data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        import bcrypt
        # Create a default merchant
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO admin (name, email, password, role) VALUES (?, ?, ?, ?)",
                       ("Test Merchant", "merchant@example.com", hashed_password, "seller"))
        merchant_id = cursor.lastrowid

        # Create sample products
        sample_products = [
            ("iPhone 16", "Latest Apple iPhone", "Electronics", 79999.00, "Iphone16.jpg", merchant_id),
            ("Laptop", "High performance laptop", "Electronics", 55000.00, "Laptop.jpg", merchant_id),
            ("Watch", "Stylish smart watch", "Accessories", 2500.00, "Watch.jpg", merchant_id),
            ("Shoe", "Comfortable running shoes", "Fashion", 1500.00, "Shoe.jpg", merchant_id),
            ("TV", "4K Ultra HD Smart TV", "Electronics", 35000.00, "TV.jpg", merchant_id),
            ("Mixer", "Powerful kitchen mixer", "Home", 2500.00, "mixer.jpg", merchant_id),
            ("Cotton T-Shirt", "100% Pure cotton t-shirt", "Fashion", 500.00, "Mens_Cotton_T-Shirt.webp", merchant_id),
            ("Pants", "Casual comfortable pants", "Fashion", 1200.00, "pant.jpg", merchant_id),
            ("Wireless Buds", "Noise-cancelling earbuds", "Electronics", 3000.00, "buds.webp", merchant_id),
            ("iPhone 15", "Premium Apple iPhone", "Electronics", 65000.00, "i_phone_15.webp", merchant_id)
        ]
        cursor.executemany("INSERT INTO products (name, description, category, price, image, admin_id) VALUES (?, ?, ?, ?, ?, ?)",
                          sample_products)
        print("Seed data added successfully.")
        conn.commit()

    conn.close()
    print(f"Database initialized at {config.DB_PATH}")


if __name__ == "__main__":
    init_db()
