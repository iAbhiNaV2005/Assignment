# Architecture & Technical Design Specification

## 1. System Architecture Diagram

```
                 ┌────────────────────────────────────────────────────────┐
                 │                 Elexon BMRS Live API                  │
                 │   https://data.elexon.co.uk/bmrs/api/v1                │
                 └───────────┬────────────────────────────────┬───────────┘
                             │                                │
              FUELHH (Half-hourly Actuals)      WINDFOR (Hourly Forecasts)
              WIND Generation stream            National forecast stream
                             │                                │
                             ▼                                ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                  Ingestion Subsystem                   │
                 │   backend/ingest/fetch.py (Chunked + Retry/Backoff)    │
                 │   backend/ingest/clean.py (Deduplication + UTC Norm)   │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                 Processed Data Store                   │
                 │   backend/data/wind_data.db (SQLite ~3.1 MB)           │
                 │   - actuals: 1,488 records (Jan 1 - Jan 31, 2026)      │
                 │   - forecasts: 22,192 records (Dec 25 - Jan 31)        │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                 Python Analysis Engine                 │
                 │   backend/analysis/selection.py                        │
                 │   - Strict anti-future-data gate closure cutoff rule   │
                 │   - Forecast revisions evolution extractor            │
                 │   backend/analysis/metrics.py                          │
                 │   - MAE, RMSE, Bias, nMAE%, Tail quantiles             │
                 │   - Walk-forward rolling safety buffer backtesting     │
                 │   - Forecast error vs horizon (0-72h) lead curves      │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                  FastAPI Backend API                   │
                 │   backend/app/routes.py (Pydantic v2 Contracts)        │
                 │   - /api/decision?date=...&cutoff=...                  │
                 │   - /api/metrics?from=...&to=...&cutoff=...            │
                 │   - /api/buffer?percentile=90                          │
                 │   - /api/revisions, /api/horizon, /api/export.csv      │
                 └───────────────────────────┬────────────────────────────┘
                                             │ JSON over HTTP
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │            Next.js / React 19 Frontend Desk            │
                 │   frontend/src/app (Tailwind CSS + Recharts)           │
                 │   - Day-Ahead Decision Desk (48 SP Intraday Area Chart)│
                 │   - Accuracy & Risk Suite (Buffer Slider, Diurnal)     │
                 │   - Interactive Methodology & Provenance Guide         │
                 └────────────────────────────────────────────────────────┘
```

## 2. Core Anti-Leakage Guarantee

Day-ahead wholesale electricity procurement occurs strictly on day $D-1$ before gate closure.

$$\text{Cutoff}(D) = (D - 1\text{ day}) \text{ at } \text{CUTOFF\_LOCAL} \text{ (Europe/London)}$$
$$\text{forecast}(T) = \operatorname{argmax}_{publishTime \le \text{Cutoff}(D)} \text{WINDFOR}(startTime = T)$$

- **Strict Validation:** If a forecast has $publishTime > \text{Cutoff}(D)$, it was physically unknown to the trading desk when bids were submitted. Using it constitutes data leakage.
- **Missing Periods:** If no forecast was published prior to cutoff for target period $T$, the period is marked as missing/uncovered ($null$), never forward-filled or interpolated with future data.

## 3. Walk-Forward Safety Buffer Formulation

To establish an honest procurement safety margin without look-ahead bias:
1. For delivery day $D$, the system isolates all historical errors strictly from days $1$ to $D-1$:
   $$\mathcal{H}_{D} = \{ \max(0, \text{forecast}(t) - \text{actual}(t)) \mid \text{date}(t) < D \}$$
2. The recommended buffer $\mathcal{B}_D$ is the $q$-th percentile (e.g. 90th percentile) of $\mathcal{H}_D$.
3. Day $D$ periods are evaluated out-of-sample against $\mathcal{B}_D$.
4. Achieved coverage across January 2026 is **89.3%** against the target 90% confidence level.

## 4. Container & Production Deployment

- **Containerization:** Clean multi-stage Dockerfiles for backend (Python 3.12 slim) and frontend (Node 20 Alpine).
- **Orchestration:** `docker-compose.yml` boots both services with health checks and zero configuration.
- **Portability:** Self-contained SQLite data layer enables instantaneous startup with zero network dependencies.
