# Express-Kart E-Commerce Platform

Express-Kart is a multi-vendor Flask-based e-commerce application featuring User, Merchant, and Super Admin panels. Use this project to build a robust online marketplace with product management, secure authentication, and payment integration.

## Key Features
- **User Panel**: Browse products, manage cart, place orders, and track order history.
- **Merchant Panel**: Register as a seller, list products, manage inventory, and track sales performance with analytics.
- **Super Admin Panel**: Full platform control, merchant approval, user/product management, and system overview.
- **Security**: Password hashing with Bcrypt, OTP-based registration, and secure admin access.
- **Integrations**: Razorpay for payments, Flask-Mail for OTP/notifications, and xhtml2pdf for invoice generation.

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Installation
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/your-repo/express-kart.git
cd express-kart
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Open `config.py` and update the following settings:
- `SECRET_KEY`: For session security.
- `MAIL_SERVER` settings: Your SMTP provider details for OTP delivery.
- `RAZORPAY` keys: From your Razorpay dashboard (Test/Live).
- `SUPER_ADMIN` credentials: (See below for details on managing admins).

### 4. Database Setup
Initialize the SQLite database:
```bash
python init_db.py
```

### 5. Running the Application
```bash
python app.py
```
Access the app at `http://127.0.0.1:5000`.

## Super Admin Access
The Super Admin panel is accessible via a secure, hidden route to prevent unauthorized access.
- **URL**: `/admin-secure-access-xk9`
- **Default Credentials**: Check `config.py` for default values.

### Changing Super Admin Credentials
To change the Super Admin email or password:
1.  Open `config.py`.
2.  Locate `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD`.
3.  Update the values and restart the application.

*Note: For production, it is highly recommended to use environment variables instead of hard-coded values in `config.py`.*

## License
MIT License.
