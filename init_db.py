import config
import os

def init_db():
    # Helper to determine identity column syntax
    is_postgres = getattr(config, 'DB_TYPE', 'sqlite') == 'postgres'
    id_type = "SERIAL" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    placeholder = "%s" if is_postgres else "?"
    
    # We use a simplified connection here to avoid dependency loops if possible,
    # but since app.py is already there, we can import it.
    from app import get_db_connection, execute_query
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS users (
        user_id {id_type if not is_postgres else "SERIAL PRIMARY KEY"},
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        status TEXT DEFAULT 'active'
    )
    ''')
    if not is_postgres: # SQLite specific check because it doesn't handle SERIAL PRIMARY KEY the same way in CREATE
         pass # Handled by id_type above

    # 2. Admin Table
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS admin (
        admin_id {id_type if not is_postgres else "SERIAL PRIMARY KEY"},
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'seller',
        status TEXT DEFAULT 'pending',
        is_seen INTEGER DEFAULT 0
    )
    ''')

    # 3. Products Table
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS products (
        product_id {id_type if not is_postgres else "SERIAL PRIMARY KEY"},
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

    # 4. Orders Table
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS orders (
        order_id {id_type if not is_postgres else "SERIAL PRIMARY KEY"},
        user_id INTEGER,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        amount REAL,
        payment_status TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # 5. Order Items Table
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id {id_type if not is_postgres else "SERIAL PRIMARY KEY"},
        order_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        price REAL,
        is_seen INTEGER DEFAULT 0,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    )
    ''')

    # --- Migration Logic ---
    tables_to_check = {
        "users": [("status", "TEXT DEFAULT 'active'")],
        "products": [("stock", "INTEGER DEFAULT 10")],
        "orders": [("address", "TEXT")],
        "admin": [("status", "TEXT DEFAULT 'pending'"), ("is_seen", "INTEGER DEFAULT 0")],
        "order_items": [("is_seen", "INTEGER DEFAULT 0")]
    }

    if not is_postgres:
        for table, columns in tables_to_check.items():
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [col[1] for col in cursor.fetchall()]
            for col_name, col_def in columns:
                if col_name not in existing_columns:
                    print(f"Adding column {col_name} to {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
    else:
        # Postgres migration check
        for table, columns in tables_to_check.items():
            for col_name, col_def in columns:
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col_name}'")
                if not cursor.fetchone():
                    print(f"Adding column {col_name} to {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

    conn.commit()

    # Seed initial data
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        import bcrypt
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        insert_admin_query = f"INSERT INTO admin (name, email, password, role, status) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"
        cursor.execute(insert_admin_query, ("Test Merchant", "merchant@example.com", hashed_password, "seller", "active"))
        
        # Get last inserted ID
        if is_postgres:
            cursor.execute("SELECT lastval()")
            merchant_id = cursor.fetchone()[0]
        else:
            merchant_id = cursor.lastrowid

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
        
        for p in sample_products:
            insert_prod_query = f"INSERT INTO products (name, description, category, price, image, admin_id) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"
            cursor.execute(insert_prod_query, p)
            
        print("Seed data added successfully.")
        conn.commit()

    conn.close()
    print(f"Database initialized.")

if __name__ == "__main__":
    init_db()

