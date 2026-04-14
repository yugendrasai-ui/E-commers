from flask import Flask, app, render_template, request, redirect, session, flash, make_response
from flask_mail import Mail, Message
import sqlite3

import bcrypt
import random
import config
import os
import razorpay
import traceback
from werkzeug.utils import secure_filename
from utils.pdf_generator import generate_pdf
from auth_utils import send_otp



# db connection function
def get_db_connection():
    """
    This function creates and returns 
    a connection to the SQLite database.
    """
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


app=Flask(__name__)

app.secret_key = config.SECRET_KEY
# ---------------- EMAIL CONFIGURATION ----------------
app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_USERNAME

mail = Mail(app)

# Custom Jinja filter for date formatting (SQLite returns strings for dates)
@app.template_filter('strftime')
def strftime_filter(date_str, format='%b %d, %Y'):
    if not date_str:
        return ""
    if isinstance(date_str, str):
        try:
            from datetime import datetime
            # Handle standard SQLite timestamp format
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime(format)
        except Exception:
            return date_str
    return date_str.strftime(format)


from forgot_password import forgot_pw
app.register_blueprint(forgot_pw)



#--------------------------------------Payment------------------------------------------
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))


# ------------------- IMAGE UPLOAD PATH -------------------
UPLOAD_FOLDER = 'static/uploads/product_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------------------------------------------------
# ROUTE 1: ADMIN SIGNUP (SEND OTP)
# ROUTE 1: MERCHANT SIGNUP (SEND OTP)
# ---------------------------------------------------------
@app.route('/merchant-signup', methods=['GET', 'POST'])
def merchant_signup():

    # If already logged in, redirect to merchant dashboard
    if 'merchant_id' in session:
        return redirect('/merchant/dashboard')

    # Show form
    if request.method == "GET":
        return render_template("merchant/signup.html")

    # POST → Process signup
    name = request.form['name']
    email = request.form['email']

    # 1️⃣ Check if merchant email already exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id FROM admin WHERE email=?", (email,))
    existing_admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if existing_admin:
        flash("This email is already registered. Please login instead.", "danger")
        return redirect('/merchant-signup')

    # 2️⃣ Save user input temporarily in session
    session['signup_name'] = name
    session['signup_email'] = email
    session['signup_role'] = 'merchant'

    # 3️⃣ Generate OTP and store in session
    otp = random.randint(100000, 999999)
    session['otp'] = otp

    # 4️⃣ Send OTP Email
    subject = "Express-Kart Merchant OTP"
    body = "Your OTP for Express-Kart Merchant Registration is: {otp}"

    if send_otp(mail, email, subject, body):
        flash("OTP sent to your email!", "success")
        return redirect('/verify-otp')
    else:
        flash("Failed to send OTP. Please check your email or try again.", "danger")
        return redirect('/merchant-signup')



# ---------------------------------------------------------
# ROUTE 2: DISPLAY OTP PAGE
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['GET'])
def verify_otp_get():
    return render_template("merchant/verify_otp.html")




# ---------------------------------------------------------
# ROUTE 3: VERIFY OTP + SAVE MERCHANT
# ---------------------------------------------------------
@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    
    # User submitted OTP + Password
    user_otp = request.form['otp']
    password = request.form['password']

    # Compare OTP
    if str(session.get('otp')) != str(user_otp):
        flash("Invalid OTP. Try again!", "danger")
        return redirect('/verify-otp')

    # Hash password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert into database based on session role
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session.get('signup_role') == 'user':
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (session['signup_name'], session['signup_email'], hashed_password)
        )
        msg = "Account Registered Successfully! Please Login."
        redirect_url = '/user-login'
    else:
        cursor.execute(
            "INSERT INTO admin (name, email, password, status, is_seen) VALUES (?, ?, ?, ?, ?)",
            (session['signup_name'], session['signup_email'], hashed_password, 'pending', 0)
        )
        msg = "Merchant Registered Successfully! Please wait for Super Admin approval."
        redirect_url = '/merchant-login'
        
    conn.commit()
    cursor.close()
    conn.close()

    # Clear temporary session data
    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)
    session.pop('signup_role', None)

    flash(msg, "success")
    return redirect(redirect_url)



# ---------------------------------------------------------
# ROUTE: RESEND OTP
# ---------------------------------------------------------
@app.route('/resend-otp')
def resend_otp():
    email = session.get('signup_email')
    role = session.get('signup_role')

    if not email:
        flash("Session expired. Please register again.", "danger")
        if role == 'user':
            return redirect('/user-register')
        return redirect('/merchant-signup')

    otp = random.randint(100000, 999999)
    session['otp'] = otp

    subject = "Express-Kart Registration OTP (Resend)"
    body = "Your NEW OTP for Express-Kart Registration is: {otp}"

    if send_otp(mail, email, subject, body):
        flash("A new OTP has been sent to your email.", "success")
    else:
        flash("Failed to resend OTP. Please check your email or try again.", "danger")

    return redirect('/verify-otp')



# =================================================================
# ACCESS CONTROL HELPER
# Centralised check: allow merchant (merchant_id) OR super admin (super_id)
# =================================================================
def merchant_or_admin_required():
    """
    Returns None if the caller is allowed to proceed.
    Returns a redirect Response if they are not authenticated.
    Rule: super_id  → always allowed (super admin can access all merchant routes)
          merchant_id → allowed (regular seller)
          neither    → redirect to merchant login
    """
    if 'super_id' in session or 'merchant_id' in session:
        return None  # Access granted
    flash("Please login to continue!", "danger")
    return redirect('/merchant-login')


# =================================================================
# ROUTE 4: MERCHANT LOGIN PAGE (GET + POST)
# =================================================================
@app.route('/merchant-login', methods=['GET', 'POST'])
def merchant_login():

    # If already logged in as merchant, redirect
    if 'merchant_id' in session:
        return redirect('/merchant/dashboard')
    # If already logged in as super admin - super admin is NOT a merchant, don't redirect here

    # Show login page
    if request.method == 'GET':
        return render_template("merchant/login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 0: Super Admin credentials are handled on a SEPARATE SECURE route.
    # Do NOT allow super admin login from this route for security.

    # Step 1: Check if merchant email exists in DB for regular sellers
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE email=?", (email,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin is None:
        flash("Email not found! Please register first.", "danger")
        return redirect('/merchant-login')

    # Step 2: Compare entered password with hashed password
    stored_hashed_password = admin['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):

        flash("Incorrect password! Try again.", "danger")
        return redirect('/merchant-login')

    if admin['status'] == 'blocked':
        flash("Your account has been blocked by the Super Admin.", "danger")
        return redirect('/merchant-login')

    if admin['status'] == 'pending':
        flash("Your account is currently pending approval from the Super Admin. Please check back later.", "warning")
        return redirect('/merchant-login')

    # Step 5: If login success → Create merchant session (do NOT affect super_id)
    session['merchant_id'] = admin['admin_id']
    session['merchant_name'] = admin['name']
    session['merchant_email'] = admin['email']
    session['merchant_role'] = 'seller'
    # NOTE: We do NOT clear super_id here to allow separate tab sessions

    flash("Login Successful!", "success")
    return redirect('/merchant/dashboard')

# =================================================================
# SECURE SUPER ADMIN LOGIN (HIDDEN ROUTE - NOT LINKED ANYWHERE)
# Only the website owner should know this URL.
# =================================================================

# Simple in-memory brute-force tracker {ip: [fail_count, lockout_until]}
_admin_failed_attempts = {}

@app.route('/admin-secure-access-xk9', methods=['GET', 'POST'])
def super_admin_login():
    import time

    # If already logged in as super admin, go to dashboard
    if 'super_id' in session:
        return redirect('/super-admin/dashboard')

    ip = request.remote_addr
    now = time.time()

    # --- Brute-force protection ---
    record = _admin_failed_attempts.get(ip, [0, 0])
    fail_count, locked_until = record

    if locked_until > now:
        remaining = int((locked_until - now) / 60) + 1
        return f"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#111;color:#fff;">
        <h2>Access Temporarily Blocked</h2>
        <p>Too many failed attempts. Try again in <strong>{remaining} minute(s)</strong>.</p>
        </body></html>
        """, 429

    if request.method == 'GET':
        return render_template('super_admin/login.html')

    # POST - validate credentials
    email = request.form.get('email', '')
    password = request.form.get('password', '')

    if email == config.SUPER_ADMIN_EMAIL and password == config.SUPER_ADMIN_PASSWORD:
        # SUCCESS - reset fail counter and set super session ONLY
        _admin_failed_attempts[ip] = [0, 0]
        session['super_id']    = 0
        session['super_name']  = 'Platform Super Admin'
        session['super_email'] = 'admin@123'
        session['super_role']  = 'super_admin'
        # NOTE: We do NOT touch merchant_id - sessions are fully independent
        flash("Welcome, Super Admin!", "success")
        return redirect('/super-admin/dashboard')
    else:
        # FAIL - increment counter
        fail_count += 1
        lockout = now + 15 * 60 if fail_count >= 5 else 0  # 15-min lockout after 5 fails
        _admin_failed_attempts[ip] = [fail_count, lockout]
        remaining_attempts = max(0, 5 - fail_count)
        flash(f"Invalid credentials. {remaining_attempts} attempt(s) remaining before lockout.", "danger")
        return redirect('/admin-secure-access-xk9')


# =================================================================
# ROUTE 5: MERCHANT DASHBOARD (PROTECTED ROUTE)
# =================================================================
@app.route('/merchant/dashboard')
def merchant_dashboard():
    # Only logged-in merchant can access
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    # Super admin gets their own dashboard; redirect them there
    if 'merchant_id' not in session and 'super_id' in session:
        return redirect('/super-admin/dashboard')

    admin_id = session['merchant_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total Products
    cursor.execute("SELECT COUNT(*) FROM products WHERE admin_id = ?", (admin_id,))
    total_products = cursor.fetchone()[0]

    # 2. Total Orders & Revenue
    cursor.execute("""
        SELECT COUNT(DISTINCT oi.order_id), SUM(oi.price * oi.quantity)
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.admin_id = ?
    """, (admin_id,))
    row = cursor.fetchone()
    total_orders = row[0] or 0
    total_revenue = row[1] or 0
    
    # 3. Profit Gain (Assuming 20% margin as per cart logic)
    total_profit = round(total_revenue * 0.2, 2)

    # 4. Products in Stock
    cursor.execute("SELECT SUM(stock) FROM products WHERE admin_id = ?", (admin_id,))
    total_stock = cursor.fetchone()[0] or 0

    # 5. Recent Orders
    cursor.execute("""
        SELECT o.*, u.name as customer_name
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN users u ON o.user_id = u.user_id
        WHERE p.admin_id = ?
        GROUP BY o.order_id
        ORDER BY o.created_at DESC LIMIT 5
    """, (admin_id,))
    recent_orders = cursor.fetchall()

    # Data for Charts
    # Bar Chart: Sales per Category
    cursor.execute("""
        SELECT p.category, SUM(oi.quantity) as total_sold
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.admin_id = ?
        GROUP BY p.category
    """, (admin_id,))
    sales_data = cursor.fetchall()
    categories = [row['category'] for row in sales_data]
    sold_counts = [row['total_sold'] for row in sales_data]

    # Pie Chart: Revenue per Category
    cursor.execute("""
        SELECT p.category, SUM(oi.price * oi.quantity) as revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE p.admin_id = ?
        GROUP BY p.category
    """, (admin_id,))
    revenue_data = cursor.fetchall()
    revenue_labels = [row['category'] for row in revenue_data]
    revenue_values = [row['revenue'] for row in revenue_data]

    # 6. Notifications (Unseen Order Items)
    cursor.execute("""
        SELECT oi.*, p.name as product_name, o.created_at, u.name as customer_name
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        JOIN users u ON o.user_id = u.user_id
        WHERE p.admin_id = ? AND oi.is_seen = 0
        ORDER BY o.created_at DESC
    """, (admin_id,))
    notifications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("merchant/dashboard.html", 
                           total_products=total_products,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           total_profit=total_profit,
                           total_stock=total_stock,
                           recent_orders=recent_orders,
                           categories=categories,
                           sold_counts=sold_counts,
                           revenue_labels=revenue_labels,
                           revenue_values=revenue_values,
                           notifications=notifications)

@app.route('/merchant/mark-seen/<int:item_id>')
def mark_order_item_seen(item_id):
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE order_items SET is_seen = 1 WHERE item_id = ?", (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/merchant/dashboard')


@app.route('/merchant/orders')
def merchant_orders():
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    admin_id = session['merchant_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all orders related to this merchant's products
    cursor.execute("""
        SELECT o.*, u.name as customer_name
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN users u ON o.user_id = u.user_id
        WHERE p.admin_id = ?
        GROUP BY o.order_id
        ORDER BY o.created_at DESC
    """, (admin_id,))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("merchant/orders.html", orders=orders)


# =================================================================
# ROUTE 6: ADMIN LOGOUT
# =================================================================
@app.route('/merchant-logout')
def admin_logout():
    # Clear merchant session
    session.pop('merchant_id', None)
    session.pop('merchant_name', None)
    session.pop('merchant_email', None)
    session.pop('merchant_role', None)

    flash("Logged out successfully.", "success")
    return redirect('/merchant-login')

# =================================================================
# MERCHANT PROFILE & DELETE ACCOUNT
# =================================================================
@app.route('/merchant/profile')
def merchant_profile():
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE admin_id = ?", (session['merchant_id'],))
    merchant = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template("merchant/profile.html", merchant=merchant)

@app.route('/merchant/delete-account', methods=['POST'])
def merchant_delete_account():
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check
    
    merchant_id = session['merchant_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete products and the merchant account
    cursor.execute("DELETE FROM products WHERE admin_id = ?", (merchant_id,))
    cursor.execute("DELETE FROM admin WHERE admin_id = ?", (merchant_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    session.clear()
    flash("Your merchant account has been deleted successfully.", "success")
    return redirect('/merchant-login')



# =================================================================
# ROUTE 1: SHOW ADD PRODUCT PAGE (Protected Route)
# =================================================================
@app.route('/merchant/add-item', methods=['GET'])
def add_item_page():

    # Only logged-in admin can access
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    admin_id = session['merchant_id']

    return render_template("merchant/add_item.html")



# =================================================================
# ROUTE 2: ADD PRODUCT INTO DATABASE
# =================================================================
@app.route('/merchant/add-item', methods=['POST'])
def add_item():

    # Check admin session
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    # 1️⃣ Get form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']
    stock = request.form.get('stock', 10) # Get stock from form, default to 10
    image_file = request.files['image']

    # 2️⃣ Validate image upload
    if image_file.filename == "":
        flash("Please upload a product image!", "danger")
        return redirect('/merchant/add-item')

    # 3️⃣ Secure the file name
    filename = secure_filename(image_file.filename)

    # 4️⃣ Create full path
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 5️⃣ Save image into folder
    image_file.save(image_path)

    # 6️⃣ Insert product into database
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO products (name, description, category, price, image, admin_id, stock) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, description, category, price, filename, session['merchant_id'], stock)
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect('/merchant/add-item')


# =================================================================
# ROUTE 9: DISPLAY ALL PRODUCTS (Admin)
# =================================================================
@app.route('/merchant/item-list')
def item_list():

    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch category list for dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # 2️⃣ Build dynamic query based on filters
    # Multi-seller logic: Filter by admin_id unless super_admin
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    # ─── PRODUCT FILTER LOGIC ───────────────────────────────────────────
    # RULE: merchant_id ALWAYS takes priority.
    #   • If merchant_id in session  → ONLY show that merchant's products
    #   • Else if super_id in session → show ALL products (super admin view)
    #   • Otherwise                  → redirect to login (shouldn't reach here)
    # This prevents stale super_id cookies from leaking all products to merchants.
    if 'merchant_id' in session:
        # Merchant mode: strictly filter to their own products only
        query += " AND admin_id = ?"
        params.append(session['merchant_id'])
    # else: super admin only (super_id present, no merchant_id) → no extra filter → all products

    if search:
        query += " AND name LIKE ?"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "merchant/item_list.html",
        products=products,
        categories=categories
    )


# =================================================================
# DELETE PRODUCT (DELETE DB ROW + DELETE IMAGE FILE)
# =================================================================
@app.route('/merchant/delete-item/<int:item_id>')
def delete_item(item_id):

    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch product to get image name and owner
    cursor.execute("SELECT image, admin_id FROM products WHERE product_id=?", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/merchant/item-list')

    # Ownership check
    if 'merchant_id' in session and product['admin_id'] != session['merchant_id']:
        flash("You do not have permission to delete this product!", "danger")
        return redirect('/merchant/item-list')

    image_name = product['image']

    # Delete image from folder
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    if os.path.exists(image_path):
        os.remove(image_path)

    # 2️⃣ Delete product from DB
    cursor.execute("DELETE FROM products WHERE product_id=?", (item_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/merchant/item-list')


#=================================================================
# ROUTE 10: VIEW SINGLE PRODUCT DETAILS
# =================================================================
@app.route('/merchant/view-item/<int:item_id>')
def view_item(item_id):

    # Check admin session
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/merchant/item-list')

    # Ownership check
    if 'merchant_id' in session and product['admin_id'] != session['merchant_id']:
        flash("You do not have permission to view this product!", "danger")
        return redirect('/merchant/item-list')

    return render_template("merchant/view_item.html", product=product)

# =================================================================
# ROUTE 11: SHOW UPDATE FORM WITH EXISTING DATA
# =================================================================
@app.route('/merchant/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    # Security
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    admin_id = session['merchant_id']

    # Fetch product data
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/merchant/item-list')

    # Ownership check
    if 'merchant_id' in session and product['admin_id'] != session['merchant_id']:
        flash("You do not have permission to update this product!", "danger")
        return redirect('/merchant/item-list')

    return render_template("merchant/update_item.html", product=product)


# =================================================================
# ROUTE: UPDATE PRODUCT + OPTIONAL IMAGE REPLACE
# =================================================================
@app.route('/merchant/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    # 1️⃣ Get updated form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']
    stock = request.form.get('stock', 10)

    new_image = request.files['image']

    # 2️⃣ Fetch old product data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/merchant/item-list')

    # Ownership check
    if 'merchant_id' in session and product['admin_id'] != session['merchant_id']:
        flash("You do not have permission to update this product!", "danger")
        return redirect('/merchant/item-list')

    old_image_name = product['image']

    # 3️⃣ If admin uploaded a new image → replace it
    if new_image and new_image.filename != "":
        
        # Secure filename
        from werkzeug.utils import secure_filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        new_image_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        new_image.save(new_image_path)

        # Delete old image file
        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image_name)
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        final_image_name = new_filename

    else:
        # No new image uploaded → keep old one
        final_image_name = old_image_name

    # 4️⃣ Update product in the database
    cursor.execute("""
        UPDATE products
        SET name=?, description=?, category=?, price=?, image=?, stock=?
        WHERE product_id=?
    """, (name, description, category, price, final_image_name, stock, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect('/merchant/item-list')



# =================================================================
# ROUTE: USER REGISTRATION
# =================================================================
@app.route('/user-register', methods=['GET', 'POST'])
def user_register():

    if 'user_id' in session:
        return redirect('/')

    if request.method == 'GET':
        return render_template("user/user_register.html")

    name = request.form['name']
    email = request.form['email']

    # Check if user already exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash("Email already registered! Please login.", "danger")
        return redirect('/user-login')

    # Save user input temporarily in session
    session['signup_name'] = name
    session['signup_email'] = email
    session['signup_role'] = 'user' # To distinguish in verify-otp

    # Generate OTP and store in session
    otp = random.randint(100000, 999999)
    session['otp'] = otp

    # 4️⃣ Send OTP Email
    subject = "Express-Kart Registration OTP"
    body = "Your OTP for Express-Kart Account Registration is: {otp}"

    if send_otp(mail, email, subject, body):
        flash("OTP sent to your email!", "success")
        return redirect('/verify-otp')
    else:
        flash("Failed to send OTP. Please check your email or try again.", "danger")
        return redirect('/user-register')

# =================================================================
# ROUTE: USER LOGIN
# =================================================================
@app.route('/user-login', methods=['GET', 'POST'])
def user_login():

    if 'user_id' in session:
        return redirect('/')

    if request.method == 'GET':
        return render_template("user/user_login.html")

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        flash("Email not found! Please register.", "danger")
        return redirect('/user-login')

    # Verify password
    stored_hashed_password = user['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):

        flash("Incorrect password!", "danger")
        return redirect('/user-login')

    if user['status'] == 'blocked':
        flash("Your account has been blocked by the Admin.", "danger")
        return redirect('/user-login')

    # Create user session
    session['user_id'] = user['user_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    flash("Login successful!", "success")
    return redirect('/user/products')


# =================================================================
# ROUTE: USER DASHBOARD
# =================================================================
@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total orders
    cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (session['user_id'],))
    order_count = cursor.fetchone()[0]

    # Get total spent
    cursor.execute("SELECT SUM(amount) FROM orders WHERE user_id=?", (session['user_id'],))
    total_spent = cursor.fetchone()[0] or 0

    # Get recent orders with product info
    cursor.execute("""
        SELECT o.*, 
            (SELECT p.name FROM order_items oi 
             JOIN products p ON oi.product_id = p.product_id 
             WHERE oi.order_id = o.order_id LIMIT 1) as product_name,
            (SELECT p.image FROM order_items oi 
             JOIN products p ON oi.product_id = p.product_id 
             WHERE oi.order_id = o.order_id LIMIT 1) as product_image
        FROM orders o
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
        LIMIT 3
    """, (session['user_id'],))
    recent_orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/user_dashboard.html", 
                           user_name=session['user_name'],
                           order_count=order_count,
                           total_spent=total_spent,
                           recent_orders=recent_orders)


# =================================================================
# ROUTE: USER LOGOUT
# =================================================================
@app.route('/user-logout')
def user_logout():
    
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)

    flash("Logged out successfully!", "success")
    return redirect('/user-login')



# =================================================================
# ROUTE: USER PRODUCT LISTING (SEARCH + FILTER)
# =================================================================
@app.route('/')
@app.route('/user/products')
def user_products():
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # Build dynamic SQL
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/user_products.html",
        products=products,
        categories=categories
    )



# =================================================================
# ROUTE: USER PRODUCT DETAILS PAGE
# =================================================================
@app.route('/user/product/<int:product_id>')
def user_product_details(product_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    return render_template("user/product_details.html", product=product)


# =================================================================
# ADD ITEM TO CART
# =================================================================
@app.route('/user/add-to-cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Create cart if doesn't exist
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect(request.referrer)

    pid = str(product_id)

    # If exists → increase quantity
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }

    session['cart'] = cart

    flash("Item added to cart!", "success")
    return redirect(request.referrer)

# =================================================================
# BUY NOW (Direct Checkout)
# =================================================================
@app.route('/user/buy/<int:product_id>')
def buy_now(product_id):

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # CLEAR CART for direct checkout
    session['cart'] = {}
    cart = session['cart']

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect('/user/products')

    pid = str(product_id)

    # Add to cart (set quantity to 1 if not present, or keep existing)
    if pid not in cart:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }
    
    session['cart'] = cart
    session.modified = True

    return redirect('/user/address')

# =================================================================
# VIEW CART PAGE
# =================================================================
@app.route('/user/cart')
def view_cart():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})

    # Calculate totals with 20% Markup (MRP = Selling Price / 0.8)
    total_mrp = 0
    total_discount = 0
    grand_total = 0

    for item in cart.values():
        mrp = round(item['price'] / 0.8) if item['price'] > 0 else 0
        discount = mrp - item['price']
        
        total_mrp += mrp * item['quantity']
        total_discount += discount * item['quantity']
        grand_total += item['price'] * item['quantity']

    return render_template("user/cart.html", 
                           cart=cart, 
                           total_mrp=total_mrp, 
                           total_discount=total_discount, 
                           grand_total=grand_total)

# =================================================================
# INCREASE QUANTITY
# =================================================================
@app.route('/user/cart/increase/<pid>')
def increase_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] += 1

    session['cart'] = cart
    return redirect('/user/cart')


# =================================================================
# DECREASE QUANTITY
# =================================================================
@app.route('/user/cart/decrease/<pid>')
def decrease_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] -= 1

        # If quantity becomes 0 → remove item
        if cart[pid]['quantity'] <= 0:
            cart.pop(pid)

    session['cart'] = cart
    return redirect('/user/cart')


# =================================================================
# REMOVE ITEM
# =================================================================
@app.route('/user/cart/remove/<pid>')
def remove_from_cart(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart.pop(pid)

    session['cart'] = cart

    flash("Item removed!", "success")
    return redirect('/user/cart')

# =================================================================
# ROUTE: CREATE RAZORPAY ORDER
# =================================================================
@app.route('/user/pay')
def user_pay():

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})

    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect('/user/products')

    # Calculate totals with 20% Markup
    total_mrp = 0
    total_discount = 0
    grand_total = 0

    for item in cart.values():
        mrp = round(item['price'] / 0.8) if item['price'] > 0 else 0
        discount = mrp - item['price']
        total_mrp += mrp * item['quantity']
        total_discount += discount * item['quantity']
        grand_total += item['price'] * item['quantity']

    razorpay_amount = int(grand_total * 100)

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    session['razorpay_order_id'] = razorpay_order['id']

    # Get address summary if available
    addr = session.get('delivery_address', {})

    return render_template(
        "user/payment.html",
        cart=cart,
        total_mrp=total_mrp,
        total_discount=total_discount,
        amount=grand_total,
        addr=addr,
        key_id=config.RAZORPAY_KEY_ID,
        order_id=razorpay_order['id']
    )

# =================================================================
# TEMP SUCCESS PAGE (Verification in Day 13)
# =================================================================
@app.route('/payment-success')
def payment_success():

    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')

    if not payment_id:
        flash("Payment failed!", "danger")
        return redirect('/user/cart')

    return render_template(
        "user/payment_success.html",
        payment_id=payment_id,
        order_id=order_id
    )

# ------------------------------
# Route: Verify Payment and Store Order
# ------------------------------
@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    if 'user_id' not in session:
        flash("Please login to complete the payment.", "danger")
        return redirect('/user-login')

    # Read values posted from frontend
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        flash("Payment verification failed (missing data).", "danger")
        return redirect('/user/cart')

    # Build verification payload required by Razorpay client.utility
    payload = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # This will raise an error if signature invalid
        razorpay_client.utility.verify_payment_signature(payload)

    except Exception as e:
        # Verification failed
        app.logger.error("Razorpay signature verification failed: %s", str(e))

        flash("Payment verification failed. Please contact support.", "danger")
        return redirect('/user/cart')

    # Signature verified — now store order and items into DB
    user_id = session['user_id']
    cart = session.get('cart', {})

    if not cart:
        flash("Cart is empty. Cannot create order.", "danger")
        return redirect('/user/products')

    # Calculate total amount (ensure same as earlier)
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())

    # DB insert: orders and order_items
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get delivery address from session
        addr_dict = session.get('delivery_address', {})
        address_str = f"{addr_dict.get('name')}\n{addr_dict.get('phone')}\n{addr_dict.get('address')}, {addr_dict.get('city')} - {addr_dict.get('pincode')}"

        # Insert into orders table
        cursor.execute("""
            INSERT INTO orders (user_id, razorpay_order_id, razorpay_payment_id, amount, payment_status, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, razorpay_order_id, razorpay_payment_id, total_amount, 'paid', address_str))

        order_db_id = cursor.lastrowid  # newly created order's primary key

        # Insert all items and reduce stock
        for pid_str, item in cart.items():
            product_id = int(pid_str)
            
            # 1. Insert into order_items
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (order_db_id, product_id, item['name'], item['quantity'], item['price']))

            # 2. Reduce Stock
            cursor.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?", (item['quantity'], product_id))

        # Commit transaction
        conn.commit()

        # Clear cart and temporary razorpay order id
        session.pop('cart', None)
        session.pop('razorpay_order_id', None)

        flash("Payment successful and order placed!", "success")
        return redirect(f"/user/order-success/{order_db_id}")

    except Exception as e:
        # Rollback and log error
        conn.rollback()
        app.logger.error("Order storage failed: %s\n%s", str(e), traceback.format_exc())

        flash("There was an error saving your order. Contact support.", "danger")
        return redirect('/user/cart')

    finally:
        cursor.close()
        conn.close()



@app.route('/user/order-success/<int:order_db_id>')
def order_success(order_db_id):
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_id=? AND user_id=?", (order_db_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("""
        SELECT oi.*, p.name, p.image, p.price as selling_price 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
    """, (order_db_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/products')

    # Calculate total quantity for summary
    total_qty = sum(item['quantity'] for item in items)

    return render_template("user/order_success.html", 
                           order=order, 
                           items=items, 
                           total_qty=total_qty)

@app.route('/user/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch orders with product details for the first item in each order (to show image)
    # Using subqueries to avoid ONLY_FULL_GROUP_BY issues in strict SQL modes
    cursor.execute("""
        SELECT o.*, 
            (SELECT p.name FROM order_items oi 
             JOIN products p ON oi.product_id = p.product_id 
             WHERE oi.order_id = o.order_id LIMIT 1) as product_name,
            (SELECT p.image FROM order_items oi 
             JOIN products p ON oi.product_id = p.product_id 
             WHERE oi.order_id = o.order_id LIMIT 1) as product_image
        FROM orders o
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
    """, (session['user_id'],))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("user/my_orders.html", orders=orders)

# =================================================================
# USER PROFILE & DELETE ACCOUNT
# =================================================================
@app.route('/user/profile')
def user_profile():
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("user/profile.html", user=user)

@app.route('/user/delete-account', methods=['POST'])
def user_delete_account():
    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete user's orders and items (simplified, ideally keep records but anonymize)
    cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE user_id = ?)", (user_id,))
    cursor.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.", "success")
    return redirect('/')

# =================================================================
# ADDRESS PAGE
# =================================================================
@app.route('/user/address', methods=['GET', 'POST'])
def user_address():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    if request.method == 'GET':
        cart = session.get('cart', {})

        # Calculate totals with 20% Markup (MRP = Selling Price / 0.8)
        total_mrp = 0
        total_discount = 0
        grand_total = 0

        for item in cart.values():
            mrp = round(item['price'] / 0.8) if item['price'] > 0 else 0
            discount = mrp - item['price']

            total_mrp += mrp * item['quantity']
            total_discount += discount * item['quantity']
            grand_total += item['price'] * item['quantity']

        return render_template("user/address.html",
                               cart=cart,
                               total_mrp=total_mrp,
                               total_discount=total_discount,
                               grand_total=grand_total)

    # POST → Save address in session
    session['delivery_address'] = {
        'name': request.form['name'],
        'phone': request.form['phone'],
        'address': request.form['address'],
        'city': request.form['city'],
        'pincode': request.form['pincode']
    }

    return redirect('/user/pay')



# ----------------------------
# GENERATE INVOICE PDF
# ----------------------------
@app.route("/user/download-invoice/<int:order_id>")
def download_invoice(order_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    # Fetch order
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_id=? AND user_id=?",
                   (order_id, session['user_id']))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect('/user/my-orders')

    # Generate PDF using reportlab (pass objects directly)
    pdf = generate_pdf(order, items)
    if not pdf:
        flash("Error generating PDF invoice. Please try again later.", "danger")
        return redirect('/user/my-orders')

    # Prepare response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=invoice_{order_id}.pdf"

    return response



@app.route("/super-admin/generate-invoice/<int:order_id>")
def super_admin_generate_invoice(order_id):
    # Rule: super_id OR merchant_id required
    auth_check = merchant_or_admin_required()
    if auth_check: return auth_check

    conn = get_db_connection()
    cursor = conn.cursor()

    # If it's a merchant, check if the order contains their products
    if 'merchant_id' in session:
        admin_id = session['merchant_id']
        cursor.execute("""
            SELECT o.* FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_id = ? AND p.admin_id = ?
            LIMIT 1
        """, (order_id, admin_id))
    else:
        # Super Admin can see any order
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    
    order = cursor.fetchone()
    if not order:
        cursor.close()
        conn.close()
        flash("Order not found or access denied.", "danger")
        return redirect(request.referrer or '/merchant/orders')

    # Fetch items
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    # Generate PDF using reportlab (pass objects directly)
    pdf = generate_pdf(order, items)
    if not pdf:
        flash("Error generating PDF invoice. Please try again later.", "danger")
        return redirect(request.referrer or '/merchant/orders')

    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"inline; filename=invoice_{order_id}.pdf"

    return response


# =================================================================
# SUPER ADMIN ROUTES
# =================================================================

def super_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'super_id' not in session:
            return redirect('/admin-secure-access-xk9')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/super-admin/logout')
def super_admin_logout():
    """Dedicated logout for Super Admin - clears all super_* session keys."""
    session.pop('super_id', None)
    session.pop('super_name', None)
    session.pop('super_email', None)
    session.pop('super_role', None)
    flash("Logged out successfully.", "success")
    return redirect('/admin-secure-access-xk9')


# -----------------------------------------------------------------
# SUPER ADMIN: ALL PRODUCTS (view products from ALL merchants)
# -----------------------------------------------------------------
@app.route('/super-admin/products')
@super_admin_required
def super_admin_products():
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    merchant_filter = request.args.get('merchant_id', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Category list for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = cursor.fetchall()

    # Merchant list for filter dropdown
    cursor.execute("SELECT admin_id, name FROM admin WHERE role='seller' ORDER BY name")
    merchants = cursor.fetchall()

    # Build query - super admin sees EVERYTHING
    query = """
        SELECT p.*, a.name as merchant_name
        FROM products p
        LEFT JOIN admin a ON p.admin_id = a.admin_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND p.name LIKE ?"
        params.append("%" + search + "%")
    if category_filter:
        query += " AND p.category = ?"
        params.append(category_filter)
    if merchant_filter:
        query += " AND p.admin_id = ?"
        params.append(merchant_filter)

    query += " ORDER BY p.product_id DESC"
    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'super_admin/products.html',
        products=products,
        categories=categories,
        merchants=merchants,
        total=len(products)
    )


# -----------------------------------------------------------------
# SUPER ADMIN: DELETE ANY PRODUCT
# -----------------------------------------------------------------
@app.route('/super-admin/delete-product/<int:product_id>')
@super_admin_required
def super_admin_delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT image FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/super-admin/products')

    # Delete image file
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'])
    if os.path.exists(image_path):
        os.remove(image_path)

    cursor.execute("DELETE FROM products WHERE product_id=?", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/super-admin/products')


@app.route('/super-admin/dashboard')
@super_admin_required
def super_admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Stats
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM admin WHERE role='seller'")
    total_merchants = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM orders WHERE payment_status='paid'")
    total_revenue = cursor.fetchone()[0] or 0

    # Recent Activities (Orders)
    cursor.execute("""
        SELECT o.*, u.name as customer_name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        ORDER BY o.created_at DESC LIMIT 10
    """)
    recent_orders = cursor.fetchall()

    # New Merchant Notifications
    cursor.execute("SELECT * FROM admin WHERE role='seller' AND is_seen=0 ORDER BY admin_id DESC")
    new_merchants = cursor.fetchall()

    # Category Distribution for Charts
    cursor.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category")
    category_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("super_admin/dashboard.html",
                           total_users=total_users,
                           total_merchants=total_merchants,
                           total_products=total_products,
                           total_revenue=total_revenue,
                           recent_orders=recent_orders,
                           new_merchants=new_merchants,
                           category_data=category_data)

@app.route('/super-admin/api/notifications')
@super_admin_required
def super_admin_notifications_api():
    conn = get_db_connection()
    cursor = conn.row_factory = sqlite3.Row  # Ensure row factory for JSON serialization
    cursor = conn.cursor()
    
    cursor.execute("SELECT admin_id, name, email FROM admin WHERE role='seller' AND is_seen=0 ORDER BY admin_id DESC")
    new_merchants = cursor.fetchall()
    
    # Convert to list of dicts for JSON
    merchants_list = [dict(row) for row in new_merchants]
    
    cursor.close()
    conn.close()
    
    return {
        "unseen_count": len(merchants_list),
        "merchants": merchants_list
    }

@app.route('/super-admin/mark-seen/<int:id>')
@super_admin_required
def super_admin_mark_seen(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET is_seen=1 WHERE admin_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/super-admin/dashboard')

@app.route('/super-admin/merchants')
@super_admin_required
def manage_merchants():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE role='seller'")
    merchants = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("super_admin/manage_merchants.html", merchants=merchants)

@app.route('/super-admin/users')
@super_admin_required
def manage_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("super_admin/manage_users.html", users=users)

@app.route('/super-admin/block-merchant/<int:id>')
@super_admin_required
def block_merchant(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET status='blocked', is_seen=1 WHERE admin_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Merchant blocked successfully!", "warning")
    return redirect('/super-admin/merchants')

@app.route('/super-admin/unblock-merchant/<int:id>')
@super_admin_required
def unblock_merchant(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET status='active', is_seen=1 WHERE admin_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Merchant unblocked successfully!", "success")
    return redirect('/super-admin/merchants')

@app.route('/super-admin/approve-merchant/<int:id>')
@super_admin_required
def approve_merchant(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET status='active', is_seen=1 WHERE admin_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Merchant approved successfully!", "success")
    return redirect('/super-admin/merchants')

@app.route('/super-admin/reject-merchant/<int:id>')
@super_admin_required
def reject_merchant(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete the pending merchant account - this will naturally clear notification
    cursor.execute("DELETE FROM admin WHERE admin_id=? AND role='seller'", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Merchant application rejected.", "danger")
    return redirect('/super-admin/merchants')

@app.route('/super-admin/block-user/<int:id>')
@super_admin_required
def block_user(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='blocked' WHERE user_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("User blocked successfully!", "success")
    return redirect('/super-admin/users')

@app.route('/super-admin/unblock-user/<int:id>')
@super_admin_required
def unblock_user(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='active' WHERE user_id=?", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("User unblocked successfully!", "success")
    return redirect('/super-admin/users')

@app.route('/super-admin/merchant-history/<int:id>')
@super_admin_required
def merchant_history(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Merchant Details
    cursor.execute("SELECT * FROM admin WHERE admin_id=?", (id,))
    merchant = cursor.fetchone()
    # Products added by merchant
    cursor.execute("SELECT * FROM products WHERE admin_id=?", (id,))
    products = cursor.fetchall()
    # Orders for merchant's products
    cursor.execute("""
        SELECT oi.*, o.created_at, u.name as customer_name, o.payment_status
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN users u ON o.user_id = u.user_id
        WHERE p.admin_id = ?
        ORDER BY o.created_at DESC
    """, (id,))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("super_admin/merchant_history.html", merchant=merchant, products=products, orders=orders)

@app.route('/super-admin/user-history/<int:id>')
@super_admin_required
def user_history(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # User Details
    cursor.execute("SELECT * FROM users WHERE user_id=?", (id,))
    user = cursor.fetchone()
    # Orders placed by user
    cursor.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (id,))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("super_admin/user_history.html", user=user, orders=orders)

if __name__ == '__main__':
    from init_db import init_db
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
