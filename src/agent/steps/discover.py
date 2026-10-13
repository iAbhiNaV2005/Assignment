from abc import ABC, abstractmethod
import csv
import json
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import random
from pydantic import BaseModel, Field

from agent.clients.exa import ExaClient
from agent.clients.yutori import YutoriClient
from agent.config import DATA_DIR, EnvSettings, load_env_settings, load_upthrust_config
from agent.db import Database
from agent.llm import LLMClient
from agent.models import Candidate
from agent.netsafe import is_safe_ip

BLOCKED_DOMAINS = {
    "clutch.co", "yelp.com", "linkedin.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "yellowpages.com", "g2.com", "capterra.com",
    "trustpilot.com", "crunchbase.com", "wikipedia.org", "youtube.com",
}


def normalize_domain(raw_url_or_domain: str) -> str:
    cleaned = raw_url_or_domain.strip().lower()
    if "://" in cleaned:
        parsed = urlparse(cleaned)
        cleaned = parsed.netloc
    else:
        cleaned = cleaned.split("/")[0]
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    return cleaned.split(":")[0]


def is_domain_valid(domain: str, timeout_s: float = 6.0) -> bool:
    """Check DNS resolution and public IP."""
    norm = normalize_domain(domain)
    if norm in BLOCKED_DOMAINS:
        return False
    try:
        addr_info = socket.getaddrinfo(norm, None)
        has_public_ip = False
        for item in addr_info:
            ip_str = item[4][0]
            if is_safe_ip(ip_str):
                has_public_ip = True
                break
        return has_public_ip
    except Exception:
        return False


def load_candidates_from_seed(
    seed_csv_path: Path = DATA_DIR / "seed_prospects.csv",
    with_control: bool = False,
) -> list[Candidate]:
    if not seed_csv_path.exists():
        return []

    candidates: list[Candidate] = []
    with open(seed_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            is_control = str(row.get("control", "")).lower() in ("true", "1", "yes")
            if is_control and not with_control:
                continue

            domain = normalize_domain(row.get("domain", ""))
            if not domain:
                continue

            candidates.append(
                Candidate(
                    company_name=row.get("company_name", domain),
                    domain=domain,
                    website_url=f"https://{domain}",
                    industry=row.get("industry"),
                    location=row.get("location"),
                    why_relevant=row.get("note"),
                    source="control" if is_control else "seed",
                )
            )
    return candidates


# --- Pluggable SearchProvider Interface ---

class SearchProvider(ABC):
    @abstractmethod
    def search_candidates(self, limit: int = 15, exclude_domains: set[str] | None = None) -> list[Candidate]:
        """Search and return candidate companies."""
        pass


class CandidateItemLLM(BaseModel):
    company_name: str
    domain: str
    website_url: str
    industry: str | None = None
    location: str | None = None
    size_estimate: str | None = None
    why_relevant: str | None = None


class ExaCandidateExtraction(BaseModel):
    candidates: list[CandidateItemLLM] = Field(default_factory=list)


class ExaSearchProvider(SearchProvider):
    """
    Primary discovery provider using Exa AI search + 1 LLM extraction call.
    Runs 2-4 ICP queries, gathers snippets, and extracts filtered commercial candidates.
    """
    def __init__(
        self,
        exa_client: ExaClient | None = None,
        llm_client: LLMClient | None = None,
        settings: EnvSettings | None = None,
    ):
        self.settings = settings or load_env_settings()
        self.exa_client = exa_client or ExaClient(settings=self.settings)
        self.llm_client = llm_client or LLMClient(settings=self.settings)

    def search_candidates(self, limit: int = 15, exclude_domains: set[str] | None = None) -> list[Candidate]:
        cfg = load_upthrust_config()
        known_exclusions = set(exclude_domains or set()) | BLOCKED_DOMAINS

        all_queries = [
            "fast growing direct to consumer DTC ecommerce brands home wellness apparel in US",
            "innovative B2B SaaS software platform for engineering productivity workflow teams",
            "independent healthcare dental clinic physical therapy practice modern medical",
            "high growth consumer beverage food snack organic brands in US",
            "AI agents developer tools cloud infrastructure startups B2B",
            "modern fintech financial services payment software in US",
            "direct to consumer sustainable home goods furniture bedding brands",
            "clinical skincare dermatology aesthetic medical clinic practices in US",
            "specialty coffee craft tea artisanal food ecommerce brands",
            "supply chain logistics fleet management software platforms in US",
        ]

        queries = list(all_queries)
        random.shuffle(queries)

        unique_results = {}
        for q in queries:
            try:
                results = self.exa_client.search(query=q, num_results=6, category="company")
                for r in results:
                    url = r.get("url", "")
                    d = normalize_domain(url)
                    if d and d not in unique_results and d not in known_exclusions:
                        unique_results[d] = r
                if len(unique_results) >= limit * 2:
                    break
            except Exception:
                continue

        if not unique_results:
            return []

        snippets_text = "\n\n".join([
            f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('text', '')[:400]}"
            for r in list(unique_results.values())[:20]
        ])

        user_prompt = f"""
You are a lead generation analyst for Upthrust growth agency.
Below are search results retrieved from Exa:

{snippets_text}

TASK:
Extract up to {limit} commercial businesses that fit Upthrust's ICP:
- Small to mid-size companies (roughly 5-200 employees) in ecommerce, SaaS/IT, health/medical, or professional services.
- MUST have an active commercial website.

STRICT DISQUALIFIERS (DO NOT EXTRACT):
- Marketing, advertising, SEO, or creative agencies (competitors)
- Directories, review platforms, aggregators (like Yelp, Clutch, G2, Capterra)
- Listicles, blog posts, news articles
- Massive enterprises (e.g. Google, Microsoft, Amazon)
- Non-commercial sites (personal blogs, non-profits, government)

Return valid JSON with 'candidates' containing:
company_name, domain (normalized lowercase, no www), website_url (https://...), industry, location, size_estimate, why_relevant.
"""

        try:
            extraction = self.llm_client.generate_structured(
                schema=ExaCandidateExtraction,
                prompt=user_prompt,
                temperature=0.1,
            )
            candidates: list[Candidate] = []
            for item in extraction.candidates:
                d = normalize_domain(item.domain or item.website_url)
                if d and d not in BLOCKED_DOMAINS:
                    candidates.append(
                        Candidate(
                            company_name=item.company_name,
                            domain=d,
                            website_url=f"https://{d}",
                            industry=item.industry,
                            location=item.location,
                            size_estimate=item.size_estimate,
                            why_relevant=item.why_relevant,
                            source="exa",
                        )
                    )
            return candidates
        except Exception:
            return []


class YutoriSearchProvider(SearchProvider):
    """Optional discovery provider using Yutori Research API."""
    def __init__(
        self,
        yutori_client: YutoriClient | None = None,
        resume_task_id: str | None = None,
        settings: EnvSettings | None = None,
    ):
        self.settings = settings or load_env_settings()
        self.yutori_client = yutori_client or YutoriClient(settings=self.settings)
        self.resume_task_id = resume_task_id

    def search_candidates(self, limit: int = 15) -> list[Candidate]:
        if not self.settings.yutori_api_key and not self.resume_task_id:
            return []

        candidates: list[Candidate] = []
        try:
            if self.resume_task_id:
                result = self.yutori_client.poll_until_complete(self.resume_task_id, timeout_seconds=600)
            else:
                cfg = load_upthrust_config()
                icp = cfg.get("icp", {})
                industries = ", ".join(icp.get("priority_industries", ["ecommerce", "healthcare", "SaaS"]))
                query = (
                    f"Find {limit} fast-growing small and mid-size businesses (5-200 employees) with an active website "
                    f"in {industries} located in the US, UK, Canada, Australia. "
                    "Exclude marketing agencies, consulting agencies, large enterprises, and directory sites."
                )
                output_schema = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company_name": {"type": "string"},
                            "domain": {"type": "string"},
                            "website_url": {"type": "string"},
                            "industry": {"type": "string"},
                            "location": {"type": "string"},
                            "size_estimate": {"type": "string"},
                            "why_relevant": {"type": "string"},
                        },
                        "required": ["company_name", "domain", "website_url"],
                    },
                }
                task_resp = self.yutori_client.create_research_task(query, output_schema=output_schema)
                task_id = task_resp.get("task_id")
                if not task_id:
                    return []
                result = self.yutori_client.poll_until_complete(task_id, timeout_seconds=600)

            struct_res = result.get("structured_result", [])
            raw_items = struct_res if isinstance(struct_res, list) else list(struct_res.values())[0] if isinstance(struct_res, dict) else []
            for item in raw_items:
                c_domain = normalize_domain(item.get("domain", ""))
                if c_domain and is_domain_valid(c_domain):
                    candidates.append(
                        Candidate(
                            company_name=item.get("company_name", c_domain),
                            domain=c_domain,
                            website_url=item.get("website_url", f"https://{c_domain}"),
                            industry=item.get("industry"),
                            location=item.get("location"),
                            source="yutori",
                        )
                    )
        except Exception:
            return []
        return candidates


class SeedSearchProvider(SearchProvider):
    """Fallback discovery provider reading from data/seed_prospects.csv."""
    def __init__(self, seed_csv_path: Path = DATA_DIR / "seed_prospects.csv", with_control: bool = False):
        self.seed_csv_path = seed_csv_path
        self.with_control = with_control

    def search_candidates(self, limit: int = 15, exclude_domains: set[str] | None = None) -> list[Candidate]:
        candidates = load_candidates_from_seed(self.seed_csv_path, with_control=self.with_control)
        if exclude_domains:
            candidates = [c for c in candidates if c.domain not in exclude_domains]
        return candidates[:limit]


# --- Main Discovery Coordinator ---

class DiscoveryStep:
    def __init__(
        self,
        db: Database,
        settings: EnvSettings | None = None,
        exa_client: ExaClient | None = None,
        yutori_client: YutoriClient | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.db = db
        self.settings = settings or load_env_settings()
        self.exa_client = exa_client or ExaClient(settings=self.settings)
        self.yutori_client = yutori_client or YutoriClient(settings=self.settings)
        self.llm_client = llm_client or LLMClient(settings=self.settings)

    def get_provider(self, source: str = "auto", with_control: bool = False, resume_task_id: str | None = None) -> SearchProvider:
        src = source.lower()
        if src == "auto":
            if self.settings.exa_api_key:
                src = "exa"
            elif self.settings.yutori_api_key or resume_task_id:
                src = "yutori"
            else:
                src = "seed"

        if src == "exa" and self.settings.exa_api_key:
            return ExaSearchProvider(exa_client=self.exa_client, llm_client=self.llm_client, settings=self.settings)
        elif src == "yutori" and (self.settings.yutori_api_key or resume_task_id):
            return YutoriSearchProvider(yutori_client=self.yutori_client, resume_task_id=resume_task_id, settings=self.settings)
        else:
            return SeedSearchProvider(with_control=with_control)

    def run(
        self,
        source: str = "auto",
        limit: int = 15,
        with_control: bool = False,
        resume_task_id: str | None = None,
        fresh: bool = False,
    ) -> list[Candidate]:
        if fresh:
            from agent.cache import DiskCache
            self.exa_client = ExaClient(settings=self.settings, cache=DiskCache(enabled=False))
            self.llm_client = LLMClient(settings=self.settings, cache=DiskCache(enabled=False))

        existing_domains = {p["domain"] for p in self.db.list_prospects()}
        provider = self.get_provider(source=source, with_control=with_control, resume_task_id=resume_task_id)
        candidates = provider.search_candidates(limit=limit, exclude_domains=existing_domains)

        # Fallback to seed if provider returned empty
        if not candidates and not isinstance(provider, SeedSearchProvider):
            fallback_provider = SeedSearchProvider(with_control=with_control)
            candidates = fallback_provider.search_candidates(limit=limit, exclude_domains=existing_domains)

        # Guarantee control candidate is present if requested
        if with_control and not any(c.source == "control" for c in candidates):
            control_candidates = [c for c in load_candidates_from_seed(with_control=True) if c.source == "control"]
            if control_candidates:
                candidates.append(control_candidates[0])

        # Filter, deduplicate and save to database
        saved_candidates: list[Candidate] = []
        for cand in candidates:
            cand.domain = normalize_domain(cand.domain)
            if self.db.is_suppressed(cand.domain):
                continue
            if cand.domain in BLOCKED_DOMAINS:
                continue
            inserted = self.db.upsert_candidate(cand)
            if inserted:
                saved_candidates.append(cand)

        return saved_candidates
