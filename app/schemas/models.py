"""
Pydantic v2 request/response schemas for the ReviewLens API.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Payload for POST /analyze."""

    reviews: List[str] = Field(
        ...,
        min_length=1,
        description="List of review texts to analyse.",
        examples=[["Great battery life!", "Shipping was slow but product is good."]],
    )
    product_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional product name for contextual output.",
    )

    @field_validator("reviews")
    @classmethod
    def reviews_not_empty(cls, v: List[str]) -> List[str]:
        filtered = [r.strip() for r in v if r and r.strip()]
        if not filtered:
            raise ValueError("At least one non-empty review is required.")
        return filtered


class BatchAnalyzeRequest(BaseModel):
    """Payload for POST /analyze/batch."""

    products: List[AnalyzeRequest] = Field(
        ...,
        min_length=1,
        description="List of products, each with their reviews.",
    )


# ---------------------------------------------------------------------------
# Nested response sub-schemas
# ---------------------------------------------------------------------------


class AspectScores(BaseModel):
    """Per-aspect sentiment scores in the range [-1.0, 1.0]."""

    quality: float = Field(default=0.0, ge=-1.0, le=1.0)
    shipping: float = Field(default=0.0, ge=-1.0, le=1.0)
    price: float = Field(default=0.0, ge=-1.0, le=1.0)
    durability: float = Field(default=0.0, ge=-1.0, le=1.0)
    customer_service: float = Field(default=0.0, ge=-1.0, le=1.0)
    usability: float = Field(default=0.0, ge=-1.0, le=1.0)


class TopIssue(BaseModel):
    """A single recurring issue identified from negative reviews."""

    issue: str = Field(..., description="Short description of the issue.")
    frequency: int = Field(..., ge=0, description="Number of reviews mentioning this issue.")
    severity: SeverityLevel
    seller_action: str = Field(..., description="Actionable recommendation for the seller.")
    trend: TrendDirection = TrendDirection.UNKNOWN
    example_review: Optional[str] = Field(
        default=None,
        description="Representative review excerpt illustrating the issue.",
    )


class SellerReport(BaseModel):
    """Structured intelligence report intended for product sellers."""

    top_issues: List[TopIssue] = Field(default_factory=list)
    positive_highlights: List[str] = Field(
        default_factory=list,
        description="Top positive aspects to maintain or market.",
    )
    overall_health: str = Field(
        default="",
        description="Short executive summary of product health.",
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Prioritised action items for the seller.",
    )
    review_velocity_note: Optional[str] = Field(
        default=None,
        description="Comment on review volume and recency trends.",
    )


# ---------------------------------------------------------------------------
# Primary response schemas
# ---------------------------------------------------------------------------


class SentimentBreakdown(BaseModel):
    """Count of reviews by sentiment type."""
    positive: int = Field(default=0, ge=0)
    negative: int = Field(default=0, ge=0)
    mixed: int = Field(default=0, ge=0)
    neutral: int = Field(default=0, ge=0)


class AnalyzeResponse(BaseModel):
    """Full analysis response for POST /analyze."""

    product_name: Optional[str] = None
    overall_sentiment: float = Field(
        ..., ge=-1.0, le=1.0, description="Aggregate sentiment score."
    )
    aspect_scores: AspectScores
    top_issues: List[TopIssue] = Field(default_factory=list)
    buyer_summary: str = Field(
        ..., description="Human-readable summary for prospective buyers."
    )
    seller_report: SellerReport
    outlier_insights: List[str] = Field(
        default_factory=list,
        description="Rare or isolated issues that do not form a cluster.",
    )
    pros: List[str] = Field(default_factory=list, description="Top positive points for buyers.")
    cons: List[str] = Field(default_factory=list, description="Top negative points for buyers.")
    red_flags: List[str] = Field(
        default_factory=list,
        description="Potential deal-breakers identified in reviews.",
    )
    review_count: int = Field(..., ge=0)
    confidence: ConfidenceLevel
    sentiment_breakdown: Optional[SentimentBreakdown] = None


class BatchAnalyzeResponse(BaseModel):
    """Response for POST /analyze/batch."""

    results: List[AnalyzeResponse]
    total_products: int
    total_reviews: int


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str = "ok"
    version: str
    models_loaded: Dict[str, bool] = Field(default_factory=dict)
