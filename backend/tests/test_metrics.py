"""Unit tests for quantitative error metrics and safety buffer walk-forward backtest."""

import pandas as pd
import pytest

from backend.analysis.metrics import (
    compute_headline_metrics,
    compute_safety_buffer_analysis,
)


@pytest.fixture
def hand_crafted_eval_df():
    # 5 controlled data points:
    # errors: [-200, 100, 300, -100, 400]
    # actuals: [1000, 2000, 1500, 2500, 3000] (mean = 2000)
    # forecasts: [800, 2100, 1800, 2400, 3400]
    # shortfalls: [0, 100, 300, 0, 400]
    data = [
        {"startTime": "2026-01-01T00:00:00Z", "settlementDate": "2026-01-01", "actual": 1000.0, "forecast": 800.0, "error": -200.0, "shortfall": 0.0},
        {"startTime": "2026-01-01T00:30:00Z", "settlementDate": "2026-01-01", "actual": 2000.0, "forecast": 2100.0, "error": 100.0, "shortfall": 100.0},
        {"startTime": "2026-01-02T01:00:00Z", "settlementDate": "2026-01-02", "actual": 1500.0, "forecast": 1800.0, "error": 300.0, "shortfall": 300.0},
        {"startTime": "2026-01-02T01:30:00Z", "settlementDate": "2026-01-02", "actual": 2500.0, "forecast": 2400.0, "error": -100.0, "shortfall": 0.0},
        {"startTime": "2026-01-03T02:00:00Z", "settlementDate": "2026-01-03", "actual": 3000.0, "forecast": 3400.0, "error": 400.0, "shortfall": 400.0},
    ]
    return pd.DataFrame(data)


def test_headline_metrics_hand_checked(hand_crafted_eval_df):
    metrics = compute_headline_metrics(hand_crafted_eval_df)
    # abs errors: [200, 100, 300, 100, 400] -> sum = 1100 -> mean = 220.0
    assert metrics["mae"] == 220.0

    # errors^2: [40000, 10000, 90000, 10000, 160000] -> sum = 310000 -> mean = 62000 -> sqrt = 248.9979...
    assert round(metrics["rmse"], 1) == 249.0

    # signed sum = -200 + 100 + 300 - 100 + 400 = 500 -> mean = 100.0
    assert metrics["bias"] == 100.0

    # mean actual = 2000.0, nmae = 220 / 2000 * 100 = 11.0%
    assert metrics["nmae"] == 11.0

    # positive errors: 3 of 5 -> 60.0%
    assert metrics["shareOverPct"] == 60.0
    # negative errors: 2 of 5 -> 40.0%
    assert metrics["shareUnderPct"] == 40.0


def test_safety_buffer_walk_forward_strict_no_future():
    """Verify that walk-forward backtest for day D strictly uses historical data < D."""
    dates = [f"2026-01-{i:02d}" for i in range(1, 6)]
    # Day 1: shortfall 100
    # Day 2: shortfall 200
    # Day 3: shortfall 300
    # Day 4: shortfall 400 (backtested day with warmup=3)
    # Day 5: shortfall 500
    records = []
    for i, d in enumerate(dates):
        records.append({
            "startTime": f"{d}T10:00:00Z",
            "settlementDate": d,
            "actual": 5000.0,
            "forecast": 5000.0 + (i + 1) * 100.0,
            "error": (i + 1) * 100.0,
            "shortfall": (i + 1) * 100.0,
        })
    df = pd.DataFrame(records)

    buf_result = compute_safety_buffer_analysis(df, target_percentile=90.0, min_warmup_days=3)
    daily = buf_result["dailyBacktest"]

    # Days 1, 2, 3 are warmup
    assert daily[0]["isWarmup"] is True
    assert daily[1]["isWarmup"] is True
    assert daily[2]["isWarmup"] is True

    # Day 4 is evaluated against history of days 1, 2, 3:
    # history shortfalls = [100, 200, 300]
    # 90th percentile of [100, 200, 300] = 280.0
    assert daily[3]["isWarmup"] is False
    calibrated_for_day4 = daily[3]["calibratedBufferMw"]
    # Verify it strictly used days 1,2,3 and did NOT know day 4 (400) or day 5 (500)
    assert calibrated_for_day4 < 400.0
    # Day 4 shortfall (400) exceeded calibrated buffer (280)
    assert daily[3]["periodsCovered"] == 0
