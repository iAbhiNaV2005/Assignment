"""Backend configuration settings."""

import os
from typing import ClassVar


class Settings:
    PROJECT_NAME: str = "UK Wind Forecast Decision & Accuracy Portal API"
    VERSION: str = "1.0.0"
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH",
        os.path.join(os.path.dirname(__file__), "..", "data", "wind_data.db"),
    )
    DEFAULT_CUTOFF: str = "09:00"
    MIN_DATE: str = "2026-01-01"
    MAX_DATE: str = "2026-01-31"
    CORS_ORIGINS: ClassVar[list[str]] = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "*",  # permissive for demo/evaluator review
    ]


settings = Settings()
