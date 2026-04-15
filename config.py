SECRET_KEY = "sai1234"

# Database Configuration
import os
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DB_TYPE = "postgres"
    DB_PATH = DATABASE_URL
else:
    DB_TYPE = "sqlite"
    DB_PATH = os.path.join(os.getcwd(), 'ecommerce.db')

# Email SMTP Settings

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False


MAIL_USERNAME = 'yugendrasai797@gmail.com'
MAIL_PASSWORD = 'ckcfrfofnknjmkss'

# PayMent Configuration
RAZORPAY_KEY_ID = "rzp_live_SO2OyNtnyLYLQQ"
RAZORPAY_KEY_SECRET = "FZRv4xly9j2QbccfG1S1299e"

# Brevo API Configuration
import os
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

# Super Admin Credentials

SUPER_ADMIN_EMAIL = "yugendrasai797@gmail.com"
SUPER_ADMIN_PASSWORD = "admin123"
