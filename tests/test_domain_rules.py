from app.domain.analysis_rules import (
    confidence_level,
    issue_ratio,
    normalize_score,
    score_label,
    sentiment_label_tr,
)


def test_domain_score_rules() -> None:
    assert normalize_score(-1.0) == 0
    assert normalize_score(0.0) == 50
    assert normalize_score(1.0) == 100
    assert score_label(90) == "good"
    assert score_label(50) == "medium"
    assert score_label(20) == "bad"


def test_domain_confidence_and_sentiment_labels() -> None:
    assert confidence_level(60) == "high"
    assert confidence_level(20) == "medium"
    assert confidence_level(5) == "low"
    assert sentiment_label_tr(0.6) == "çok olumlu"
    assert sentiment_label_tr(-0.5) == "çok olumsuz"


def test_issue_ratio_bounds() -> None:
    assert issue_ratio(5, 20) == 25
    assert issue_ratio(100, 20) == 100
    assert issue_ratio(1, 0) == 0
