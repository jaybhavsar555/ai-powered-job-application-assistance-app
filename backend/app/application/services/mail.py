import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class MailService:
    def __init__(self):
        self.settings = get_settings()

    @property
    def smtp_configured(self) -> bool:
        return bool(self.settings.SMTP_HOST and self.settings.SMTP_USER)

    def send_email(self, to_email: str, subject: str, body: str, from_email: str = None) -> bool:
        """
        Sends email via SMTP when configured.
        Dev without SMTP: logs a mock send and returns True.
        Production without SMTP: raises — callers should offer copy/mailto instead.
        """
        if not self.smtp_configured:
            if self.settings.is_production:
                raise RuntimeError(
                    "SMTP is not configured. Copy the draft or use mailto — do not mark as sent."
                )
            logger.info("MOCK SEND EMAIL to %s subject=%s", to_email, subject)
            print(
                f"--- MOCK EMAIL --- \nTo: {to_email}\nSubject: {subject}\n"
                f"Body: {body}\n------------------"
            )
            return True

        sender = from_email or self.settings.SMTP_USER

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT)
            server.starttls()
            server.login(self.settings.SMTP_USER, self.settings.SMTP_PASS)
            server.send_message(msg)
            server.quit()
            logger.info("Successfully sent email to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            raise RuntimeError(f"SMTP Error: {e}") from e
