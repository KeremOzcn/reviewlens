from app.domain.value_objects import (
    build_issue_summary,
    build_partial_reason,
    build_score_profile,
    build_score_profile_from_score,
)


def test_build_score_profile_variants() -> None:
    assert build_score_profile(-1.0).score == 0
    assert build_score_profile(0.0).label == "medium"
    assert build_score_profile_from_score(101).score == 100
    assert build_score_profile_from_score(-5).score == 0


def test_build_issue_summary_and_partial_reason() -> None:
    issue = build_issue_summary("Kargo gecikmesi", 7, 20)
    assert issue.title == "Kargo gecikmesi"
    assert issue.ratio == 35

    reason = build_partial_reason(["", "Yıldız yok", "Yıldız yok", "Fallback kullanıldı"])
    assert reason == "Yıldız yok | Fallback kullanıldı"
    assert build_partial_reason([]) is None
