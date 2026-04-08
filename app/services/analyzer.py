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
from typing import Dict, List, Optional

from app.models.sentiment import ASPECTS, SentimentAnalyzer, ASPECT_KEYWORDS
from app.models.summarizer import (
    detect_red_flags,
    extract_pros_cons,
    generate_buyer_summary,
    generate_seller_report,
    generate_top_issues,
    _confidence_level,
)
from app.models.topic_extractor import TopicExtractor
from app.preprocessing.cleaner import clean_reviews_batch
from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AspectScores,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    SentimentBreakdown,
    TopIssue,
)

logger = logging.getLogger(__name__)

_NEGATIVE_THRESHOLD = float(os.getenv("NEGATIVE_THRESHOLD", "-0.1"))
_MAX_OUTLIER_DISPLAY = int(os.getenv("MAX_OUTLIER_DISPLAY", "5"))


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


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


# Use aspect keywords from sentiment module
_ASPECT_KW = ASPECT_KEYWORDS


def _aggregate_aspect_scores(
    aspect_dicts: List[Dict[str, float]],
    reviews: Optional[List[str]] = None,
) -> AspectScores:
    """
    Per-review weighted aspect score aggregation.

    Her aspect için:
    - O aspect'i mention eden reviewların skorları toplanır (ağırlık: 1.0)
    - Mention etmeyen reviewların _general skoru düşük ağırlıkla eklenir (ağırlık: 0.1)
    - Bu sayede her yorum genel skora katkıda bulunur ama aspect-specific yorumlar daha fazla etkiler
    """
    if not aspect_dicts:
        return AspectScores()

    result: Dict[str, float] = {}
    for aspect in ASPECTS:
        keywords = _ASPECT_KW.get(aspect, [])
        weighted_sum = 0.0
        total_weight = 0.0

        for d, rev in zip(aspect_dicts, reviews or [""]*len(aspect_dicts)):
            mentions = reviews and any(kw in rev.lower() for kw in keywords)
            if mentions:
                # Bu yorum bu aspect'i açıkça söylüyor → tam ağırlık
                weighted_sum += d.get(aspect, 0.0) * 1.0
                total_weight += 1.0
            else:
                # Mention etmiyor → genel sentiment ile düşük ağırlıkla katkı
                weighted_sum += d.get("_general", 0.0) * 0.1
                total_weight += 0.1

        result[aspect] = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return AspectScores(**result)


def _review_overall_sentiment(aspect_dict: Dict[str, float], review: str) -> float:
    """
    Compute overall sentiment for a single review.

    Strategy:
    - Collect scores only for aspects explicitly mentioned in the review.
    - Blend with a general sentiment score (_general key) to anchor the
      direction for generic positive/negative reviews that don't mention
      any specific aspect.

    Weights: 60% aspect-based (when available), 40% general.
    Falls back to 100% general when no aspects are mentioned.
    """
    review_lower = review.lower()
    general = aspect_dict.get("_general", 0.0)

    mentioned_scores = [
        aspect_dict[aspect]
        for aspect, keywords in _ASPECT_KW.items()
        if any(kw in review_lower for kw in keywords)
        and abs(aspect_dict.get(aspect, 0.0)) >= 0.05
    ]

    if mentioned_scores:
        aspect_avg = sum(mentioned_scores) / len(mentioned_scores)
        blended = 0.6 * aspect_avg + 0.4 * general
    else:
        # No specific aspect mentioned → rely on general sentiment
        blended = general

    return round(blended, 4)


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

    # 1. Clean
    logger.debug("Cleaning %d reviews …", len(raw_reviews))
    cleaned = clean_reviews_batch(raw_reviews)
    cleaned = [r for r in cleaned if r]          # drop empties post-clean

    if not cleaned:
        raise ValueError("All reviews were empty after cleaning.")

    # 2. Sentiment inference
    logger.debug("Running sentiment inference …")
    sentiment_analyzer = _get_sentiment_analyzer()
    aspect_dicts = sentiment_analyzer.predict(cleaned)

    # 3. Per-review overall scores — her yorumun _general BERT skoru
    overall_per_review: List[float] = [
        d.get("_general", 0.0) for d in aspect_dicts
    ]

    # 4. Aggregate aspect scores (per-review weighted)
    aggregated = _aggregate_aspect_scores(aspect_dicts, reviews=cleaned)
    overall_sentiment = round(
        sum(overall_per_review) / len(overall_per_review), 4
    )

    # 5. Topic extraction on negative reviews
    logger.debug("Clustering negative reviews …")
    negative_reviews = TopicExtractor.filter_negative(
        cleaned, overall_per_review, threshold=_NEGATIVE_THRESHOLD
    )
    extractor = _get_topic_extractor()
    clustering = extractor.extract(negative_reviews)

    # 6. Generate structured outputs
    top_issues: List[TopIssue] = generate_top_issues(clustering, max_issues=3)
    seller_report = generate_seller_report(
        top_issues=top_issues,
        aspect_scores=aggregated,
        overall_sentiment=overall_sentiment,
        review_count=len(cleaned),
        outlier_insights=clustering.outliers,
    )
    buyer_summary = generate_buyer_summary(
        overall_sentiment=overall_sentiment,
        aspect_scores=aggregated,
        top_issues=top_issues,
        review_count=len(cleaned),
        product_name=product_name,
    )
    pros, cons = extract_pros_cons(aggregated)
    red_flags = detect_red_flags(top_issues)
    outlier_insights = _build_outlier_insights(clustering.outliers)
    confidence = _confidence_level(len(cleaned))

    # Sentiment breakdown from per-review types
    sentiment_breakdown = SentimentBreakdown(
        positive=sum(1 for d in aspect_dicts if d.get("_type") == "positive"),
        negative=sum(1 for d in aspect_dicts if d.get("_type") == "negative"),
        mixed=sum(1 for d in aspect_dicts if d.get("_type") == "mixed"),
        neutral=sum(1 for d in aspect_dicts if d.get("_type") == "neutral"),
    )

    return AnalyzeResponse(
        product_name=product_name,
        overall_sentiment=overall_sentiment,
        aspect_scores=aggregated,
        top_issues=top_issues,
        buyer_summary=buyer_summary,
        seller_report=seller_report,
        outlier_insights=outlier_insights,
        pros=pros,
        cons=cons,
        red_flags=red_flags,
        review_count=len(cleaned),
        confidence=confidence,
        sentiment_breakdown=sentiment_breakdown,
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
