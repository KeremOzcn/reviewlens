from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from app.models.topic_extractor import ClusteringResult, TopicExtractor


@dataclass(frozen=True)
class TopicStageOutput:
    negative_reviews: List[str]
    clustering: ClusteringResult


class ExtractTopicsUseCase:
    def __init__(
        self,
        negative_filter: Callable[[List[str], List[float], float], List[str]] = TopicExtractor.filter_negative,
    ) -> None:
        self._negative_filter = negative_filter

    def execute(
        self,
        cleaned_reviews: List[str],
        overall_per_review: List[float],
        threshold: float,
        extractor: TopicExtractor,
    ) -> TopicStageOutput:
        negative_reviews = self._negative_filter(cleaned_reviews, overall_per_review, threshold)
        clustering = extractor.extract(negative_reviews)
        return TopicStageOutput(negative_reviews=negative_reviews, clustering=clustering)
