"""API endpoint tests using FastAPI TestClient."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["actualRecordsCount"] == 1488
    assert data["forecastRecordsCount"] > 0


def test_config_endpoint():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["minDate"] == "2026-01-01"
    assert data["maxDate"] == "2026-01-31"
    assert data["defaultCutoff"] == "09:00"


def test_decision_endpoint_valid():
    resp = client.get("/api/decision?date=2026-01-10&cutoff=09:00")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deliveryDate"] == "2026-01-10"
    assert data["cutoffLocal"] == "09:00"
    assert len(data["periods"]) == 48
    assert "summary" in data
    assert data["summary"]["totalPeriods"] == 48


def test_decision_endpoint_invalid_date():
    # Outside January 2026
    resp = client.get("/api/decision?date=2025-12-31&cutoff=09:00")
    assert resp.status_code == 422
    assert "must be within scope" in resp.json()["detail"]


def test_decision_endpoint_invalid_cutoff():
    resp = client.get("/api/decision?date=2026-01-10&cutoff=25:00")
    assert resp.status_code == 422
    assert "must be formatted as HH:MM" in resp.json()["detail"]


def test_revisions_endpoint():
    resp = client.get("/api/revisions?date=2026-01-10&cutoff=09:00")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deliveryDate"] == "2026-01-10"
    assert "revisions" in data
    assert "actuals" in data


def test_metrics_endpoint():
    resp = client.get("/api/metrics?from=2026-01-01&to=2026-01-10&cutoff=09:00")
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluatedPeriods"] == 10 * 48
    assert data["mae"] is not None
    assert data["rmse"] is not None
    assert data["coveragePct"] == 100.0


def test_breakdown_endpoints():
    for dimension in ["day", "hour", "wind_level"]:
        resp = client.get(f"/api/metrics/breakdown?by={dimension}&from=2026-01-01&to=2026-01-05&cutoff=09:00")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


def test_histogram_endpoint():
    resp = client.get("/api/metrics/histogram?from=2026-01-01&to=2026-01-05&cutoff=09:00&bins=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10


def test_horizon_endpoint():
    resp = client.get("/api/horizon?from=2026-01-01&to=2026-01-05")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert "bucket" in data[0]
    assert "mae" in data[0]


def test_buffer_endpoint():
    resp = client.get("/api/buffer?from=2026-01-01&to=2026-01-10&cutoff=09:00&percentile=90")
    assert resp.status_code == 200
    data = resp.json()
    assert "inSampleBufferMw" in data
    assert "backtestBufferAvgMw" in data
    assert "achievedCoveragePct" in data
    assert len(data["dailyBacktest"]) == 10


def test_export_csv_endpoint():
    resp = client.get("/api/export.csv?from=2026-01-01&to=2026-01-02&cutoff=09:00")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    content = resp.text
    assert "startTimeUtc" in content
    assert "actualGenerationMw" in content
    assert "decisionForecastMw" in content
