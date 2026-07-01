from app.schemas.models import SeverityLevel, TopIssue, TrendDirection
from app.services.contract import normalize_score, summary_label, to_issue_summaries


def test_normalize_score_range() -> None:
    assert normalize_score(-1.0) == 0
    assert normalize_score(0.0) == 50
    assert normalize_score(1.0) == 100


def test_summary_label_thresholds() -> None:
    assert summary_label(80).value == "good"
    assert summary_label(50).value == "medium"
    assert summary_label(10).value == "bad"


def test_to_issue_summaries_top3_and_ratio() -> None:
    issues = [
        TopIssue(
            issue="Kargo gecikmesi",
            frequency=20,
            severity=SeverityLevel.MEDIUM,
            seller_action="Action",
            trend=TrendDirection.UNKNOWN,
        ),
        TopIssue(
            issue="Kalite sorunu",
            frequency=10,
            severity=SeverityLevel.HIGH,
            seller_action="Action",
            trend=TrendDirection.UNKNOWN,
        ),
        TopIssue(
            issue="Fiyat yüksek",
            frequency=5,
            severity=SeverityLevel.LOW,
            seller_action="Action",
            trend=TrendDirection.UNKNOWN,
        ),
        TopIssue(
            issue="Dördüncü sorun",
            frequency=3,
            severity=SeverityLevel.LOW,
            seller_action="Action",
            trend=TrendDirection.UNKNOWN,
        ),
    ]

    summaries = to_issue_summaries(issues, review_count=40)

    assert len(summaries) == 3
    assert summaries[0].title == "Kargo gecikmesi"
    assert summaries[0].ratio == 50
