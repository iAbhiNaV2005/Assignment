"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.config import settings
from backend.app.routes import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Analytical API for UK Day-Ahead Wind Generation Forecast Selection and Quantitative Accuracy Evaluation.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for Next.js frontend, local development, and all Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", include_in_schema=False)
def direct_health():
    """Alias for /api/health to ensure health checks pass under any base path."""
    from backend.app.routes import get_health

    return get_health()


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to OpenAPI docs."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
