"""
Orchestrator service — ties all models together into a single analysis pipeline.

Flow
----
raw reviews
    → clean_reviews_batch()
    → SentimentAnalyzer.predict()          (aspect scores per review)
    → compute per-review overall sentiment
    → aggregate aspect scores
    → TopicExtractor.extract()             (cluster negative reviews)
    → generate_top_issues()
    → generate_seller_report()
    → generate_buyer_summary()
    → detect_red_flags()
    → build AnalyzeResponse
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Dict, List

from app.application.use_cases.build_analysis_response import (
    BuildAnalysisResponseInput,
    BuildAnalysisResponseUseCase,
)
from app.application.use_cases.extract_topics import ExtractTopicsUseCase
from app.application.use_cases.prepare_sentiment_features import PrepareSentimentFeaturesUseCase
from app.domain.analysis_rules import confidence_level
from app.models.sentiment import SentimentAnalyzer
from app.models.summarizer import (
    detect_red_flags,
    extract_pros_cons,
    generate_buyer_summary,
    generate_seller_report,
    generate_top_issues,
)
from app.models.topic_extractor import TopicExtractor
from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    ConfidenceLevel,
    SentimentBreakdown,
    TopIssue,
)

logger = logging.getLogger(__name__)

_NEGATIVE_THRESHOLD = float(os.getenv("NEGATIVE_THRESHOLD", "-0.1"))
_MAX_OUTLIER_DISPLAY = int(os.getenv("MAX_OUTLIER_DISPLAY", "5"))
_build_response_use_case = BuildAnalysisResponseUseCase()
_prepare_sentiment_use_case = PrepareSentimentFeaturesUseCase()
_extract_topics_use_case = ExtractTopicsUseCase()


def _confidence_enum(review_count: int) -> ConfidenceLevel:
    level = confidence_level(review_count)
    if level == "high":
        return ConfidenceLevel.HIGH
    if level == "medium":
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# Lazy model singletons
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_sentiment_analyzer() -> SentimentAnalyzer:
    model_name = os.getenv("SENTIMENT_MODEL_NAME", "savasy/bert-base-turkish-sentiment-cased")
    logger.info("Loading SentimentAnalyzer with model: %s …", model_name)
    return SentimentAnalyzer(model_name=model_name)


@lru_cache(maxsize=1)
def _get_topic_extractor() -> TopicExtractor:
    logger.info("Loading TopicExtractor …")
    return TopicExtractor()


def _build_outlier_insights(outliers: List[str], limit: int = _MAX_OUTLIER_DISPLAY) -> List[str]:
    """
    Turn raw outlier texts into concise one-liner insights.

    Args:
        outliers: List of raw review strings that did not cluster.
        limit: Maximum number to include in the response.

    Returns:
        List of short insight strings.
    """
    insights: List[str] = []
    for review in outliers[:limit]:
        # Truncate to first 120 characters for display
        snippet = review[:120].rstrip()
        if len(review) > 120:
            snippet += "…"
        insights.append(f"Isolated report: \"{snippet}\"")
    return insights


def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the full ReviewLens analysis pipeline on a single product's reviews.

    Args:
        request: Validated AnalyzeRequest containing reviews and product name.

    Returns:
        AnalyzeResponse with all insights populated.

    Raises:
        ValueError: If the request contains no valid reviews after cleaning.
    """
    raw_reviews = request.reviews
    product_name = request.product_name

    # 1. Sentiment stage (clean + infer + aggregate)
    logger.debug("Running sentiment stage for %d reviews …", len(raw_reviews))
    sentiment_analyzer = _get_sentiment_analyzer()
    sentiment_stage = _prepare_sentiment_use_case.execute(
        raw_reviews=raw_reviews,
        predictor=sentiment_analyzer,
    )

    # 2. Topic extraction on negative reviews
    logger.debug("Clustering negative reviews …")
    extractor = _get_topic_extractor()
    topic_stage = _extract_topics_use_case.execute(
        cleaned_reviews=sentiment_stage.cleaned_reviews,
        overall_per_review=sentiment_stage.overall_per_review,
        threshold=_NEGATIVE_THRESHOLD,
        extractor=extractor,
    )

    # 3. Generate structured outputs
    top_issues: List[TopIssue] = generate_top_issues(topic_stage.clustering, max_issues=3)
    seller_report = generate_seller_report(
        top_issues=top_issues,
        aspect_scores=sentiment_stage.aspect_scores,
        overall_sentiment=sentiment_stage.overall_sentiment,
        review_count=len(sentiment_stage.cleaned_reviews),
        outlier_insights=topic_stage.clustering.outliers,
    )
    buyer_summary = generate_buyer_summary(
        overall_sentiment=sentiment_stage.overall_sentiment,
        aspect_scores=sentiment_stage.aspect_scores,
        top_issues=top_issues,
        review_count=len(sentiment_stage.cleaned_reviews),
        product_name=product_name,
    )
    pros, cons = extract_pros_cons(sentiment_stage.aspect_scores)
    red_flags = detect_red_flags(top_issues)
    outlier_insights = _build_outlier_insights(topic_stage.clustering.outliers)
    confidence = _confidence_enum(len(sentiment_stage.cleaned_reviews))

    # Sentiment breakdown from per-review types
    sentiment_breakdown = SentimentBreakdown(
        positive=sum(1 for d in sentiment_stage.aspect_dicts if d.get("_type") == "positive"),
        negative=sum(1 for d in sentiment_stage.aspect_dicts if d.get("_type") == "negative"),
        mixed=sum(1 for d in sentiment_stage.aspect_dicts if d.get("_type") == "mixed"),
        neutral=sum(1 for d in sentiment_stage.aspect_dicts if d.get("_type") == "neutral"),
    )

    return _build_response_use_case.execute(
        BuildAnalysisResponseInput(
            product_name=product_name,
            overall_sentiment=sentiment_stage.overall_sentiment,
            aspect_scores=sentiment_stage.aspect_scores,
            top_issues=top_issues,
            buyer_summary=buyer_summary,
            seller_report=seller_report,
            outlier_insights=outlier_insights,
            pros=pros,
            cons=cons,
            red_flags=red_flags,
            review_count=len(sentiment_stage.cleaned_reviews),
            confidence=confidence,
            sentiment_breakdown=sentiment_breakdown,
            scrape_warnings=request.scrape_warnings,
        )
    )


def analyze_batch(batch_request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    """
    Run the analysis pipeline for multiple products sequentially.

    Args:
        batch_request: Contains a list of AnalyzeRequest objects.

    Returns:
        BatchAnalyzeResponse with per-product results and aggregate counts.
    """
    results: List[AnalyzeResponse] = []
    total_reviews = 0

    for product_request in batch_request.products:
        try:
            result = analyze(product_request)
            results.append(result)
            total_reviews += result.review_count
        except Exception as exc:
            logger.error(
                "Failed to analyze product '%s': %s",
                product_request.product_name,
                exc,
                exc_info=True,
            )
            # Continue processing remaining products; failed ones are skipped.

    return BatchAnalyzeResponse(
        results=results,
        total_products=len(results),
        total_reviews=total_reviews,
    )


# ---------------------------------------------------------------------------
# Model health check
# ---------------------------------------------------------------------------


def models_loaded_status() -> Dict[str, bool]:
    """
    Return a dict indicating whether each model singleton is initialised.

    Used by GET /health to report readiness without triggering a load.
    """
    return {
        "sentiment_analyzer": _get_sentiment_analyzer.cache_info().currsize > 0,
        "topic_extractor": _get_topic_extractor.cache_info().currsize > 0,
    }
