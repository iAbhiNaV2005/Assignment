import json
import time
from typing import Any
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.config import EnvSettings, load_env_settings
from agent.models import Candidate


class YutoriAPIError(Exception):
    pass


class YutoriClient:
    BASE_URL = "https://api.yutori.com"

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
        return {
            "X-API-Key": self.settings.yutori_api_key,
            "Content-Type": "application/json",
        }

    def check_usage(self) -> dict[str, Any]:
        """Cheap /v1/usage ping for doctor check."""
        if not self.settings.yutori_api_key:
            raise YutoriAPIError("Missing YUTORI_API_KEY in configuration")
        url = f"{self.BASE_URL}/v1/usage"
        resp = httpx.get(url, headers=self.headers, timeout=10.0)
        if resp.status_code != 200:
            raise YutoriAPIError(f"Yutori usage check failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def create_research_task(
        self,
        query: str,
        output_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new async research task."""
        self.budget.check_yutori_task()

        cache_params = {"query": query, "schema": output_schema, "loc": self.settings.yutori_user_location}
        cached = self.cache.get("yutori", "create_task", cache_params)
        if cached:
            return cached

        if not self.settings.yutori_api_key:
            raise YutoriAPIError("Missing YUTORI_API_KEY in configuration")

        payload: dict[str, Any] = {
            "query": query,
            "user_location": self.settings.yutori_user_location,
            "skip_email": True,
        }
        if output_schema:
            payload["output_schema"] = output_schema

        url = f"{self.BASE_URL}/v1/research/tasks"
        resp = httpx.post(url, headers=self.headers, json=payload, timeout=20.0)
        if resp.status_code not in (200, 201, 202):
            raise YutoriAPIError(f"Yutori create task failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        self.budget.record_yutori_task(cost_usd=0.35)
        self.cache.set("yutori", "create_task", cache_params, data)
        return data

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Poll research task status and result."""
        cached = self.cache.get("yutori", f"get_task_{task_id}", {})
        if cached and cached.get("status") in ("succeeded", "failed"):
            return cached

        if not self.settings.yutori_api_key:
            raise YutoriAPIError("Missing YUTORI_API_KEY in configuration")

        url = f"{self.BASE_URL}/v1/research/tasks/{task_id}"
        resp = httpx.get(url, headers=self.headers, timeout=15.0)
        if resp.status_code != 200:
            raise YutoriAPIError(f"Yutori get task failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        if data.get("status") in ("succeeded", "failed"):
            self.cache.set("yutori", f"get_task_{task_id}", {}, data)
        return data

    def poll_until_complete(
        self,
        task_id: str,
        timeout_seconds: int = 900,
        interval_seconds: int = 15,
    ) -> dict[str, Any]:
        """Poll task every interval until succeeded or failed."""
        start = time.time()
        while time.time() - start < timeout_seconds:
            data = self.get_task(task_id)
            status = data.get("status")
            if status == "succeeded":
                return data
            if status == "failed":
                reason = data.get("rejection_reason", "unknown")
                raise YutoriAPIError(f"Yutori task failed with rejection reason: {reason}")
            time.sleep(interval_seconds)

        raise TimeoutError(f"Yutori task {task_id} did not finish within {timeout_seconds} seconds")
