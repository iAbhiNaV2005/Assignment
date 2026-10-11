# Upthrust AI Outbound Prospecting & Qualification Agent

[![Tests](https://img.shields.io/badge/pytest-32%20passed-brightgreen.svg)](#6-testing)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](#prerequisites)
[![Safety](https://img.shields.io/badge/safety-safe--by--default-emerald.svg)](#safety-by-default-guarantees)
[![Architecture](https://img.shields.io/badge/pipeline-deterministic%208--stage-orange.svg)](#2-architecture--pipeline)

A production-grade, evidence-grounded AI outbound prospecting and qualification system built for **[Upthrust](https://upthrust.io)** — a B2B marketing agency that has generated **$21.45M+ in pipeline** for 31 SaaS and tech brands including Dell, QpiAI, VEGA, Acadly, and Coolstra.

---

## Table of Contents
1. [Why This Agent?](#1-why-this-agent)
2. [Architecture & Pipeline](#2-architecture--pipeline)
3. [Quickstart Setup](#3-quickstart-setup)
4. [Configuration (`.env`)](#4-configuration-env)
5. [CLI Commands Reference](#5-cli-commands-reference)
6. [Interactive Web Command Hub](#6-interactive-web-command-hub)
7. [Safety by Default Guarantees](#7-safety-by-default-guarantees)
8. [Testing & Quality Assurance](#8-testing--quality-assurance)
9. [Repository Structure](#9-repository-structure)

---

## 1. Why This Agent?

Most AI outbound lead generation bots suffer from fatal flaws:
* **Fragile autonomous loops:** They get stuck navigating JavaScript pages, burn hundreds of LLM calls, or hallucinate company stats.
* **Ungrounded personalization:** They invent fake praise (*"Loved your latest blog post!"*) or fabricate performance metrics.
* **Unsafe dispatch:** One configuration bug can send hundreds of unauthorized cold emails to real executives.

### Our Engineering Philosophy: *Reliability Beats Cleverness*
* **Zero Autonomous Web Browsing Loops:** Deterministic, SSRF-safe HTML parsing extracts verifiable evidence (Meta Pixels, Google Ads tags, GA4, schema markup, and robots.txt AI-bot directives) in milliseconds without burning LLM tokens.
* **Strict Evidence-Grounded Copy:** Jinja2 `StrictUndefined` templates render only variables cited against extracted evidence keys. Ungrounded claims or hallucinated statistics fail immediately.
* **Hard Rule Disqualifiers:** Competitor marketing agencies, directory aggregators (Clutch, Yelp, G2), and listicles are rejected in code before invoking expensive LLM or contact APIs.
* **Multi-Tier Search Discovery:** Fast neural search via **Exa AI** as primary (~2-4 seconds), with Yutori API and curated seed CSVs as zero-fail fallbacks.
* **Safe by Default:** Operates in `SAFE_MODE=true` by default, prepending a clear test banner and routing all emails exclusively to your configured test inbox.

---

## 2. Architecture & Pipeline

```
                                  ┌────────────────────────── agent discover (~2-4s) ──────────────────────────┐
  config/upthrust.yaml ───────────► build ICP queries ──► Exa Search API (Primary) ──► LLM Extract ──► validate ──► SQLite pool
                                                            │ (optional)               │ (fallback)                  │
                                                        Yutori API         data/seed_prospects.csv ──────────────────┘

                                  ┌─────────────────────────────── agent run (per prospect) ───────────────────────────────┐
  pool ──► 1 PICK ──► 2 ENRICH ──► 3 QUALIFY ──fit?──► 4 CONTACT ──► 5 COMPOSE ──► 6 GUARDRAILS ──► 7 SEND ──► 8 RECORD
            next       fetch site    hard rules +   │     Hunter       choose        deterministic     SAFE_MODE    SQLite +
           domain      + signals     LLM subscores  │     OR site      template +    checks +          → test       CSV mirror +
                       (no LLM)      → code score   │     mailto       LLM fills     LLM claim-check   inbox        Google Sheets
                                                    │     fallback     variables                       (or live)    (gspread)
                                              no ───►└─► REJECTED (logged with reasons)        BLOCKED (logged with reasons)
```

### The 8 Deterministic Stages:
1. **Pick:** Selects the next pending prospect from SQLite with atomic state locking.
2. **Enrich:** Deterministically scrapes homepage HTML and `robots.txt` using SSRF-safe IP resolution (`agent.netsafe`). Extracts 15+ verifiable technical signals.
3. **Qualify:** Evaluates candidate fit. First runs hard deterministic disqualifiers (e.g., competing agencies, directories). If eligible, computes weighted fit score (0–100) combining ICP Match, Need, Reachability, and Budget.
4. **Contact:** Discovers verified decision-makers. Checks Hunter API if configured; otherwise seamlessly falls back to site `mailto:` links and role inboxes with `verification="unverified"`.
5. **Compose:** Selects targeted Jinja2 template and prompts the LLM to populate specific variables using strict evidence key citations.
6. **Guardrails:** Pre-send deterministic audits (word count bounds, placeholder detection, banned phrase scan, single question mark rule) followed by an LLM claim verification check.
7. **Send:** Dispatches message through Gmail SMTP, Resend, or local DryRun mailer.
8. **Record:** Idempotently records outcome in SQLite, mirrors to CSV (`runs/results.csv`), and syncs to Google Sheets.

---

## 3. Quickstart Setup

### Prerequisites
* **Python 3.11+** (Python 3.12 recommended)
* **Git**

### 1. Clone & Set Up Environment

```powershell
# Clone the repository
git clone https://github.com/iAbhiNaV2005/Assignment.git
cd Assignment

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
# source .venv/bin/activate

# Install the package and dependencies in editable mode
pip install -e .
```

### 2. Configure Environment (`.env`)

Copy the example file to `.env`:
```powershell
cp .env.example .env
```

Open `.env` and fill in your keys:
```ini
# --- LLM Provider ---
LLM_PROVIDER=gemini            # gemini | anthropic | openai
LLM_MODEL=gemini-2.5-flash     # recommended model
LLM_API_KEY=your_gemini_api_key

# --- Discovery ---
SEARCH_PROVIDER=exa            # exa | yutori | seed
EXA_API_KEY=your_exa_api_key   # Fast Exa AI company search
YUTORI_API_KEY=                # Optional

# --- Contact Finding ---
HUNTER_API_KEY=                # Optional: falls back to site mailto links

# --- Email Dispatch ---
MAIL_PROVIDER=dryrun           # 'dryrun' for local preview, 'gmail' for real inbox test
SMTP_USER=you@gmail.com        # Your Gmail address (if MAIL_PROVIDER=gmail)
SMTP_APP_PASSWORD=             # Google App Password (16 letters from myaccount.google.com/apppasswords)
SAFE_MODE=true                 # True by default (never emails real prospects)
TEST_RECIPIENT=you@gmail.com   # All test emails route here!
```

---

## 4. Configuration Reference

| Environment Variable | Required? | Default | Purpose |
|---|---|---|---|
| `LLM_PROVIDER` | Yes | `gemini` | LLM backend (`gemini`, `openai`, `anthropic`) |
| `LLM_MODEL` | Yes | `gemini-2.5-flash` | Model identifier |
| `LLM_API_KEY` | Yes | - | API key for LLM calls |
| `SEARCH_PROVIDER` | No | `exa` | Primary discovery provider (`exa`, `yutori`, `seed`) |
| `EXA_API_KEY` | Recommended | - | Exa AI Search API key (takes ~2-4s) |
| `HUNTER_API_KEY` | Optional | - | Hunter.io API key (skipped cleanly if omitted) |
| `MAIL_PROVIDER` | No | `dryrun` | Dispatch engine (`dryrun`, `gmail`, `resend`) |
| `SMTP_USER` | For Gmail | - | Sender Gmail address |
| `SMTP_APP_PASSWORD`| For Gmail | - | 16-character Google App Password |
| `SAFE_MODE` | Critical | `true` | When true, redirects all emails to `TEST_RECIPIENT` |
| `TEST_RECIPIENT` | Yes | - | Your email address to receive safe test dispatches |

---

## 5. CLI Commands Reference

The CLI entrypoint is `agent`:

```powershell
# 1. Run Doctor Diagnostic Check
# Verifies database, configs, LLM, Exa, SMTP credentials, and placeholders
agent doctor

# 2. Discover Prospects
# Fast discovery via Exa AI (~2-4s), adding commercial prospects to the pool
agent discover --provider exa --n 5 --with-control

# 3. View Prospect Pool
# Lists all prospects, their pipeline state, and acquisition source
agent pool

# 4. Run Pipeline on Single Prospect
# Runs end-to-end pipeline with human approval prompt before send
agent run --domain ridge.com --approve

# 5. Run Competitor Rejection Test
# Proves immediate rule-based disqualification for marketing agencies
agent run --domain wpromote.com

# 6. Deep Audit Trail
# Inspects extracted HTML signals, subscores, contact, and email copy
agent show ridge.com

# 7. Funnel Performance Report
# Prints stage conversion metrics and total API token costs
agent report

# 8. Launch Interactive Web Dashboard
agent dashboard --port 8000
```

---

## 6. Interactive Web Command Hub

Launch the web command center with:
```powershell
agent dashboard --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access:

* **Real-Time Funnel Stats:** Live counts of Prospect Pool, Qualified Fit %, Dispatched Emails, and Disqualified Targets.
* **Two-Column Cockpit:** Filter prospects by state (`DISCOVERED`, `QUALIFIED`, `SENT`, `REJECTED`), search by company name, and view status badges.
* **Prospect Inspector:**
  * **Deterministic Signals:** Meta Pixel, Google Ads tags, GA4 status, and `robots.txt` AI crawler rules.
  * **Qualification Scores:** ICP Match, Need Signal, Reachability, and Budget Score breakdown.
  * **Email Preview:** Rendered personalized email copy, subject line, and Jinja template ID.
* **One-Click Actions:** Run diagnostics, trigger Exa discovery, and process pipeline runs directly from the browser.

---

## 7. Safety by Default Guarantees

This agent is engineered with defensive guardrails to ensure zero risk during development and demonstration:

1. **`SAFE_MODE=true` Enabled by Default:**
   * Emails are never sent to prospect inboxes during testing.
   * Every email is prepended with a clear header:
     ```text
     [TEST SEND. Intended recipient: Contact <decision_maker@company.com>]
     ```
   * All emails are routed exclusively to `TEST_RECIPIENT`.
2. **Explicit Confirmation Required for Live Sends:**
   * Live dispatch requires: `--live` flag, `SAFE_MODE=false`, `LIVE_SEND_CONFIRM=I_UNDERSTAND`, and valid contact verification.
3. **Strict Idempotency:**
   * The SQLite database enforces a unique constraint on successful sends (`WHERE status = 'sent'`). Re-running a prospect will never send a duplicate message.
4. **SSRF Network Security:**
   * `agent.netsafe` validates all target URLs, resolving hostnames and strictly blocking loopback (`127.0.0.1`), private RFC1918 ranges, and link-local addresses.
5. **Claim-Check & Placeholder Audits:**
   * Composed emails are scanned for template leakages (`{{`, `}}`, `<REQUIRED>`), banned phrases, word counts (>175 words rejected), and multiple question marks.
   * An LLM claim-check verifies that every factual statement matches extracted evidence keys.

---

## 8. Testing & Quality Assurance

The codebase includes an offline test suite of **32 tests** covering database idempotency, SSRF protection, signal extraction, Jinja templates, qualification logic, guardrails, and mock E2E pipeline runs:

```powershell
# Run the complete test suite
pytest -v
```

```text
============================= test session starts =============================
tests/test_db_idempotency.py ...                             PASSED [  9%]
tests/test_discover_providers.py ...                        PASSED [ 28%]
tests/test_enrich_signals.py ...                             PASSED [ 37%]
tests/test_guardrails.py ...                                 PASSED [ 56%]
tests/test_netsafe.py ...                                    PASSED [ 65%]
tests/test_pipeline_e2e.py ...                               PASSED [ 68%]
tests/test_qualify_golden.py ...                             PASSED [ 87%]
tests/test_templates.py ...                                  PASSED [100%]

============================= 32 passed in 1.70s ==============================
```

---

## 9. Repository Structure

```
├── config/
│   ├── templates.yaml          # Jinja2 outbound email templates & rules
│   └── upthrust.yaml           # Upthrust agency context, ICP, & verified proof points
├── data/
│   ├── fixtures/               # Recorded API fixtures (Exa, signals, mock responses)
│   └── seed_prospects.csv      # Offline seed pool & control rejection targets
├── scripts/
│   └── spike_exa.py            # Diagnostic script to verify Exa API response schema
├── src/agent/
│   ├── clients/                # API clients (Exa, Gemini/LLM, Hunter, Gmail SMTP, Sheets)
│   ├── dashboard/              # FastAPI server & interactive Command Hub UI
│   ├── steps/                  # 8 pipeline stages (discover, enrich, qualify, contact, compose, guardrails, send, record)
│   ├── budget.py               # Token & credit usage tracking
│   ├── cache.py                # Disk-based response caching & replay support
│   ├── cli.py                  # Typer CLI application (`agent`)
│   ├── config.py               # Pydantic environment settings & YAML loaders
│   ├── db.py                   # SQLite source of truth with schema migrations
│   ├── models.py               # Strongly-typed Pydantic domain models
│   ├── netsafe.py              # SSRF protection and DNS resolution security
│   └── pipeline.py             # Deterministic pipeline orchestrator
├── tests/                      # 32 offline unit and integration tests
├── .env.example                # Template configuration file
├── .gitignore                  # Git ignore rules (protects credentials & DB)
├── pyproject.toml              # Build system & package dependencies
└── README.md                   # Project documentation
```

---

## License

Built for **Upthrust** growth marketing evaluation. All rights reserved.
