import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.clients.sheets import SheetsMirror
from agent.config import RUNS_DIR
from agent.db import Database


class RecordStep:
    def __init__(self, db: Database, sheets: SheetsMirror | None = None, runs_dir: Path = RUNS_DIR):
        self.db = db
        self.sheets = sheets or SheetsMirror()
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def write_jsonl_trace(self, run_id: str, step_data: dict[str, Any]) -> None:
        file_path = self.runs_dir / f"{run_id}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(step_data, default=str) + "\n")

    def record_run_outcome(
        self,
        run_id: str,
        domain: str,
        duration_s: float = 0.0,
        extra_metrics: dict[str, Any] | None = None,
    ) -> None:
        norm_domain = domain.strip().lower()
        prospect = self.db.get_prospect(norm_domain) or {}
        qual = self.db.get_qualification(norm_domain) or {}
        contact = self.db.get_contact(norm_domain) or {}
        email = self.db.get_email(norm_domain) or {}
        send = self.db.get_send(norm_domain) or {}
        now_str = datetime.now(timezone.utc).isoformat()
        metrics = extra_metrics or {}

        if qual.get("fit") is False or prospect.get("state") == "REJECTED":
            # Record in rejected tables
            row = {
                "run_id": run_id,
                "timestamp": now_str,
                "company": prospect.get("company_name", norm_domain),
                "domain": norm_domain,
                "disqualifier": qual.get("disqualifier") or "Low fit score",
                "final_score": qual.get("final_score", 0),
                "reasons_against": "; ".join(qual.get("reasons_against", [])),
            }
            self.sheets.record_rejected(row)
            self.write_jsonl_trace(run_id, {"event": "rejected", "data": row})
        else:
            # Record in Results table
            pain_points = qual.get("pain_points", [])
            pain_text = "; ".join([f"{p.get('text')} [keys: {','.join(p.get('evidence_keys', []))}]" for p in pain_points])

            row = {
                "run_id": run_id,
                "timestamp": now_str,
                "company": prospect.get("company_name", norm_domain),
                "domain": norm_domain,
                "website": prospect.get("website_url", f"https://{norm_domain}"),
                "industry": prospect.get("industry", ""),
                "location": prospect.get("location", ""),
                "fit_score": qual.get("final_score", 0),
                "fit": qual.get("fit", False),
                "primary_service": qual.get("primary_service", ""),
                "pain_points_with_evidence": pain_text,
                "contact_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                "contact_title": contact.get("position", ""),
                "contact_email": contact.get("email", ""),
                "email_verification": contact.get("verification", ""),
                "hunter_confidence": contact.get("confidence", ""),
                "template_id": email.get("template_id", ""),
                "subject": email.get("subject", ""),
                "body": email.get("body_text", ""),
                "send_mode": send.get("mode", ""),
                "intended_to": send.get("intended_to", ""),
                "actual_to": send.get("actual_to", ""),
                "send_status": send.get("status", ""),
                "message_id": send.get("message_id", ""),
                "error": send.get("error", ""),
                "yutori_task_id": metrics.get("yutori_task_id", ""),
                "yutori_cost_usd": metrics.get("yutori_cost_usd", 0.0),
                "hunter_credits": metrics.get("hunter_credits", 0.0),
                "llm_tokens": metrics.get("llm_tokens", 0),
                "duration_s": round(duration_s, 2),
            }
            self.sheets.record_result(row)
            self.write_jsonl_trace(run_id, {"event": "result", "data": row})

        # Update database state to LOGGED
        if prospect.get("state") == "SENT":
            self.db.update_state(norm_domain, "LOGGED")
