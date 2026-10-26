"""Unit tests for the decision selection rule and anti-future-data leakage guarantees."""

import sqlite3

import pytest

from backend.analysis.selection import (
    compute_cutoff_utc,
    get_forecast_revisions_for_day,
    select_decision_forecasts_for_range,
)


@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE actuals (
            startTime TEXT PRIMARY KEY,
            settlementDate TEXT NOT NULL,
            settlementPeriod INTEGER NOT NULL,
            generation REAL NOT NULL,
            publishTime TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publishTime TEXT NOT NULL,
            startTime TEXT NOT NULL,
            generation REAL NOT NULL
        )
    """)

    # Delivery day: 2026-01-05
    # Actuals for period 1 (00:00) and period 2 (00:30)
    cur.execute("INSERT INTO actuals VALUES ('2026-01-05T00:00:00Z', '2026-01-05', 1, 10000.0, '2026-01-05T01:00:00Z')")
    cur.execute("INSERT INTO actuals VALUES ('2026-01-05T00:30:00Z', '2026-01-05', 2, 10200.0, '2026-01-05T01:00:00Z')")

    conn.commit()
    yield conn
    conn.close()


def test_compute_cutoff_utc():
    # For delivery day 2026-01-05, cutoff 09:00 London time -> 2026-01-04T09:00:00Z
    cutoff = compute_cutoff_utc("2026-01-05", "09:00")
    assert cutoff == "2026-01-04T09:00:00Z"


def test_selection_rule_at_and_before_cutoff(mock_db):
    """Forecast published before or at cutoff is chosen; post-cutoff is NEVER chosen."""
    cur = mock_db.cursor()
    # Cutoff is 2026-01-04T09:00:00Z
    # 1. Early forecast: 2026-01-03T18:00:00Z -> 9000 MW
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-03T18:00:00Z', '2026-01-05T00:00:00Z', 9000.0)")
    # 2. Exactly at cutoff: 2026-01-04T09:00:00Z -> 9500 MW (Qualifies!)
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T09:00:00Z', '2026-01-05T00:00:00Z', 9500.0)")
    # 3. 1 minute AFTER cutoff: 2026-01-04T09:01:00Z -> 10000 MW (Closer to actual 10000, but FORBIDDEN!)
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T09:01:00Z', '2026-01-05T00:00:00Z', 10000.0)")
    mock_db.commit()

    df = select_decision_forecasts_for_range(mock_db, "2026-01-05", "2026-01-05", "09:00")
    assert len(df) == 2

    row_p1 = df[df["settlementPeriod"] == 1].iloc[0]
    # Must select 9500 MW (at cutoff), NOT 10000 MW (after cutoff) and NOT 9000 MW (older)
    assert row_p1["forecast"] == 9500.0
    assert row_p1["publishTime"] == "2026-01-04T09:00:00Z"
    assert row_p1["actual"] == 10000.0
    # error = forecast - actual = 9500 - 10000 = -500 MW
    assert row_p1["error"] == -500.0
    assert row_p1["shortfall"] == 0.0


def test_selection_rule_post_cutoff_never_chosen(mock_db):
    """When ONLY post-cutoff forecasts exist, period is marked missing (null), never filled with future data."""
    cur = mock_db.cursor()
    # Only forecast published 1 minute after cutoff
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T09:01:00Z', '2026-01-05T00:00:00Z', 10000.0)")
    mock_db.commit()

    df = select_decision_forecasts_for_range(mock_db, "2026-01-05", "2026-01-05", "09:00")
    assert len(df) == 2
    row = df.iloc[0]
    assert row["forecast"] is None
    assert row["error"] is None
    assert row["shortfall"] is None


def test_hourly_to_half_hourly_mapping(mock_db):
    """An hourly forecast at 00:00 maps to both 00:00 (period 1) and 00:30 (period 2)."""
    cur = mock_db.cursor()
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T08:30:00Z', '2026-01-05T00:00:00Z', 12000.0)")
    mock_db.commit()

    df = select_decision_forecasts_for_range(mock_db, "2026-01-05", "2026-01-05", "09:00")
    p1 = df[df["settlementPeriod"] == 1].iloc[0]
    p2 = df[df["settlementPeriod"] == 2].iloc[0]

    assert p1["forecast"] == 12000.0
    assert p2["forecast"] == 12000.0
    # Period 1 error: 12000 - 10000 = 2000
    assert p1["error"] == 2000.0
    # Period 2 error: 12000 - 10200 = 1800
    assert p2["error"] == 1800.0


def test_forecast_revisions(mock_db):
    cur = mock_db.cursor()
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T06:00:00Z', '2026-01-05T00:00:00Z', 9000.0)")
    cur.execute("INSERT INTO forecasts (publishTime, startTime, generation) VALUES ('2026-01-04T08:00:00Z', '2026-01-05T00:00:00Z', 9500.0)")
    mock_db.commit()

    revs = get_forecast_revisions_for_day(mock_db, "2026-01-05", "09:00")
    assert revs["deliveryDate"] == "2026-01-05"
    assert len(revs["revisions"]) == 2
    assert revs["decisionPublishTime"] == "2026-01-04T08:00:00Z"
    assert revs["revisions"][-1]["isDecisionForecast"] is True
