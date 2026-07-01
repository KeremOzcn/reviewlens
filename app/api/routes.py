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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.application.use_cases.analyze_reviews import AnalyzeReviewsUseCase
from app.auth import verify_api_key
from app.infrastructure.analyzers.review_analyzer_adapter import ReviewAnalyzerAdapter
from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    HealthResponse,
)

logger = logging.getLogger(__name__)

_API_VERSION = os.getenv("API_VERSION", "0.1.0")
_ANALYZE_RATE_LIMIT = os.getenv("ANALYZE_RATE_LIMIT", "20/minute")

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
_analyze_use_case = AnalyzeReviewsUseCase(ReviewAnalyzerAdapter())


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
@limiter.limit(_ANALYZE_RATE_LIMIT)
async def analyze_reviews(
    request: Request,
    payload: AnalyzeRequest,
    api_key: str = Depends(verify_api_key),
) -> AnalyzeResponse:
    """
    Run the full ReviewLens analysis pipeline on a single product's reviews.

    - **reviews**: Non-empty list of review strings (max 500 per request).
    - **product_name**: Optional label used in generated summaries.
    """
    try:
        result = _analyze_use_case.execute(payload)
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
@limiter.limit(_ANALYZE_RATE_LIMIT)
async def analyze_batch(
    request: Request,
    payload: BatchAnalyzeRequest,
    api_key: str = Depends(verify_api_key),
) -> BatchAnalyzeResponse:
    """
    Analyse multiple products in a single request.

    - **products**: List of AnalyzeRequest objects (max 20 products).
    """
    try:
        result = _analyze_use_case.execute_batch(payload)
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
        models_loaded=_analyze_use_case.model_status(),
    )
