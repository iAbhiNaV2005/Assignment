import pytest
from unittest.mock import MagicMock
from agent.db import Database
from agent.llm import LLMClient
from agent.models import (
    Candidate,
    EnrichmentProfile,
    PainPoint,
    QualificationLLMOutput,
    Signal,
)
from agent.steps.qualify import QualificationStep


@pytest.fixture
def tmp_db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


def test_disqualifies_marketing_agency_in_code_without_llm(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "apexmedia.agency"
    profile = EnrichmentProfile(
        domain=domain,
        title="Apex Media - Premier Digital Marketing Agency",
        meta_description="We are a full-service growth agency and SEO agency.",
        headings=["Top Marketing Agency for Brands"],
        text_excerpt="Apex Media is a digital marketing agency providing SEO and paid ads.",
    )
    tmp_db.save_enrichment(profile)

    qual = step.run(domain)
    assert not qual.fit
    assert "is_marketing_agency" in (qual.disqualifier or "")
    # LLM should never be called when disqualified by hard rules
    mock_llm.generate_structured.assert_not_called()


def test_disqualifies_control_sample_in_code(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "enterprise-giant.com"
    cand = Candidate(
        company_name="Enterprise Giant",
        domain=domain,
        website_url=f"https://{domain}",
        source="control",
    )
    tmp_db.upsert_candidate(cand)

    qual = step.run(domain)
    assert not qual.fit
    assert "control_sample_disqualified" in (qual.disqualifier or "")
    mock_llm.generate_structured.assert_not_called()


def test_qualifies_good_fit_ecommerce_brand(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "solesneakers.com"
    cand = Candidate(
        company_name="Sole Sneakers",
        domain=domain,
        website_url=f"https://{domain}",
        industry="ecommerce",
        source="seed",
    )
    tmp_db.upsert_candidate(cand)

    profile = EnrichmentProfile(
        domain=domain,
        title="Sole Sneakers - Handcrafted Footwear",
        headings=["Shop Handcrafted Sneakers"],
        text_excerpt="Direct to consumer sneaker brand based in Austin.",
        signals=[
            Signal(key="meta_pixel_present", value=False, evidence_url="https://solesneakers.com", evidence_snippet="No Meta Pixel"),
            Signal(key="ga4_present", value=False, evidence_url="https://solesneakers.com", evidence_snippet="No GA4"),
        ],
    )
    tmp_db.save_enrichment(profile)

    mock_llm.generate_structured.return_value = QualificationLLMOutput(
        subscores={"icp_match": 90, "need_signal": 85, "reachability": 80, "budget_signal": 75},
        disqualifier=None,
        primary_service="meta_ads",
        pain_points=[
            PainPoint(text="No Meta Pixel tag installed despite active online store", evidence_keys=["meta_pixel_present"]),
        ],
        reasons_for=["Strong DTC ecommerce fit", "Clear ad tracking gap"],
        reasons_against=[],
    )

    qual = step.run(domain)
    assert qual.fit is True
    assert qual.final_score >= 65
    assert len(qual.pain_points) == 1
    assert qual.primary_service == "meta_ads"


def test_qualifies_good_fit_b2b_saas(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "cloudmetrics.io"
    cand = Candidate(company_name="CloudMetrics", domain=domain, website_url=f"https://{domain}", industry="saas_it_services")
    tmp_db.upsert_candidate(cand)

    profile = EnrichmentProfile(
        domain=domain,
        title="CloudMetrics - Real-time Infrastructure Monitoring",
        signals=[
            Signal(key="robots_blocks_gptbot", value=True, evidence_url="https://cloudmetrics.io/robots.txt", evidence_snippet="Blocks GPTBot"),
        ],
    )
    tmp_db.save_enrichment(profile)

    mock_llm.generate_structured.return_value = QualificationLLMOutput(
        subscores={"icp_match": 85, "need_signal": 80, "reachability": 85, "budget_signal": 80},
        disqualifier=None,
        primary_service="ai_search_visibility",
        pain_points=[
            PainPoint(text="robots.txt blocks AI search crawlers", evidence_keys=["robots_blocks_gptbot"]),
        ],
        reasons_for=["High fit B2B SaaS"],
        reasons_against=[],
    )

    qual = step.run(domain)
    assert qual.fit is True
    assert qual.final_score >= 65


def test_qualifies_good_fit_healthcare_clinic(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "austinspinecare.com"
    cand = Candidate(company_name="Austin Spine Care", domain=domain, website_url=f"https://{domain}", industry="health_medical")
    tmp_db.upsert_candidate(cand)

    profile = EnrichmentProfile(
        domain=domain,
        title="Austin Spine Care Clinic",
        signals=[
            Signal(key="title_missing_or_weak", value=True, evidence_url="https://austinspinecare.com", evidence_snippet="Weak SEO"),
        ],
    )
    tmp_db.save_enrichment(profile)

    mock_llm.generate_structured.return_value = QualificationLLMOutput(
        subscores={"icp_match": 80, "need_signal": 75, "reachability": 75, "budget_signal": 70},
        disqualifier=None,
        primary_service="seo",
        pain_points=[
            PainPoint(text="Weak SEO title metadata hurting local discovery", evidence_keys=["title_missing_or_weak"]),
        ],
        reasons_for=["Local medical clinic in primary service area"],
        reasons_against=[],
    )

    qual = step.run(domain)
    assert qual.fit is True
    assert qual.final_score >= 65


def test_rejects_thin_evidence_low_score(tmp_db):
    mock_llm = MagicMock(spec=LLMClient)
    step = QualificationStep(db=tmp_db, llm=mock_llm)

    domain = "vagueventure.co"
    cand = Candidate(company_name="Vague Venture", domain=domain, website_url=f"https://{domain}", industry="unknown")
    tmp_db.upsert_candidate(cand)

    profile = EnrichmentProfile(domain=domain, title="Vague", signals=[])
    tmp_db.save_enrichment(profile)

    mock_llm.generate_structured.return_value = QualificationLLMOutput(
        subscores={"icp_match": 40, "need_signal": 30, "reachability": 35, "budget_signal": 30},
        disqualifier=None,
        primary_service="seo",
        pain_points=[],
        reasons_for=[],
        reasons_against=["Thin website content", "No clear business model or budget"],
    )

    qual = step.run(domain)
    assert qual.fit is False
    assert qual.final_score < 65
