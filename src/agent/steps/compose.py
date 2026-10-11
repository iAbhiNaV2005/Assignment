import re
from typing import Any
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, Field

from agent.config import PROJECT_ROOT, load_templates_config, load_upthrust_config
from agent.db import Database
from agent.llm import LLMClient
from agent.models import ComposedEmail, Contact, Qualification


class VariablesLLMOutput(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)
    evidence_keys_used: list[str] = Field(default_factory=list)


def clean_company_name(name: str) -> str:
    cleaned = re.sub(r",?\s+(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|Co\.?)$", "", name, flags=re.I).strip()
    return cleaned or name


class ComposeStep:
    def __init__(self, db: Database, llm: LLMClient | None = None):
        self.db = db
        self.llm = llm or LLMClient()
        self.templates_cfg = load_templates_config()
        self.upthrust_cfg = load_upthrust_config()
        self.jinja_env = Environment(undefined=StrictUndefined, autoescape=False)

    def _select_template(self, qual: Qualification) -> dict[str, Any]:
        templates = self.templates_cfg.get("templates", [])

        # 1. If trigger event with evidence exists -> short_trigger
        if qual.trigger_event and qual.trigger_event.evidence_keys:
            for t in templates:
                if t.get("id") == "short_trigger":
                    return t

        # 2. Match service_tags containing primary_service
        for t in templates:
            if qual.primary_service in t.get("service_tags", []):
                return t

        # 3. Fallback to first template (site_gap)
        return templates[0]

    def _get_service_phrase(self, service_id: str) -> str:
        services = self.upthrust_cfg.get("services", [])
        for s in services:
            if s.get("id") == service_id:
                return s.get("phrase", service_id)
        return "growth marketing"

    def _get_proof_point(self, service_id: str) -> str:
        proof_points = self.upthrust_cfg.get("proof_points", [])
        for p in proof_points:
            if p.get("verified") is True and service_id in p.get("service_tags", []):
                return p.get("text", "")
        return ""

    def run(self, domain: str) -> ComposedEmail:
        norm_domain = domain.strip().lower()
        prospect = self.db.get_prospect(norm_domain) or {}
        enrichment = self.db.get_enrichment(norm_domain) or {}
        qual_data = self.db.get_qualification(norm_domain)
        contact_data = self.db.get_contact(norm_domain) or {}

        if not qual_data:
            raise ValueError(f"Cannot compose email for {norm_domain}: not qualified")

        qual = Qualification(
            subscores=qual_data["subscores"],
            disqualifier=qual_data.get("disqualifier"),
            primary_service=qual_data["primary_service"],
            pain_points=qual_data.get("pain_points", []),
            trigger_event=qual_data.get("trigger_event"),
            reasons_for=qual_data.get("reasons_for", []),
            reasons_against=qual_data.get("reasons_against", []),
            final_score=qual_data["final_score"],
            fit=qual_data["fit"],
        )

        template = self._select_template(qual)
        template_id = template["id"]

        # Prepare non-LLM variables
        cta_options = self.templates_cfg.get("shared", {}).get("cta_options", ["Worth a quick 15-minute chat?"])
        # Rotate based on domain hash
        cta_idx = abs(hash(norm_domain)) % len(cta_options)
        cta_question = cta_options[cta_idx]

        company_clean = clean_company_name(prospect.get("company_name", norm_domain))
        first_name = contact_data.get("first_name") or "there"
        if first_name.lower() in ("info", "sales", "admin", "support", "hello", "team"):
            first_name = "there"

        sender = self.upthrust_cfg.get("sender", {})
        sender_name = sender.get("name", "Upthrust Growth Team")
        sender_title = sender.get("title", "Growth Specialist")
        proof_point = self._get_proof_point(qual.primary_service)
        service_phrase = self._get_service_phrase(qual.primary_service)

        # Prepare prompt for LLM variables
        prompt_file = PROJECT_ROOT / "src" / "agent" / "prompts" / "fill_variables.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""

        var_specs = dict(self.templates_cfg.get("shared", {}).get("llm_variables", {}))
        if "extra_llm_variables" in template:
            var_specs.update(template["extra_llm_variables"])

        signals = enrichment.get("signals", [])
        signals_text = "\n".join([
            f"- {s['key']}: {s['value']} (Snippet: {s.get('evidence_snippet', '')})"
            for s in signals
        ])
        pain_points_text = "\n".join([
            f"- {p.text if hasattr(p, 'text') else p.get('text', '')} (Keys: {p.evidence_keys if hasattr(p, 'evidence_keys') else p.get('evidence_keys', [])})"
            for p in qual.pain_points
        ])

        user_prompt = f"""
Candidate: {company_clean} ({norm_domain})
Primary Service Focus: {qual.primary_service} ({service_phrase})
Template Selected: {template_id} ({template['name']})

Verified Evidence Signals:
{signals_text}

Evidence-Backed Pain Points:
{pain_points_text}

Variable Specifications to Fill:
{var_specs}

Generate the exact JSON containing 'variables' and 'evidence_keys_used'.
"""

        llm_out = self.llm.generate_structured(
            schema=VariablesLLMOutput,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )

        all_vars = dict(llm_out.variables)
        all_vars.update({
            "first_name": first_name,
            "company_name": company_clean,
            "cta_question": cta_question,
            "sender_name": sender_name,
            "sender_title": sender_title,
            "proof_point": proof_point,
            "service_phrase": service_phrase,
        })

        # Render Subject & Body
        subject_tmpl = self.jinja_env.from_string(template["subject"])
        subject_rendered = subject_tmpl.render(**all_vars)

        body_tmpl = self.jinja_env.from_string(template["body"])
        body_core = body_tmpl.render(**all_vars).strip()

        # Append Footer
        opt_out = sender.get("opt_out_line", "If this isn't relevant, reply 'no thanks'.")
        postal = sender.get("postal_address", "Austin, TX, US")
        full_body = f"{body_core}\n\n--\n{opt_out}\n{postal}"

        composed = ComposedEmail(
            template_id=template_id,
            subject=subject_rendered,
            body_text=full_body,
            variables=all_vars,
            evidence_keys_used=llm_out.evidence_keys_used,
        )

        self.db.save_email(norm_domain, composed)
        self.db.update_state(norm_domain, "COMPOSED")
        return composed
