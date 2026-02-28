from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from auth_utils import send_otp, verify_otp
import bcrypt
import sqlite3

import config

forgot_pw = Blueprint('forgot_pw', __name__)

def get_db_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@forgot_pw.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        account_type = request.args.get('type', 'user') # 'user' or 'merchant'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        table = 'users' if account_type == 'user' else 'admin'
        cursor.execute(f"SELECT * FROM {table} WHERE email = ?", (email,))
        account = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not account:
            flash(f"No {account_type} account found with that email.", "danger")
            return redirect(url_for('forgot_pw.forgot_password', type=account_type))
        
        # Send OTP
        from app import mail # Import mail from main app
        subject = "Password Reset OTP - Express-Kart"
        body = "Your OTP for password reset is: {otp}"
        
        if send_otp(mail, email, subject, body):
            session['reset_email'] = email
            session['reset_account_type'] = account_type
            flash("OTP has been sent to your email.", "success")
            return redirect(url_for('forgot_pw.verify_reset_otp'))
        else:
            flash("Failed to send OTP. Please try again.", "danger")
            
    return render_template('auth/forgot_password.html')

@forgot_pw.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if verify_otp(user_otp):
            flash("OTP verified. Please set your new password.", "success")
            return redirect(url_for('forgot_pw.reset_password'))
        else:
            flash("Invalid or expired OTP.", "danger")
            
    return render_template('auth/verify_reset_otp.html')

@forgot_pw.route('/resend-reset-otp')
def resend_reset_otp():
    email = session.get('reset_email')
    account_type = session.get('reset_account_type')

    if not email:
        flash("Session expired. Please start over.", "danger")
        return redirect(url_for('forgot_pw.forgot_password'))

    from app import mail
    subject = "Password Reset OTP (Resend) - Express-Kart"
    body = "Your NEW OTP for password reset is: {otp}"

    if send_otp(mail, email, subject, body):
        flash("A new OTP has been sent to your email.", "success")
    else:
        flash("Failed to resend OTP. Please try again.", "danger")

    return redirect(url_for('forgot_pw.verify_reset_otp'))

@forgot_pw.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['password']
        email = session.get('reset_email')
        account_type = session.get('reset_account_type')
        
        if not email or not account_type:
            flash("Session expired. Please start over.", "danger")
            return redirect(url_for('forgot_pw.forgot_password'))
        
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        table = 'users' if account_type == 'user' else 'admin'
        cursor.execute(f"UPDATE {table} SET password = ? WHERE email = ?", (hashed_password, email))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        session.pop('reset_email', None)
        session.pop('reset_account_type', None)
        session.pop('otp', None)
        
        flash("Password updated successfully! Please login.", "success")
        login_url = '/user-login' if account_type == 'user' else '/merchant-login'
        return redirect(login_url)
        
    return render_template('auth/reset_password.html')
