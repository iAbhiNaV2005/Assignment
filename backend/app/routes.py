"""FastAPI route handlers implementing the full analytical API contract."""

import csv
import io
import os
import re
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

try:
    from backend.analysis.metrics import (
        compute_daily_breakdown,
        compute_error_histogram,
        compute_headline_metrics,
        compute_horizon_analysis,
        compute_hourly_breakdown,
        compute_safety_buffer_analysis,
        compute_wind_level_breakdown,
    )
    from backend.analysis.selection import (
        compute_cutoff_utc,
        get_forecast_revisions_for_day,
        select_decision_forecasts_for_range,
    )
    from backend.app.config import settings
    from backend.app.database import get_db_connection, get_db_path
    from backend.app.schemas import (
        BufferResponse,
        ConfigResponse,
        DecisionResponse,
        HealthResponse,
        HistogramBin,
        HorizonItem,
        MetricsResponse,
        RevisionsResponse,
    )
except (ImportError, ModuleNotFoundError):
    from analysis.metrics import (  # type: ignore
        compute_daily_breakdown,
        compute_error_histogram,
        compute_headline_metrics,
        compute_horizon_analysis,
        compute_hourly_breakdown,
        compute_safety_buffer_analysis,
        compute_wind_level_breakdown,
    )
    from analysis.selection import (  # type: ignore
        compute_cutoff_utc,
        get_forecast_revisions_for_day,
        select_decision_forecasts_for_range,
    )
    from app.config import settings  # type: ignore
    from app.database import get_db_connection, get_db_path  # type: ignore
    from app.schemas import (  # type: ignore
        BufferResponse,
        ConfigResponse,
        DecisionResponse,
        HealthResponse,
        HistogramBin,
        HorizonItem,
        MetricsResponse,
        RevisionsResponse,
    )

router = APIRouter(prefix="/api")


def validate_date(date_str: str, param_name: str = "date") -> str:
    """Validate date format and range within January 2026."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise HTTPException(
            status_code=422,
            detail=f"Parameter '{param_name}' must be formatted as YYYY-MM-DD (e.g. 2026-01-15).",
        )
    if date_str < settings.MIN_DATE or date_str > settings.MAX_DATE:
        raise HTTPException(
            status_code=422,
            detail=f"Parameter '{param_name}' must be within scope: {settings.MIN_DATE} to {settings.MAX_DATE}.",
        )
    return date_str


def validate_cutoff(cutoff_str: str) -> str:
    """Validate cutoff time format (HH:MM)."""
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", cutoff_str):
        raise HTTPException(
            status_code=422,
            detail=f"Cutoff time '{cutoff_str}' must be formatted as HH:MM between 00:00 and 23:59.",
        )
    return cutoff_str


def sanitize_floats(obj):
    """Recursively convert float NaN/Inf to None for JSON compliance."""
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_floats(v) for v in obj]
    return obj


@router.get("/health", response_model=HealthResponse)
def get_health():
    """System health check, dataset coverage, and record counts."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=500, detail="Database file not found.")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM actuals")
    act_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM forecasts")
    fc_count = cur.fetchone()[0]
    cur.execute("SELECT min(startTime), max(startTime) FROM actuals")
    r_act = cur.fetchone()
    conn.close()

    return HealthResponse(
        status="healthy",
        databasePath=os.path.basename(db_path),
        databaseSizeBytes=os.path.getsize(db_path),
        actualRecordsCount=act_count,
        forecastRecordsCount=fc_count,
        dataRangeStart=r_act[0] if r_act else None,
        dataRangeEnd=r_act[1] if r_act else None,
    )


@router.get("/config", response_model=ConfigResponse)
def get_config():
    """Application constants, allowed date scope, and default cutoff."""
    return ConfigResponse(
        minDate=settings.MIN_DATE,
        maxDate=settings.MAX_DATE,
        defaultCutoff=settings.DEFAULT_CUTOFF,
        defaultPercentile=90.0,
        timeZone="Europe/London",
    )


@router.get("/decision", response_model=DecisionResponse)
def get_decision(
    date: str = Query("2026-01-15", description="Delivery day (YYYY-MM-DD)"),
    cutoff: str = Query("09:00", description="Cutoff time (HH:MM local) on day D-1"),
):
    """
    Returns 48 settlement periods for delivery day with selected decision-time forecast,
    actual outturn, error, and day summary statistics.
    """
    valid_date = validate_date(date, "date")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_date, valid_date, valid_cutoff)
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for delivery date {valid_date}")

    periods = sanitize_floats(df.to_dict(orient="records"))
    cutoff_utc = compute_cutoff_utc(valid_date, valid_cutoff)

    # Compute day summary
    valid_mask = df["error"].notna()
    if valid_mask.any():
        errs = df.loc[valid_mask, "error"].to_numpy()
        abs_errs = np.abs(errs)
        mean_act = float(df.loc[valid_mask, "actual"].mean())
        mean_fc = float(df.loc[valid_mask, "forecast"].mean())
        mae = float(np.mean(abs_errs))
        rmse = float(np.sqrt(np.mean(errs**2)))
        bias = float(np.mean(errs))
        p90_shortfall = float(np.percentile(df.loc[valid_mask, "shortfall"], 90))
    else:
        mean_act = mean_fc = mae = rmse = bias = p90_shortfall = None

    summary = {
        "date": valid_date,
        "totalPeriods": len(df),
        "meanActualMw": round(mean_act, 2) if mean_act is not None else None,
        "meanForecastMw": round(mean_fc, 2) if mean_fc is not None else None,
        "maeMw": round(mae, 2) if mae is not None else None,
        "rmseMw": round(rmse, 2) if rmse is not None else None,
        "biasMw": round(bias, 2) if bias is not None else None,
        "shortfallP90Mw": round(p90_shortfall, 2) if p90_shortfall is not None else None,
    }

    return DecisionResponse(
        deliveryDate=valid_date,
        cutoffLocal=valid_cutoff,
        cutoffUtc=cutoff_utc,
        summary=summary,
        periods=periods,
    )


@router.get("/revisions", response_model=RevisionsResponse)
def get_revisions(
    date: str = Query("2026-01-15", description="Delivery day (YYYY-MM-DD)"),
    cutoff: str = Query("09:00", description="Cutoff time (HH:MM local) on day D-1"),
):
    """
    Returns forecast series evolution across successive publication times up to cutoff,
    overlayed with actual outturn.
    """
    valid_date = validate_date(date, "date")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    revs = get_forecast_revisions_for_day(conn, valid_date, valid_cutoff)
    conn.close()

    return sanitize_floats(revs)


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    from_date: str = Query("2026-01-01", alias="from", description="Start date YYYY-MM-DD"),
    to_date: str = Query("2026-01-31", alias="to", description="End date YYYY-MM-DD"),
    cutoff: str = Query("09:00", description="Cutoff time (HH:MM local)"),
):
    """Compute aggregate accuracy metrics (MAE, RMSE, Bias, nMAE, Percentiles) across date range."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")
    valid_cutoff = validate_cutoff(cutoff)

    if valid_from > valid_to:
        raise HTTPException(
            status_code=422,
            detail=f"'from' date ({valid_from}) cannot be after 'to' date ({valid_to}).",
        )

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_from, valid_to, valid_cutoff)
    conn.close()

    metrics = compute_headline_metrics(df)
    metrics["dateFrom"] = valid_from
    metrics["dateTo"] = valid_to
    metrics["cutoffLocal"] = valid_cutoff
    return sanitize_floats(metrics)


@router.get("/metrics/breakdown")
def get_breakdown(
    by: Literal["day", "hour", "wind_level"] = Query("day", description="Grouping dimension"),
    from_date: str = Query("2026-01-01", alias="from"),
    to_date: str = Query("2026-01-31", alias="to"),
    cutoff: str = Query("09:00"),
):
    """Metric breakdowns by day, hour of day, or wind generation level."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_from, valid_to, valid_cutoff)
    conn.close()

    if by == "day":
        return sanitize_floats(compute_daily_breakdown(df))
    elif by == "hour":
        return sanitize_floats(compute_hourly_breakdown(df))
    elif by == "wind_level":
        return sanitize_floats(compute_wind_level_breakdown(df))


@router.get("/metrics/histogram", response_model=list[HistogramBin])
def get_histogram(
    from_date: str = Query("2026-01-01", alias="from"),
    to_date: str = Query("2026-01-31", alias="to"),
    cutoff: str = Query("09:00"),
    bins: int = Query(18, ge=5, le=50),
):
    """Error distribution histogram bins."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_from, valid_to, valid_cutoff)
    conn.close()

    return sanitize_floats(compute_error_histogram(df, num_bins=bins))


@router.get("/horizon", response_model=list[HorizonItem])
def get_horizon(
    from_date: str = Query("2026-01-01", alias="from"),
    to_date: str = Query("2026-01-31", alias="to"),
):
    """Secondary analysis: forecast accuracy versus horizon in hours."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")

    conn = get_db_connection()
    res = compute_horizon_analysis(conn, valid_from, valid_to)
    conn.close()

    return sanitize_floats(res)


@router.get("/buffer", response_model=BufferResponse)
def get_buffer(
    from_date: str = Query("2026-01-01", alias="from"),
    to_date: str = Query("2026-01-31", alias="to"),
    cutoff: str = Query("09:00"),
    percentile: float = Query(90.0, ge=50.0, le=99.9),
):
    """Safety buffer recommendation and out-of-sample walk-forward backtest."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_from, valid_to, valid_cutoff)
    conn.close()

    res = compute_safety_buffer_analysis(df, target_percentile=percentile)
    return sanitize_floats(res)


@router.get("/export.csv")
def export_csv(
    from_date: str = Query("2026-01-01", alias="from"),
    to_date: str = Query("2026-01-31", alias="to"),
    cutoff: str = Query("09:00"),
):
    """Download period-by-period decision data as CSV."""
    valid_from = validate_date(from_date, "from")
    valid_to = validate_date(to_date, "to")
    valid_cutoff = validate_cutoff(cutoff)

    conn = get_db_connection()
    df = select_decision_forecasts_for_range(conn, valid_from, valid_to, valid_cutoff)
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "startTimeUtc",
        "settlementDate",
        "settlementPeriod",
        "actualGenerationMw",
        "decisionForecastMw",
        "forecastErrorMw",
        "shortfallMw",
        "forecastPublishTimeUtc",
        "decisionCutoffUtc",
    ])

    for _, row in df.iterrows():
        writer.writerow([
            row["startTime"],
            row["settlementDate"],
            row["settlementPeriod"],
            row["actual"],
            row["forecast"],
            row["error"],
            row["shortfall"],
            row["publishTime"],
            row["cutoffUtc"],
        ])

    output.seek(0)
    filename = f"wind_decision_data_{valid_from}_{valid_to}_cutoff_{valid_cutoff.replace(':', '')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
