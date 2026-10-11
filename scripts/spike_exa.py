import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from agent.clients.exa import ExaClient
from agent.config import DATA_DIR, load_env_settings

def run_spike():
    settings = load_env_settings()
    fixtures_dir = DATA_DIR / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    raw_file = fixtures_dir / "exa_search_raw.json"

    print("Running Exa API spike...")
    if not settings.exa_api_key:
        print("EXA_API_KEY not set in .env. Checking existing fixture...")
        if raw_file.exists():
            with open(raw_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Loaded recorded fixture ({len(data)} results). Field keys: {list(data[0].keys())}")
            return
        else:
            print("No key and no fixture found. Please set EXA_API_KEY in .env.")
            return

    client = ExaClient(settings=settings)
    query = "fast growing direct to consumer DTC ecommerce wellness brands in US"
    print(f"Executing search: '{query}'")
    # Bypass old cache if necessary
    cache_params = {"query": query, "numResults": 3, "category": "company", "max_chars": 800}
    client.cache.delete("exa", "search", cache_params)
    results = client.search(query=query, num_results=3, category="company")
    print(f"Successfully retrieved {len(results)} results from Exa.")
    for idx, r in enumerate(results, 1):
        print(f"[{idx}] {r.get('title')} -> {r.get('url')}")

    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved raw response to {raw_file}")

if __name__ == "__main__":
    run_spike()
