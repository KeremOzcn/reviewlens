"""
Integration tests for the full analysis pipeline: application use-case ->
infrastructure adapter -> analyzer service -> domain rules -> response
contract. Only the ML model boundary (BERT sentiment model, sentence
embeddings + HDBSCAN clustering) is replaced with deterministic fakes,
since those require multi-gigabyte model downloads. Everything else
(cleaning, use-case orchestration, contract building, domain rules) runs
for real.
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from app.application.use_cases.analyze_reviews import AnalyzeReviewsUseCase
from app.infrastructure.analyzers.review_analyzer_adapter import ReviewAnalyzerAdapter
from app.models.topic_extractor import Cluster, ClusteringResult
from app.schemas.models import AnalyzeRequest, AnalyzeResponse, BatchAnalyzeRequest
from app.services import analyzer as analyzer_service

ASPECTS = ["quality", "shipping", "price", "durability", "customer_service", "usability"]

POSITIVE_REVIEWS = [
    "Kargo çok hızlıydı, ürün harika!",
    "Mükemmel bir ürün, çok güzel.",
    "Fiyatına göre gayet iyi, tavsiye ederim.",
]

MIXED_REVIEWS = POSITIVE_REVIEWS + [
    "Ürün kırık geldi, berbat bir deneyimdi.",
    "Kutusu kırık geldi, hiç memnun kalmadım.",
]


class _FakeSentimentAnalyzer:
    """Deterministic stand-in for the real Turkish BERT sentiment model."""

    def predict(self, reviews):
        results = []
        for review in reviews:
            lower = review.lower()
            if any(w in lower for w in ("harika", "mükemmel", "hızlı", "güzel", "iyi")):
                general, sentiment_type = 0.8, "positive"
            elif any(w in lower for w in ("berbat", "kırık", "kötü", "yavaş")):
                general, sentiment_type = -0.8, "negative"
            else:
                general, sentiment_type = 0.0, "neutral"

            scores = {
                "_general": general,
                "_type": sentiment_type,
                "_pos": 1 if general > 0.1 else 0,
                "_neg": 1 if general < -0.1 else 0,
            }
            for aspect in ASPECTS:
                scores[aspect] = general
            results.append(scores)
        return results


class _FakeTopicExtractor:
    """Deterministic stand-in for sentence-transformers + HDBSCAN clustering."""

    def extract(self, reviews):
        if not reviews:
            return ClusteringResult(clusters=[], outliers=[], n_reviews_processed=0)
        cluster = Cluster(
            label=0,
            theme="Kırık Ürün",
            reviews=list(reviews),
            keywords=["kırık"],
            representative_review=reviews[0],
        )
        return ClusteringResult(clusters=[cluster], outliers=[], n_reviews_processed=len(reviews))


@pytest.fixture()
def wired_use_case(monkeypatch):
    """Wire the real application/domain/infrastructure stack with fake ML models."""

    @lru_cache(maxsize=1)
    def _fake_get_sentiment_analyzer():
        return _FakeSentimentAnalyzer()

    @lru_cache(maxsize=1)
    def _fake_get_topic_extractor():
        return _FakeTopicExtractor()

    monkeypatch.setattr(analyzer_service, "_get_sentiment_analyzer", _fake_get_sentiment_analyzer)
    monkeypatch.setattr(analyzer_service, "_get_topic_extractor", _fake_get_topic_extractor)

    return AnalyzeReviewsUseCase(ReviewAnalyzerAdapter())


def test_analyze_reviews_end_to_end_produces_valid_contract(wired_use_case):
    request = AnalyzeRequest(reviews=MIXED_REVIEWS, product_name="Test Ürün")

    response = wired_use_case.execute(request)

    assert isinstance(response, AnalyzeResponse)
    assert 0 <= response.score <= 100
    assert response.label.value in {"good", "medium", "bad"}
    assert response.review_count == len(MIXED_REVIEWS)
    assert response.processed_review_count == response.review_count
    assert response.partial is False
    assert response.partial_reason is None

    breakdown = response.sentiment_breakdown
    assert breakdown is not None
    assert (
        breakdown.positive + breakdown.negative + breakdown.mixed + breakdown.neutral
        == response.review_count
    )
    for summary in response.top_issue_summaries:
        assert 0 <= summary.ratio <= 100


def test_analyze_reviews_marks_response_partial_when_scrape_warnings_present(wired_use_case):
    request = AnalyzeRequest(
        reviews=POSITIVE_REVIEWS,
        scrape_warnings=["Sayfa sonundaki 3 yorum yüklenemedi."],
    )

    response = wired_use_case.execute(request)

    assert response.partial is True
    assert response.partial_reason == "Sayfa sonundaki 3 yorum yüklenemedi."


def test_analyze_reviews_confidence_reflects_review_volume(wired_use_case):
    low_volume = wired_use_case.execute(AnalyzeRequest(reviews=POSITIVE_REVIEWS))
    assert low_volume.confidence.value == "low"

    medium_volume = wired_use_case.execute(AnalyzeRequest(reviews=POSITIVE_REVIEWS * 6))
    assert medium_volume.confidence.value == "medium"


def test_analyze_batch_end_to_end(wired_use_case):
    batch_request = BatchAnalyzeRequest(
        products=[
            AnalyzeRequest(reviews=POSITIVE_REVIEWS, product_name="Ürün A"),
            AnalyzeRequest(reviews=MIXED_REVIEWS, product_name="Ürün B"),
        ]
    )

    batch_response = wired_use_case.execute_batch(batch_request)

    assert batch_response.total_products == 2
    assert batch_response.total_reviews == len(POSITIVE_REVIEWS) + len(MIXED_REVIEWS)
    assert [r.product_name for r in batch_response.results] == ["Ürün A", "Ürün B"]


def test_model_status_reports_loaded_models_after_analysis(wired_use_case):
    wired_use_case.execute(AnalyzeRequest(reviews=POSITIVE_REVIEWS))

    status = wired_use_case.model_status()

    assert status == {"sentiment_analyzer": True, "topic_extractor": True}
