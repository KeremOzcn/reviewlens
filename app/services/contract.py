from __future__ import annotations

from typing import List

from app.domain.value_objects import (
    build_issue_summary,
    build_score_profile,
    build_score_profile_from_score,
)
from app.schemas.models import SummaryLabel, TopIssue, TopIssueSummary


def normalize_score(overall_sentiment: float) -> int:
    return build_score_profile(overall_sentiment).score


def summary_label(score: int) -> SummaryLabel:
    label = build_score_profile_from_score(score).label
    if label == "good":
        return SummaryLabel.GOOD
    if label == "medium":
        return SummaryLabel.MEDIUM
    return SummaryLabel.BAD


def to_issue_summaries(top_issues: List[TopIssue], review_count: int) -> List[TopIssueSummary]:
    if review_count <= 0:
        return []
    summaries: List[TopIssueSummary] = []
    for issue in top_issues[:3]:
        summary = build_issue_summary(issue.issue, issue.frequency, review_count)
        summaries.append(
            TopIssueSummary(
                title=summary.title,
                ratio=summary.ratio,
            )
        )
    return summaries
