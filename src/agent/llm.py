import json
import re
from typing import Any, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agent.cache import DiskCache
from agent.config import EnvSettings, load_env_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, settings: EnvSettings | None = None, cache: DiskCache | None = None):
        self.settings = settings or load_env_settings()
        self.cache = cache or DiskCache()

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code fence if present."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def call_raw(self, prompt: str, system_prompt: str | None = None, temperature: float = 0.0) -> tuple[str, int, int]:
        """
        Calls the LLM provider and returns (raw_text_response, prompt_tokens, completion_tokens).
        """
        provider = self.settings.llm_provider
        model = self.settings.llm_model
        api_key = self.settings.llm_api_key

        cache_params = {
            "model": model,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
        }
        cached = self.cache.get(provider, "generate", cache_params)
        if cached:
            return cached["text"], cached.get("prompt_tokens", 0), cached.get("completion_tokens", 0)

        if not api_key:
            raise LLMError(f"Missing LLM_API_KEY for provider '{provider}'. Please set it in .env")

        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            contents = []
            if system_prompt:
                contents.append({"role": "user", "parts": [{"text": f"System Instructions:\n{system_prompt}"}]})
                contents.append({"role": "model", "parts": [{"text": "Understood. I will follow all instructions and output strict JSON."}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload: dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            }

            resp = httpx.post(url, json=payload, timeout=30.0)
            if resp.status_code != 200:
                raise LLMError(f"Gemini API error ({resp.status_code}): {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMError(f"Gemini returned no candidates: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            usage = data.get("usageMetadata", {})
            p_tokens = usage.get("promptTokenCount", 0)
            c_tokens = usage.get("candidatesTokenCount", 0)

        elif provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model or "gpt-4o-mini",
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
            if resp.status_code != 200:
                raise LLMError(f"OpenAI API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)

        elif provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": model or "claude-3-5-haiku-20241022",
                "max_tokens": 2048,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                payload["system"] = system_prompt
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
            if resp.status_code != 200:
                raise LLMError(f"Anthropic API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            text = "".join(c.get("text", "") for c in data.get("content", []))
            usage = data.get("usage", {})
            p_tokens = usage.get("input_tokens", 0)
            c_tokens = usage.get("output_tokens", 0)

        else:
            raise LLMError(f"Unsupported LLM provider: {provider}")

        # Cache response
        self.cache.set(provider, "generate", cache_params, {
            "text": text,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
        })
        return text, p_tokens, c_tokens

    def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        """
        Generate JSON conforming to a Pydantic model with 1 retry on validation failure.
        """
        text, _, _ = self.call_raw(prompt, system_prompt, temperature)
        clean = self._clean_json_text(text)
        try:
            parsed = json.loads(clean)
            return schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            # One retry with the error feedback
            retry_prompt = (
                f"{prompt}\n\n"
                f"Your previous output failed validation with error: {e}\n"
                f"Previous output was:\n{text}\n"
                f"Please fix and output ONLY valid JSON matching the schema."
            )
            retry_text, _, _ = self.call_raw(retry_prompt, system_prompt, temperature)
            clean_retry = self._clean_json_text(retry_text)
            parsed_retry = json.loads(clean_retry)
            return schema.model_validate(parsed_retry)
