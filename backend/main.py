"""Vercel entrypoint for FastAPI application."""

import os
import sys
import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

for path in [BASE_DIR, PARENT_DIR]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ImportError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [BASE_DIR]
        sys.modules["backend"] = backend_pkg

from app.main import app

application = app
handler = app

__all__ = ["app", "application", "handler"]
