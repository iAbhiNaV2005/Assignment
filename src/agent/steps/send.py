from datetime import datetime, timezone
from agent.budget import BudgetTracker
from agent.clients.mailer import Mailer, get_mailer
from agent.config import EnvSettings, load_env_settings, load_upthrust_config
from agent.db import Database
from agent.models import ComposedEmail, Contact, SendResult


class SendStep:
    def __init__(
        self,
        db: Database,
        mailer: Mailer | None = None,
        settings: EnvSettings | None = None,
        budget: BudgetTracker | None = None,
    ):
        self.db = db
        self.settings = settings or load_env_settings()
        self.mailer = mailer or get_mailer(self.settings)
        self.budget = budget or BudgetTracker()
        self.upthrust_cfg = load_upthrust_config()

    def run(
        self,
        domain: str,
        email: ComposedEmail,
        contact: Contact,
        live: bool = False,
    ) -> SendResult:
        norm_domain = domain.strip().lower()

        # 1. Idempotency check: don't send if already sent
        if self.db.has_successful_send(norm_domain):
            res = SendResult(
                mode="dryrun",
                intended_to=contact.email,
                actual_to="",
                status="skipped",
                error=f"Domain {norm_domain} already received an email",
                sent_at=datetime.now(timezone.utc),
            )
            return res

        # 2. Budget check
        self.budget.check_send()

        # 3. Determine send mode & recipient
        is_live_allowed = (
            live
            and not self.settings.safe_mode
            and self.settings.live_send_confirm == "I_UNDERSTAND"
            and "<REQUIRED" not in self.upthrust_cfg.get("sender", {}).get("postal_address", "")
            and contact.verification == "valid"
        )

        if is_live_allowed:
            mode = "live"
            actual_to = contact.email
            send_body = email.body_text
        else:
            # Safe Mode by default
            mode = "test" if self.settings.mail_provider != "dryrun" else "dryrun"
            actual_to = self.settings.test_recipient or "test-recipient@upthrust.local"
            contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() or "Contact"
            banner = f"[TEST SEND. Intended recipient: {contact_name} <{contact.email}>]\n\n"
            send_body = banner + email.body_text

        # 4. Dispatch email
        send_result = self.mailer.send(
            to_email=actual_to,
            subject=email.subject,
            body_text=send_body,
            intended_to=contact.email,
            mode=mode,
        )

        # 5. Record result and update state
        self.db.record_send(norm_domain, send_result)
        if send_result.status == "sent":
            self.budget.record_send()
            self.db.update_state(norm_domain, "SENT")
        else:
            self.db.update_state(norm_domain, "SEND_FAILED")

        return send_result
