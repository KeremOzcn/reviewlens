from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol

from app.models.sentiment import ASPECTS, ASPECT_KEYWORDS
from app.preprocessing.cleaner import clean_reviews_batch
from app.schemas.models import AspectScores


class SentimentPredictor(Protocol):
    def predict(self, reviews: List[str]) -> List[Dict[str, float]]:
        ...


@dataclass(frozen=True)
class SentimentStageOutput:
    cleaned_reviews: List[str]
    aspect_dicts: List[Dict[str, float]]
    overall_per_review: List[float]
    aspect_scores: AspectScores
    overall_sentiment: float


def _aggregate_aspect_scores(
    aspect_dicts: List[Dict[str, float]],
    reviews: List[str],
) -> AspectScores:
    if not aspect_dicts:
        return AspectScores()

    result: Dict[str, float] = {}
    for aspect in ASPECTS:
        keywords = ASPECT_KEYWORDS.get(aspect, [])
        weighted_sum = 0.0
        total_weight = 0.0

        for aspect_dict, review in zip(aspect_dicts, reviews):
            mentions = any(kw in review.lower() for kw in keywords)
            if mentions:
                weighted_sum += aspect_dict.get(aspect, 0.0) * 1.0
                total_weight += 1.0
            else:
                weighted_sum += aspect_dict.get("_general", 0.0) * 0.1
                total_weight += 0.1

        result[aspect] = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return AspectScores(**result)


class PrepareSentimentFeaturesUseCase:
    def execute(
        self,
        raw_reviews: List[str],
        predictor: SentimentPredictor,
    ) -> SentimentStageOutput:
        cleaned = [r for r in clean_reviews_batch(raw_reviews) if r]
        if not cleaned:
            raise ValueError("All reviews were empty after cleaning.")

        aspect_dicts = predictor.predict(cleaned)
        overall_per_review = [d.get("_general", 0.0) for d in aspect_dicts]
        aspect_scores = _aggregate_aspect_scores(aspect_dicts, cleaned)
        overall_sentiment = round(sum(overall_per_review) / len(overall_per_review), 4)

        return SentimentStageOutput(
            cleaned_reviews=cleaned,
            aspect_dicts=aspect_dicts,
            overall_per_review=overall_per_review,
            aspect_scores=aspect_scores,
            overall_sentiment=overall_sentiment,
        )
