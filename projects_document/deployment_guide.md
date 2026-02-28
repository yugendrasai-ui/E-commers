# PythonAnywhere Hosting Guide - Express-Kart

This guide provides a step-by-step walkthrough for deploying your Express-Kart platform specifically on **PythonAnywhere**.

## 1. Upload Your Project
- **Option A (GitHub)**: Open a **Bash Console** on PythonAnywhere and run:
  ```bash
  git clone https://github.com/your-username/Ecommers.git
  ```
- **Option B (Manual)**: Go to the **Files** tab and upload your project folder or a ZIP file.

## 2. Set Up Virtual Environment
In your PythonAnywhere Bash Console, create a virtual environment and install dependencies:
```bash
mkvirtualenv --python=/usr/bin/python3.10 express_env
pip install -r requirements.txt
```

## 3. Configure Database & Static Paths
On PythonAnywhere, you MUST use absolute paths. Update your `config.py` in the **Files** tab:
```python
import os

# Get the absolute path to the folder where config.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Update DB_PATH to be absolute
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")

# Ensure UPLOAD_FOLDER in app.py uses this BASE_DIR if needed
```

## 4. Web Tab Configuration
Go to the **Web** tab in your PythonAnywhere dashboard and click **"Add a new web app"**.
1. **Domain**: yourusername.pythonanywhere.com
2. **Framework**: Select **Manual Configuration** (do not select Flask yet).
3. **Python Version**: Select **3.10**.

### After Creating the Web App:
- **Source Code**: Set to `/home/yourusername/Ecommers` (or your project folder).
- **Working Directory**: Set to `/home/yourusername/Ecommers`.
- **Virtualenv**: Set to `/home/yourusername/.virtualenvs/express_env`.

## 5. WSGI Configuration
In the **Web** tab, find the **"WSGI configuration file"** link and edit it. Replace everything with:

```python
import sys
import os

# Add your project directory to the sys.path
path = '/home/yourusername/Ecommers'
if path not in sys.path:
    sys.path.append(path)

# Import the Flask app object from app.py
from app import app as application
```

## 6. Static Files Configuration (CRITICAL)
For images and CSS to load properly, go to the **Static Files** section in the **Web** tab and add:
- **URL**: `/static/`
- **Path**: `/home/yourusername/Ecommers/static/`

## 7. Reload and Test
Click the big green **"Reload"** button at the top of the **Web** tab. Your site should now be live at `yourusername.pythonanywhere.com`.

---
> [!IMPORTANT]
> Since PythonAnywhere uses a different filesystem, always ensure that your folders like `static/uploads/product_images` exist. You might need to create them manually via the Files tab if they weren't included in your upload.
