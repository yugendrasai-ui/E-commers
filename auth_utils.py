from flask import session, flash
from flask_mail import Message
import random
import config

def send_otp(mail, email, subject, body_template):
    """
    Generates a 6-digit OTP and sends it to the specified email.
    Stores the OTP and target email in the session.
    """
    otp = random.randint(100000, 999999)
    session['otp'] = otp
    session['otp_email'] = email
    
    msg = Message(
        subject=subject,
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    msg.body = body_template.format(otp=otp)
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        # Render Free Tier blocks SMTP (Port 587/465). 
        # For demo purposes, we fallback to showing the OTP on screen.
        error_msg = str(e)
        if "Network is unreachable" in error_msg or "Timeout" in error_msg:
            flash(f"DEMO MODE: Render blocks emails. Your OTP is: {otp}", "warning")
            return True # Allow registration to proceed in demo mode
        
        flash(f"Email Error: {error_msg}", "danger")
        with open('email_error.log', 'a') as f:
            f.write(f"Error sending email to {email}: {error_msg}\n")
        return False



def verify_otp(user_otp):
    """
    Verifies if the provided OTP matches the one in session.
    """
    stored_otp = session.get('otp')
    if not stored_otp:
        return False
    
    return str(user_otp) == str(stored_otp)
