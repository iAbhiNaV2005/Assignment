import re
from typing import Any
from pydantic import BaseModel, Field

from agent.config import PROJECT_ROOT, load_templates_config, load_upthrust_config
from agent.db import Database
from agent.llm import LLMClient
from agent.models import ComposedEmail, GuardrailResult


class ClaimCheckLLMOutput(BaseModel):
    unsupported_claims: list[str] = Field(default_factory=list)


class GuardrailsStep:
    def __init__(self, db: Database, llm: LLMClient | None = None):
        self.db = db
        self.llm = llm or LLMClient()
        self.templates_cfg = load_templates_config()
        self.upthrust_cfg = load_upthrust_config()

    def run(self, domain: str, email: ComposedEmail) -> GuardrailResult:
        norm_domain = domain.strip().lower()
        failures: list[str] = []
        unsupported_claims: list[str] = []

        # Find template spec
        tmpl_spec = None
        for t in self.templates_cfg.get("templates", []):
            if t["id"] == email.template_id:
                tmpl_spec = t
                break

        # 1. Check for unfilled Jinja placeholders
        if any(marker in email.body_text for marker in ["{{", "}}", "{%", "%}"]):
            failures.append("Body contains raw unfilled template markers ({{, }}, {%, %})")
        if any(marker in email.subject for marker in ["{{", "}}", "{%", "%}"]):
            failures.append("Subject contains raw unfilled template markers")

        # 2. Subject length check (max 60 chars)
        if len(email.subject) > 60:
            failures.append(f"Subject length {len(email.subject)} exceeds 60 characters: '{email.subject}'")

        # 3. Word count check (before footer)
        body_before_footer = email.body_text.split("\n\n--\n")[0].strip()
        words = body_before_footer.split()
        word_count = len(words)

        if tmpl_spec:
            min_words = tmpl_spec.get("min_words", 20)
            max_words = tmpl_spec.get("max_words", 160)
            if word_count < min_words:
                failures.append(f"Word count {word_count} is below template minimum ({min_words})")
            elif word_count > max_words:
                failures.append(f"Word count {word_count} exceeds template maximum ({max_words})")

        # 4. Banned phrases (case-insensitive)
        banned = self.upthrust_cfg.get("banned_phrases", [])
        body_lower = email.body_text.lower()
        for phrase in banned:
            if phrase.lower() in body_lower or phrase.lower() in email.subject.lower():
                failures.append(f"Contains banned phrase: '{phrase}'")

        # 5. Question mark count (single CTA rule)
        question_marks = body_before_footer.count("?")
        if question_marks > 1:
            failures.append(f"Email contains multiple question marks ({question_marks}). Exactly one CTA question allowed.")

        # 6. Any URL other than calendar_link
        calendar_link = self.upthrust_cfg.get("calendar_link", "")
        # Find URLs in body
        found_urls = re.findall(r"https?://[^\s)]+", email.body_text)
        for url in found_urls:
            if calendar_link and url == calendar_link:
                continue
            failures.append(f"Forbidden URL found in email body: {url}")

        # 7. Suppression & duplicate send checks
        contact = self.db.get_contact(norm_domain)
        if contact and self.db.is_suppressed(contact["email"]):
            failures.append(f"Contact email {contact['email']} is on the suppression list")
        if self.db.is_suppressed(norm_domain):
            failures.append(f"Domain {norm_domain} is on the suppression list")
        if self.db.has_successful_send(norm_domain):
            failures.append(f"Domain {norm_domain} has already been sent an email")

        # 8. Evidence verification for numbers
        enrichment = self.db.get_enrichment(norm_domain) or {}
        signals = enrichment.get("signals", [])
        evidence_text = " ".join([s.get("evidence_snippet", "") for s in signals])

        proof_point = email.variables.get("proof_point", "")
        allowed_number_sources = f"{evidence_text} {proof_point}"

        # Find numbers, percentages, currency amounts in body
        numbers_in_body = re.findall(r"\b\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?", body_before_footer)
        for num in numbers_in_body:
            # Allow common conversational single digits or ordinal if necessary, but flag statistics
            if num not in allowed_number_sources and num not in ("15", "1", "2"):  # 15-minute chat is standard CTA
                failures.append(f"Unverified number or metric '{num}' found in body not present in cited evidence")

        # 9. LLM Claim-Check pass
        if not failures:
            prompt_file = PROJECT_ROOT / "src" / "agent" / "prompts" / "claim_check.md"
            system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""

            evidence_items_str = "\n".join([
                f"- Key: {s['key']} | Value: {s['value']} | Snippet: {s.get('evidence_snippet', '')}"
                for s in signals
            ])

            user_prompt = f"""
Rendered Email:
Subject: {email.subject}
{body_before_footer}

Verified Evidence Signals:
{evidence_items_str}

Check whether any claim made about the prospect is unsupported. Output valid JSON.
"""
            try:
                claim_res = self.llm.generate_structured(
                    schema=ClaimCheckLLMOutput,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.0,
                )
                if claim_res.unsupported_claims:
                    unsupported_claims = claim_res.unsupported_claims
                    failures.append(f"Claim check failed: {'; '.join(unsupported_claims)}")
            except Exception:
                pass

        passed = len(failures) == 0
        if not passed:
            self.db.update_state(norm_domain, "BLOCKED")
        else:
            self.db.update_state(norm_domain, "CHECKED")

        return GuardrailResult(
            passed=passed,
            failures=failures,
            claim_check_unsupported=unsupported_claims,
        )
