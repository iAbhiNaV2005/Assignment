from pathlib import Path
from unittest.mock import MagicMock
import pytest
from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.clients.mailer import DryRunMailer
from agent.clients.sheets import SheetsMirror
from agent.config import EnvSettings
from agent.db import Database
from agent.llm import LLMClient
from agent.models import (
    Candidate,
    PainPoint,
    QualificationLLMOutput,
)
from agent.pipeline import OutboundPipeline
from agent.steps.compose import VariablesLLMOutput
from agent.steps.guardrails import ClaimCheckLLMOutput


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "test.db"
    cache_dir = tmp_path / "cache"
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    db = Database(db_path=db_file)
    cache = DiskCache(cache_dir=cache_dir)
    budget = BudgetTracker()
    mailer = DryRunMailer(runs_dir=runs_dir)
    sheets = SheetsMirror(runs_dir=runs_dir)

    settings = EnvSettings(
        mail_provider="dryrun",
        safe_mode=True,
        test_recipient="test-qa@upthrust.local",
    )

    return {
        "db": db,
        "cache": cache,
        "budget": budget,
        "mailer": mailer,
        "sheets": sheets,
        "runs_dir": runs_dir,
        "settings": settings,
    }


def test_e2e_full_pipeline_dry_run(test_env):
    db = test_env["db"]
    domain = "brightsmile-dental.com"

    # Add candidate to pool
    cand = Candidate(
        company_name="Bright Smile Dental",
        domain=domain,
        website_url=f"https://{domain}",
        industry="health_medical",
        location="Austin, TX, US",
        source="seed",
    )
    db.upsert_candidate(cand)

    # Setup mock LLM
    mock_llm = MagicMock(spec=LLMClient)

    def fake_structured(schema, prompt, system_prompt=None, temperature=0.0):
        if schema == QualificationLLMOutput:
            return QualificationLLMOutput(
                subscores={"icp_match": 85, "need_signal": 80, "reachability": 75, "budget_signal": 75},
                disqualifier=None,
                primary_service="landing_pages_cro",
                pain_points=[
                    PainPoint(
                        text="Homepage lacks conversion tracking pixels for patient bookings.",
                        evidence_keys=["meta_pixel_present"],
                    )
                ],
                reasons_for=["Established dental clinic with booking intent"],
                reasons_against=[],
            )
        elif schema == VariablesLLMOutput:
            return VariablesLLMOutput(
                variables={
                    "observation": "I noticed your clinic appointment page lacks Meta Pixel tracking, despite active social channels.",
                    "consequence": "This likely makes it difficult to measure which ads drive new patient bookings, leading to wasted budget.",
                    "icp_phrase": "independent dental practices",
                },
                evidence_keys_used=["meta_pixel_present"],
            )
        elif schema == ClaimCheckLLMOutput:
            return ClaimCheckLLMOutput(unsupported_claims=[])
        raise ValueError(f"Unknown schema {schema}")

    mock_llm.generate_structured.side_effect = fake_structured

    pipeline = OutboundPipeline(
        db=db,
        settings=test_env["settings"],
        cache=test_env["cache"],
        budget=test_env["budget"],
        llm=mock_llm,
        mailer=test_env["mailer"],
    )
    # Inject test sheets mirror
    pipeline.record_step.sheets = test_env["sheets"]

    # Mock website fetch to avoid external network call
    pipeline.enrich_step.fetcher.fetch = MagicMock(return_value=(
        200,
        "<html><title>Bright Smile Dental Clinic</title><body><h1>Modern Dentistry</h1><a href='mailto:info@brightsmile-dental.com'>Contact</a></body></html>",
        f"https://{domain}",
    ))

    # Process prospect
    res = pipeline.process_prospect(domain=domain, run_id="e2e_test_run")

    assert res["status"] == "sent"
    assert db.get_prospect(domain)["state"] == "LOGGED"

    # Verify .eml file created in runs_dir
    eml_files = list(test_env["runs_dir"].glob("*.eml"))
    assert len(eml_files) == 1
    eml_text = eml_files[0].read_text(encoding="utf-8")
    assert "Bright Smile Dental" in eml_text
    assert "[TEST SEND." in eml_text

    # Verify results.csv exists and has row
    results_csv = test_env["runs_dir"] / "results.csv"
    assert results_csv.exists()
    csv_text = results_csv.read_text(encoding="utf-8")
    assert "brightsmile-dental.com" in csv_text
    assert "landing_pages_cro" in csv_text
