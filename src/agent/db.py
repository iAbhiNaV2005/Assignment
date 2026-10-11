import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from agent.config import PROJECT_ROOT
from agent.models import (
    Candidate,
    Contact,
    EnrichmentProfile,
    Qualification,
    ComposedEmail,
    SendResult,
)

DEFAULT_DB_PATH = PROJECT_ROOT / "agent.db"


class Database:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.init_db()

    def get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                summary TEXT
            );

            CREATE TABLE IF NOT EXISTS prospects (
                domain TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                website_url TEXT NOT NULL,
                industry TEXT,
                location TEXT,
                size_estimate TEXT,
                why_relevant TEXT,
                source TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS enrichments (
                domain TEXT PRIMARY KEY,
                title TEXT,
                meta_description TEXT,
                headings_json TEXT,
                signals_json TEXT,
                emails_json TEXT,
                errors_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (domain) REFERENCES prospects(domain) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS qualifications (
                domain TEXT PRIMARY KEY,
                subscores_json TEXT,
                disqualifier TEXT,
                primary_service TEXT,
                pain_points_json TEXT,
                trigger_event_json TEXT,
                reasons_for_json TEXT,
                reasons_against_json TEXT,
                final_score REAL,
                fit INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (domain) REFERENCES prospects(domain) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contacts (
                domain TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                source TEXT NOT NULL,
                verification TEXT NOT NULL,
                confidence INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (domain) REFERENCES prospects(domain) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS emails (
                domain TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_text TEXT NOT NULL,
                variables_json TEXT,
                evidence_keys_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (domain) REFERENCES prospects(domain) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                mode TEXT NOT NULL,
                intended_to TEXT NOT NULL,
                actual_to TEXT NOT NULL,
                status TEXT NOT NULL,
                message_id TEXT,
                provider_response TEXT,
                error TEXT,
                sent_at TEXT,
                FOREIGN KEY (domain) REFERENCES prospects(domain) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_sends_success_domain 
            ON sends(domain) WHERE status = 'sent';

            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                provider TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                cost_units REAL NOT NULL DEFAULT 0.0,
                cache_hit INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suppression (
                value TEXT PRIMARY KEY,
                reason TEXT,
                added_at TEXT NOT NULL
            );
            """)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # --- Suppression ---
    def is_suppressed(self, value: str) -> bool:
        norm = value.strip().lower()
        with self.get_conn() as conn:
            row = conn.execute("SELECT 1 FROM suppression WHERE lower(value) = ?", (norm,)).fetchone()
            return row is not None

    def add_suppression(self, value: str, reason: str = "manual") -> None:
        norm = value.strip().lower()
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO suppression (value, reason, added_at) VALUES (?, ?, ?)",
                (norm, reason, self._now()),
            )

    # --- Prospects & State Machine ---
    def upsert_candidate(self, candidate: Candidate) -> bool:
        """Insert candidate if not already existing. Returns True if inserted."""
        norm_domain = candidate.domain.strip().lower()
        now = self._now()
        with self.get_conn() as conn:
            existing = conn.execute("SELECT domain FROM prospects WHERE domain = ?", (norm_domain,)).fetchone()
            if existing:
                return False
            conn.execute(
                """
                INSERT INTO prospects (
                    domain, company_name, website_url, industry, location,
                    size_estimate, why_relevant, source, state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    candidate.company_name,
                    str(candidate.website_url),
                    candidate.industry,
                    candidate.location,
                    candidate.size_estimate,
                    candidate.why_relevant,
                    candidate.source,
                    "DISCOVERED",
                    now,
                    now,
                ),
            )
            return True

    def update_state(self, domain: str, state: str) -> None:
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE prospects SET state = ?, updated_at = ? WHERE domain = ?",
                (state, self._now(), domain.strip().lower()),
            )

    def get_prospect(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM prospects WHERE domain = ?", (domain.strip().lower(),)).fetchone()
            return dict(row) if row else None

    def list_prospects(self, state: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM prospects"
        params: list[Any] = []
        if state:
            query += " WHERE state = ?"
            params.append(state)
        query += " ORDER BY created_at ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with self.get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def _ensure_prospect_exists(self, conn: sqlite3.Connection, norm_domain: str) -> None:
        now = self._now()
        conn.execute(
            """
            INSERT OR IGNORE INTO prospects (
                domain, company_name, website_url, source, state, created_at, updated_at
            ) VALUES (?, ?, ?, 'direct', 'DISCOVERED', ?, ?)
            """,
            (norm_domain, norm_domain, f"https://{norm_domain}", now, now),
        )

    # --- Enrichment ---
    def save_enrichment(self, enrichment: EnrichmentProfile) -> None:
        norm_domain = enrichment.domain.strip().lower()
        now = self._now()
        with self.get_conn() as conn:
            self._ensure_prospect_exists(conn, norm_domain)
            conn.execute(
                """
                INSERT OR REPLACE INTO enrichments (
                    domain, title, meta_description, headings_json, signals_json,
                    emails_json, errors_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    enrichment.title,
                    enrichment.meta_description,
                    json.dumps(enrichment.headings),
                    json.dumps([s.model_dump() for s in enrichment.signals]),
                    json.dumps(enrichment.emails_found),
                    json.dumps(enrichment.errors),
                    now,
                ),
            )

    def get_enrichment(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM enrichments WHERE domain = ?", (domain.strip().lower(),)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["headings"] = json.loads(res["headings_json"])
            res["signals"] = json.loads(res["signals_json"])
            res["emails_found"] = json.loads(res["emails_json"])
            res["errors"] = json.loads(res["errors_json"])
            return res

    # --- Qualification ---
    def save_qualification(self, domain: str, qual: Qualification) -> None:
        norm_domain = domain.strip().lower()
        now = self._now()
        with self.get_conn() as conn:
            self._ensure_prospect_exists(conn, norm_domain)
            conn.execute(
                """
                INSERT OR REPLACE INTO qualifications (
                    domain, subscores_json, disqualifier, primary_service,
                    pain_points_json, trigger_event_json, reasons_for_json,
                    reasons_against_json, final_score, fit, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    json.dumps(qual.subscores),
                    qual.disqualifier,
                    qual.primary_service,
                    json.dumps([p.model_dump() for p in qual.pain_points]),
                    json.dumps(qual.trigger_event.model_dump() if qual.trigger_event else None),
                    json.dumps(qual.reasons_for),
                    json.dumps(qual.reasons_against),
                    qual.final_score,
                    1 if qual.fit else 0,
                    now,
                ),
            )

    def get_qualification(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM qualifications WHERE domain = ?", (domain.strip().lower(),)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["subscores"] = json.loads(res["subscores_json"])
            res["pain_points"] = json.loads(res["pain_points_json"])
            res["trigger_event"] = json.loads(res["trigger_event_json"]) if res["trigger_event_json"] else None
            res["reasons_for"] = json.loads(res["reasons_for_json"])
            res["reasons_against"] = json.loads(res["reasons_against_json"])
            res["fit"] = bool(res["fit"])
            return res

    # --- Contact ---
    def save_contact(self, domain: str, contact: Contact) -> None:
        norm_domain = domain.strip().lower()
        now = self._now()
        with self.get_conn() as conn:
            self._ensure_prospect_exists(conn, norm_domain)
            conn.execute(
                """
                INSERT OR REPLACE INTO contacts (
                    domain, email, first_name, last_name, position,
                    source, verification, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    contact.email,
                    contact.first_name,
                    contact.last_name,
                    contact.position,
                    contact.source,
                    contact.verification,
                    contact.confidence,
                    now,
                ),
            )

    def get_contact(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM contacts WHERE domain = ?", (domain.strip().lower(),)).fetchone()
            return dict(row) if row else None

    # --- Email ---
    def save_email(self, domain: str, email: ComposedEmail) -> None:
        norm_domain = domain.strip().lower()
        now = self._now()
        with self.get_conn() as conn:
            self._ensure_prospect_exists(conn, norm_domain)
            conn.execute(
                """
                INSERT OR REPLACE INTO emails (
                    domain, template_id, subject, body_text,
                    variables_json, evidence_keys_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    email.template_id,
                    email.subject,
                    email.body_text,
                    json.dumps(email.variables),
                    json.dumps(email.evidence_keys_used),
                    now,
                ),
            )

    def get_email(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM emails WHERE domain = ?", (domain.strip().lower(),)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["variables"] = json.loads(res["variables_json"])
            res["evidence_keys_used"] = json.loads(res["evidence_keys_json"])
            return res

    # --- Sends & Idempotency ---
    def has_successful_send(self, domain: str) -> bool:
        norm_domain = domain.strip().lower()
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM sends WHERE domain = ? AND status = 'sent'",
                (norm_domain,),
            ).fetchone()
            return row is not None

    def record_send(self, domain: str, send_result: SendResult) -> None:
        norm_domain = domain.strip().lower()
        sent_at_str = send_result.sent_at.isoformat() if send_result.sent_at else self._now()
        with self.get_conn() as conn:
            self._ensure_prospect_exists(conn, norm_domain)
            conn.execute(
                """
                INSERT INTO sends (
                    domain, mode, intended_to, actual_to, status,
                    message_id, provider_response, error, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    norm_domain,
                    send_result.mode,
                    send_result.intended_to,
                    send_result.actual_to,
                    send_result.status,
                    send_result.message_id,
                    send_result.provider_response,
                    send_result.error,
                    sent_at_str,
                ),
            )

    def get_send(self, domain: str) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sends WHERE domain = ? ORDER BY id DESC LIMIT 1",
                (domain.strip().lower(),),
            ).fetchone()
            return dict(row) if row else None

    # --- API Calls tracking ---
    def record_api_call(self, provider: str, endpoint: str, cost_units: float = 0.0, cache_hit: bool = False, run_id: str | None = None) -> None:
        with self.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO api_calls (run_id, provider, endpoint, cost_units, cache_hit, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, provider, endpoint, cost_units, 1 if cache_hit else 0, self._now()),
            )

    def get_run_stats(self, run_id: str | None = None) -> dict[str, Any]:
        with self.get_conn() as conn:
            total_prospects = conn.execute("SELECT count(*) as count FROM prospects").fetchone()["count"]
            by_state = dict(conn.execute("SELECT state, count(*) as count FROM prospects GROUP BY state").fetchall())
            total_sent = conn.execute("SELECT count(*) as count FROM sends WHERE status = 'sent'").fetchone()["count"]
            costs = dict(conn.execute("SELECT provider, sum(cost_units) as total FROM api_calls GROUP BY provider").fetchall())
            return {
                "total_prospects": total_prospects,
                "by_state": by_state,
                "total_sent": total_sent,
                "costs": costs,
            }
