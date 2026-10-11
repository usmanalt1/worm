"""Plain-text alert email over Gmail SMTP."""

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
# SSL on 465 rather than STARTTLS on 587, so there is no cleartext upgrade step to fail.
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 30

DEFAULT_ADDRESS = "6usmana@gmail.com"


def send_alert_email(subject: str, body: str) -> bool:
    """Email one alert. Returns False, without raising, when GMAIL_APP_PASSWORD is unset."""
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not password:
        return False

    sender = os.getenv("ALERT_EMAIL_FROM", DEFAULT_ADDRESS)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = os.getenv("ALERT_EMAIL_TO", DEFAULT_ADDRESS)
    message.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        # Google shows app passwords in four spaced groups; it rejects them that way.
        smtp.login(sender, password.replace(" ", ""))
        smtp.send_message(message)
    return True
