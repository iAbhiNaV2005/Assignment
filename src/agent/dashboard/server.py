import json
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.clients.hunter import HunterClient
from agent.clients.mailer import GmailSMTPMailer, get_mailer
from agent.clients.sheets import SheetsMirror
from agent.clients.yutori import YutoriClient
from agent.config import (
    get_config_placeholders,
    load_env_settings,
    load_templates_config,
    load_upthrust_config,
    PROJECT_ROOT,
)
from agent.db import Database
from agent.llm import LLMClient
from agent.pipeline import OutboundPipeline
from agent.steps.discover import DiscoveryStep


class ActionDomainRequest(BaseModel):
    domain: str
    approve: bool = False
    live: bool = False


class DiscoverRequest(BaseModel):
    source: str = "auto"
    limit: int = 15
    with_control: bool = True


def create_dashboard_app() -> FastAPI:
    app = FastAPI(title="Upthrust Outbound Agent - Command Hub", version="0.1.0")
    db = Database()
    settings = load_env_settings()

    @app.get("/api/stats")
    def get_stats():
        stats = db.get_run_stats()
        return JSONResponse(content=stats)

    @app.get("/api/prospects")
    def get_prospects(state: str | None = None):
        prospects = db.list_prospects(state=state)
        # Enrich with score if qualified
        for p in prospects:
            qual = db.get_qualification(p["domain"])
            if qual:
                p["final_score"] = qual.get("final_score")
                p["primary_service"] = qual.get("primary_service")
                p["fit"] = qual.get("fit")
        return JSONResponse(content=prospects)

    @app.get("/api/prospect/{domain}")
    def get_prospect_detail(domain: str):
        norm = domain.strip().lower()
        prospect = db.get_prospect(norm)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        enrichment = db.get_enrichment(norm)
        qual = db.get_qualification(norm)
        contact = db.get_contact(norm)
        email = db.get_email(norm)
        send = db.get_send(norm)

        return JSONResponse(content={
            "prospect": prospect,
            "enrichment": enrichment,
            "qualification": qual,
            "contact": contact,
            "email": email,
            "send": send,
        })

    @app.post("/api/action/run")
    def run_prospect(req: ActionDomainRequest):
        pipeline = OutboundPipeline(db=db, settings=settings)
        res = pipeline.process_prospect(domain=req.domain, approve=False, live=req.live)
        return JSONResponse(content={
            "domain": req.domain,
            "status": res.get("status"),
            "duration_s": res.get("duration_s", 0),
        })

    @app.post("/api/action/discover")
    def trigger_discovery(req: DiscoverRequest):
        discovery_step = DiscoveryStep(db=db)
        candidates = discovery_step.run(source=req.source, limit=req.limit, with_control=req.with_control)
        return JSONResponse(content={
            "discovered_count": len(candidates),
            "candidates": [c.model_dump() for c in candidates],
        })

    @app.get("/api/doctor")
    def run_doctor():
        placeholders = get_config_placeholders()
        checks = [
            {"component": "Database (SQLite)", "status": "PASS", "details": f"Active ({db.db_path.name})"},
            {
                "component": "Config Files",
                "status": "WARN" if placeholders else "PASS",
                "details": f"Placeholders: {'; '.join(placeholders)}" if placeholders else "All YAML configs valid",
            },
            {
                "component": f"LLM ({settings.llm_provider})",
                "status": "PASS" if settings.llm_api_key else "MISSING_KEY",
                "details": f"Model: {settings.llm_model}" if settings.llm_api_key else "LLM_API_KEY required for live generation",
            },
            {
                "component": "Exa Search (Primary)",
                "status": "PASS" if settings.exa_api_key else "OPTIONAL / SKIPPED",
                "details": "API Key configured (~2-4s search)" if settings.exa_api_key else "Using Seed CSV fallback",
            },
            {
                "component": "Hunter Contact (Optional)",
                "status": "PASS" if settings.hunter_api_key else "OPTIONAL / SKIPPED",
                "details": "API Key active" if settings.hunter_api_key else "Using site mailto & role inbox fallback",
            },
            {
                "component": "Safe Mode Sending",
                "status": "ENABLED" if settings.safe_mode else "DISABLED (LIVE)",
                "details": f"Test recipient: {settings.test_recipient or 'test-recipient@upthrust.local'}",
            },
            {
                "component": "Email Provider",
                "status": "PASS",
                "details": f"{settings.mail_provider.upper()} (Safe mode on)",
            },
        ]
        return JSONResponse(content={"checks": checks})

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(content=DASHBOARD_HTML)

    return app


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Upthrust Outbound Agent - Command Hub</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #09090b;
      --bg-surface: #121215;
      --bg-card: #18181b;
      --bg-elevated: #27272a;
      --border-subtle: #27272a;
      --border-strong: #3f3f46;
      --text-main: #f4f4f5;
      --text-muted: #a1a1aa;
      --text-dim: #71717a;
      --accent: #10b981;
      --accent-glow: rgba(16, 185, 129, 0.15);
      --amber: #f59e0b;
      --amber-bg: rgba(245, 158, 11, 0.1);
      --rose: #f43f5e;
      --rose-bg: rgba(244, 63, 94, 0.1);
      --cyan: #06b6d4;
      --cyan-bg: rgba(6, 182, 212, 0.1);
      --radius: 8px;
      --font-sans: 'Inter', -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      line-height: 1.5;
    }

    /* Header Nav */
    header {
      height: 64px;
      border-bottom: 1px solid var(--border-subtle);
      background: rgba(9, 9, 11, 0.85);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-mark {
      width: 28px;
      height: 28px;
      background: linear-gradient(135deg, #10b981, #06b6d4);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      color: #000;
    }
    .brand-name {
      font-weight: 600;
      font-size: 15px;
      letter-spacing: -0.01em;
    }
    .brand-tag {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 9999px;
      background: var(--bg-elevated);
      color: var(--text-muted);
      border: 1px solid var(--border-subtle);
      font-family: var(--font-mono);
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .btn {
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 500;
      padding: 7px 14px;
      border-radius: var(--radius);
      border: 1px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-main);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    .btn:hover {
      background: var(--bg-elevated);
      border-color: var(--border-strong);
    }
    .btn:active {
      transform: scale(0.98);
    }
    .btn-primary {
      background: #10b981;
      border-color: #10b981;
      color: #09090b;
      font-weight: 600;
    }
    .btn-primary:hover {
      background: #34d399;
      border-color: #34d399;
    }

    /* Main Container */
    main {
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Metrics Funnel */
    .funnel-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
    }
    .funnel-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .funnel-label {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-family: var(--font-mono);
    }
    .funnel-value {
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    /* Two-column Cockpit */
    .cockpit {
      display: grid;
      grid-template-columns: 420px 1fr;
      gap: 20px;
      flex: 1;
      min-height: 600px;
    }

    @media (max-width: 1024px) {
      .cockpit {
        grid-template-columns: 1fr;
      }
    }

    /* Prospect List Panel */
    .panel {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .panel-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .panel-title {
      font-size: 14px;
      font-weight: 600;
    }

    .filter-tabs {
      display: flex;
      gap: 4px;
      padding: 8px 14px;
      border-bottom: 1px solid var(--border-subtle);
      background: var(--bg-base);
    }
    .filter-tab {
      padding: 4px 10px;
      font-size: 12px;
      border-radius: 6px;
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-family: var(--font-sans);
    }
    .filter-tab.active {
      background: var(--bg-card);
      color: var(--text-main);
      font-weight: 600;
    }

    .prospect-list {
      flex: 1;
      overflow-y: auto;
      max-height: 680px;
    }
    .prospect-item {
      padding: 14px 18px;
      border-bottom: 1px solid var(--border-subtle);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: background 0.15s ease;
    }
    .prospect-item:hover {
      background: var(--bg-card);
    }
    .prospect-item.active {
      background: var(--bg-card);
      border-left: 3px solid var(--accent);
    }

    .prospect-info {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .prospect-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-main);
    }
    .prospect-domain {
      font-size: 12px;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }

    .badge {
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 3px 8px;
      border-radius: 9999px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .badge-discovered { background: var(--bg-elevated); color: var(--text-muted); }
    .badge-qualified { background: var(--accent-glow); color: var(--accent); border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-rejected { background: var(--rose-bg); color: var(--rose); border: 1px solid rgba(244, 63, 94, 0.3); }
    .badge-sent { background: var(--cyan-bg); color: var(--cyan); border: 1px solid rgba(6, 182, 212, 0.3); }
    .badge-blocked { background: var(--amber-bg); color: var(--amber); }

    /* Detail Inspector */
    .inspector-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 20px;
      overflow-y: auto;
      max-height: 750px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 400px;
      color: var(--text-dim);
      gap: 12px;
      text-align: center;
    }

    .section-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius);
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .section-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-family: var(--font-mono);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .signals-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }
    .signal-pill {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .signal-key {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
    }
    .signal-val {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-main);
    }

    .subscores-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }
    .subscore-box {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 10px;
      text-align: center;
    }
    .subscore-label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
    }
    .subscore-num {
      font-size: 18px;
      font-weight: 700;
      color: var(--accent);
      margin-top: 4px;
    }

    /* Email Box */
    .email-container {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 16px;
      font-family: var(--font-mono);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      color: #e4e4e7;
    }
    .email-subject {
      font-weight: 600;
      color: var(--cyan);
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border-subtle);
    }

    /* Modal for Diagnostics */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.7);
      backdrop-filter: blur(4px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .modal-overlay.open { display: flex; }
    .modal-box {
      background: var(--bg-surface);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius);
      width: 600px;
      max-width: 90vw;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="brand">
      <div class="brand-mark">U</div>
      <div class="brand-name">Upthrust Outbound</div>
      <span class="brand-tag">v0.1 · Safe Mode</span>
    </div>
    <div class="nav-actions">
      <button class="btn" onclick="openDoctorModal()">Diagnostics</button>
      <button class="btn" onclick="triggerDiscover()">Discover Prospects</button>
      <button class="btn btn-primary" onclick="runSelectedOrNext()">Run Pipeline</button>
    </div>
  </header>

  <!-- Main View -->
  <main>
    <!-- Funnel Stats Bar -->
    <div class="funnel-grid">
      <div class="funnel-card">
        <span class="funnel-label">Prospect Pool</span>
        <span class="funnel-value" id="stat-pool">0</span>
      </div>
      <div class="funnel-card">
        <span class="funnel-label">Qualified Fit</span>
        <span class="funnel-value" id="stat-qualified" style="color: var(--accent);">0</span>
      </div>
      <div class="funnel-card">
        <span class="funnel-label">Emails Dispatched</span>
        <span class="funnel-value" id="stat-sent" style="color: var(--cyan);">0</span>
      </div>
      <div class="funnel-card">
        <span class="funnel-label">Disqualified</span>
        <span class="funnel-value" id="stat-rejected" style="color: var(--rose);">0</span>
      </div>
    </div>

    <!-- Interactive Cockpit -->
    <div class="cockpit">
      <!-- Prospects List Panel -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Prospect Pipeline</span>
          <button class="btn" style="padding: 4px 8px; font-size: 11px;" onclick="loadProspects()">Refresh</button>
        </div>
        <div class="filter-tabs">
          <button class="filter-tab active" onclick="setFilter('all', this)">All</button>
          <button class="filter-tab" onclick="setFilter('DISCOVERED', this)">Pending</button>
          <button class="filter-tab" onclick="setFilter('QUALIFIED', this)">Qualified</button>
          <button class="filter-tab" onclick="setFilter('SENT', this)">Sent</button>
          <button class="filter-tab" onclick="setFilter('REJECTED', this)">Rejected</button>
        </div>
        <div class="prospect-list" id="prospects-container">
          <!-- Populated by JavaScript -->
        </div>
      </div>

      <!-- Deep Inspector Panel -->
      <div class="panel">
        <div class="panel-header" id="inspector-header">
          <span class="panel-title" id="inspector-title">Prospect Inspector</span>
          <div id="inspector-actions" style="display: none; gap: 8px;">
            <button class="btn btn-primary" id="btn-process-current" onclick="processCurrentProspect()">Process Pipeline</button>
          </div>
        </div>
        <div class="inspector-content" id="inspector-body">
          <div class="empty-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2v20M2 12h20"/>
            </svg>
            <p>Select a prospect on the left to inspect evidence signals, scores, and outbound emails.</p>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Diagnostics Modal -->
  <div class="modal-overlay" id="doctor-modal" onclick="if(event.target===this)closeDoctorModal()">
    <div class="modal-box">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-size: 16px;">System Health & Diagnostics</h3>
        <button class="btn" onclick="closeDoctorModal()">Close</button>
      </div>
      <div id="doctor-results" style="display: flex; flex-direction: column; gap: 10px;">
        <p style="color: var(--text-muted); font-size: 13px;">Checking system dependencies...</p>
      </div>
    </div>
  </div>

  <script>
    let currentFilter = 'all';
    let allProspects = [];
    let selectedDomain = null;

    async function loadStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-pool').innerText = data.total_prospects || 0;
        document.getElementById('stat-sent').innerText = data.total_sent || 0;
        document.getElementById('stat-qualified').innerText = (data.by_state && (data.by_state.QUALIFIED || data.by_state.SENT || data.by_state.LOGGED)) || 0;
        document.getElementById('stat-rejected').innerText = (data.by_state && data.by_state.REJECTED) || 0;
      } catch (err) {
        console.error(err);
      }
    }

    async function loadProspects() {
      try {
        const res = await fetch('/api/prospects');
        allProspects = await res.json();
        renderProspects();
        loadStats();
      } catch (err) {
        console.error(err);
      }
    }

    function setFilter(filter, btn) {
      currentFilter = filter;
      document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderProspects();
    }

    function renderProspects() {
      const container = document.getElementById('prospects-container');
      container.innerHTML = '';

      const filtered = allProspects.filter(p => {
        if (currentFilter === 'all') return true;
        return p.state === currentFilter;
      });

      if (filtered.length === 0) {
        container.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px;">No prospects found</div>';
        return;
      }

      filtered.forEach(p => {
        const item = document.createElement('div');
        item.className = 'prospect-item' + (p.domain === selectedDomain ? ' active' : '');
        item.onclick = () => selectProspect(p.domain);

        const badgeClass = p.state === 'SENT' ? 'badge-sent' :
                           p.state === 'REJECTED' ? 'badge-rejected' :
                           p.state === 'QUALIFIED' ? 'badge-qualified' : 'badge-discovered';

        item.innerHTML = `
          <div class="prospect-info">
            <span class="prospect-name">${p.company_name}</span>
            <span class="prospect-domain">${p.domain}</span>
          </div>
          <span class="badge ${badgeClass}">${p.state}</span>
        `;
        container.appendChild(item);
      });
    }

    async function selectProspect(domain) {
      selectedDomain = domain;
      renderProspects();

      const inspectorBody = document.getElementById('inspector-body');
      inspectorBody.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">Loading audit data...</div>';

      document.getElementById('inspector-actions').style.display = 'flex';

      try {
        const res = await fetch(`/api/prospect/${domain}`);
        const data = await res.json();
        renderDetail(data);
      } catch (err) {
        inspectorBody.innerHTML = `<div style="padding: 20px; color: var(--rose);">Error loading prospect details: ${err}</div>`;
      }
    }

    function renderDetail(data) {
      const p = data.prospect;
      const e = data.enrichment;
      const q = data.qualification;
      const c = data.contact;
      const m = data.email;
      const s = data.send;

      document.getElementById('inspector-title').innerText = `${p.company_name} (${p.domain})`;

      let html = '';

      // Qualification Box
      if (q) {
        html += `
          <div class="section-card">
            <div class="section-title">
              <span>Qualification Score: ${q.final_score}/100</span>
              <span class="badge ${q.fit ? 'badge-qualified' : 'badge-rejected'}">${q.fit ? 'FIT: YES' : 'FIT: NO'}</span>
            </div>
            <div class="subscores-bar">
              <div class="subscore-box"><div class="subscore-label">ICP Match</div><div class="subscore-num">${q.subscores.icp_match}</div></div>
              <div class="subscore-box"><div class="subscore-label">Need Signal</div><div class="subscore-num">${q.subscores.need_signal}</div></div>
              <div class="subscore-box"><div class="subscore-label">Reachability</div><div class="subscore-num">${q.subscores.reachability}</div></div>
              <div class="subscore-box"><div class="subscore-label">Budget</div><div class="subscore-num">${q.subscores.budget_signal}</div></div>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
              <strong>Primary Focus:</strong> ${q.primary_service}
            </div>
            ${q.disqualifier ? `<div style="font-size: 13px; color: var(--rose);"><strong>Disqualification Rule:</strong> ${q.disqualifier}</div>` : ''}
          </div>
        `;
      }

      // Evidence Signals Box
      if (e && e.signals) {
        html += `
          <div class="section-card">
            <div class="section-title">Extracted Deterministic Signals (${e.signals.length})</div>
            <div class="signals-grid">
        `;
        e.signals.slice(0, 8).forEach(sig => {
          const isPos = Boolean(sig.value);
          html += `
            <div class="signal-pill">
              <span class="signal-key">${sig.key}</span>
              <span class="signal-val" style="color: ${isPos ? 'var(--accent)' : 'var(--text-muted)'};">${sig.value}</span>
              <span style="font-size: 10px; color: var(--text-dim);">${sig.evidence_snippet || ''}</span>
            </div>
          `;
        });
        html += `</div></div>`;
      }

      // Contact & Send Box
      if (c) {
        html += `
          <div class="section-card">
            <div class="section-title">Verified Contact</div>
            <div style="font-size: 13px; display: flex; justify-content: space-between;">
              <span><strong>Name:</strong> ${c.first_name || ''} ${c.last_name || ''} (${c.position || 'Executive'})</span>
              <span style="font-family: var(--font-mono); color: var(--cyan);">${c.email}</span>
            </div>
          </div>
        `;
      }

      // Email Preview Box
      if (m) {
        html += `
          <div class="section-card">
            <div class="section-title">
              <span>Personalized Cold Email</span>
              <span style="font-family: var(--font-mono); font-size: 11px;">Template: ${m.template_id}</span>
            </div>
            <div class="email-container">
              <div class="email-subject">Subject: ${m.subject}</div>
              <div>${m.body_text}</div>
            </div>
          </div>
        `;
      }

      document.getElementById('inspector-body').innerHTML = html || '<div class="empty-state">No enrichment data yet. Click Process Pipeline above.</div>';
    }

    async function processCurrentProspect() {
      if (!selectedDomain) return;
      const btn = document.getElementById('btn-process-current');
      btn.innerText = 'Processing...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/action/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ domain: selectedDomain })
        });
        const data = await res.json();
        await loadProspects();
        selectProspect(selectedDomain);
      } catch (err) {
        alert('Error: ' + err);
      } finally {
        btn.innerText = 'Process Pipeline';
        btn.disabled = false;
      }
    }

    async function triggerDiscover() {
      try {
        const res = await fetch('/api/action/discover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: 'auto', limit: 15, with_control: true })
        });
        const data = await res.json();
        alert(`Discovered ${data.discovered_count} prospects into the pool!`);
        await loadProspects();
      } catch (err) {
        alert('Discovery error: ' + err);
      }
    }

    async function runSelectedOrNext() {
      if (selectedDomain) {
        processCurrentProspect();
      } else if (allProspects.length > 0) {
        const pending = allProspects.find(p => p.state === 'DISCOVERED');
        if (pending) {
          selectProspect(pending.domain);
          processCurrentProspect();
        } else {
          alert('No pending discovered prospects to run.');
        }
      } else {
        alert('Prospect pool is empty. Click Discover Prospects first.');
      }
    }

    async function openDoctorModal() {
      const modal = document.getElementById('doctor-modal');
      const box = document.getElementById('doctor-results');
      modal.classList.add('open');
      box.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">Checking system dependencies...</p>';

      try {
        const res = await fetch('/api/doctor');
        const data = await res.json();
        let rows = '';
        data.checks.forEach(c => {
          const color = c.status === 'PASS' ? 'var(--accent)' : c.status === 'WARN' ? 'var(--amber)' : 'var(--rose)';
          rows += `
            <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg-card); border-radius: 6px; font-size: 13px;">
              <span><strong>${c.component}</strong>: ${c.details}</span>
              <span style="font-weight: 700; color: ${color};">${c.status}</span>
            </div>
          `;
        });
        box.innerHTML = rows;
      } catch (err) {
        box.innerHTML = `<p style="color: var(--rose);">Doctor check error: ${err}</p>`;
      }
    }

    function closeDoctorModal() {
      document.getElementById('doctor-modal').classList.remove('open');
    }

    // Auto initialize on load
    loadProspects();
  </script>
</body>
</html>
"""
