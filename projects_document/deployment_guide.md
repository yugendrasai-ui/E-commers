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

## Deployment Note: PDF Invoices

We have switched from `xhtml2pdf` to **ReportLab** for invoice generation. This ensures:
1. **Easy Installation**: No specialized C headers or "Clock skew" issues on PythonAnywhere.
2. **Standard Requirements**: Simply run `pip install -r requirements.txt` and it will work out of the box.
