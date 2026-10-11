from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import make_msgid
import smtplib
from typing import Any
import httpx

from agent.config import EnvSettings, RUNS_DIR, load_env_settings
from agent.models import SendResult


class Mailer(ABC):
    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        intended_to: str,
        mode: str = "test",
        headers: dict[str, str] | None = None,
    ) -> SendResult:
        pass


class GmailSMTPMailer(Mailer):
    def __init__(self, settings: EnvSettings | None = None):
        self.settings = settings or load_env_settings()

    def check_connection(self) -> bool:
        """Verify SMTP credentials without sending."""
        if not self.settings.smtp_user or not self.settings.smtp_app_password:
            raise ValueError("SMTP_USER or SMTP_APP_PASSWORD missing")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10.0) as server:
            server.login(self.settings.smtp_user, self.settings.smtp_app_password)
        return True

    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        intended_to: str,
        mode: str = "test",
        headers: dict[str, str] | None = None,
    ) -> SendResult:
        now = datetime.now(timezone.utc)
        msg_id = make_msgid(domain="upthrust.com")

        msg = MIMEText(body_text, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.settings.smtp_user
        msg["To"] = to_email
        msg["Reply-To"] = self.settings.smtp_user
        msg["Message-ID"] = msg_id
        msg["X-Intended-Recipient"] = intended_to

        if headers:
            for k, v in headers.items():
                msg[k] = v

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15.0) as server:
                server.login(self.settings.smtp_user, self.settings.smtp_app_password)
                server.send_message(msg)

            return SendResult(
                mode=mode,  # type: ignore
                intended_to=intended_to,
                actual_to=to_email,
                status="sent",
                message_id=msg_id,
                provider_response="250 Message accepted",
                sent_at=now,
            )
        except Exception as e:
            return SendResult(
                mode=mode,  # type: ignore
                intended_to=intended_to,
                actual_to=to_email,
                status="failed",
                error=str(e),
                sent_at=now,
            )


class ResendMailer(Mailer):
    def __init__(self, settings: EnvSettings | None = None):
        self.settings = settings or load_env_settings()

    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        intended_to: str,
        mode: str = "test",
        headers: dict[str, str] | None = None,
    ) -> SendResult:
        now = datetime.now(timezone.utc)
        if not self.settings.resend_api_key:
            return SendResult(
                mode=mode,  # type: ignore
                intended_to=intended_to,
                actual_to=to_email,
                status="failed",
                error="RESEND_API_KEY missing",
                sent_at=now,
            )

        url = "https://api.resend.com/emails"
        req_headers = {
            "Authorization": f"Bearer {self.settings.resend_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": "Upthrust Growth <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "text": body_text,
            "headers": {"X-Intended-Recipient": intended_to, **(headers or {})},
        }

        try:
            resp = httpx.post(url, headers=req_headers, json=payload, timeout=15.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                return SendResult(
                    mode=mode,  # type: ignore
                    intended_to=intended_to,
                    actual_to=to_email,
                    status="sent",
                    message_id=data.get("id"),
                    provider_response=resp.text,
                    sent_at=now,
                )
            else:
                return SendResult(
                    mode=mode,  # type: ignore
                    intended_to=intended_to,
                    actual_to=to_email,
                    status="failed",
                    error=f"Resend error ({resp.status_code}): {resp.text}",
                    sent_at=now,
                )
        except Exception as e:
            return SendResult(
                mode=mode,  # type: ignore
                intended_to=intended_to,
                actual_to=to_email,
                status="failed",
                error=str(e),
                sent_at=now,
            )


class DryRunMailer(Mailer):
    def __init__(self, runs_dir=RUNS_DIR):
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        intended_to: str,
        mode: str = "dryrun",
        headers: dict[str, str] | None = None,
    ) -> SendResult:
        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        msg_id = make_msgid(domain="dryrun.upthrust.local")

        eml_content = (
            f"Message-ID: {msg_id}\n"
            f"Date: {now.isoformat()}\n"
            f"Subject: {subject}\n"
            f"From: Upthrust <agent@upthrust.com>\n"
            f"To: {to_email}\n"
            f"X-Intended-Recipient: {intended_to}\n"
            f"X-Send-Mode: {mode}\n\n"
            f"{body_text}\n"
        )

        safe_to = to_email.replace("@", "_at_")
        file_path = self.runs_dir / f"email_{timestamp_str}_{safe_to}.eml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(eml_content)

        return SendResult(
            mode=mode,  # type: ignore
            intended_to=intended_to,
            actual_to=to_email,
            status="sent",
            message_id=msg_id,
            provider_response=f"Dry run saved to {file_path}",
            sent_at=now,
        )


def get_mailer(settings: EnvSettings) -> Mailer:
    if settings.mail_provider == "gmail":
        return GmailSMTPMailer(settings)
    elif settings.mail_provider == "resend":
        return ResendMailer(settings)
    return DryRunMailer()
