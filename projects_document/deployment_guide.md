# PythonAnywhere Deployment Guide - Express-Kart

Your project is almost ready for deployment! Here are the steps and considerations for hosting it on PythonAnywhere.

## Deployment Checklist

- [x] **app.py**: correctly structured with standard Flask patterns.
- [x] **requirements.txt**: Generated and ready for environment setup.
- [/] **Database Path**: Needs to be absolute for reliable access on the server.
- [ ] **WSGI Configuration**: Required by PythonAnywhere to bridge the web server and Flask.

## Steps to Deploy

### 1. Upload your code
- You can either use `git clone` if your code is on GitHub, or upload a ZIP file via the PythonAnywhere dashboard.

### 2. Create a Virtual Environment
In the PythonAnywhere bash console:
```bash
mkvirtualenv --python=/usr/bin/python3.10 myenv
pip install -r requirements.txt
```

### 3. Update paths in `app.py`
To ensure the database and uploads are found correctly, it's best to use absolute paths. Update `config.py` on the server:
```python
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")
```

### 4. Configure the Web Tab
- Go to the **Web** tab on PythonAnywhere.
- Add a new web app pointing to your project folder.
- Set the **Virtualenv** path to your newly created environment.
- Edit the **WSGI configuration file** provided by PythonAnywhere:

```python
import sys
import os

# Path to your project
path = '/home/yourusername/Ecommers'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
```

## Security Recommendation
> [!IMPORTANT]
> Your `config.py` currently contains plain-text passwords and API keys. For a production environment, it is highly recommended to use **Environment Variables** to store these secrets.

## Final Verification
Once deployed, verify that:
1.  Emails (OTP) are still sending.
2.  Payment (Razorpay) integration works in test mode.
3.  Images are being uploaded and served correctly from the `static/uploads` folder.
