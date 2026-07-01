from __future__ import annotations


def normalize_score(overall_sentiment: float) -> int:
    return max(0, min(100, round((overall_sentiment + 1.0) * 50)))


def score_label(score: int) -> str:
    if score >= 67:
        return "good"
    if score >= 34:
        return "medium"
    return "bad"


def sentiment_label_tr(score: float) -> str:
    if score >= 0.5:
        return "çok olumlu"
    if score >= 0.2:
        return "olumlu"
    if score >= -0.1:
        return "karışık"
    if score >= -0.4:
        return "olumsuz"
    return "çok olumsuz"


def confidence_level(review_count: int) -> str:
    if review_count >= 50:
        return "high"
    if review_count >= 15:
        return "medium"
    return "low"


def issue_ratio(frequency: int, review_count: int) -> int:
    if review_count <= 0:
        return 0
    return max(0, min(100, round((frequency / review_count) * 100)))
