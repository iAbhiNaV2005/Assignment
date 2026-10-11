from typing import Any
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agent.cache import DiskCache
from agent.config import EnvSettings, load_env_settings


class ExaAPIError(Exception):
    pass


class ExaClient:
    BASE_URL = "https://api.exa.ai"

    def __init__(
        self,
        settings: EnvSettings | None = None,
        cache: DiskCache | None = None,
    ):
        self.settings = settings or load_env_settings()
        self.cache = cache or DiskCache()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.settings.exa_api_key,
            "Content-Type": "application/json",
        }

    def ping(self) -> bool:
        """Lightweight check to verify API key validity."""
        if not self.settings.exa_api_key:
            raise ExaAPIError("Missing EXA_API_KEY in configuration")
        # Perform minimal 1-result search
        url = f"{self.BASE_URL}/search"
        payload = {
            "query": "Upthrust growth marketing",
            "numResults": 1,
            "type": "auto",
        }
        resp = httpx.post(url, headers=self.headers, json=payload, timeout=10.0)
        if resp.status_code != 200:
            raise ExaAPIError(f"Exa authentication failed ({resp.status_code}): {resp.text}")
        return True

    def search(
        self,
        query: str,
        num_results: int = 5,
        category: str = "company",
        max_chars: int = 800,
        exclude_domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search Exa company index and return list of result objects.
        Each result has: id, title, url, text.
        """
        cache_params = {
            "query": query,
            "numResults": num_results,
            "category": category,
            "max_chars": max_chars,
        }
        cached = self.cache.get("exa", "search", cache_params)
        if cached:
            return cached.get("results", [])

        if not self.settings.exa_api_key:
            raise ExaAPIError("Missing EXA_API_KEY in configuration")

        url = f"{self.BASE_URL}/search"
        default_excludes = [
            "clutch.co", "yelp.com", "linkedin.com", "facebook.com",
            "g2.com", "capterra.com", "wikipedia.org", "crunchbase.com",
            "youtube.com", "instagram.com", "twitter.com", "x.com",
        ]
        payload: dict[str, Any] = {
            "query": query,
            "numResults": num_results,
            "type": "neural",
            "category": category,
            "contents": {
                "text": {
                    "maxCharacters": max_chars,
                }
            },
        }
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains
        elif category != "company":
            payload["excludeDomains"] = default_excludes

        resp = httpx.post(url, headers=self.headers, json=payload, timeout=25.0)
        if resp.status_code != 200:
            raise ExaAPIError(f"Exa search error ({resp.status_code}): {resp.text}")

        data = resp.json()
        results = data.get("results", [])
        self.cache.set("exa", "search", cache_params, {"results": results, "requestId": data.get("requestId")})
        return results
