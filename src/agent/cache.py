import hashlib
import json
from pathlib import Path
from typing import Any
from agent.config import CACHE_DIR


class CacheMissReplayError(RuntimeError):
    """Raised when running in --replay mode and a cache miss occurs."""
    pass


class DiskCache:
    def __init__(self, cache_dir: Path = CACHE_DIR, enabled: bool = True, replay: bool = False):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.replay = replay
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, provider: str, endpoint: str, params: Any) -> str:
        serialized = json.dumps(params, sort_keys=True, default=str)
        raw_key = f"{provider}:{endpoint}:{serialized}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, provider: str, endpoint: str, params: Any) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        key = self._make_key(provider, endpoint, params)
        file_path = self.cache_dir / f"{provider}_{key}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        if self.replay:
            raise CacheMissReplayError(
                f"[REPLAY MODE ERROR] Cache miss for {provider} {endpoint}. Replay requires recorded responses."
            )
        return None

    def set(self, provider: str, endpoint: str, params: Any, response_data: Any) -> None:
        if not self.enabled:
            return
        key = self._make_key(provider, endpoint, params)
        file_path = self.cache_dir / f"{provider}_{key}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2, default=str)
        except Exception:
            pass

    def delete(self, provider: str, endpoint: str, params: Any) -> bool:
        key = self._make_key(provider, endpoint, params)
        file_path = self.cache_dir / f"{provider}_{key}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                pass
        return False
