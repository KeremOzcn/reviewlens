from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from app.domain.analysis_rules import issue_ratio, normalize_score, score_label


@dataclass(frozen=True)
class ScoreProfile:
    score: int
    label: str


@dataclass(frozen=True)
class IssueSummary:
    title: str
    ratio: int


def build_score_profile(overall_sentiment: float) -> ScoreProfile:
    score = normalize_score(overall_sentiment)
    return build_score_profile_from_score(score)


def build_score_profile_from_score(score: int) -> ScoreProfile:
    bounded_score = max(0, min(100, score))
    return ScoreProfile(score=bounded_score, label=score_label(bounded_score))


def build_issue_summary(title: str, frequency: int, review_count: int) -> IssueSummary:
    return IssueSummary(title=title, ratio=issue_ratio(frequency, review_count))


def build_partial_reason(warnings: Iterable[str]) -> Optional[str]:
    cleaned = [w.strip() for w in warnings if w and w.strip()]
    if not cleaned:
        return None
    return " | ".join(dict.fromkeys(cleaned))
