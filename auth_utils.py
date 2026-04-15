from flask import session, flash
from flask_mail import Message
import random
import config

def send_otp(mail, email, subject, body_template):
    """
    Generates a 6-digit OTP and sends it via Brevo API or SMTP.
    """
    otp = random.randint(100000, 999999)
    session['otp'] = otp
    session['otp_email'] = email
    
    body = body_template.format(otp=otp)

    # 1. Try Brevo API (Works on Render Free Tier)
    if config.BREVO_API_KEY:
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
            
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = config.BREVO_API_KEY
            
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": email}],
                sender={"email": config.MAIL_USERNAME, "name": "Express-Kart"},
                subject=subject,
                html_content=f"<html><body><p>{body}</p></body></html>"
            )
            
            api_instance.send_transac_email(send_smtp_email)
            return True
        except Exception as e:
            flash(f"Brevo API Error: {str(e)}", "danger")
            # Continue to fallback if Brevo fails

    # 2. Fallback to Flask-Mail (SMTP)
    msg = Message(
        subject=subject,
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )
    msg.body = body
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        error_msg = str(e)
        if "Network is unreachable" in error_msg or "Timeout" in error_msg:
            flash(f"DEMO MODE: Render blocks emails. Your OTP is: {otp}", "warning")
            return True 
        
        flash(f"Email Error: {error_msg}", "danger")
        return False




def verify_otp(user_otp):
    """
    Verifies if the provided OTP matches the one in session.
    """
    stored_otp = session.get('otp')
    if not stored_otp:
        return False
    
    return str(user_otp) == str(stored_otp)
