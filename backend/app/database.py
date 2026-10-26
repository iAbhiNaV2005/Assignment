"""Database connection provider."""

import os
import sqlite3

from backend.app.config import settings


def get_db_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database with row factory."""
    db_path = os.path.abspath(settings.DATABASE_PATH)
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Please run ingest pipeline first.")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
