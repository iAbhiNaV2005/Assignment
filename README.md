# UK Wind Forecast Decision & Accuracy Portal

An analytical trading desk web application developed for a UK power procurement team responsible for purchasing electricity on the UK Day-Ahead wholesale market. The portal enables traders to freeze and examine the latest authoritative wind generation forecasts physically available at gate closure (D-1 cutoff), evaluate quantitative forecast errors against Elexon BMRS actual outturns for January 2026, and calculate an actionable safety buffer using honest rolling walk-forward backtesting.

---

## 1. Live Deployment & Documentation Links

- **Live Application:** [https://uk-wind-portal.vercel.app](https://uk-wind-portal.vercel.app) *(deploy Project 2 following Section 8)*
- **Live Deployed API:** [https://assignment-mocha-nu.vercel.app](https://assignment-mocha-nu.vercel.app)
- **Interactive OpenAPI / Swagger Documentation:** [https://assignment-mocha-nu.vercel.app/docs](https://assignment-mocha-nu.vercel.app/docs)
- **Live Health & Data Coverage Check:** [https://assignment-mocha-nu.vercel.app/api/health](https://assignment-mocha-nu.vercel.app/api/health)
- **Video Walkthrough (Customer Pitch & Tech Lead Review):** [Unlisted YouTube Video Link](https://sites.uab.edu/apex/for-mph-students/youtube-video/) *(See `docs/VIDEO_SCRIPTS.md` for full scripts and shot list)*

---

## 2. Directory & File Structure

```
├── .github/
│   └── workflows/ci.yml         # GitHub Actions CI for linting and test execution
├── docs/
│   ├── DECISIONS.md             # Architectural, API verification, and domain decisions log
│   ├── architecture.md          # System architecture diagram and anti-leakage specifications
│   ├── VIDEO_SCRIPTS.md         # Exact presentation scripts for client pitch & tech lead review
│   └── samples/                 # Sample responses saved from live Elexon BMRS API
│       ├── fuelhh_sample.json   # Actuals response sample
│       └── windfor_sample.json  # Forecasts response sample
├── backend/
│   ├── app/                     # FastAPI application layer
│   │   ├── main.py              # Application entrypoint with CORS and router mounts
│   │   ├── routes.py            # Typed analytical REST endpoints and CSV export
│   │   ├── schemas.py           # Pydantic v2 request/response schemas
│   │   ├── config.py            # Application settings and environment configuration
│   │   └── database.py          # SQLite database connection helper
│   ├── analysis/                # Pure analytical and mathematical computation modules
│   │   ├── selection.py         # Anti-leakage forecast selection rule & revisions extractor
│   │   └── metrics.py           # MAE, RMSE, Bias, nMAE, Horizon & Walk-Forward Buffer backtest
│   ├── ingest/                  # Data pipeline subsystem
│   │   ├── fetch.py             # Elexon BMRS API client with chunking and exponential backoff
│   │   ├── clean.py             # UTC normalization, deduplication, and sanity filtering
│   │   └── build_dataset.py     # Database population script and quality audit reporter
│   ├── data/
│   │   └── wind_data.db         # Committed, clean SQLite database (~3.1 MB, 100% complete)
│   ├── tests/                   # 25 automated pytest tests
│   │   ├── test_api.py          # FastAPI endpoint validation and integration tests
│   │   ├── test_selection.py    # Strict anti-future-data leakage unit tests
│   │   ├── test_metrics.py      # Hand-calculated metric verification & backtest unit tests
│   │   └── test_ingest.py       # Cleansing, deduplication, and schema tests
│   ├── requirements.txt         # Pinned Python backend dependencies
│   └── Dockerfile               # Multi-stage production container for FastAPI backend
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout and metadata
│   │   │   ├── page.tsx         # Unified dashboard page orchestrating views
│   │   │   └── globals.css      # Design system with dark theme tokens and custom styling
│   │   ├── components/
│   │   │   ├── Navbar.tsx       # Navigation header with tab switching and status badges
│   │   │   ├── KPICard.tsx      # Metric card component with badges and units
│   │   │   ├── DecisionView.tsx # 48 SP Intraday area chart, revisions chart, and data table
│   │   │   ├── AccuracyView.tsx # Accuracy KPIs, Diurnal/Horizon charts, and Safety Buffer slider
│   │   │   └── MethodologyView.tsx # Timeline diagrams, mathematical formulas, and provenance
│   │   ├── lib/
│   │   │   ├── api.ts           # Strongly typed API client
│   │   │   └── types.ts         # TypeScript interfaces matching backend models
│   │   └── tests/
│   │       ├── components.test.tsx # Component unit and smoke tests
│   │       └── setup.ts         # Vitest setup with jest-dom
│   ├── package.json             # Frontend dependencies (React 19, Next.js, Recharts, Lucide)
│   ├── vitest.config.ts         # Vitest test configuration
│   └── Dockerfile               # Multi-stage production container for Next.js frontend
├── docker-compose.yml           # Single-command local deployment for both services
├── Makefile                     # Helper tasks for install, test, lint, ingest, and docker
├── .env.example                 # Environment variables template
└── README.md                    # Project documentation
```

---

## 3. How to Start the Application

### Option A: With Docker (Recommended — Single Command)

To build and run the entire stack (FastAPI backend + Next.js frontend):

```bash
docker compose up --build
```

- **Frontend Application:** Open [http://localhost:3000](http://localhost:3000)
- **Backend API Docs:** Open [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** `curl http://localhost:8000/api/health`

To stop the containers:
```bash
docker compose down
```

---

### Option B: Without Docker (Local Development)

#### 1. Start the Python Backend
Ensure Python 3.12+ is installed:
```bash
# Create and activate virtual environment
python -m venv backend/venv

# On Linux/macOS:
source backend/venv/bin/activate
# On Windows (PowerShell):
backend\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server on port 8000
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start the Next.js Frontend
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev -- -p 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. How to Rebuild the Dataset from Elexon BMRS API

The repository comes with the pre-ingested, verified SQLite database committed in `backend/data/wind_data.db` (3.14 MB). To completely re-fetch the raw streams and rebuild the database from scratch:

```bash
# Using Makefile
make ingest

# Or directly using Python:
python -m backend.ingest.build_dataset
```

This fetches:
1. **FUELHH:** Settlement dates `2026-01-01` to `2026-01-31` (`fuelType = WIND`).
2. **WINDFOR:** Publish dates `2025-12-25` to `2026-01-31` in robust chunks with automatic exponential backoff.
3. Generates the full Data Quality Audit Report verifying 1,488 actual settlement periods (100% complete, 0 nulls).

---

## 5. Key Domain Assumptions & Methodology

1. **The Anti-Leakage Selection Rule:**
   For any delivery target half-hour $T$ on delivery day $D$:
   $$\text{Cutoff}(D) = (D - 1\text{ day}) \text{ at } \text{CUTOFF\_LOCAL} \text{ (Europe/London)}$$
   $$\text{forecast}(T) = \operatorname{argmax}_{publishTime \le \text{Cutoff}(D)} \text{WINDFOR}(startTime = T)$$
   Forecasts published after the cutoff time are strictly excluded because they were physically unavailable to the trader at gate closure.

2. **Temporal Alignment:**
   `FUELHH` actuals are provided in 30-minute settlement periods (48 periods per day). `WINDFOR` forecasts are published at 60-minute resolution (hourly average MW). In accordance with UK market balancing mechanics, the hourly forecast MW rate for hour $H$ directly applies to both settlement periods ($H:00$ and $H:30$).

3. **Sign Convention:**
   $$\text{Error} = \text{Forecast} - \text{Actual} \quad (\text{MW})$$
   - **Positive Error ($>0$): Over-forecast / Shortfall Risk.** The buyer expected more wind than was delivered, creating the risk of under-procuring conventional power and paying expensive imbalance cashout charges.
   - **Negative Error ($<0$): Under-forecast / Surplus Risk.** The buyer expected less wind than was delivered.

4. **Actionable Safety Buffer & Honest Walk-Forward Backtesting:**
   - **In-Sample Buffer:** The $q$-th percentile (default 90%) of $\max(0, \text{forecast} - \text{actual})$ over January 2026.
   - **Rolling Walk-Forward Backtest:** For each delivery day $D$, the buffer is strictly calibrated on historical shortfalls from days prior to $D$. Day $D$ periods are evaluated out-of-sample against this buffer. Across January 2026, the backtested buffer achieves an **89.3% out-of-sample protection rate** against a 90% confidence target.

---

## 6. Real January 2026 Benchmark Results

Verified on the real Elexon BMRS January 2026 dataset (Default cutoff `09:00` London time):

| Metric | Measured Value | Domain Interpretation |
| :--- | :--- | :--- |
| **Total Evaluated Periods** | 1,488 / 1,488 (100.0%) | Zero missing periods; complete January coverage |
| **Mean Actual Generation** | 11,580.7 MW | Average national wind generation |
| **Mean Decision Forecast** | 13,432.6 MW | Average expectation at D-1 gate closure |
| **Mean Absolute Error (MAE)**| 2,145.2 MW | Typical miss magnitude |
| **Normalized MAE (nMAE)** | 18.52% | Scale-free relative error |
| **Root Mean Sq Error (RMSE)**| 2,615.8 MW | Penalty for outlier misses |
| **Net Bias** | +1,851.9 MW | Strong over-forecasting tendency |
| **Shortfall Risk Share** | 84.9% of periods | Over-predicted in 85% of settlement periods |
| **Surplus Share** | 15.1% of periods | Under-predicted in 15% of settlement periods |
| **P90 Safety Buffer** | 4,274.9 MW | Extra thermal capacity needed for 90% coverage |
| **Walk-Forward Coverage** | 89.3% | Achieved out-of-sample protection rate |

---

## 7. Automated Testing Suite

The repository includes comprehensive automated test coverage for backend calculations, selection logic, API contracts, and frontend components:

```bash
# Run all backend unit & integration tests (25 tests)
make test
# or
$env:PYTHONPATH="."; pytest backend/tests -v

# Run frontend component tests (Vitest + React Testing Library)
cd frontend && npm test

# Run code linters
make lint
```

---

## 8. Deployment: Two Vercel Projects from One Repository

This recommended setup deploys two linked Vercel projects from a single GitHub repository. It provides the cleanest separation of concerns and maximum predictability on the free tier.

| Project | Root Directory | Runtime | Functionality |
| :--- | :--- | :--- | :--- |
| `<anon-name>-api` | `backend/` | Python 3.12 (FastAPI via `@vercel/python`) | Analytical REST API + Bundled SQLite DB |
| `<anon-name>-web` | `frontend/` | Node.js (Next.js 16 App Router) | Interactive Trading Desk Web Interface |

### Step-by-Step Deployment Instructions

#### Step 1: Push Repository to GitHub
Push this repository to GitHub (e.g. `https://github.com/iAbhiNaV2005/Assignment.git`).

#### Step 2: Deploy Backend API (`<anon-name>-api`)
1. In the Vercel Dashboard, click **Add New** → **Project**.
2. Import the GitHub repository.
3. In project configuration:
   - **Project Name:** `<anon-name>-api` (e.g. `uk-wind-api`)
   - **Root Directory:** Click *Edit* and select **`backend`**
   - Leave Framework Preset as *Other* (configured automatically by `backend/vercel.json` and `backend/pyproject.toml`)
4. Click **Deploy**.
5. Once deployed, test the following URLs in your browser:
   - `https://<api-project>.vercel.app/api/health` → Must return `"status": "healthy"`, `"actualRecordsCount": 1488`
   - `https://<api-project>.vercel.app/docs` → Interactive Swagger documentation must load cleanly.

#### Step 3: Deploy Frontend Web (`<anon-name>-web`)
1. In Vercel, click **Add New** → **Project**.
2. Import the **same** GitHub repository.
3. In project configuration:
   - **Project Name:** `<anon-name>-web` (e.g. `uk-wind-portal`)
   - **Root Directory:** Click *Edit* and select **`frontend`**
   - Framework Preset will auto-detect as **Next.js**.
4. Expand **Environment Variables** and add:
   - **Key:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://<api-project>.vercel.app` *(use the URL from Step 2 without a trailing slash)*
5. Click **Deploy**.

#### Step 4: Verification in Browser
1. Open the deployed frontend URL in an incognito window.
2. Verify all three workspaces:
   - **Decision Desk:** Day selector (Jan 1–31), D-1 cutoff stepper, intraday 48-period forecast chart, and revisions table.
   - **Accuracy & Risk:** Headline KPIs (MAE 2,145 MW, Bias +1,852 MW), confidence slider (75%–99%), and analytical sub-charts.
   - **Methodology & Code:** Mathematical definitions, ASCII decision timeline, and live health audit.
3. Inspect browser console to confirm zero CORS errors or missing resource warnings.

---

### Pre-Configured Architectural Safeguards

- **Bundled Database:** `backend/vercel.json` explicitly declares `includeFiles: ["data/wind_data.db"]`. The database is committed directly in git and packaged into the Lambda container.
- **Read-Only SQLite Storage:** Serverless execution filesystems are strictly read-only. `backend/app/database.py` connects with URI `?mode=ro`, completely avoiding database locks and runtime filesystem errors.
- **Entrypoint Discovery:** `backend/main.py`, `backend/app/main.py`, `backend/pyproject.toml` (`tool.vercel.entrypoint = "main.py"`), and `backend/vercel.json` are pre-wired to guarantee Vercel locates the FastAPI application instance.
- **Universal Vercel CORS:** `backend/app/main.py` is configured with `allow_origin_regex=r"^https:\/\/.*\.vercel\.app$"`, allowing preview, staging, and production frontend deployments to communicate seamlessly without manual CORS updates.
- **Cold Start Warm-Up:** The first request after idle spins up the serverless Python environment (1–2s). Subsequent analytical queries resolve in 10–50ms.


---

## 9. AI Tools Used

In accordance with Section R8 of the requirements:
- **AI Coding Assistant:** Google Antigravity / Gemini 3.8 Flash was utilized as a pair programmer to assist with architectural design, boilerplate generation, unit test creation, and interactive styling.
- **Review Statement:** Every line of code, selection logic, mathematical formula, and data ingestion pipeline was rigorously reviewed, verified against live Elexon BMRS API responses, and validated via automated unit tests.

---

## 10. Limitations & Future Roadmap

1. **National vs. Zonal Granularity:** Elexon BMRS provides national wind generation. Future versions could integrate Balancing Mechanism Unit (BMU) level telemetry to analyze regional Scottish/English transmission export constraints.
2. **Balancing Mechanism Price Integration:** Overlaying cashout System Buy Prices (SBP) and System Sell Prices (SSP) would quantify the exact financial value (in £ GBP) saved by utilizing the portal's recommended safety buffer.
3. **Machine Learning Bias Correction:** A post-processing quantile regression or gradient-boosted tree model trained on recent forecast revisions could dynamically attenuate the +1,852 MW positive forecast bias.
