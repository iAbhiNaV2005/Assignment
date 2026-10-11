from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl


class Candidate(BaseModel):
    company_name: str
    domain: str  # normalised, lowercase, no scheme or www
    website_url: str
    industry: str | None = None
    location: str | None = None
    size_estimate: str | None = None
    why_relevant: str | None = None
    source_url: str | None = None
    source: Literal["exa", "yutori", "seed", "control"] = "seed"


class Signal(BaseModel):
    key: str  # e.g. "meta_pixel_present", "robots_blocks_gptbot"
    value: Any = None
    evidence_url: str
    evidence_snippet: str | None = None


class EnrichmentProfile(BaseModel):
    domain: str
    fetched_pages: list[str] = Field(default_factory=list)
    title: str | None = None
    meta_description: str | None = None
    headings: list[str] = Field(default_factory=list)
    text_excerpt: str = ""  # capped excerpt of untrusted page content
    signals: list[Signal] = Field(default_factory=list)
    emails_found: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def signal_dict(self) -> dict[str, Any]:
        return {s.key: s.value for s in self.signals}


class PainPoint(BaseModel):
    text: str
    evidence_keys: list[str] = Field(default_factory=list)


class TriggerEvent(BaseModel):
    event_type: str
    text: str
    evidence_keys: list[str] = Field(default_factory=list)


class QualificationLLMOutput(BaseModel):
    subscores: dict[Literal["icp_match", "need_signal", "reachability", "budget_signal"], int]
    disqualifier: str | None = None
    primary_service: str
    pain_points: list[PainPoint] = Field(default_factory=list)
    trigger_event: TriggerEvent | None = None
    reasons_for: list[str] = Field(default_factory=list)
    reasons_against: list[str] = Field(default_factory=list)


class Qualification(BaseModel):
    subscores: dict[Literal["icp_match", "need_signal", "reachability", "budget_signal"], int]
    disqualifier: str | None = None
    primary_service: str
    pain_points: list[PainPoint] = Field(default_factory=list)
    trigger_event: TriggerEvent | None = None
    reasons_for: list[str] = Field(default_factory=list)
    reasons_against: list[str] = Field(default_factory=list)
    final_score: float  # Computed in code from weights
    fit: bool  # score >= threshold and no disqualifier and enough evidence pain points


class Contact(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    source: Literal["hunter_domain", "hunter_finder", "site_mailto", "pattern_guess", "role_inbox"]
    verification: Literal["valid", "accept_all", "unknown", "invalid", "unverified"] = "unverified"
    confidence: int | None = None


class ComposedEmail(BaseModel):
    template_id: str
    subject: str
    body_text: str
    variables: dict[str, Any] = Field(default_factory=dict)
    evidence_keys_used: list[str] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    claim_check_unsupported: list[str] = Field(default_factory=list)


class SendResult(BaseModel):
    mode: Literal["test", "live", "dryrun"]
    intended_to: str
    actual_to: str
    status: Literal["sent", "failed", "skipped"]
    message_id: str | None = None
    provider_response: str | None = None
    error: str | None = None
    sent_at: datetime | None = None
