"""Vercel entrypoint for FastAPI application."""

import os
import sys
import types

# Ensure backend root and parent workspace directory are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

for path in [BASE_DIR, PARENT_DIR]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Alias 'backend' module so imports like 'from backend.app.main import app'
# work whether executing from repo root or with root directory set to 'backend'
if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ImportError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [BASE_DIR]
        sys.modules["backend"] = backend_pkg

try:
    try:
        from backend.app.main import app
    except (ImportError, ModuleNotFoundError):
        from app.main import app
except Exception as exc:  # noqa: BLE001
    import traceback

    err_msg = str(exc)
    err_tb = traceback.format_exc().splitlines()
    curr_cwd = os.getcwd()
    curr_path = list(sys.path)

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Backend Startup Diagnostics")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def startup_error(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FastAPI initialization failed",
                "detail": err_msg,
                "traceback": err_tb,
                "cwd": curr_cwd,
                "sys_path": curr_path,
            },
        )

__all__ = ["app"]
