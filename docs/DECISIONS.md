# Project Architectural & Domain Decisions Log

This document records key technical, domain, and methodological decisions verified during the development of the UK Wind Forecast Decision & Accuracy Portal.

---

## 1. Elexon BMRS API Discovery & Verification

- **Date:** 2026-10-26
- **Status:** Verified with live endpoints
- **API Base URL:** `https://data.elexon.co.uk/bmrs/api/v1`
- **Authentication:** No API key required.
- **Content-Type / Accept:** Endpoints accept `Accept: application/json` and return standard JSON payloads.

### Endpoints Verified
1. **Actual Generation:** `GET /datasets/FUELHH/stream`
   - Parameters used: `settlementDateFrom=YYYY-MM-DD`, `settlementDateTo=YYYY-MM-DD`, `fuelType=WIND`.
   - Resolution: 30 minutes (Settlement Periods 1 through 48 per day).
   - Fields: `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation`.
   - Data Quality Check (Jan 2026): Exactly 1,488 records (31 days × 48 half-hours). 0 nulls, 0 missing periods, 0 duplicate records. Generation ranges from 1,695 MW to 17,805 MW (mean 11,580.7 MW).

2. **Forecasted Generation:** `GET /datasets/WINDFOR/stream`
   - Parameters used: `publishDateTimeFrom=...`, `publishDateTimeTo=...`.
   - Resolution: 60 minutes (hourly start times: `00:00:00Z`, `01:00:00Z`, etc.). All records have `:00:00Z` timestamps.
   - Horizon: ~72 hours ahead (~3 days of forward projection per publication).
   - Publication Frequency: ~8 publications per 24-hour cycle (e.g. 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC).
   - Fields: `dataset`, `publishTime`, `startTime`, `generation`.

---

## 2. Temporal Alignment: Hourly Forecasts vs. Half-Hourly Actuals

- **Question:** How to align 60-minute WINDFOR forecasts with 30-minute FUELHH actuals?
- **Decision:** 
  1. In UK electricity balancing, wind power (in MW) represents average power rate. The hourly forecast for hour $H$ (starting at $H:00$) represents the projected average rate across that hour.
  2. For the primary half-hourly view (48 settlement periods per day), the hourly forecast value at $H:00$ is assigned to both settlement periods in that hour: $H:00$ and $H:30$.
  3. No artificial polynomial or spline interpolation is fabricated; step-wise assignment preserves raw forecast integrity.
  4. Both the 48-period view and an hourly aggregated view are supported.

---

## 3. Decision Timeline & Selection Rule (Core Domain Rule)

- **Rule:** For any delivery target half-hour $T$ on delivery day $D$:
  $$\text{Cutoff}(D) = (D - 1\text{ day}) \text{ at } \text{CUTOFF\_TIME} \text{ (Europe/London)}$$
  $$\text{forecast}(T) = \operatorname{argmax}_{publishTime \le \text{Cutoff}(D)} \text{WINDFOR}(startTime=T)$$
- **Strict Anti-Leakage Guarantee:** Any forecast published with $publishTime > \text{Cutoff}(D)$ was **physically unavailable** to the day-ahead trader at gate closure and **must never be used**.
- **Default Cutoff:** `09:00` Europe/London on day $D-1$ (safe default prior to standard 11:00/12:00 UK day-ahead auction gate closures).
- **Interactive Control:** Cutoff time is user-configurable in the UI; all decision-time metrics update dynamically.

---

## 4. Scope and January 2026 Interpretation

- **Interpretation:** Delivery days `2026-01-01` to `2026-01-31` inclusive (31 days, 1,488 half-hour settlement periods).
- **First Decision Day:** `2025-12-31` (at cutoff time, e.g. 09:00).
- **Ingest Window:** Forecast publish times from `2025-12-25T00:00:00Z` through `2026-01-31T23:59:59Z` are ingested to guarantee complete coverage for all January delivery targets and various cutoff horizons.

---

## 5. Sign Convention & Metric Definitions

- **Error Formula:** 
  $$\text{Error} = \text{Forecast} - \text{Actual} \quad (\text{MW})$$
- **Interpretation:**
  - **Positive Error ($\text{Error} > 0$):** Forecast was too high (Over-forecast). The buyer expected more wind than was generated $\rightarrow$ **Shortfall risk** (risk of under-procuring thermal power).
  - **Negative Error ($\text{Error} < 0$):** Forecast was too low (Under-forecast). The buyer expected less wind $\rightarrow$ **Excess risk** (risk of over-procuring thermal power).
- **Metrics Calculated:**
  - **MAE (Mean Absolute Error):** $\frac{1}{N} \sum |\text{error}|$ in MW.
  - **RMSE (Root Mean Square Error):** $\sqrt{\frac{1}{N} \sum \text{error}^2}$ in MW.
  - **Bias:** $\frac{1}{N} \sum \text{error}$ in MW.
  - **nMAE (Normalized MAE):** $\text{MAE} / \overline{\text{Actual}}$ expressed as a percentage.
  - **Percentiles:** P10, P50 (median), P90 of signed error; P95 of absolute error.
  - **Safety Buffer:** Target shortfall percentile (e.g. 90th percentile of $\max(0, \text{forecast} - \text{actual})$), reported as in-sample and rolling walk-forward backtest.

---

## 6. Storage & Architecture Decisions

- **Storage Engine:** SQLite (`backend/data/wind_data.db`).
  - Self-contained, zero-configuration, robust SQL querying.
  - Dataset size is ~2 MB, suitable for git repository inclusion and sub-millisecond query responses in Docker/cloud environments.
  - Fully rebuildable using `python -m ingest.build_dataset` or `make ingest`.
- **Backend:** FastAPI (Python 3.12) with typed Pydantic v2 schemas and clean separation:
  - `ingest/`: API fetching, data cleansing, database population.
  - `analysis/`: Pure calculation functions (selection rule, metrics, safety buffer backtesting).
  - `app/`: REST API endpoints, input validation, CORS, error handling.
- **Frontend:** Next.js (React 19 / TypeScript) with Tailwind CSS, Lucide icons, and Recharts. Built for high readability, responsive trading desk UX, and dark/light contrast.
- **Anonymity:** Configured neutral git identity (`dev` / `dev@users.noreply.github.com`). No personal or corporate identifying information in code or documentation.
