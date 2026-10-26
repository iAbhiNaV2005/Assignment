"""Unit tests for Elexon data cleaning and database initialization."""

import json
import os
import sqlite3

import pandas as pd
import pytest

from backend.ingest.build_dataset import save_to_database
from backend.ingest.clean import clean_fuelhh_data, clean_windfor_data, parse_iso_utc


@pytest.fixture
def sample_fuelhh_raw():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "samples", "fuelhh_sample.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            return json.load(f)
    return [
        {"dataset": "FUELHH", "publishTime": "2026-01-02T00:00:00Z", "startTime": "2026-01-01T00:00:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 10500},
        {"dataset": "FUELHH", "publishTime": "2026-01-02T00:00:00Z", "startTime": "2026-01-01T00:30:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 2, "fuelType": "WIND", "generation": 10700},
    ]


@pytest.fixture
def sample_windfor_raw():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "samples", "windfor_sample.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r") as f:
            return json.load(f)
    return [
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T02:30:00Z", "startTime": "2026-01-01T03:00:00Z", "generation": 11000},
        {"dataset": "WINDFOR", "publishTime": "2026-01-01T02:30:00Z", "startTime": "2026-01-01T04:00:00Z", "generation": 11500},
    ]


def test_parse_iso_utc():
    assert parse_iso_utc("2026-01-01T00:00:00Z") == "2026-01-01T00:00:00Z"
    assert parse_iso_utc("2026-01-01T00:00:00+00:00") == "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        parse_iso_utc("")


def test_clean_fuelhh(sample_fuelhh_raw):
    df = clean_fuelhh_data(sample_fuelhh_raw)
    assert not df.empty
    assert "startTime" in df.columns
    assert "generation" in df.columns
    assert (df["generation"] >= 0).all()
    # Check deduplication
    assert df["startTime"].nunique() == len(df)


def test_clean_fuelhh_filters_non_wind():
    raw = [
        {"fuelType": "NUCLEAR", "startTime": "2026-01-01T00:00:00Z", "generation": 5000},
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 12000},
    ]
    df = clean_fuelhh_data(raw)
    assert len(df) == 1
    assert df.iloc[0]["generation"] == 12000.0


def test_clean_windfor(sample_windfor_raw):
    df = clean_windfor_data(sample_windfor_raw)
    assert not df.empty
    assert "publishTime" in df.columns
    assert "startTime" in df.columns
    assert "generation" in df.columns
    assert (df["generation"] >= 0).all()


def test_clean_windfor_clamps_negative_and_deduplicates():
    raw = [
        {"publishTime": "2026-01-01T00:00:00Z", "startTime": "2026-01-01T05:00:00Z", "generation": -50},
        {"publishTime": "2026-01-01T00:00:00Z", "startTime": "2026-01-01T05:00:00Z", "generation": 250},
    ]
    df = clean_windfor_data(raw)
    assert len(df) == 1
    assert df.iloc[0]["generation"] == 250.0


def test_database_init_and_save(tmp_path):
    test_db = str(tmp_path / "test_wind.db")
    df_act = pd.DataFrame([{
        "startTime": "2026-01-01T00:00:00Z",
        "settlementDate": "2026-01-01",
        "settlementPeriod": 1,
        "generation": 10000.0,
        "publishTime": "2026-01-01T01:00:00Z",
    }])
    df_fc = pd.DataFrame([{
        "publishTime": "2025-12-31T08:00:00Z",
        "startTime": "2026-01-01T00:00:00Z",
        "generation": 10200.0,
    }])

    save_to_database(df_act, df_fc, db_path=test_db)
    assert os.path.exists(test_db)

    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM actuals")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT count(*) FROM forecasts")
    assert cur.fetchone()[0] == 1
    conn.close()
