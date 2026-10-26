"""Cleaning and validation logic for FUELHH actuals and WINDFOR forecasts."""

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def parse_iso_utc(ts: str) -> str:
    """Normalize timestamp string to standard ISO-8601 UTC format: YYYY-MM-DDTHH:MM:SSZ."""
    if not ts:
        raise ValueError("Empty timestamp string")
    # Python datetime parsing
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_fuelhh_data(raw_records: list[dict]) -> pd.DataFrame:
    """Clean, validate, and deduplicate FUELHH actual wind generation records."""
    if not raw_records:
        return pd.DataFrame(columns=["startTime", "settlementDate", "settlementPeriod", "generation", "publishTime"])

    rows = []
    for r in raw_records:
        fuel = r.get("fuelType")
        if fuel and fuel.upper() != "WIND":
            continue

        start_time = r.get("startTime")
        generation = r.get("generation")
        if start_time is None or generation is None:
            continue

        try:
            norm_start = parse_iso_utc(start_time)
            norm_pub = parse_iso_utc(r.get("publishTime", start_time))
            gen_val = float(generation)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid FUELHH record {r}: {e}")
            continue

        if gen_val < 0:
            logger.warning(f"Negative generation encountered in FUELHH: {gen_val}. Clamping to 0.")
            gen_val = 0.0

        rows.append({
            "startTime": norm_start,
            "settlementDate": r.get("settlementDate") or norm_start[:10],
            "settlementPeriod": int(r.get("settlementPeriod", 0)),
            "generation": gen_val,
            "publishTime": norm_pub,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Deduplicate by startTime, keeping the one with largest publishTime
    df = df.sort_values(by=["startTime", "publishTime"], ascending=[True, True])
    initial_count = len(df)
    df = df.drop_duplicates(subset=["startTime"], keep="last")
    if len(df) < initial_count:
        logger.info(f"Deduplicated FUELHH from {initial_count} to {len(df)} records.")

    df = df.sort_values(by="startTime").reset_index(drop=True)
    return df


def clean_windfor_data(raw_records: list[dict]) -> pd.DataFrame:
    """Clean, validate, and deduplicate WINDFOR forecast records."""
    if not raw_records:
        return pd.DataFrame(columns=["publishTime", "startTime", "generation"])

    rows = []
    for r in raw_records:
        pub_time = r.get("publishTime")
        start_time = r.get("startTime")
        generation = r.get("generation")

        if pub_time is None or start_time is None or generation is None:
            continue

        try:
            norm_pub = parse_iso_utc(pub_time)
            norm_start = parse_iso_utc(start_time)
            gen_val = float(generation)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid WINDFOR record {r}: {e}")
            continue

        if gen_val < 0:
            logger.warning(f"Negative forecast generation in WINDFOR: {gen_val}. Clamping to 0.")
            gen_val = 0.0

        rows.append({
            "publishTime": norm_pub,
            "startTime": norm_start,
            "generation": gen_val,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Deduplicate exact (publishTime, startTime)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["publishTime", "startTime"], keep="last")
    if len(df) < initial_count:
        logger.info(f"Deduplicated WINDFOR from {initial_count} to {len(df)} records.")

    df = df.sort_values(by=["publishTime", "startTime"]).reset_index(drop=True)
    return df
