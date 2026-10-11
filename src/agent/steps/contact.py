import re
from typing import Any

from agent.clients.hunter import HunterClient
from agent.db import Database
from agent.models import Contact

ROLE_KEYWORDS_PRIORITY = [
    (1, re.compile(r"\b(cmo|chief marketing|vp marketing|head of marketing|growth)\b", re.I)),
    (2, re.compile(r"\b(ceo|founder|co-founder|owner|president|managing director)\b", re.I)),
    (3, re.compile(r"\b(director|head|vp|partner)\b", re.I)),
]


def score_role(position: str | None) -> int:
    if not position:
        return 4
    for priority, pattern in ROLE_KEYWORDS_PRIORITY:
        if pattern.search(position):
            return priority
    return 5


class ContactStep:
    def __init__(self, db: Database, hunter_client: HunterClient | None = None):
        self.db = db
        self.hunter_client = hunter_client or HunterClient()

    def run(self, domain: str, safe_mode: bool = True) -> Contact | None:
        norm_domain = domain.strip().lower()
        enrichment = self.db.get_enrichment(norm_domain)

        # 1. Attempt Hunter Domain Search only if API key configured
        if self.hunter_client.settings.hunter_api_key:
            try:
                emails = self.hunter_client.domain_search(norm_domain, limit=5)
                if emails:
                    # Sort by role priority and confidence
                    ranked = sorted(
                        emails,
                        key=lambda x: (score_role(x.get("position")), -(x.get("confidence") or 0)),
                    )
                    best = ranked[0]
                    status = (best.get("verification") or {}).get("status", "unknown")
                    conf = best.get("confidence")

                    contact = Contact(
                        email=best.get("value", ""),
                        first_name=best.get("first_name"),
                        last_name=best.get("last_name"),
                        position=best.get("position"),
                        source="hunter_domain",
                        verification="valid" if status == "valid" else "accept_all" if status == "accept_all" else "unknown",
                        confidence=conf,
                    )
                    self.db.save_contact(norm_domain, contact)
                    self.db.update_state(norm_domain, "CONTACT_FOUND")
                    return contact
            except Exception:
                pass

        # 2. Fallback: Check mailto emails collected during enrichment
        if enrichment and enrichment.get("emails_found"):
            site_emails = enrichment["emails_found"]
            # Filter out generic support if possible, or pick first
            picked_email = site_emails[0]
            for e in site_emails:
                if not any(prefix in e for prefix in ["support@", "privacy@", "legal@", "press@"]):
                    picked_email = e
                    break

            contact = Contact(
                email=picked_email,
                first_name="there",
                last_name=None,
                position="Team",
                source="site_mailto",
                verification="unverified",
                confidence=60,
            )
            self.db.save_contact(norm_domain, contact)
            self.db.update_state(norm_domain, "CONTACT_FOUND")
            return contact

        # 3. Fallback: Role inbox
        contact = Contact(
            email=f"hello@{norm_domain}",
            first_name="there",
            last_name=None,
            position="Team",
            source="role_inbox",
            verification="unverified",
            confidence=40,
        )
        self.db.save_contact(norm_domain, contact)
        self.db.update_state(norm_domain, "CONTACT_FOUND")
        return contact
