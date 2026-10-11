import pytest
from unittest.mock import MagicMock
from agent.db import Database
from agent.netsafe import SafeFetcher
from agent.steps.enrich import EnrichmentStep


@pytest.fixture
def tmp_db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


SHOPIFY_STORE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Modern Goods - Sustainable Home Essentials</title>
    <meta name="description" content="Shop modern sustainable home goods and kitchen essentials.">
    <script src="https://connect.facebook.net/en_US/fbevents.js"></script>
    <script src="https://www.googletagmanager.com/gtag/js?id=G-12345ABC"></script>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Product", "name": "Ceramic Pan"}
    </script>
</head>
<body>
    <script>window.Shopify = {theme: "Dawn"};</script>
    <h1>Sustainable Kitchen Essentials</h1>
    <form action="/cart/add" method="post"><button type="submit">Add to Cart</button></form>
    <a href="mailto:support@moderngoods.com">Contact Us</a>
</body>
</html>
"""

BARE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Hi</title>
</head>
<body>
    <p>Welcome to our plain website with no tags.</p>
</body>
</html>
"""

ROBOTS_TXT_DISALLOW_GPT = """
User-agent: *
Allow: /

User-agent: GPTBot
Disallow: /
"""


def test_enrich_extracts_tracking_and_platform_signals(tmp_db):
    mock_fetcher = MagicMock(spec=SafeFetcher)
    mock_fetcher.fetch.side_effect = [
        (200, SHOPIFY_STORE_HTML, "https://moderngoods.com"),
        (200, "User-agent: *\nAllow: /", "https://moderngoods.com/robots.txt"),
        (404, "", "https://moderngoods.com/llms.txt"),
    ]

    enrich_step = EnrichmentStep(db=tmp_db, fetcher=mock_fetcher)
    profile = enrich_step.run("moderngoods.com")

    sig_dict = profile.signal_dict()
    assert sig_dict["meta_pixel_present"] is True
    assert sig_dict["ga4_present"] is True
    assert sig_dict["platform_hint"] == "Shopify"
    assert sig_dict["title_missing_or_weak"] is False
    assert sig_dict["meta_description_missing"] is False
    assert "support@moderngoods.com" in profile.emails_found


def test_enrich_detects_weak_seo_and_missing_tracking(tmp_db):
    mock_fetcher = MagicMock(spec=SafeFetcher)
    mock_fetcher.fetch.side_effect = [
        (200, BARE_HTML, "https://barebones.org"),
        (404, "", "https://barebones.org/robots.txt"),
        (404, "", "https://barebones.org/llms.txt"),
    ]

    enrich_step = EnrichmentStep(db=tmp_db, fetcher=mock_fetcher)
    profile = enrich_step.run("barebones.org")

    sig_dict = profile.signal_dict()
    assert sig_dict["meta_pixel_present"] is False
    assert sig_dict["ga4_present"] is False
    assert sig_dict["title_missing_or_weak"] is True
    assert sig_dict["meta_description_missing"] is True


def test_enrich_detects_robots_blocks_gptbot(tmp_db):
    mock_fetcher = MagicMock(spec=SafeFetcher)
    mock_fetcher.fetch.side_effect = [
        (200, "<html><title>Tech Blog with AI block</title><body><h1>Tech</h1></body></html>", "https://techcorp.io"),
        (200, ROBOTS_TXT_DISALLOW_GPT, "https://techcorp.io/robots.txt"),
        (404, "", "https://techcorp.io/llms.txt"),
    ]

    enrich_step = EnrichmentStep(db=tmp_db, fetcher=mock_fetcher)
    profile = enrich_step.run("techcorp.io")

    sig_dict = profile.signal_dict()
    assert sig_dict["robots_blocks_gptbot"] is True
