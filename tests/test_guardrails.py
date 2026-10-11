import pytest
from agent.db import Database
from agent.models import ComposedEmail, Signal
from agent.steps.guardrails import GuardrailsStep


@pytest.fixture
def tmp_db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


def test_guardrails_catches_unfilled_placeholder(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    email = ComposedEmail(
        template_id="site_gap",
        subject="Quick question about {{ company_name }}'s website",
        body_text="Hi there,\n\nI noticed {{ observation }}.\n\nAlex",
        variables={},
    )
    result = step.run("example.com", email)
    assert not result.passed
    assert any("unfilled template markers" in f for f in result.failures)


def test_guardrails_catches_subject_too_long(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    long_subject = "This is an extremely long subject line that completely exceeds sixty characters in total length"
    email = ComposedEmail(
        template_id="site_gap",
        subject=long_subject,
        body_text="Hi there,\n\nShort body.\n\nWorth a chat?\n\nAlex",
        variables={},
    )
    result = step.run("example.com", email)
    assert not result.passed
    assert any("Subject length" in f for f in result.failures)


def test_guardrails_catches_banned_phrase(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    email = ComposedEmail(
        template_id="site_gap",
        subject="Quick question",
        body_text="Hi there,\n\nI hope this email finds you well! We offer guaranteed results.\n\nWorth a chat?\n\nAlex",
        variables={},
    )
    result = step.run("example.com", email)
    assert not result.passed
    assert any("banned phrase" in f.lower() for f in result.failures)


def test_guardrails_catches_double_question_mark(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    email = ComposedEmail(
        template_id="site_gap",
        subject="Quick question",
        body_text="Hi there,\n\nAre you looking to scale? Would you be open to a 15-minute call?\n\nAlex",
        variables={},
    )
    result = step.run("example.com", email)
    assert not result.passed
    assert any("multiple question marks" in f.lower() for f in result.failures)


def test_guardrails_catches_foreign_url(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    email = ComposedEmail(
        template_id="site_gap",
        subject="Quick question",
        body_text="Hi there,\n\nCheck out our deck at https://spammy-links.com/pitch.\n\nWorth a chat?\n\nAlex",
        variables={},
    )
    result = step.run("example.com", email)
    assert not result.passed
    assert any("Forbidden URL" in f for f in result.failures)


def test_guardrails_catches_suppressed_domain(tmp_db):
    step = GuardrailsStep(db=tmp_db)
    tmp_db.add_suppression("blocked.com", reason="opted out")
    email = ComposedEmail(
        template_id="site_gap",
        subject="Quick question",
        body_text="Hi there,\n\nThis is a clean email.\n\nWorth a chat?\n\nAlex",
        variables={},
    )
    result = step.run("blocked.com", email)
    assert not result.passed
    assert any("suppression list" in f for f in result.failures)
