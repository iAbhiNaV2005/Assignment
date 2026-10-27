"""Vercel entrypoint for FastAPI application."""

import os
import sys
import types

# Ensure backend root and parent workspace directory are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Alias 'backend' module so imports like 'from backend.app.main import app'
# work whether executing from repo root or with root directory set to 'backend'
try:
    import backend  # noqa: F401
except ImportError:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [BASE_DIR]
    sys.modules["backend"] = backend_pkg

from backend.app.main import app

__all__ = ["app"]
