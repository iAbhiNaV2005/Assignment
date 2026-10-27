"""Backend configuration settings."""

import os


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
    @property
    def CORS_ORIGINS(self) -> list[str]:
        origins = [
            "http://localhost:3000",
            "https://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        env_origins = os.getenv("CORS_ORIGINS", "")
        if env_origins:
            origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])
        frontend_url = os.getenv("FRONTEND_URL", "")
        if frontend_url and frontend_url not in origins:
            origins.append(frontend_url.strip())
        return list(dict.fromkeys(origins))


settings = Settings()
