"""Database connection provider with robust serverless read-only support."""

import os
import sqlite3

try:
    from backend.app.config import settings
except (ImportError, ModuleNotFoundError):
    from app.config import settings  # type: ignore


def get_db_path() -> str:
    """Resolve database path across local development and Vercel serverless environments."""
    candidates = [
        os.getenv("DATABASE_PATH"),
        settings.DATABASE_PATH,
        os.path.join(os.path.dirname(__file__), "..", "data", "wind_data.db"),
        os.path.join(os.getcwd(), "data", "wind_data.db"),
        os.path.join(os.getcwd(), "backend", "data", "wind_data.db"),
        "/var/task/data/wind_data.db",
        "/var/task/backend/data/wind_data.db",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return os.path.abspath(path)

    # Fallback to default configured path
    return os.path.abspath(settings.DATABASE_PATH)


def get_db_connection() -> sqlite3.Connection:
    """
    Create a read-only connection to the SQLite database with row factory.
    Uses URI mode=ro to prevent writes and lock contention in read-only serverless storage.
    """
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Verify includeFiles in vercel.json.")

    norm_path = db_path.replace("\\", "/")
    # Format URI according to platform (file:///C:/... on Windows, file:/var/... on Linux)
    if len(norm_path) > 1 and norm_path[1] == ":":
        uri = f"file:///{norm_path}?mode=ro"
    else:
        uri = f"file:{norm_path}?mode=ro"

    try:
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    except sqlite3.OperationalError:
        # Fallback if URI mode is unsupported in edge environments
        conn = sqlite3.connect(db_path, check_same_thread=False)

    conn.row_factory = sqlite3.Row
    return conn

