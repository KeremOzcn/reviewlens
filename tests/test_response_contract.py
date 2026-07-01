import pytest
from pydantic import ValidationError

from app.schemas.models import (
    AnalyzeResponse,
    AspectScores,
    ConfidenceLevel,
    SellerReport,
    SummaryLabel,
)


def build_base_response(**overrides):
    payload = dict(
        product_name="Test",
        overall_sentiment=0.2,
        score=60,
        label=SummaryLabel.MEDIUM,
        summary="Özet",
        aspect_scores=AspectScores(),
        top_issues=[],
        top_issue_summaries=[],
        buyer_summary="Alıcı özeti",
        seller_report=SellerReport(),
        outlier_insights=[],
        pros=[],
        cons=[],
        red_flags=[],
        review_count=12,
        processed_review_count=12,
        confidence=ConfidenceLevel.MEDIUM,
        partial=False,
        partial_reason=None,
    )
    payload.update(overrides)
    return AnalyzeResponse(**payload)


def test_partial_requires_reason() -> None:
    with pytest.raises(ValidationError):
        build_base_response(partial=True, partial_reason=None)


def test_partial_reason_is_cleared_when_not_partial() -> None:
    model = build_base_response(partial=False, partial_reason="will be ignored")
    assert model.partial_reason is None


def test_partial_reason_kept_when_partial_true() -> None:
    model = build_base_response(partial=True, partial_reason="Yıldız verisi yok")
    assert model.partial_reason == "Yıldız verisi yok"
