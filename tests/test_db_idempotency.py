import pytest
from datetime import datetime, timezone
from agent.db import Database
from agent.models import Candidate, SendResult


@pytest.fixture
def db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


def test_unique_domain_constraint_on_upsert(db):
    cand = Candidate(
        company_name="Acme Corp",
        domain="acme.com",
        website_url="https://acme.com",
    )
    first = db.upsert_candidate(cand)
    assert first is True

    # Second upsert with same domain must return False (deduplicated)
    second = db.upsert_candidate(cand)
    assert second is False


def test_state_transitions(db):
    cand = Candidate(
        company_name="Acme Corp",
        domain="acme.com",
        website_url="https://acme.com",
    )
    db.upsert_candidate(cand)
    assert db.get_prospect("acme.com")["state"] == "DISCOVERED"

    db.update_state("acme.com", "ENRICHED")
    assert db.get_prospect("acme.com")["state"] == "ENRICHED"

    db.update_state("acme.com", "QUALIFIED")
    assert db.get_prospect("acme.com")["state"] == "QUALIFIED"


def test_idempotent_send_prevents_duplicate_send(db):
    cand = Candidate(
        company_name="Acme Corp",
        domain="acme.com",
        website_url="https://acme.com",
    )
    db.upsert_candidate(cand)
    assert not db.has_successful_send("acme.com")

    # Record first send
    send_res = SendResult(
        mode="test",
        intended_to="founder@acme.com",
        actual_to="test@upthrust.local",
        status="sent",
        message_id="<msg-123@upthrust.com>",
        sent_at=datetime.now(timezone.utc),
    )
    db.record_send("acme.com", send_res)

    assert db.has_successful_send("acme.com") is True

    # Query latest send
    rec = db.get_send("acme.com")
    assert rec["status"] == "sent"
    assert rec["message_id"] == "<msg-123@upthrust.com>"
