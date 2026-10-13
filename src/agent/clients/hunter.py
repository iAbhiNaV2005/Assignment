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
    def api_keys(self) -> list[str]:
        keys: list[str] = []
        if self.settings.hunter_api_key:
            for k in self.settings.hunter_api_key.split(","):
                k = k.strip()
                if k and k not in keys:
                    keys.append(k)
        import os
        for i in range(2, 10):
            env_k = os.getenv(f"HUNTER_API_KEY_{i}", "").strip()
            if env_k and env_k not in keys:
                keys.append(env_k)
        return keys

    @property
    def headers(self) -> dict[str, str]:
        key = self.api_keys[0] if self.api_keys else ""
        return {"X-API-KEY": key}

    def check_account(self) -> dict[str, Any]:
        """Check all configured keys and return aggregated account status."""
        keys = self.api_keys
        if not keys:
            raise HunterAPIError("Missing HUNTER_API_KEY in configuration")

        valid_accounts: list[dict[str, Any]] = []
        total_searches_left = 0
        last_error = "Unknown error"

        for k in keys:
            try:
                resp = httpx.get(f"{self.BASE_URL}/account", headers={"X-API-KEY": k}, timeout=8.0)
                if resp.status_code == 200:
                    d = resp.json().get("data", {})
                    reqs = d.get("requests", {})
                    searches = reqs.get("searches", {}).get("remaining", 0)
                    total_searches_left += searches
                    valid_accounts.append({
                        "key": f"{k[:4]}...{k[-4:]}",
                        "plan": d.get("plan_name", "Free"),
                        "searches_left": searches,
                    })
                else:
                    last_error = f"Key {k[:4]}... error ({resp.status_code})"
            except Exception as e:
                last_error = str(e)
                continue

        if not valid_accounts:
            raise HunterAPIError(f"None of the configured Hunter API keys are valid: {last_error}")

        primary = valid_accounts[0]
        return {
            "valid_count": len(valid_accounts),
            "total_keys": len(keys),
            "total_searches_left": total_searches_left,
            "plan_name": primary["plan"],
            "accounts": valid_accounts,
            "data": {"plan_name": f"{primary['plan']} ({len(valid_accounts)} keys active, {total_searches_left} searches)"},
        }

    def domain_search(
        self,
        domain: str,
        limit: int = 5,
        seniority: str = "executive,senior",
    ) -> list[dict[str, Any]]:
        """Search for emails associated with a domain with multi-key failover."""
        cached = self.cache.get("hunter", f"domain_{domain}", {"limit": limit, "seniority": seniority})
        if cached:
            return cached.get("emails", [])

        keys = self.api_keys
        if not keys:
            return []

        self.budget.check_hunter_credits(credits=1.0)

        url = f"{self.BASE_URL}/domain-search"
        params = {
            "domain": domain,
            "limit": limit,
            "seniority": seniority,
        }

        last_error = None
        for k in keys:
            try:
                resp = httpx.get(url, headers={"X-API-KEY": k}, params=params, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    emails = data.get("emails", [])
                    if emails:
                        self.budget.record_hunter_credit(1.0)
                    self.cache.set("hunter", f"domain_{domain}", {"limit": limit, "seniority": seniority}, {"emails": emails})
                    return emails
                elif resp.status_code in (401, 403, 429):
                    last_error = f"Key {k[:4]}... error ({resp.status_code})"
                    continue
                else:
                    last_error = f"Status {resp.status_code}: {resp.text}"
                    continue
            except Exception as e:
                last_error = str(e)
                continue

        # If all keys failed or returned empty
        if last_error and "401" not in last_error:
            # Only log/raise if not purely auth fail
            pass
        return []

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
