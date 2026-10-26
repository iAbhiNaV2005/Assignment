"""Quantitative evaluation metrics, breakdowns, horizon analysis, and safety buffer backtesting."""

import sqlite3

import numpy as np
import pandas as pd


def compute_headline_metrics(df_eval: pd.DataFrame) -> dict:
    """Compute primary accuracy and risk metrics on evaluated periods."""
    total_periods = len(df_eval)
    valid_mask = df_eval["error"].notna() & df_eval["actual"].notna() & df_eval["forecast"].notna()
    df_valid = df_eval[valid_mask]
    eval_count = len(df_valid)

    if eval_count == 0:
        return {
            "totalPeriods": total_periods,
            "evaluatedPeriods": 0,
            "coveragePct": 0.0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "nmae": None,
            "meanActual": None,
            "meanForecast": None,
            "p10Error": None,
            "p50Error": None,
            "p90Error": None,
            "p95AbsError": None,
            "shareOverPct": None,
            "shareUnderPct": None,
        }

    errors = df_valid["error"].to_numpy()
    abs_errors = np.abs(errors)
    actuals = df_valid["actual"].to_numpy()
    forecasts = df_valid["forecast"].to_numpy()

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors**2)))
    bias = float(np.mean(errors))
    mean_actual = float(np.mean(actuals))
    mean_forecast = float(np.mean(forecasts))
    nmae = float((mae / mean_actual) * 100.0) if mean_actual > 0 else None

    p10_err = float(np.percentile(errors, 10))
    p50_err = float(np.percentile(errors, 50))
    p90_err = float(np.percentile(errors, 90))
    p95_abs = float(np.percentile(abs_errors, 95))

    over_count = int(np.sum(errors > 0))
    under_count = int(np.sum(errors < 0))
    share_over = float((over_count / eval_count) * 100.0)
    share_under = float((under_count / eval_count) * 100.0)
    coverage = float((eval_count / total_periods) * 100.0) if total_periods > 0 else 0.0

    return {
        "totalPeriods": total_periods,
        "evaluatedPeriods": eval_count,
        "coveragePct": round(coverage, 2),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "nmae": round(nmae, 2) if nmae is not None else None,
        "meanActual": round(mean_actual, 2),
        "meanForecast": round(mean_forecast, 2),
        "p10Error": round(p10_err, 2),
        "p50Error": round(p50_err, 2),
        "p90Error": round(p90_err, 2),
        "p95AbsError": round(p95_abs, 2),
        "shareOverPct": round(share_over, 1),
        "shareUnderPct": round(share_under, 1),
    }


def compute_daily_breakdown(df_eval: pd.DataFrame) -> list[dict]:
    """Breakdown of metrics by delivery date."""
    df_valid = df_eval[df_eval["error"].notna()].copy()
    if df_valid.empty:
        return []

    breakdown = []
    for d, group in df_valid.groupby("settlementDate"):
        errs = group["error"].to_numpy()
        abs_errs = np.abs(errs)
        mae = float(np.mean(abs_errs))
        rmse = float(np.sqrt(np.mean(errs**2)))
        bias = float(np.mean(errs))
        mean_act = float(np.mean(group["actual"]))
        mean_fc = float(np.mean(group["forecast"]))
        breakdown.append({
            "date": d,
            "periods": len(group),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "bias": round(bias, 2),
            "meanActual": round(mean_act, 2),
            "meanForecast": round(mean_fc, 2),
            "shortfallP90": round(float(np.percentile(group["shortfall"], 90)), 2),
        })

    breakdown.sort(key=lambda x: x["date"])
    return breakdown


def compute_hourly_breakdown(df_eval: pd.DataFrame) -> list[dict]:
    """Breakdown of metrics by hour of day (0 to 23)."""
    df_valid = df_eval[df_eval["error"].notna()].copy()
    if df_valid.empty:
        return []

    # Extract hour from startTime (ISO string: YYYY-MM-DDTHH:MM:SSZ)
    df_valid["hour"] = df_valid["startTime"].apply(lambda s: int(s[11:13]))

    breakdown = []
    for h, group in df_valid.groupby("hour"):
        errs = group["error"].to_numpy()
        abs_errs = np.abs(errs)
        breakdown.append({
            "hour": int(h),
            "hourLabel": f"{h:02d}:00",
            "periods": len(group),
            "mae": round(float(np.mean(abs_errs)), 2),
            "rmse": round(float(np.sqrt(np.mean(errs**2))), 2),
            "bias": round(float(np.mean(errs)), 2),
            "meanActual": round(float(np.mean(group["actual"])), 2),
            "meanForecast": round(float(np.mean(group["forecast"])), 2),
        })

    breakdown.sort(key=lambda x: x["hour"])
    return breakdown


def compute_wind_level_breakdown(df_eval: pd.DataFrame) -> list[dict]:
    """Breakdown of metrics by actual wind generation level."""
    df_valid = df_eval[df_eval["error"].notna()].copy()
    if df_valid.empty:
        return []

    # Bin into Low (<7000 MW), Medium (7000-14000 MW), High (>14000 MW)
    bins = [0, 7000, 14000, 100000]
    labels = ["Low (< 7 GW)", "Medium (7-14 GW)", "High (> 14 GW)"]
    df_valid["windLevel"] = pd.cut(df_valid["actual"], bins=bins, labels=labels, right=False)

    breakdown = []
    for lvl in labels:
        group = df_valid[df_valid["windLevel"] == lvl]
        if group.empty:
            continue
        errs = group["error"].to_numpy()
        abs_errs = np.abs(errs)
        breakdown.append({
            "level": lvl,
            "periods": len(group),
            "pctOfTotal": round((len(group) / len(df_valid)) * 100.0, 1),
            "mae": round(float(np.mean(abs_errs)), 2),
            "rmse": round(float(np.sqrt(np.mean(errs**2))), 2),
            "bias": round(float(np.mean(errs)), 2),
            "meanActual": round(float(np.mean(group["actual"])), 2),
        })

    return breakdown


def compute_error_histogram(df_eval: pd.DataFrame, num_bins: int = 18) -> list[dict]:
    """Generate distribution histogram of signed errors."""
    df_valid = df_eval[df_eval["error"].notna()]
    if df_valid.empty:
        return []

    errs = df_valid["error"].to_numpy()
    counts, bin_edges = np.histogram(errs, bins=num_bins)

    hist = []
    for i in range(len(counts)):
        mid = (bin_edges[i] + bin_edges[i + 1]) / 2.0
        hist.append({
            "binStart": round(float(bin_edges[i]), 1),
            "binEnd": round(float(bin_edges[i + 1]), 1),
            "binCenter": round(float(mid), 1),
            "count": int(counts[i]),
        })
    return hist


def compute_horizon_analysis(conn: sqlite3.Connection, date_from: str, date_to: str) -> list[dict]:
    """
    Secondary analysis: Evaluate how forecast accuracy varies by forecast horizon (startTime - publishTime).
    Uses all available forecasts for the targets in the range.
    """
    query = """
        SELECT f.publishTime, f.startTime, f.generation AS forecast, a.generation AS actual
        FROM forecasts f
        JOIN actuals a ON (f.startTime = a.startTime OR f.startTime = substr(a.startTime, 1, 14) || '00:00Z')
        WHERE a.settlementDate >= ? AND a.settlementDate <= ?
    """
    df = pd.read_sql(query, conn, params=[date_from, date_to])
    if df.empty:
        return []

    # Calculate horizon in hours
    dt_target = pd.to_datetime(df["startTime"])
    dt_pub = pd.to_datetime(df["publishTime"])
    df["horizonHours"] = (dt_target - dt_pub).dt.total_seconds() / 3600.0

    # Filter out invalid horizons (< 0)
    df = df[df["horizonHours"] >= 0].copy()
    df["error"] = df["forecast"] - df["actual"]
    df["absError"] = df["error"].abs()

    # Buckets: 0-6h, 6-12h, 12-24h, 24-36h, 36-48h, 48-72h
    bins = [0, 6, 12, 24, 36, 48, 72]
    labels = ["0-6h", "6-12h", "12-24h", "24-36h", "36-48h", "48-72h"]
    df["horizonBucket"] = pd.cut(df["horizonHours"], bins=bins, labels=labels, right=False)

    results = []
    for lbl in labels:
        sub = df[df["horizonBucket"] == lbl]
        if sub.empty:
            continue
        mae = float(sub["absError"].mean())
        rmse = float(np.sqrt((sub["error"] ** 2).mean()))
        bias = float(sub["error"].mean())
        results.append({
            "bucket": lbl,
            "sampleCount": len(sub),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "bias": round(bias, 2),
        })

    return results


def compute_safety_buffer_analysis(
    df_eval: pd.DataFrame,
    target_percentile: float = 90.0,
    min_warmup_days: int = 3,
) -> dict:
    """
    Compute actionable safety buffer (extra MW capacity to hold against wind shortfall).
    Reports both:
    1. In-sample buffer: target percentile of shortfall across whole window
    2. Honest rolling walk-forward backtest:
       For day D, buffer is calibrated strictly on historical shortfalls from days < D.
       Day D periods are evaluated out-of-sample against this buffer.
    """
    df_valid = df_eval[df_eval["shortfall"].notna()].copy()
    if df_valid.empty:
        return {
            "targetPercentile": target_percentile,
            "inSampleBufferMw": 0.0,
            "backtestBufferAvgMw": 0.0,
            "achievedCoveragePct": 0.0,
            "dailyBacktest": [],
        }

    # 1. In-sample buffer
    in_sample_buffer = float(np.percentile(df_valid["shortfall"], target_percentile))

    # 2. Walk-forward backtest
    unique_dates = sorted(df_valid["settlementDate"].unique())
    daily_results = []
    total_out_of_sample_periods = 0
    covered_out_of_sample_periods = 0

    calibrated_buffers = []

    for i, d_str in enumerate(unique_dates):
        day_data = df_valid[df_valid["settlementDate"] == d_str]
        if i < min_warmup_days:
            # Warm-up phase
            daily_results.append({
                "date": d_str,
                "isWarmup": True,
                "calibratedBufferMw": None,
                "maxShortfallMw": round(float(day_data["shortfall"].max()), 2),
                "periodsCovered": len(day_data),
                "totalPeriods": len(day_data),
                "coveragePct": 100.0,
            })
            continue

        # Strictly historical data (days 0 to i-1)
        history_data = df_valid[df_valid["settlementDate"].isin(unique_dates[:i])]
        calibrated_buf = float(np.percentile(history_data["shortfall"], target_percentile))
        calibrated_buffers.append(calibrated_buf)

        day_shortfalls = day_data["shortfall"].to_numpy()
        covered = int(np.sum(day_shortfalls <= calibrated_buf))
        day_total = len(day_shortfalls)
        day_cov_pct = float((covered / day_total) * 100.0) if day_total > 0 else 0.0

        total_out_of_sample_periods += day_total
        covered_out_of_sample_periods += covered

        daily_results.append({
            "date": d_str,
            "isWarmup": False,
            "calibratedBufferMw": round(calibrated_buf, 2),
            "maxShortfallMw": round(float(day_shortfalls.max()), 2),
            "periodsCovered": covered,
            "totalPeriods": day_total,
            "coveragePct": round(day_cov_pct, 1),
        })

    achieved_cov = (
        float((covered_out_of_sample_periods / total_out_of_sample_periods) * 100.0)
        if total_out_of_sample_periods > 0
        else 0.0
    )
    avg_backtest_buf = float(np.mean(calibrated_buffers)) if calibrated_buffers else in_sample_buffer

    return {
        "targetPercentile": target_percentile,
        "inSampleBufferMw": round(in_sample_buffer, 2),
        "backtestBufferAvgMw": round(avg_backtest_buf, 2),
        "achievedCoveragePct": round(achieved_cov, 1),
        "totalEvaluatedPeriods": total_out_of_sample_periods,
        "coveredPeriods": covered_out_of_sample_periods,
        "dailyBacktest": daily_results,
    }
