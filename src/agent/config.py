import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Locate root directory relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = PROJECT_ROOT / "runs"
CACHE_DIR = DATA_DIR / "cache"


class EnvSettings(BaseModel):
    # LLM
    llm_provider: str = Field(default="gemini")
    llm_model: str = Field(default="gemini-2.5-flash")
    llm_api_key: str = Field(default="")

    # Discovery
    search_provider: str = Field(default="exa")
    exa_api_key: str = Field(default="")
    yutori_api_key: str = Field(default="")
    yutori_max_tasks_per_run: int = Field(default=2)
    yutori_user_location: str = Field(default="Austin, TX, US")

    # Contact
    hunter_api_key: str = Field(default="")
    hunter_max_credits_per_run: int = Field(default=6)

    # Email
    mail_provider: str = Field(default="dryrun")
    smtp_user: str = Field(default="")
    smtp_app_password: str = Field(default="")
    resend_api_key: str = Field(default="")
    safe_mode: bool = Field(default=True)
    test_recipient: str = Field(default="")
    live_send_confirm: str = Field(default="")
    max_sends_per_run: int = Field(default=1)

    # Logging
    google_sheet_id: str = Field(default="")
    google_service_account_json: str = Field(default="./secrets/service-account.json")


def load_env_settings(env_path: Path | None = None) -> EnvSettings:
    """Load settings from environment and .env file."""
    if env_path is None:
        env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv()

    return EnvSettings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").lower(),
        llm_model=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        search_provider=os.getenv("SEARCH_PROVIDER", "exa").lower(),
        exa_api_key=os.getenv("EXA_API_KEY", ""),
        yutori_api_key=os.getenv("YUTORI_API_KEY", ""),
        yutori_max_tasks_per_run=int(os.getenv("YUTORI_MAX_TASKS_PER_RUN", "2")),
        yutori_user_location=os.getenv("YUTORI_USER_LOCATION", "Austin, TX, US"),
        hunter_api_key=os.getenv("HUNTER_API_KEY", ""),
        hunter_max_credits_per_run=int(os.getenv("HUNTER_MAX_CREDITS_PER_RUN", "6")),
        mail_provider=os.getenv("MAIL_PROVIDER", "dryrun").lower(),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_app_password=os.getenv("SMTP_APP_PASSWORD", ""),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        safe_mode=os.getenv("SAFE_MODE", "true").lower() in ("true", "1", "yes"),
        test_recipient=os.getenv("TEST_RECIPIENT", ""),
        live_send_confirm=os.getenv("LIVE_SEND_CONFIRM", ""),
        max_sends_per_run=int(os.getenv("MAX_SENDS_PER_RUN", "1")),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./secrets/service-account.json"),
    )


def load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file missing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_upthrust_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "upthrust.yaml")


def load_templates_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "templates.yaml")


def get_config_placeholders() -> list[str]:
    """Scan upthrust.yaml and report human-input placeholders."""
    cfg = load_upthrust_config()
    placeholders = []
    sender = cfg.get("sender", {})
    if "<YOUR NAME>" in str(sender.get("name", "")):
        placeholders.append("sender.name is still <YOUR NAME>")
    if "<YOUR TITLE>" in str(sender.get("title", "")):
        placeholders.append("sender.title is still <YOUR TITLE>")
    if "<REQUIRED FOR LIVE SENDS>" in str(sender.get("postal_address", "")):
        placeholders.append("sender.postal_address has placeholder")
    
    proof_points = cfg.get("proof_points", [])
    verified_count = sum(1 for p in proof_points if p.get("verified") is True)
    if verified_count == 0:
        placeholders.append("No verified: true proof points in upthrust.yaml")

    return placeholders
