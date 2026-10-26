"""Decision timeline and forecast selection engine adhering to strict anti-future-data leakage rules."""

import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import pytz

LONDON_TZ = pytz.timezone("Europe/London")
UTC_TZ = pytz.UTC


def compute_cutoff_utc(delivery_date_str: str, cutoff_local_hhmm: str = "09:00") -> str:
    """
    Compute decision cutoff in UTC ISO-8601 string.
    Rule: Cutoff is on (delivery_date - 1 day) at cutoff_local_hhmm in Europe/London time.
    """
    deliv_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
    decision_date = deliv_date - timedelta(days=1)
    hh, mm = map(int, cutoff_local_hhmm.split(":"))

    local_dt = LONDON_TZ.localize(datetime(decision_date.year, decision_date.month, decision_date.day, hh, mm, 0))
    utc_dt = local_dt.astimezone(UTC_TZ)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def select_decision_forecasts_for_range(
    conn: sqlite3.Connection,
    date_from: str = "2026-01-01",
    date_to: str = "2026-01-31",
    cutoff_time: str = "09:00",
) -> pd.DataFrame:
    """
    For every settlement period in [date_from, date_to], select:
    - actual generation from actuals table
    - latest forecast published AT OR BEFORE cutoff(D)
    Returns DataFrame with:
      settlementDate, settlementPeriod, startTime, actual, forecast, error, shortfall, publishTime, cutoffUtc
    """
    # 1. Fetch all actuals in range
    act_query = """
        SELECT startTime, settlementDate, settlementPeriod, generation AS actual, publishTime AS actualPublishTime
        FROM actuals
        WHERE settlementDate >= ? AND settlementDate <= ?
        ORDER BY startTime
    """
    df_actuals = pd.read_sql(act_query, conn, params=[date_from, date_to])
    if df_actuals.empty:
        return pd.DataFrame()

    # 2. Group by delivery day to apply day-specific cutoff
    results = []
    unique_dates = df_actuals["settlementDate"].unique()

    for d_str in unique_dates:
        cutoff_utc = compute_cutoff_utc(d_str, cutoff_time)
        day_actuals = df_actuals[df_actuals["settlementDate"] == d_str]

        # Target start times for this day
        # For hourly mapping: both HH:00 and HH:30 map to hourly forecast HH:00
        start_min = day_actuals["startTime"].min()
        start_max = day_actuals["startTime"].max()
        # Hour prefix min and max
        hour_min = start_min[:14] + "00:00Z"
        hour_max = start_max[:14] + "00:00Z"

        # Query forecasts published on or before cutoff_utc for targets on this day
        fc_query = """
            SELECT publishTime, startTime, generation AS forecast
            FROM forecasts
            WHERE publishTime <= ?
              AND startTime >= ?
              AND startTime <= ?
            ORDER BY startTime, publishTime ASC
        """
        df_fc = pd.read_sql(fc_query, conn, params=[cutoff_utc, hour_min, hour_max])

        # For each target startTime in df_fc, get the latest published forecast (largest publishTime)
        if not df_fc.empty:
            df_latest_fc = df_fc.sort_values(by=["startTime", "publishTime"]).drop_duplicates(
                subset=["startTime"], keep="last"
            )
            # Map by startTime string
            fc_map = {row["startTime"]: (row["forecast"], row["publishTime"]) for _, row in df_latest_fc.iterrows()}
        else:
            fc_map = {}

        # Join with each actual period
        for _, row in day_actuals.iterrows():
            st = row["startTime"]
            # Look up forecast: first exact match, else hourly match
            hour_st = st[:14] + "00:00Z"
            fc_info = fc_map.get(st) or fc_map.get(hour_st)

            fc_val = fc_info[0] if fc_info else None
            pub_time = fc_info[1] if fc_info else None
            act_val = row["actual"]

            if fc_val is not None and act_val is not None:
                err = fc_val - act_val
                shortfall = max(0.0, err)
            else:
                err = None
                shortfall = None

            results.append({
                "startTime": st,
                "settlementDate": row["settlementDate"],
                "settlementPeriod": row["settlementPeriod"],
                "actual": act_val,
                "forecast": fc_val,
                "error": err,
                "shortfall": shortfall,
                "publishTime": pub_time,
                "cutoffUtc": cutoff_utc,
            })

    df_result = pd.DataFrame(results)
    return df_result


def get_forecast_revisions_for_day(
    conn: sqlite3.Connection,
    delivery_date_str: str,
    cutoff_time: str = "09:00",
) -> dict:
    """
    Retrieve all forecast revisions published up to the cutoff for delivery_date_str,
    plus actual generation outturn, to visualize forecast evolution.
    """
    cutoff_utc = compute_cutoff_utc(delivery_date_str, cutoff_time)

    # Actuals
    act_df = pd.read_sql(
        "SELECT startTime, settlementPeriod, generation AS actual FROM actuals WHERE settlementDate = ? ORDER BY startTime",
        conn,
        params=[delivery_date_str],
    )

    if act_df.empty:
        return {"deliveryDate": delivery_date_str, "revisions": [], "actuals": []}

    start_min = act_df["startTime"].min()[:14] + "00:00Z"
    start_max = act_df["startTime"].max()[:14] + "00:00Z"

    # All forecasts for this day's hours published <= cutoff_utc
    fc_query = """
        SELECT publishTime, startTime, generation AS forecast
        FROM forecasts
        WHERE publishTime <= ?
          AND startTime >= ?
          AND startTime <= ?
        ORDER BY publishTime, startTime
    """
    df_all_fc = pd.read_sql(fc_query, conn, params=[cutoff_utc, start_min, start_max])

    if df_all_fc.empty:
        return {
            "deliveryDate": delivery_date_str,
            "cutoffUtc": cutoff_utc,
            "revisions": [],
            "actuals": act_df.to_dict(orient="records"),
        }

    unique_publishes = sorted(df_all_fc["publishTime"].unique())
    decision_publish = unique_publishes[-1] if unique_publishes else None

    # Format revisions
    revisions = []
    # For chart legibility, take up to 6 distinct publishes including the first and the latest (decision)
    if len(unique_publishes) > 6:
        # Step through evenly
        step = len(unique_publishes) / 5.0
        selected_indices = sorted({round(i * step) for i in range(5)} | {len(unique_publishes) - 1})
        selected_publishes = [unique_publishes[i] for i in selected_indices if i < len(unique_publishes)]
    else:
        selected_publishes = unique_publishes

    for pub in selected_publishes:
        sub = df_all_fc[df_all_fc["publishTime"] == pub]
        data_points = []
        # Expand hourly forecast to 48 periods matching actuals
        fc_dict = dict(zip(sub["startTime"], sub["forecast"]))
        for _, act_row in act_df.iterrows():
            st = act_row["startTime"]
            hour_st = st[:14] + "00:00Z"
            val = fc_dict.get(st, fc_dict.get(hour_st))
            data_points.append({
                "startTime": st,
                "settlementPeriod": act_row["settlementPeriod"],
                "forecast": val,
            })

        revisions.append({
            "publishTime": pub,
            "isDecisionForecast": (pub == decision_publish),
            "data": data_points,
        })

    return {
        "deliveryDate": delivery_date_str,
        "cutoffUtc": cutoff_utc,
        "decisionPublishTime": decision_publish,
        "revisions": revisions,
        "actuals": act_df.to_dict(orient="records"),
    }
