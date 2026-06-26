from datetime import UTC, datetime
from email.message import EmailMessage
import smtplib
from uuid import uuid4

from app.core.config import get_settings
from app.executor.base import BaseExecutor
from app.models.job import Job


class EmailSendExecutor(BaseExecutor):
    def execute(self, job: Job) -> dict:
        payload = job.payload
        to_address = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        if not all([to_address, subject, body]):
            raise ValueError("email_send requires payload.to, payload.subject, and payload.body")

        settings = get_settings()
        message_id = f"{uuid4()}@job-orchestrator.local"
        if settings.email_dry_run or not settings.smtp_host:
            return {
                "delivered": False,
                "dry_run": True,
                "message_id": message_id,
                "sent_at": datetime.now(UTC).isoformat(),
            }

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to_address
        message["Subject"] = subject
        message["Message-ID"] = message_id
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

        return {
            "delivered": True,
            "message_id": message_id,
            "sent_at": datetime.now(UTC).isoformat(),
        }
