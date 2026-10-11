import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import gspread
from google.oauth2.service_account import Credentials

from agent.config import EnvSettings, RUNS_DIR, load_env_settings

RESULTS_COLUMNS = [
    "run_id", "timestamp", "company", "domain", "website", "industry", "location",
    "fit_score", "fit", "primary_service", "pain_points_with_evidence",
    "contact_name", "contact_title", "contact_email", "email_verification",
    "hunter_confidence", "template_id", "subject", "body", "send_mode",
    "intended_to", "actual_to", "send_status", "message_id", "error",
    "yutori_task_id", "yutori_cost_usd", "hunter_credits", "llm_tokens", "duration_s",
]

REJECTED_COLUMNS = [
    "run_id", "timestamp", "company", "domain", "disqualifier", "final_score", "reasons_against",
]


class SheetsMirror:
    def __init__(self, settings: EnvSettings | None = None, runs_dir: Path = RUNS_DIR):
        self.settings = settings or load_env_settings()
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.results_csv = self.runs_dir / "results.csv"
        self.rejected_csv = self.runs_dir / "rejected.csv"
        self._init_csvs()

    def _init_csvs(self) -> None:
        if not self.results_csv.exists():
            with open(self.results_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(RESULTS_COLUMNS)
        if not self.rejected_csv.exists():
            with open(self.rejected_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(REJECTED_COLUMNS)

    def _get_gspread_client(self) -> gspread.Client | None:
        creds_path = Path(self.settings.google_service_account_json)
        if not creds_path.exists():
            return None
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        try:
            creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
            return gspread.authorize(creds)
        except Exception:
            return None

    def check_connection(self) -> bool:
        """Test reading the sheet for doctor check."""
        if not self.settings.google_sheet_id:
            raise ValueError("GOOGLE_SHEET_ID missing")
        client = self._get_gspread_client()
        if not client:
            raise ValueError(f"Service account file not found or invalid: {self.settings.google_service_account_json}")
        sheet = client.open_by_key(self.settings.google_sheet_id)
        # Attempt to access worksheet
        sheet.sheet1.title
        return True

    def record_result(self, row_data: dict[str, Any]) -> None:
        """Write to CSV and attempt to write to Google Sheet."""
        row_values = [str(row_data.get(col, "")) for col in RESULTS_COLUMNS]

        # 1. Always append to CSV
        with open(self.results_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row_values)

        # 2. Mirror to Google Sheet if configured
        if self.settings.google_sheet_id:
            try:
                client = self._get_gspread_client()
                if client:
                    sheet = client.open_by_key(self.settings.google_sheet_id)
                    try:
                        ws = sheet.worksheet("Results")
                    except gspread.WorksheetNotFound:
                        ws = sheet.add_worksheet(title="Results", rows=1000, cols=len(RESULTS_COLUMNS))
                        ws.append_row(RESULTS_COLUMNS)
                    ws.append_row(row_values)
            except Exception as e:
                # Log warning, CSV has captured it
                pass

    def record_rejected(self, row_data: dict[str, Any]) -> None:
        row_values = [str(row_data.get(col, "")) for col in REJECTED_COLUMNS]

        # 1. Always append to CSV
        with open(self.rejected_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row_values)

        # 2. Mirror to Google Sheet if configured
        if self.settings.google_sheet_id:
            try:
                client = self._get_gspread_client()
                if client:
                    sheet = client.open_by_key(self.settings.google_sheet_id)
                    try:
                        ws = sheet.worksheet("Rejected")
                    except gspread.WorksheetNotFound:
                        ws = sheet.add_worksheet(title="Rejected", rows=1000, cols=len(REJECTED_COLUMNS))
                        ws.append_row(REJECTED_COLUMNS)
                    ws.append_row(row_values)
            except Exception as e:
                pass
