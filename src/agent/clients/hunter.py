import time
from typing import Any
import httpx

from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.config import EnvSettings, load_env_settings
from agent.models import Contact


class HunterAPIError(Exception):
    pass


class HunterClient:
    BASE_URL = "https://api.hunter.io/v2"

    def __init__(
        self,
        settings: EnvSettings | None = None,
        cache: DiskCache | None = None,
        budget: BudgetTracker | None = None,
    ):
        self.settings = settings or load_env_settings()
        self.cache = cache or DiskCache()
        self.budget = budget or BudgetTracker()

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.settings.hunter_api_key}

    def check_account(self) -> dict[str, Any]:
        """Check account credits and plan limits."""
        if not self.settings.hunter_api_key:
            raise HunterAPIError("Missing HUNTER_API_KEY in configuration")
        url = f"{self.BASE_URL}/account"
        resp = httpx.get(url, headers=self.headers, timeout=10.0)
        if resp.status_code != 200:
            raise HunterAPIError(f"Hunter account check failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def domain_search(
        self,
        domain: str,
        limit: int = 5,
        seniority: str = "executive,senior",
    ) -> list[dict[str, Any]]:
        """Search for emails associated with a domain."""
        cached = self.cache.get("hunter", f"domain_{domain}", {"limit": limit, "seniority": seniority})
        if cached:
            return cached.get("emails", [])

        if not self.settings.hunter_api_key:
            return []

        self.budget.check_hunter_credits(credits=1.0)

        url = f"{self.BASE_URL}/domain-search"
        params = {
            "domain": domain,
            "limit": limit,
            "seniority": seniority,
        }
        resp = httpx.get(url, headers=self.headers, params=params, timeout=15.0)
        if resp.status_code != 200:
            raise HunterAPIError(f"Hunter domain search failed ({resp.status_code}): {resp.text}")

        data = resp.json().get("data", {})
        emails = data.get("emails", [])
        if emails:
            self.budget.record_hunter_credit(1.0)
        self.cache.set("hunter", f"domain_{domain}", {"limit": limit, "seniority": seniority}, {"emails": emails})
        return emails

    def email_finder(
        self,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict[str, Any] | None:
        """Find email by full name and domain."""
        cached = self.cache.get("hunter", f"finder_{domain}_{first_name}_{last_name}", {})
        if cached:
            return cached

        if not self.settings.hunter_api_key:
            return None

        self.budget.check_hunter_credits(credits=1.0)

        url = f"{self.BASE_URL}/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
        }
        resp = httpx.get(url, headers=self.headers, params=params, timeout=15.0)
        if resp.status_code != 200:
            return None

        data = resp.json().get("data")
        if data and data.get("email"):
            self.budget.record_hunter_credit(1.0)
            self.cache.set("hunter", f"finder_{domain}_{first_name}_{last_name}", {}, data)
            return data
        return None

    def verify_email(self, email: str) -> dict[str, Any]:
        """Verify an email address. Costs 0.5 credit."""
        cached = self.cache.get("hunter", f"verify_{email}", {})
        if cached:
            return cached

        if not self.settings.hunter_api_key:
            return {"status": "unverified", "score": None}

        self.budget.check_hunter_credits(credits=0.5)

        url = f"{self.BASE_URL}/email-verifier"
        params = {"email": email}

        # Handle 202 polling
        for _ in range(3):
            resp = httpx.get(url, headers=self.headers, params=params, timeout=15.0)
            if resp.status_code == 202:
                time.sleep(2)
                continue
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                self.budget.record_hunter_credit(0.5)
                self.cache.set("hunter", f"verify_{email}", {}, data)
                return data
            break

        return {"status": "unknown", "score": None}
