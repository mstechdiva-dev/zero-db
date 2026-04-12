import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Sequence


class EmailService:
    """Send email notifications for schema change alerts. Full implementation in Phase 7."""

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_address = os.environ.get("EMAIL_FROM", "alerts@schemazero.com")

    async def send_alert(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
    ) -> bool:
        """Send an HTML alert email. Returns True on success."""
        if not self.smtp_host or not recipients:
            return False
        # Full HTML template implemented in Phase 7
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html"))
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, list(recipients), msg.as_string())
            return True
        except Exception:
            return False
