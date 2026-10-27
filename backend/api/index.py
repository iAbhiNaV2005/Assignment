"""Vercel api/index.py entrypoint for FastAPI application."""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app

application = app
handler = app

__all__ = ["app", "application", "handler"]
