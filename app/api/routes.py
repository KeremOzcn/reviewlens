"""
FastAPI router definitions for the ReviewLens API.

Endpoints
---------
POST /analyze          — single-product review analysis
POST /analyze/batch    — multi-product batch analysis
GET  /health           — readiness / liveness probe
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    HealthResponse,
)
from app.services import analyzer as analyzer_service

logger = logging.getLogger(__name__)

_API_VERSION = os.getenv("API_VERSION", "0.1.0")

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse product reviews",
    description=(
        "Accepts a list of review texts (and an optional product name) and returns "
        "aspect-level sentiment scores, recurring issue clusters, a buyer summary, "
        "and a structured seller report."
    ),
    tags=["Analysis"],
)
async def analyze_reviews(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the full ReviewLens analysis pipeline on a single product's reviews.

    - **reviews**: Non-empty list of review strings (max 500 per request).
    - **product_name**: Optional label used in generated summaries.
    """
    if len(request.reviews) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Maximum 500 reviews per request. Use /analyze/batch for larger sets.",
        )

    try:
        result = analyzer_service.analyze(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",
        ) from exc

    return result


# ---------------------------------------------------------------------------
# POST /analyze/batch
# ---------------------------------------------------------------------------


@router.post(
    "/analyze/batch",
    response_model=BatchAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch-analyse multiple products",
    description=(
        "Accepts a list of product review sets and runs the analysis pipeline on "
        "each one sequentially. Failed products are skipped and not included in the "
        "response — check server logs for details."
    ),
    tags=["Analysis"],
)
async def analyze_batch(request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    """
    Analyse multiple products in a single request.

    - **products**: List of AnalyzeRequest objects (max 20 products).
    """
    if len(request.products) > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Maximum 20 products per batch request.",
        )

    try:
        result = analyzer_service.analyze_batch(request)
    except Exception as exc:
        logger.exception("Unexpected error during batch analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",
        ) from exc

    if not result.results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="None of the provided products could be analysed. Check that reviews are non-empty.",
        )

    return result


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns API readiness status and which ML models are loaded.",
    tags=["Operations"],
)
async def health() -> HealthResponse:
    """Liveness / readiness probe for orchestration systems (Kubernetes, etc.)."""
    return HealthResponse(
        status="ok",
        version=_API_VERSION,
        models_loaded=analyzer_service.models_loaded_status(),
    )
