import pytest
from jinja2 import Environment, StrictUndefined, UndefinedError
from agent.config import load_templates_config

templates_cfg = load_templates_config()
jinja_env = Environment(undefined=StrictUndefined, autoescape=False)


def test_templates_load_and_have_required_fields():
    templates = templates_cfg.get("templates", [])
    assert len(templates) >= 4
    for t in templates:
        assert "id" in t
        assert "name" in t
        assert "subject" in t
        assert "body" in t
        assert "min_words" in t
        assert "max_words" in t


def test_site_gap_template_renders_and_word_count():
    site_gap = next(t for t in templates_cfg["templates"] if t["id"] == "site_gap")
    body_tmpl = jinja_env.from_string(site_gap["body"])

    sample_vars = {
        "first_name": "Sarah",
        "company_name": "Glow Cosmetics",
        "observation": "I noticed your product pages lack Meta Pixel and GA4 conversion tracking tags, despite driving paid traffic.",
        "consequence": "This likely makes it difficult to understand customer acquisition costs and leads to wasted advertising budget.",
        "icp_phrase": "growing ecommerce brands",
        "proof_point": "We scaled a similar beauty brand to 2.8x ROAS last quarter.",
        "cta_question": "Worth a quick 15-minute chat this week?",
        "sender_name": "Alex Mercer",
        "sender_title": "Growth Lead",
    }

    rendered = body_tmpl.render(**sample_vars)
    words = rendered.split()
    word_count = len(words)

    assert site_gap["min_words"] <= word_count <= site_gap["max_words"]
    assert "Hi Sarah," in rendered
    assert "Glow Cosmetics" in rendered
    assert "Alex Mercer" in rendered


def test_template_missing_variable_raises():
    site_gap = next(t for t in templates_cfg["templates"] if t["id"] == "site_gap")
    body_tmpl = jinja_env.from_string(site_gap["body"])

    incomplete_vars = {
        "first_name": "Sarah",
        # company_name omitted
        "observation": "test",
        "consequence": "test",
        "icp_phrase": "test",
        "proof_point": "",
        "cta_question": "test?",
        "sender_name": "Alex",
        "sender_title": "Lead",
    }

    with pytest.raises(UndefinedError):
        body_tmpl.render(**incomplete_vars)


def test_proof_point_optional_renders_both_ways():
    site_gap = next(t for t in templates_cfg["templates"] if t["id"] == "site_gap")
    body_tmpl = jinja_env.from_string(site_gap["body"])

    vars_with_proof = {
        "first_name": "Sarah",
        "company_name": "Acme",
        "observation": "I spent a few minutes looking at your website analytics tags.",
        "consequence": "This likely creates gaps in conversion tracking and ROI reporting.",
        "icp_phrase": "ecommerce teams",
        "proof_point": "We helped an ecommerce brand achieve 2.5x ROAS.",
        "cta_question": "Open to a quick call?",
        "sender_name": "Alex",
        "sender_title": "Lead",
    }
    rendered_with = body_tmpl.render(**vars_with_proof)
    assert "2.5x ROAS" in rendered_with

    vars_without_proof = dict(vars_with_proof)
    vars_without_proof["proof_point"] = ""
    rendered_without = body_tmpl.render(**vars_without_proof)
    assert "2.5x ROAS" not in rendered_without
