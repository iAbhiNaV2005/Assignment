from unittest.mock import MagicMock
import pytest

from agent.clients.exa import ExaClient
from agent.config import EnvSettings
from agent.db import Database
from agent.llm import LLMClient
from agent.models import Candidate
from agent.steps.contact import ContactStep
from agent.steps.discover import (
    CandidateItemLLM,
    DiscoveryStep,
    ExaCandidateExtraction,
    ExaSearchProvider,
    SeedSearchProvider,
)


@pytest.fixture
def tmp_db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


def test_seed_search_provider_returns_candidates():
    provider = SeedSearchProvider(with_control=True)
    candidates = provider.search_candidates(limit=5)
    assert len(candidates) > 0
    assert any(c.domain for c in candidates)


def test_exa_search_provider_extracts_candidates_with_llm():
    mock_exa = MagicMock(spec=ExaClient)
    mock_exa.search.return_value = [
        {
            "id": "https://casper.com",
            "title": "Casper Sleep",
            "url": "https://casper.com",
            "text": "DTC sleep wellness mattress brand",
        },
        {
            "id": "https://ridge.com",
            "title": "Ridge Wallet",
            "url": "https://ridge.com",
            "text": "Everyday carry accessories brand",
        },
    ]

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_structured.return_value = ExaCandidateExtraction(
        candidates=[
            CandidateItemLLM(
                company_name="Casper Sleep",
                domain="casper.com",
                website_url="https://casper.com",
                industry="ecommerce",
                location="New York, NY",
                size_estimate="50-100",
                why_relevant="Fast growing DTC brand",
            ),
            CandidateItemLLM(
                company_name="Ridge Wallet",
                domain="ridge.com",
                website_url="https://ridge.com",
                industry="ecommerce",
                location="Santa Monica, CA",
                size_estimate="20-50",
                why_relevant="Everyday carry gear",
            ),
        ]
    )

    provider = ExaSearchProvider(exa_client=mock_exa, llm_client=mock_llm)
    candidates = provider.search_candidates(limit=5)

    assert len(candidates) == 2
    assert candidates[0].domain == "casper.com"
    assert candidates[0].source == "exa"
    assert candidates[1].domain == "ridge.com"
    assert candidates[1].source == "exa"
    assert mock_llm.generate_structured.call_count == 1


def test_discovery_step_auto_fallback_to_seed_when_no_keys(tmp_db):
    settings = EnvSettings(exa_api_key="", yutori_api_key="")
    step = DiscoveryStep(db=tmp_db, settings=settings)

    candidates = step.run(source="auto", limit=5, with_control=True)
    assert len(candidates) > 0
    assert any(c.source in ("seed", "control") for c in candidates)


def test_discovery_step_falls_back_to_seed_on_exa_error(tmp_db):
    mock_exa = MagicMock(spec=ExaClient)
    mock_exa.search.side_effect = RuntimeError("Exa network error")

    settings = EnvSettings(exa_api_key="test-exa-key")
    step = DiscoveryStep(db=tmp_db, settings=settings, exa_client=mock_exa)

    # Should not crash, must fall back to seed
    candidates = step.run(source="exa", limit=5, with_control=True)
    assert len(candidates) > 0
    assert any(c.source in ("seed", "control") for c in candidates)


def test_contact_step_without_hunter_key_falls_back_to_mailto(tmp_db):
    settings = EnvSettings(hunter_api_key="")
    step = ContactStep(db=tmp_db)
    step.hunter_client.settings = settings

    domain = "shopmodern.com"
    # Seed enrichment with mailto address
    from agent.models import EnrichmentProfile
    tmp_db.save_enrichment(EnrichmentProfile(domain=domain, emails_found=["contact@shopmodern.com"]))

    contact = step.run(domain, safe_mode=True)
    assert contact is not None
    assert contact.email == "contact@shopmodern.com"
    assert contact.source == "site_mailto"
    assert contact.verification == "unverified"


def test_contact_step_without_hunter_and_without_mailto_falls_back_to_role_inbox(tmp_db):
    settings = EnvSettings(hunter_api_key="")
    step = ContactStep(db=tmp_db)
    step.hunter_client.settings = settings

    domain = "shopmodern.com"
    # No enrichment saved, no mailto addresses
    contact = step.run(domain, safe_mode=False)
    assert contact is not None
    assert contact.email == "hello@shopmodern.com"
    assert contact.source == "role_inbox"
    assert contact.verification == "unverified"
