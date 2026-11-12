"""SMTP email delivery for one-time verification codes."""

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


def send_otp_email(recipient: str, code: str) -> None:
    settings = get_settings()
    if not settings.email_otp_enabled or not all((settings.smtp_host, settings.email_from)):
        raise RuntimeError("Email OTP delivery is not configured")
    message = EmailMessage()
    message["Subject"] = "Your DOGO verification code"
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(f"Your DOGO verification code is {code}. It expires in {settings.email_otp_ttl_minutes} minutes. If you did not request this, ignore this email.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
