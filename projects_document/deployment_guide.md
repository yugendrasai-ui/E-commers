# Local Deployment Guide - Express-Kart

This guide explains how to set up and run the Express-Kart platform on your local machine.

## Prerequisites
- Python 3.8 or higher installed on your system.
- Git (optional, for cloning the repository).

## Option 1: Deployment WITH Virtual Environment (Recommended)
Using a virtual environment keeps the project dependencies isolated from your system Python.

1. **Open your terminal** and navigate to the project folder:
   ```bash
   cd Ecommers
   ```
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   - **Windows**: `venv\Scripts\activate`
   - **Mac/Linux**: `source venv/bin/activate`
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Initialize the database** (First time only):
   ```bash
   python init_db.py
   ```
6. **Run the application**:
   ```bash
   python app.py
   ```

## Option 2: Deployment WITHOUT Virtual Environment
Use this if you want to install requirements directly to your system or global Python environment.

1. **Open your terminal** in the project folder.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Initialize the database** (First time only):
   ```bash
   python init_db.py
   ```
4. **Run the application**:
   ```bash
   python app.py
   ```

## Accessing the Platform
Once the server is running, open your web browser and go to:
`http://127.0.0.1:5000`

## Important Configuration
- **config.py**: Edit this file to update your secret keys, email SMTP settings (for OTP), and Razorpay API keys.
- **Port**: The app defaults to port 5000. Ensure no other service is using this port.

---

## PythonAnywhere Troubleshooting

If you encounter errors while installing requirements on **PythonAnywhere** (like "Clock skew detected" or "pycairo metadata-generation-failed"):

### 1. Fix for `pycairo` Error
The error happens because `pycairo` is trying to compile and hitting a bug in the server environment.

**Solution:**
Run these commands in your PythonAnywhere console:
```bash
pip install --no-build-isolation pycairo
pip install -r requirements.txt
```

### 2. Emergency Workaround
If the error persists, you can make the PDF generator optional so the main website still works:
1. Open `app.py`.
2. Find line 12: `from utils.pdf_generator import generate_pdf`.
3. Wrap it in a try-except block or comment it out if you don't need PDFs on the server yet.
