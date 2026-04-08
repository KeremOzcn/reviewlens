"""
Issue/topic clustering for negative reviews.

Pipeline
--------
1. Encode negative review sentences with sentence-transformers.
2. Cluster embeddings using HDBSCAN (density-based, no fixed k needed).
3. Label each cluster with TF-IDF key-phrases.
4. Separate HDBSCAN outliers (label == -1) as rare/isolated insights.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"
)
_HDBSCAN_MIN_CLUSTER = int(os.getenv("HDBSCAN_MIN_CLUSTER_SIZE", "3"))
_HDBSCAN_MIN_SAMPLES = int(os.getenv("HDBSCAN_MIN_SAMPLES", "2"))
_TFIDF_MAX_FEATURES = int(os.getenv("TFIDF_MAX_FEATURES", "500"))
_TFIDF_NGRAM_MAX = int(os.getenv("TFIDF_NGRAM_MAX", "3"))
_TOP_KEYWORDS_PER_CLUSTER = int(os.getenv("TOP_KEYWORDS_PER_CLUSTER", "5"))


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class Cluster:
    """A group of similar negative reviews sharing a common theme."""

    label: int
    theme: str                         # Human-readable TF-IDF label
    reviews: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    representative_review: str = ""

    @property
    def frequency(self) -> int:
        return len(self.reviews)

    @property
    def severity(self) -> str:
        """Map cluster size to severity tier."""
        if self.frequency >= 10:
            return "high"
        if self.frequency >= 4:
            return "medium"
        return "low"


@dataclass
class ClusteringResult:
    """Output of the full topic extraction pipeline."""

    clusters: List[Cluster]
    outliers: List[str]          # Reviews that did not fit any cluster
    n_reviews_processed: int
    silhouette_score: Optional[float] = None  # Populated by evaluate.py


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class TopicExtractor:
    """
    Identifies recurring issues in a collection of (negative) review texts.

    Args:
        embedding_model_name: sentence-transformers model to use for encoding.
        min_cluster_size: HDBSCAN minimum cluster size.
        min_samples: HDBSCAN minimum samples (controls noise tolerance).
        top_keywords: Number of TF-IDF keywords to describe each cluster.
        batch_size: Batch size for sentence-transformer encoding.
    """

    def __init__(
        self,
        embedding_model_name: str = _EMBEDDING_MODEL,
        min_cluster_size: int = _HDBSCAN_MIN_CLUSTER,
        min_samples: int = _HDBSCAN_MIN_SAMPLES,
        top_keywords: int = _TOP_KEYWORDS_PER_CLUSTER,
        batch_size: int = 64,
    ) -> None:
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.top_keywords = top_keywords
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, reviews: List[str]) -> ClusteringResult:
        """
        Run the full topic-extraction pipeline.

        Args:
            reviews: List of (pre-cleaned) review strings to cluster.
                     Typically the subset of reviews with negative sentiment.

        Returns:
            ClusteringResult containing discovered clusters and outliers.
        """
        if not reviews:
            return ClusteringResult(clusters=[], outliers=[], n_reviews_processed=0)

        # Edge-case: too few reviews to form meaningful clusters
        if len(reviews) < self.min_cluster_size:
            return ClusteringResult(
                clusters=[],
                outliers=list(reviews),
                n_reviews_processed=len(reviews),
            )

        embeddings = self._encode(reviews)
        labels = self._cluster(embeddings)
        clusters, outliers = self._build_clusters(reviews, labels)
        return ClusteringResult(
            clusters=clusters,
            outliers=outliers,
            n_reviews_processed=len(reviews),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to L2-normalised dense embeddings."""
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    def _cluster(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Run HDBSCAN on the embedding matrix.

        Returns an array of integer cluster labels where -1 denotes outliers.
        """
        n = len(embeddings)
        # Adapt min_cluster_size to input size; never larger than n//2
        min_cluster_size = max(2, min(self.min_cluster_size, n // 2))
        min_samples = max(1, min(self.min_samples, min_cluster_size - 1))

        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean",
            cluster_selection_method="eom",
            allow_single_cluster=True,
        )
        clusterer.fit(embeddings)
        return clusterer.labels_

    def _build_clusters(
        self, reviews: List[str], labels: np.ndarray
    ) -> Tuple[List[Cluster], List[str]]:
        """
        Group reviews by cluster label and generate TF-IDF themes.

        Returns:
            Tuple of (list of Cluster objects sorted by frequency desc,
                      list of outlier review strings).
        """
        grouped: Dict[int, List[str]] = defaultdict(list)
        for review, label in zip(reviews, labels):
            grouped[int(label)].append(review)

        outliers = grouped.pop(-1, [])
        clusters: List[Cluster] = []

        for label, cluster_reviews in grouped.items():
            keywords = self._tfidf_keywords(cluster_reviews)
            theme = self._build_theme(keywords)
            representative = self._pick_representative(cluster_reviews)
            clusters.append(
                Cluster(
                    label=label,
                    theme=theme,
                    reviews=cluster_reviews,
                    keywords=keywords,
                    representative_review=representative,
                )
            )

        clusters.sort(key=lambda c: c.frequency, reverse=True)
        return clusters, outliers

    def _tfidf_keywords(self, texts: List[str]) -> List[str]:
        """
        Extract top TF-IDF n-gram keywords from a group of texts.

        Args:
            texts: Reviews belonging to one cluster.

        Returns:
            List of keyword strings, sorted by TF-IDF score descending.
        """
        try:
            vectorizer = TfidfVectorizer(
                max_features=_TFIDF_MAX_FEATURES,
                ngram_range=(1, _TFIDF_NGRAM_MAX),
                stop_words="english",
                min_df=1,
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = np.array(vectorizer.get_feature_names_out())
            # Sum TF-IDF scores across all documents in the cluster
            scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
            top_indices = scores.argsort()[::-1][: self.top_keywords]
            return feature_names[top_indices].tolist()
        except ValueError:
            # Happens if all texts are empty after stop-word removal
            return []

    @staticmethod
    def _build_theme(keywords: List[str]) -> str:
        """Convert a keyword list to a human-readable theme string."""
        if not keywords:
            return "Unknown issue"
        # Capitalise first keyword, join the rest with commas
        theme = keywords[0].title()
        if len(keywords) > 1:
            theme += f" ({', '.join(keywords[1:3])})"
        return theme

    @staticmethod
    def _pick_representative(reviews: List[str]) -> str:
        """
        Select the most 'average' review as the cluster representative.

        Picks the review closest in length to the median length of the cluster.
        """
        if not reviews:
            return ""
        median_len = float(np.median([len(r) for r in reviews]))
        return min(reviews, key=lambda r: abs(len(r) - median_len))

    # ------------------------------------------------------------------
    # Utility: filter negative reviews
    # ------------------------------------------------------------------

    @staticmethod
    def filter_negative(
        reviews: List[str],
        sentiment_scores: List[float],
        threshold: float = -0.1,
    ) -> List[str]:
        """
        Return only reviews whose overall sentiment is below the threshold.

        Args:
            reviews: Full list of review strings.
            sentiment_scores: Overall sentiment score for each review [-1, 1].
            threshold: Scores at or below this value are considered negative.

        Returns:
            Subset of reviews that are negative.
        """
        return [
            review
            for review, score in zip(reviews, sentiment_scores)
            if score <= threshold
        ]
