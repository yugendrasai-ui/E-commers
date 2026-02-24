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

    # If already logged in, redirect to merchant list
    if 'admin_id' in session:
        return redirect('/merchant/item-list')

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
    message = Message(
        subject="Express-Kart Merchant OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    message.body = f"Your OTP for Express-Kart Merchant Registration is: {otp}"

    mail.send(message)

    flash("OTP sent to your email!", "success")
    return redirect('/verify-otp')



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
            "INSERT INTO admin (name, email, password) VALUES (?, ?, ?)",
            (session['signup_name'], session['signup_email'], hashed_password)
        )
        msg = "Merchant Registered Successfully!"
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


# =================================================================
# ROUTE 4: MERCHANT LOGIN PAGE (GET + POST)
# =================================================================
@app.route('/merchant-login', methods=['GET', 'POST'])
def merchant_login():

    # If already logged in, redirect to merchant list
    if 'admin_id' in session:
        return redirect('/merchant/item-list')

    # Show login page
    if request.method == 'GET':
        return render_template("merchant/login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 0: Check for hardcoded Super Admin credentials
    if email == 'admin@123' and password == 'admin123':
        session['admin_id'] = 0  # Special ID for Super Admin
        session['admin_name'] = 'Platform Super Admin'
        session['admin_email'] = 'admin@123'
        session['admin_role'] = 'super_admin'
        flash("Logged in as SUPER ADMIN", "success")
        return redirect('/merchant/item-list')

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

    # Step 5: If login success → Create merchant session
    session['admin_id'] = admin['admin_id']
    session['admin_name'] = admin['name']
    session['admin_email'] = admin['email']
    # Explicitly set to 'seller' for database logins (reserve 'super_admin' for hardcoded login)
    session['admin_role'] = 'seller'

    flash("Login Successful!", "success")
    return redirect('/merchant/item-list')

# =================================================================
# ROUTE 5: MERCHANT DASHBOARD (PROTECTED ROUTE)
# =================================================================
@app.route('/merchant-dashboard')
def merchant_dashboard():
    # Only logged-in merchant can access
    if 'admin_id' not in session:
        flash("Please login to access dashboard!", "danger")
        return redirect('/merchant-login')
    
    return redirect('/merchant/item-list')


# =================================================================
# ROUTE 6: ADMIN LOGOUT
# =================================================================
@app.route('/merchant-logout')
def admin_logout():

    # Clear admin session
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)

    flash("Logged out successfully.", "success")
    return redirect('/merchant-login')



# =================================================================
# ROUTE 1: SHOW ADD PRODUCT PAGE (Protected Route)
# =================================================================
@app.route('/merchant/add-item', methods=['GET'])
def add_item_page():

    # Only logged-in admin can access
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/merchant-login')

    return render_template("merchant/add_item.html")



# =================================================================
# ROUTE 2: ADD PRODUCT INTO DATABASE
# =================================================================
@app.route('/merchant/add-item', methods=['POST'])
def add_item():

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/merchant-login')

    # 1️⃣ Get form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']
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
        "INSERT INTO products (name, description, category, price, image, admin_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, category, price, filename, session['admin_id'])
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

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/merchant-login')

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

    if session.get('admin_role') != 'super_admin':
        query += " AND admin_id = ?"
        params.append(session['admin_id'])

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

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/merchant-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch product to get image name and owner
    cursor.execute("SELECT image, admin_id FROM products WHERE product_id=?", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/merchant/item-list')

    # Ownership check
    if session.get('admin_role') != 'super_admin' and product['admin_id'] != session['admin_id']:
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
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/merchant-login')

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
    if session.get('admin_role') != 'super_admin' and product['admin_id'] != session['admin_id']:
        flash("You do not have permission to view this product!", "danger")
        return redirect('/merchant/item-list')

    return render_template("merchant/view_item.html", product=product)

# =================================================================
# ROUTE 11: SHOW UPDATE FORM WITH EXISTING DATA
# =================================================================
@app.route('/merchant/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    # Check login
    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/merchant-login')

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
    if session.get('admin_role') != 'super_admin' and product['admin_id'] != session['admin_id']:
        flash("You do not have permission to update this product!", "danger")
        return redirect('/merchant/item-list')

    return render_template("merchant/update_item.html", product=product)


# =================================================================
# ROUTE: UPDATE PRODUCT + OPTIONAL IMAGE REPLACE
# =================================================================
@app.route('/merchant/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/merchant-login')

    # 1️⃣ Get updated form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

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
    if session.get('admin_role') != 'super_admin' and product['admin_id'] != session['admin_id']:
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
        SET name=?, description=?, category=?, price=?, image=?
        WHERE product_id=?
    """, (name, description, category, price, final_image_name, item_id))

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

    # Send OTP Email
    message = Message(
        subject="Express-Kart Registration OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    message.body = f"Your OTP for Express-Kart Account Registration is: {otp}"
    mail.send(message)

    flash("OTP sent to your email!", "success")
    return redirect('/verify-otp')

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

    return render_template("user/user_dashboard.html", user_name=session['user_name'])


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
        # Insert into orders table
        cursor.execute("""
            INSERT INTO orders (user_id, razorpay_order_id, razorpay_payment_id, amount, payment_status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, razorpay_order_id, razorpay_payment_id, total_amount, 'paid'))

        order_db_id = cursor.lastrowid  # newly created order's primary key

        # Insert all items
        for pid_str, item in cart.items():
            product_id = int(pid_str)
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (order_db_id, product_id, item['name'], item['quantity'], item['price']))

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

    # Render invoice HTML
    html = render_template("user/invoice.html", order=order, items=items)

    pdf = generate_pdf(html)
    if not pdf:
        flash("Error generating PDF", "danger")
        return redirect('/user/my-orders')

    # Prepare response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f"attachment; filename=invoice_{order_id}.pdf"

    return response


if __name__ == '__main__':
    app.run(debug=True)
