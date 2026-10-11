import json
import re
from pathlib import Path
from typing import Any

from agent.config import load_upthrust_config, PROJECT_ROOT
from agent.db import Database
from agent.llm import LLMClient
from agent.models import (
    EnrichmentProfile,
    PainPoint,
    Qualification,
    QualificationLLMOutput,
    TriggerEvent,
)

AGENCY_KEYWORDS = [
    "digital marketing agency", "marketing agency", "seo agency", "growth agency",
    "advertising agency", "creative agency", "performance agency", "media agency",
]

DIRECTORY_KEYWORDS = [
    "business directory", "find local businesses", "marketplace", "yellow pages",
    "directory of", "browse companies",
]


class QualificationStep:
    def __init__(self, db: Database, llm: LLMClient | None = None):
        self.db = db
        self.llm = llm or LLMClient()
        self.cfg = load_upthrust_config()

    def _check_hard_disqualifiers(
        self,
        domain: str,
        company_name: str,
        enrichment: EnrichmentProfile | None,
        source: str = "seed",
    ) -> str | None:
        """Evaluate hard disqualifiers strictly in code without LLM."""
        if source == "control":
            return "control_sample_disqualified"

        if not enrichment:
            return "no_commercial_site"

        searchable_text = " ".join([
            enrichment.title or "",
            enrichment.meta_description or "",
            " ".join(enrichment.headings),
            enrichment.text_excerpt[:1500],
        ]).lower()

        # 1. Agency detection (competitor)
        for kw in AGENCY_KEYWORDS:
            if kw in searchable_text:
                return f"is_marketing_agency ({kw})"

        # 2. Directory or marketplace
        for kw in DIRECTORY_KEYWORDS:
            if kw in searchable_text:
                return f"directory_or_marketplace ({kw})"

        # 3. Enterprise indicator
        if any(w in searchable_text for w in ["nyse:", "nasdaq:", "fortune 500", "enterprise cloud platform for 100,000+"]):
            return "enterprise_over_1000"

        # 4. Non-commercial site
        if any(w in searchable_text for w in ["personal blog", "student project", "wikipedia"]):
            return "no_commercial_site"

        return None

    def run(self, domain: str, candidate_info: dict[str, Any] | None = None) -> Qualification:
        norm_domain = domain.strip().lower()
        enrichment_data = self.db.get_enrichment(norm_domain)
        prospect_data = self.db.get_prospect(norm_domain) or candidate_info or {}

        enrichment = None
        signals_map = {}
        if enrichment_data:
            enrichment = EnrichmentProfile(
                domain=norm_domain,
                title=enrichment_data.get("title"),
                meta_description=enrichment_data.get("meta_description"),
                headings=enrichment_data.get("headings", []),
                signals=enrichment_data.get("signals", []),
                emails_found=enrichment_data.get("emails_found", []),
                errors=enrichment_data.get("errors", []),
            )
            for s in enrichment_data.get("signals", []):
                signals_map[s["key"]] = s

        # Step 1: Evaluate hard disqualifiers
        source = prospect_data.get("source", "seed")
        disqualifier = self._check_hard_disqualifiers(
            norm_domain,
            prospect_data.get("company_name", norm_domain),
            enrichment,
            source=source,
        )

        scoring_cfg = self.cfg.get("scoring", {})
        weights = scoring_cfg.get("weights", {"icp_match": 35, "need_signal": 35, "reachability": 15, "budget_signal": 15})
        threshold = scoring_cfg.get("threshold", 65)
        min_evidence_points = scoring_cfg.get("min_evidence_backed_pain_points", 1)

        if disqualifier:
            # Short-circuit without LLM
            qual = Qualification(
                subscores={"icp_match": 20, "need_signal": 20, "reachability": 20, "budget_signal": 20},
                disqualifier=disqualifier,
                primary_service="landing_pages_cro",
                pain_points=[],
                reasons_for=[],
                reasons_against=[f"Disqualified by rule: {disqualifier}"],
                final_score=20.0,
                fit=False,
            )
            self.db.save_qualification(norm_domain, qual)
            self.db.update_state(norm_domain, "REJECTED")
            return qual

        # Step 2: LLM scoring
        prompt_file = PROJECT_ROOT / "src" / "agent" / "prompts" / "qualify.md"
        system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""

        signals_summary = "\n".join([
            f"- Key: {s['key']} | Value: {s['value']} | Evidence: {s.get('evidence_snippet', '')}"
            for s in (enrichment_data.get("signals", []) if enrichment_data else [])
        ])

        user_prompt = f"""
Candidate:
- Company Name: {prospect_data.get('company_name', norm_domain)}
- Domain: {norm_domain}
- Industry: {prospect_data.get('industry', 'Unknown')}
- Location: {prospect_data.get('location', 'Unknown')}

Verified Signals:
{signals_summary}

Page Content Excerpt:
<untrusted_page_content>
{enrichment.text_excerpt if enrichment else 'No content fetched'}
</untrusted_page_content>

Please evaluate and score this prospect according to instructions. Output valid JSON.
"""

        llm_out = self.llm.generate_structured(
            schema=QualificationLLMOutput,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.0,
        )

        # Step 3: Validate pain point evidence keys against actual signals
        valid_pain_points: list[PainPoint] = []
        for pp in llm_out.pain_points:
            verified_keys = [k for k in pp.evidence_keys if k in signals_map]
            if verified_keys:
                valid_pain_points.append(PainPoint(text=pp.text, evidence_keys=verified_keys))

        # Compute final score in code
        score_val = (
            weights.get("icp_match", 35) * llm_out.subscores.get("icp_match", 0)
            + weights.get("need_signal", 35) * llm_out.subscores.get("need_signal", 0)
            + weights.get("reachability", 15) * llm_out.subscores.get("reachability", 0)
            + weights.get("budget_signal", 15) * llm_out.subscores.get("budget_signal", 0)
        ) / 100.0

        is_fit = (
            (score_val >= threshold)
            and (llm_out.disqualifier is None)
            and (len(valid_pain_points) >= min_evidence_points)
        )

        qual = Qualification(
            subscores=llm_out.subscores,
            disqualifier=llm_out.disqualifier,
            primary_service=llm_out.primary_service,
            pain_points=valid_pain_points,
            trigger_event=llm_out.trigger_event,
            reasons_for=llm_out.reasons_for,
            reasons_against=llm_out.reasons_against,
            final_score=round(score_val, 1),
            fit=is_fit,
        )

        self.db.save_qualification(norm_domain, qual)
        self.db.update_state(norm_domain, "QUALIFIED" if is_fit else "REJECTED")
        return qual
