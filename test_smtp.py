import smtplib
from email.message import EmailMessage
import config

def test_email():
    msg = EmailMessage()
    msg.set_content("Test email from Express-Kart project.")
    msg['Subject'] = 'SMTP Test'
    msg['From'] = config.MAIL_USERNAME
    msg['To'] = config.MAIL_USERNAME # Send to self

    try:
        print(f"Connecting to {config.MAIL_SERVER}:{config.MAIL_PORT}...")
        server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT)
        server.set_debuglevel(1)
        server.starttls()
        print("Logging in...")
        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        print("Sending...")
        server.send_message(msg)
        server.quit()
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_email()
