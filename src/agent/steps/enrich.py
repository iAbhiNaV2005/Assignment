import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from agent.db import Database
from agent.models import EnrichmentProfile, Signal
from agent.netsafe import SafeFetcher, SSRFValidationError, PoliteFetchError


class EnrichmentStep:
    def __init__(self, db: Database, fetcher: SafeFetcher | None = None):
        self.db = db
        self.fetcher = fetcher or SafeFetcher()

    def run(self, domain: str) -> EnrichmentProfile:
        norm_domain = domain.strip().lower()
        base_url = f"https://{norm_domain}"
        profile = EnrichmentProfile(domain=norm_domain)

        # 1. Fetch Homepage
        try:
            status, html_text, final_url = self.fetcher.fetch(base_url)
            profile.fetched_pages.append(final_url)
        except Exception as e:
            profile.errors.append(f"Homepage fetch failed: {e}")
            self.db.update_state(norm_domain, "ENRICH_FAILED")
            self.db.save_enrichment(profile)
            return profile

        soup = BeautifulSoup(html_text, "lxml")

        # Basic metadata
        title_tag = soup.find("title")
        profile.title = title_tag.get_text(strip=True) if title_tag else None

        meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
        if meta_desc and meta_desc.get("content"):
            profile.meta_description = meta_desc["content"].strip()

        # Headings
        h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
        profile.headings = h1s + h2s[:8]

        # Forms and CTAs
        forms = soup.find_all("form")
        buttons = [b.get_text(strip=True) for b in soup.find_all(["button", "a"]) if b.get("role") == "button" or "btn" in (b.get("class") or [])]
        ctas = [btn for btn in buttons if btn and len(btn) < 40]

        # Text excerpt (capped at 6000 chars)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        body_text = soup.get_text(separator=" ", strip=True)
        profile.text_excerpt = body_text[:6000]

        # Emails found on site
        mailtos = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                email_part = href[7:].split("?")[0].strip()
                if "@" in email_part:
                    mailtos.add(email_part.lower())
        profile.emails_found = sorted(list(mailtos))

        # --- Deterministic Signal Extraction ---
        signals: list[Signal] = []

        # Tracking signals
        raw_html_lower = html_text.lower()

        ga4_present = "gtag/js?id=g-" in raw_html_lower or "googletagmanager.com/gtm.js" in raw_html_lower
        signals.append(
            Signal(
                key="ga4_present",
                value=ga4_present,
                evidence_url=final_url,
                evidence_snippet="Google Analytics GA4 tag found in page HTML" if ga4_present else "No GA4 tag detected in page HTML",
            )
        )

        meta_pixel_present = "connect.facebook.net" in raw_html_lower or "fbq(" in raw_html_lower
        signals.append(
            Signal(
                key="meta_pixel_present",
                value=meta_pixel_present,
                evidence_url=final_url,
                evidence_snippet="Meta (Facebook) Pixel detected" if meta_pixel_present else "No Meta Pixel script detected in page source",
            )
        )

        linkedin_pixel = "snap.licdn.com" in raw_html_lower or "_linkedin_partner_id" in raw_html_lower
        signals.append(
            Signal(
                key="linkedin_insight_present",
                value=linkedin_pixel,
                evidence_url=final_url,
                evidence_snippet="LinkedIn Insight Tag detected" if linkedin_pixel else "No LinkedIn Insight Tag detected",
            )
        )

        google_ads_tag = "aw-" in raw_html_lower or "googleads" in raw_html_lower
        signals.append(
            Signal(
                key="google_ads_tag_present",
                value=google_ads_tag,
                evidence_url=final_url,
                evidence_snippet="Google Ads conversion tracking tag detected" if google_ads_tag else "No Google Ads conversion tag found",
            )
        )

        # SEO basics
        title_weak = profile.title is None or len(profile.title) < 12
        signals.append(
            Signal(
                key="title_missing_or_weak",
                value=title_weak,
                evidence_url=final_url,
                evidence_snippet=f"Title: '{profile.title or 'None'}' (length: {len(profile.title) if profile.title else 0})",
            )
        )

        meta_missing = not bool(profile.meta_description)
        signals.append(
            Signal(
                key="meta_description_missing",
                value=meta_missing,
                evidence_url=final_url,
                evidence_snippet=f"Meta description: '{profile.meta_description or 'None'}'",
            )
        )

        signals.append(
            Signal(
                key="h1_count",
                value=len(h1s),
                evidence_url=final_url,
                evidence_snippet=f"Found {len(h1s)} H1 tag(s): {', '.join(h1s[:2]) if h1s else 'None'}",
            )
        )

        # Schemas
        schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        schema_types = []
        for s in schema_scripts:
            try:
                content = s.string or ""
                match = re.search(r'"@type"\s*:\s*"([^"]+)"', content)
                if match:
                    schema_types.append(match.group(1))
            except Exception:
                pass
        signals.append(
            Signal(
                key="schema_types",
                value=schema_types,
                evidence_url=final_url,
                evidence_snippet=f"JSON-LD Schema types: {', '.join(schema_types) if schema_types else 'None'}",
            )
        )

        # Conversion signals
        signals.append(
            Signal(
                key="forms_on_homepage",
                value=len(forms),
                evidence_url=final_url,
                evidence_snippet=f"Page has {len(forms)} HTML form(s)",
            )
        )

        signals.append(
            Signal(
                key="cta_count",
                value=len(ctas),
                evidence_url=final_url,
                evidence_snippet=f"Page has {len(ctas)} call-to-action button(s)",
            )
        )

        testimonials = bool(re.search(r"\b(testimonials|reviews|what our clients say|customer stories)\b", raw_html_lower))
        signals.append(
            Signal(
                key="has_testimonials_or_reviews_text",
                value=testimonials,
                evidence_url=final_url,
                evidence_snippet="Found reviews/testimonials section on page" if testimonials else "No customer reviews or testimonials found on page",
            )
        )

        # Tech stack
        shopify = "cdn.shopify.com" in raw_html_lower or "shopify" in raw_html_lower
        wordpress = "wp-content" in raw_html_lower or "wp-includes" in raw_html_lower
        webflow = "webflow" in raw_html_lower
        platform = "Shopify" if shopify else "WordPress" if wordpress else "Webflow" if webflow else "Custom/Other"
        signals.append(
            Signal(
                key="platform_hint",
                value=platform,
                evidence_url=final_url,
                evidence_snippet=f"Identified site platform: {platform}",
            )
        )

        # Check robots.txt and llms.txt
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            _, r_text, _ = self.fetcher.fetch(robots_url)
            r_lower = r_text.lower()
            gptbot_blocked = "gptbot" in r_lower and "disallow: /" in r_lower
            signals.append(
                Signal(
                    key="robots_blocks_gptbot",
                    value=gptbot_blocked,
                    evidence_url=robots_url,
                    evidence_snippet="robots.txt blocks GPTBot" if gptbot_blocked else "GPTBot is not blocked in robots.txt",
                )
            )
        except Exception:
            signals.append(
                Signal(key="robots_blocks_gptbot", value=False, evidence_url=robots_url, evidence_snippet="robots.txt not found or could not be fetched")
            )

        llms_url = urljoin(base_url, "/llms.txt")
        try:
            s_code, _, _ = self.fetcher.fetch(llms_url)
            llms_present = (s_code == 200)
            signals.append(
                Signal(
                    key="llms_txt_present",
                    value=llms_present,
                    evidence_url=llms_url,
                    evidence_snippet="llms.txt file is present at /llms.txt" if llms_present else "No llms.txt file found",
                )
            )
        except Exception:
            signals.append(
                Signal(key="llms_txt_present", value=False, evidence_url=llms_url, evidence_snippet="No llms.txt found at root")
            )

        # Check trigger events (hiring, launch, funding)
        hiring = bool(re.search(r"\b(we're hiring|now hiring|join our team|careers|open roles)\b", raw_html_lower))
        signals.append(
            Signal(
                key="trigger_hiring",
                value=hiring,
                evidence_url=final_url,
                evidence_snippet="Found hiring/careers mentions on site" if hiring else "No hiring signals found",
            )
        )

        profile.signals = signals
        self.db.save_enrichment(profile)
        self.db.update_state(norm_domain, "ENRICHED")
        return profile
