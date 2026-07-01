from app.application.use_cases.build_analysis_response import (
    BuildAnalysisResponseInput,
    BuildAnalysisResponseUseCase,
)
from app.schemas.models import (
    AspectScores,
    ConfidenceLevel,
    SellerReport,
    SentimentBreakdown,
    SeverityLevel,
    TopIssue,
    TrendDirection,
)


def test_build_analysis_response_use_case_maps_contract_fields() -> None:
    use_case = BuildAnalysisResponseUseCase()
    result = use_case.execute(
        BuildAnalysisResponseInput(
            product_name="Test Product",
            overall_sentiment=0.1,
            aspect_scores=AspectScores(),
            top_issues=[
                TopIssue(
                    issue="Kargo gecikmesi",
                    frequency=5,
                    severity=SeverityLevel.MEDIUM,
                    seller_action="Aksiyon",
                    trend=TrendDirection.UNKNOWN,
                )
            ],
            buyer_summary="Kısa özet",
            seller_report=SellerReport(),
            outlier_insights=[],
            pros=[],
            cons=[],
            red_flags=[],
            review_count=10,
            confidence=ConfidenceLevel.MEDIUM,
            sentiment_breakdown=SentimentBreakdown(),
            scrape_warnings=["Yıldız bilgisi yok"],
        )
    )

    assert result.score == 55
    assert result.label.value == "medium"
    assert result.summary == "Kısa özet"
    assert result.top_issue_summaries[0].ratio == 50
    assert result.partial is True
    assert result.partial_reason == "Yıldız bilgisi yok"
