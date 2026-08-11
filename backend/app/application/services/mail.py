import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Sequence, Union

from app.core.config import get_settings

logger = logging.getLogger(__name__)

AttachmentPath = Union[Path, str]
AttachmentSpec = tuple[AttachmentPath, str]  # (path, filename)


class MailService:
    def __init__(self):
        self.settings = get_settings()

    @property
    def smtp_configured(self) -> bool:
        return bool(self.settings.SMTP_HOST and self.settings.SMTP_USER)

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: str = None,
        attachments: Optional[Sequence[AttachmentSpec]] = None,
    ) -> bool:
        """
        Sends email via SMTP when configured.
        Optional file attachments (resume PDF/DOCX) — cuts missed-resume sends.
        Dev without SMTP: logs a mock send and returns True.
        Production without SMTP: raises — callers should offer Gmail/mailto instead.
        """
        if not self.smtp_configured:
            if self.settings.is_production:
                raise RuntimeError(
                    "SMTP is not configured. Copy the draft or use mailto — do not mark as sent."
                )
            logger.info(
                "MOCK SEND EMAIL to %s subject=%s attachments=%s",
                to_email,
                subject,
                [name for _, name in (attachments or [])],
            )
            print(
                f"--- MOCK EMAIL --- \nTo: {to_email}\nSubject: {subject}\n"
                f"Attachments: {[n for _, n in (attachments or [])]}\n"
                f"Body: {body}\n------------------"
            )
            return True

        sender = from_email or self.settings.SMTP_USER

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        for raw_path, filename in attachments or []:
            path = Path(raw_path)
            if not path.is_file():
                logger.warning("Skipping missing attachment: %s", path)
                continue
            part = MIMEApplication(path.read_bytes(), Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            msg.attach(part)

        try:
            server = smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT)
            server.starttls()
            server.login(self.settings.SMTP_USER, self.settings.SMTP_PASS)
            server.send_message(msg)
            server.quit()
            logger.info(
                "Successfully sent email to %s with %s attachment(s)",
                to_email,
                len(list(attachments or [])),
            )
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            raise RuntimeError(f"SMTP Error: {e}") from e
