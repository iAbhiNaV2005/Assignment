"""Fetch raw FUELHH and WINDFOR data streams from Elexon BMRS API with robust chunking and retry."""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


def fetch_with_retry(
    url: str,
    max_retries: int = 4,
    backoff_factor: float = 1.5,
    timeout: int = 35,
) -> list[dict]:
    """Fetch JSON from URL with exponential backoff on 429 or 5xx errors."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "UK-Wind-Forecast-Decision-Portal/1.0",
    }
    req = urllib.request.Request(url, headers=headers)

    last_error = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.status
                if status == 200:
                    raw_data = response.read().decode("utf-8")
                    return json.loads(raw_data)
                elif status == 429 or status >= 500:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else (backoff_factor**attempt)
                    logger.warning(
                        f"Received status {status}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"Unexpected HTTP status {status} from {url}")
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429 or e.code >= 500:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                wait_time = float(retry_after) if retry_after else (backoff_factor**attempt)
                logger.warning(
                    f"HTTPError {e.code}: {e.reason}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(wait_time)
            else:
                body = e.read().decode("utf-8", errors="replace")
                logger.error(f"HTTPError {e.code} for URL {url}: {body}")
                raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            wait_time = backoff_factor**attempt
            logger.warning(
                f"Request failed: {e}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch data from {url} after {max_retries} attempts. Error: {last_error}")


def fetch_fuelhh_actuals(
    start_date: str = "2026-01-01",
    end_date: str = "2026-01-31",
    fuel_type: str = "WIND",
) -> list[dict]:
    """Fetch actual generation outturn (FUELHH) for WIND fuelType."""
    params = urllib.parse.urlencode({
        "settlementDateFrom": start_date,
        "settlementDateTo": end_date,
        "fuelType": fuel_type,
    })
    url = f"{ELEXON_BASE_URL}/datasets/FUELHH/stream?{params}"
    logger.info(f"Fetching FUELHH data from {start_date} to {end_date}...")
    records = fetch_with_retry(url)
    logger.info(f"Fetched {len(records)} FUELHH records.")
    return records


def fetch_windfor_forecasts(
    publish_from_iso: str = "2025-12-25T00:00:00Z",
    publish_to_iso: str = "2026-01-31T23:59:59Z",
    chunk_days: int = 7,
) -> list[dict]:
    """Fetch WINDFOR forecast stream in robust chunks to avoid API timeouts and rate limits."""
    dt_from = datetime.fromisoformat(publish_from_iso)
    dt_to = datetime.fromisoformat(publish_to_iso)

    all_records: list[dict] = []
    current_start = dt_from

    while current_start < dt_to:
        current_end = min(current_start + timedelta(days=chunk_days), dt_to)
        start_str = current_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = current_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = urllib.parse.urlencode({
            "publishDateTimeFrom": start_str,
            "publishDateTimeTo": end_str,
        })
        url = f"{ELEXON_BASE_URL}/datasets/WINDFOR/stream?{params}"
        logger.info(f"Fetching WINDFOR chunk: {start_str} to {end_str}...")

        chunk_records = fetch_with_retry(url)
        all_records.extend(chunk_records)
        logger.info(f"Chunk returned {len(chunk_records)} records. Total accumulated: {len(all_records)}")

        # Advance window (avoid overlap on the exact second)
        current_start = current_end + timedelta(seconds=1)
        time.sleep(0.2)  # Polite inter-request pause

    return all_records
