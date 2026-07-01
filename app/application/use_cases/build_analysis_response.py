from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.domain.value_objects import build_partial_reason
from app.schemas.models import (
    AnalyzeResponse,
    AspectScores,
    ConfidenceLevel,
    SellerReport,
    SentimentBreakdown,
    TopIssue,
)
from app.services.contract import normalize_score, summary_label, to_issue_summaries


@dataclass(frozen=True)
class BuildAnalysisResponseInput:
    product_name: Optional[str]
    overall_sentiment: float
    aspect_scores: AspectScores
    top_issues: List[TopIssue]
    buyer_summary: str
    seller_report: SellerReport
    outlier_insights: List[str]
    pros: List[str]
    cons: List[str]
    red_flags: List[str]
    review_count: int
    confidence: ConfidenceLevel
    sentiment_breakdown: SentimentBreakdown
    scrape_warnings: List[str]


class BuildAnalysisResponseUseCase:
    def execute(self, data: BuildAnalysisResponseInput) -> AnalyzeResponse:
        score = normalize_score(data.overall_sentiment)
        label = summary_label(score)
        partial_reason = build_partial_reason(data.scrape_warnings)

        return AnalyzeResponse(
            product_name=data.product_name,
            overall_sentiment=data.overall_sentiment,
            score=score,
            label=label,
            summary=data.buyer_summary,
            aspect_scores=data.aspect_scores,
            top_issues=data.top_issues,
            top_issue_summaries=to_issue_summaries(data.top_issues, data.review_count),
            buyer_summary=data.buyer_summary,
            seller_report=data.seller_report,
            outlier_insights=data.outlier_insights,
            pros=data.pros,
            cons=data.cons,
            red_flags=data.red_flags,
            review_count=data.review_count,
            processed_review_count=data.review_count,
            confidence=data.confidence,
            sentiment_breakdown=data.sentiment_breakdown,
            partial=bool(partial_reason),
            partial_reason=partial_reason,
        )
