"""
ReviewLens FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Environment variables (see .env.example):
    API_VERSION          — semver string shown in /health (default: 0.1.0)
    EMBEDDING_MODEL_NAME — sentence-transformers model for clustering
    NEGATIVE_THRESHOLD   — overall sentiment threshold for negative filter
    LOG_LEVEL            — logging level (default: INFO)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import router

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # load .env file if present

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_API_VERSION = os.getenv("API_VERSION", "0.1.0")

logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # type: ignore[type-arg]
    """
    Application lifespan manager.

    Starts model loading in a background thread so the server becomes
    available immediately. First request may be slightly slower if models
    haven't finished loading yet.
    """
    import threading

    logger.info("ReviewLens v%s starting up …", _API_VERSION)

    def _preload_models():
        from app.services.analyzer import _get_sentiment_analyzer, _get_topic_extractor
        try:
            _get_sentiment_analyzer()
            _get_topic_extractor()
            logger.info("All models loaded. Server is ready.")
        except Exception as e:
            logger.error("Error preloading models: %s", e)

    threading.Thread(target=_preload_models, daemon=True).start()
    yield
    logger.info("ReviewLens shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ReviewLens",
    description=(
        "AI-powered product review intelligence API. "
        "Uses Turkish BERT (Transformer) for aspect-level sentiment analysis, "
        "sentence-transformers + HDBSCAN for issue clustering, "
        "and generates actionable insights for both buyers and sellers."
    ),
    version=_API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow all origins in development; restrict in production via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under /api/v1 prefix
app.include_router(router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to interactive API docs."""
    return RedirectResponse(url="/docs")
