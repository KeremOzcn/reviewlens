"""
Insight generator — produces human-readable summaries for both buyers and sellers.

Does NOT call an external LLM. Instead it applies deterministic template-based
generation backed by the structured data produced by the sentiment and clustering
models. This keeps latency low and makes the output fully reproducible.

Buyer summary includes:
    - Overall sentiment label with score
    - Top 3 pros / cons
    - Red flags (high-severity issues)
    - Confidence statement

Seller report includes:
    - Top 3 recurring issues ranked by frequency × severity
    - Actionable fix suggestions per issue
    - Trend detection flag (placeholder — populated by analyzer)
    - Positive highlights to maintain / market
    - Executive health summary
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.domain.analysis_rules import confidence_level, sentiment_label_tr
from app.models.topic_extractor import Cluster, ClusteringResult
from app.schemas.models import (
    AspectScores,
    ConfidenceLevel,
    SellerReport,
    SeverityLevel,
    TopIssue,
    TrendDirection,
)


# ---------------------------------------------------------------------------
# Severity weight mapping  (used for ranking)
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT: Dict[str, float] = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Seller action templates keyed on leading TF-IDF keyword
_SELLER_ACTION_MAP: Dict[str, str] = {
    "battery": "Consider upgrading battery capacity or optimising power-management firmware.",
    "shipping": "Partner with additional carriers and communicate tracking updates proactively.",
    "price": "Review pricing strategy; consider bundles or loyalty discounts to improve perceived value.",
    "quality": "Increase QC sampling rate and review supplier tolerances.",
    "durability": "Stress-test materials under extended-use conditions; improve packaging to reduce transit damage.",
    "customer service": "Invest in first-response time targets and self-service knowledge-base articles.",
    "size": "Clarify sizing information on product pages; consider adding a size guide.",
    "instruction": "Rewrite assembly / usage instructions with clearer diagrams.",
    "smell": "Investigate material sourcing; allow off-gassing time before shipment.",
    "noise": "Audit mechanical tolerances; add vibration-dampening materials.",
    "default": "Investigate root cause of reported issue and implement a corrective action plan.",
}


def _seller_action_for(keywords: List[str]) -> str:
    """Return an actionable recommendation based on cluster keywords."""
    for kw in keywords:
        for key, action in _SELLER_ACTION_MAP.items():
            if key in kw.lower():
                return action
    return _SELLER_ACTION_MAP["default"]


def _sentiment_label(score: float) -> str:
    """Convert a [-1, 1] score to a human-readable Turkish label."""
    return sentiment_label_tr(score)


def _confidence_level(review_count: int) -> ConfidenceLevel:
    """Determine confidence level based on review volume."""
    level = confidence_level(review_count)
    if level == "high":
        return ConfidenceLevel.HIGH
    if level == "medium":
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# Pros / cons extraction from aspect scores
# ---------------------------------------------------------------------------


def extract_pros_cons(
    aspect_scores: AspectScores,
    top_n: int = 3,
) -> tuple[List[str], List[str]]:
    """
    Derive buyer-facing pros and cons from aspect sentiment scores.

    Args:
        aspect_scores: Aspect-level sentiment scores.
        top_n: Maximum number of pros / cons to return each.

    Returns:
        Tuple of (pros, cons) as lists of readable strings.
    """
    _ASPECT_LABELS: Dict[str, str] = {
        "quality": "Kalite",
        "shipping": "Kargo & Teslimat",
        "price": "Fiyat / Değer",
        "durability": "Dayanıklılık",
        "customer_service": "Müşteri Hizmetleri",
        "usability": "Kullanım Kolaylığı",
    }

    scores = aspect_scores.model_dump()
    sorted_aspects = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Soft threshold: show aspects with meaningful signal; always show at least 1
    pros = [
        f"{_ASPECT_LABELS.get(a, a)}: {score:+.2f}"
        for a, score in sorted_aspects
        if score > 0.03
    ][:top_n]

    cons = [
        f"{_ASPECT_LABELS.get(a, a)}: {score:+.2f}"
        for a, score in sorted_aspects
        if score < -0.03
    ][:top_n]

    # Fallback: always show the best and worst aspect even if all scores are near 0
    if not pros and sorted_aspects:
        a, score = sorted_aspects[0]
        pros = [f"{_ASPECT_LABELS.get(a, a)}: {score:+.2f}"]

    if not cons and sorted_aspects:
        a, score = sorted_aspects[-1]
        cons = [f"{_ASPECT_LABELS.get(a, a)}: {score:+.2f}"]

    return pros, cons


# ---------------------------------------------------------------------------
# Buyer summary
# ---------------------------------------------------------------------------


def generate_buyer_summary(
    overall_sentiment: float,
    aspect_scores: AspectScores,
    top_issues: List[TopIssue],
    review_count: int,
    product_name: Optional[str] = None,
) -> str:
    """
    Generate a concise, reader-friendly product summary for buyers.

    Args:
        overall_sentiment: Aggregate score in [-1, 1].
        aspect_scores: Per-aspect sentiment scores.
        top_issues: Ranked list of recurring issues.
        review_count: Total number of reviews analysed.
        product_name: Optional product name for personalisation.

    Returns:
        Multi-sentence summary string.
    """
    _ASPECT_TR = {
        "quality": "kalite", "shipping": "kargo", "price": "fiyat",
        "durability": "dayanıklılık", "customer_service": "müşteri hizmetleri",
        "usability": "kullanım kolaylığı",
    }

    label = _sentiment_label(overall_sentiment)
    product = product_name or "Bu ürün"
    confidence = _confidence_level(review_count)

    # Opening sentence
    parts = [
        f"{product} için {review_count} yorum analiz edildi. "
        f"Genel değerlendirme: {label} (skor: {overall_sentiment:+.2f})."
    ]

    # Aspect highlights
    scores = aspect_scores.model_dump()
    best_aspect = max(scores, key=scores.get)
    worst_aspect = min(scores, key=scores.get)

    if scores[best_aspect] > 0.15:
        parts.append(
            f"Kullanıcılar en çok {_ASPECT_TR.get(best_aspect, best_aspect)} konusunda memnun "
            f"({scores[best_aspect]:+.2f})."
        )
    if scores[worst_aspect] < -0.15:
        parts.append(
            f"En önemli şikayet konusu {_ASPECT_TR.get(worst_aspect, worst_aspect)} "
            f"({scores[worst_aspect]:+.2f})."
        )

    # Top recurring issue
    if top_issues:
        top = top_issues[0]
        parts.append(
            f"En sık tekrarlanan sorun: \"{top.issue}\" "
            f"({top.frequency} yorumda geçiyor)."
        )

    # Confidence caveat
    if confidence == ConfidenceLevel.LOW:
        parts.append(
            "Not: Az sayıda yorum nedeniyle güven düzeyi düşük — "
            "sonuçları temkinli değerlendirin."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Seller report
# ---------------------------------------------------------------------------


def generate_top_issues(
    clustering_result: ClusteringResult,
    max_issues: int = 3,
) -> List[TopIssue]:
    """
    Convert HDBSCAN clusters to ranked TopIssue objects for the seller report.

    Ranking: frequency × severity_weight, descending.

    Args:
        clustering_result: Output of TopicExtractor.extract().
        max_issues: Maximum number of top issues to return.

    Returns:
        List of TopIssue instances.
    """
    ranked: List[TopIssue] = []

    for cluster in clustering_result.clusters:
        severity = SeverityLevel(cluster.severity)
        weight = _SEVERITY_WEIGHT[cluster.severity]
        score = cluster.frequency * weight

        issue = TopIssue(
            issue=cluster.theme,
            frequency=cluster.frequency,
            severity=severity,
            seller_action=_seller_action_for(cluster.keywords),
            trend=TrendDirection.UNKNOWN,
            example_review=cluster.representative_review or None,
        )
        ranked.append((score, issue))  # type: ignore[arg-type]

    ranked.sort(key=lambda x: x[0], reverse=True)  # type: ignore[arg-type, return-value]
    return [item[1] for item in ranked[:max_issues]]  # type: ignore[index]


def generate_seller_report(
    top_issues: List[TopIssue],
    aspect_scores: AspectScores,
    overall_sentiment: float,
    review_count: int,
    outlier_insights: List[str],
) -> SellerReport:
    """
    Build a full SellerReport from pre-computed artefacts.

    Args:
        top_issues: Ranked list of recurring issues.
        aspect_scores: Per-aspect sentiment for positive highlights.
        overall_sentiment: Aggregate score in [-1, 1].
        review_count: Total reviews analysed.
        outlier_insights: One-liner outlier review snippets.

    Returns:
        Populated SellerReport instance.
    """
    # Positive highlights: aspects with score > 0.2
    scores = aspect_scores.model_dump()
    positive_highlights = [
        f"Strong {k.replace('_', ' ')} score ({v:+.2f}) — highlight this in marketing."
        for k, v in scores.items()
        if v > 0.2
    ]

    # Recommended actions: seller_action fields from top issues
    recommended_actions = [issue.seller_action for issue in top_issues]
    if outlier_insights:
        recommended_actions.append(
            "Monitor outlier reports for emerging patterns before they escalate."
        )

    # Review velocity note
    velocity_note: Optional[str] = None
    if review_count < 10:
        velocity_note = "Very few reviews — actively solicit customer feedback."
    elif review_count < 30:
        velocity_note = "Moderate review volume; trend data will improve with more reviews."

    # Executive health summary
    label = _sentiment_label(overall_sentiment)
    health = (
        f"Overall product health is {label} (score: {overall_sentiment:+.2f}). "
    )
    if top_issues:
        issue_names = ", ".join(f'"{i.issue}"' for i in top_issues)
        health += f"Priority areas for improvement: {issue_names}."
    else:
        health += "No significant recurring issues detected."

    return SellerReport(
        top_issues=top_issues,
        positive_highlights=positive_highlights,
        overall_health=health,
        recommended_actions=recommended_actions,
        review_velocity_note=velocity_note,
    )


# ---------------------------------------------------------------------------
# Red flags
# ---------------------------------------------------------------------------


def detect_red_flags(top_issues: List[TopIssue]) -> List[str]:
    """
    Identify deal-breaker issues for the buyer-facing summary.

    A red flag is any high-severity issue or an issue with frequency ≥ 10.

    Args:
        top_issues: Full list of issues.

    Returns:
        List of red-flag strings.
    """
    flags: List[str] = []
    for issue in top_issues:
        if issue.severity == SeverityLevel.HIGH or issue.frequency >= 10:
            flags.append(
                f"{issue.issue} (reported {issue.frequency} times, severity: {issue.severity.value})"
            )
    return flags
