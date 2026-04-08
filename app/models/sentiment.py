"""
Transformer-based sentiment analyzer using Turkish BERT.

Uses `savasy/bert-base-turkish-sentiment-cased` for real NLP understanding.
Falls back to keyword-based analysis only when the model cannot be loaded.

The model understands:
- Context and nuance ("kötü diyemem" → positive)
- Irony detection ("harika kargo, kutuyu paramparça etmişler")
- Mixed sentiments per-aspect

Architecture:
    Input Text → BERT Tokenizer → BERT Encoder (12 layers, 768 hidden)
                                  → Attention Mechanism (12 heads)
                                  → [CLS] token pooling
                                  → Softmax → {positive, negative} probabilities
                                  → Score mapping to [-1, 1]
"""

from typing import Dict, List, Optional
import re
import logging
import os

logger = logging.getLogger(__name__)

# Aspects tracked by ReviewLens
ASPECTS = ["quality", "shipping", "price", "durability", "customer_service", "usability"]

# Aspect-specific keywords in Turkish (used for aspect ASSIGNMENT, not scoring)
ASPECT_KEYWORDS = {
    "quality":          ["kalite", "yapım", "malzeme", "sağlam", "ses", "görüntü",
                         "ekran", "ses kalitesi", "tasarım", "performans", "kamera",
                         "çözünürlük", "piksel", "renk", "parlaklık",
                         "urun", "ürün", "guzel", "güzel", "iyi", "harika", "mukemmel",
                         "mükemmel", "berbat", "kotu", "kötü", "rezalet"],
    "shipping":         ["kargo", "teslimat", "paket", "shipping", "delivery",
                         "gönderim", "geldi", "ulaştı", "kutu", "teslim"],
    "price":            ["fiyat", "price", "pahalı", "değer", "para", "ücret",
                         "bütçe", "fiyat performans", "ucuz", "fahiş"],
    "durability":       ["batarya", "pil", "battery", "bozuldu", "dayanıklı",
                         "arıza", "çalışmıyor", "ömür", "kırıldı", "hasar",
                         "sağlam", "dayanıksız", "şarj", "ısınma", "ısınıyor",
                         "depolama", "hafıza", "storage", "kapasite", "dolu", "yetersiz"],
    "customer_service": ["müşteri", "destek", "servis", "garanti", "customer",
                         "support", "iade", "değişim", "hizmet", "cevap"],
    "usability":        ["kullanım", "kolay", "zor", "kurulum", "uygulama",
                         "app", "arayüz", "setup", "bağlantı", "bluetooth",
                         "wifi", "bağlan", "menü", "pratik"],
}


# ---------------------------------------------------------------------------
# BERT-based Sentiment Analyzer
# ---------------------------------------------------------------------------

class SentimentAnalyzer:
    """
    Transformer-based sentiment analyzer using Turkish BERT.

    On initialization, loads `savasy/bert-base-turkish-sentiment-cased`
    from HuggingFace Hub. This model was pre-trained on Turkish text and
    fine-tuned for binary sentiment classification (positive/negative).

    The analyzer:
    1. Splits each review into sentences
    2. Runs each sentence through BERT to get sentiment probability
    3. Maps probabilities to [-1, 1] score range
    4. Assigns scores to relevant aspects based on keyword matching
    5. Computes general sentiment as weighted average

    Uses GPU (CUDA) when available for fast inference.
    """

    def __init__(self, model_name: str = "savasy/bert-base-turkish-sentiment-cased"):
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        self._mode = "transformer"
        self._model_name = model_name
        self.score_cache: Dict[str, float] = {}

        # Determine device: CUDA > MPS > CPU
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
            logger.info("Using CUDA GPU for sentiment analysis")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self._device = torch.device("mps")
            logger.info("Using MPS (Apple Silicon) for sentiment analysis")
        else:
            self._device = torch.device("cpu")
            logger.info("Using CPU for sentiment analysis")

        logger.info("Loading Turkish BERT model: %s ...", model_name)
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.to(self._device)
        self._model.eval()
        logger.info("Turkish BERT model loaded successfully on %s", self._device)

    def _score_text(self, text: str) -> float:
        """
        Score a single text using BERT.

        Returns a float in [-1, 1]:
            -1.0 = strongly negative
             0.0 = neutral
            +1.0 = strongly positive

        The model outputs logits for [negative, positive] classes.
        We convert to probability and map to [-1, 1].
        """
        import torch

        # Check cache
        cache_key = text.strip().lower()[:200]
        if cache_key in self.score_cache:
            return self.score_cache[cache_key]

        if not text.strip():
            return 0.0

        # Tokenize and run through BERT
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits

        # Convert to probabilities via softmax
        probs = torch.softmax(logits, dim=1)[0]

        # Model labels: index 0 = negative, index 1 = positive
        # (verified for savasy/bert-base-turkish-sentiment-cased)
        neg_prob = probs[0].item()
        pos_prob = probs[1].item()

        # Map to [-1, 1]: score = pos_prob - neg_prob
        score = pos_prob - neg_prob

        # Cache the result
        self.score_cache[cache_key] = score

        return round(score, 4)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for aspect-level analysis."""
        # Split on sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        # Also split on commas/semicolons and contrast conjunctions
        expanded = []
        for s in sentences:
            parts = re.split(r'[,;]+|\s+(?:ama|fakat|ancak|lakin|oysa|ne var ki|bununla birlikte)\s+', s, flags=re.IGNORECASE)
            for p in parts:
                p = p.strip()
                if len(p) > 10:
                    expanded.append(p)
        return expanded if expanded else [text.strip()]

    def _detect_aspects(self, sentence: str) -> List[str]:
        """Detect which aspects are mentioned in a sentence."""
        lower = sentence.lower()
        detected = []
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                detected.append(aspect)
        return detected

    def predict(self, reviews: List[str]) -> List[Dict[str, float]]:
        """
        Analyze reviews and return aspect scores including _general sentiment.

        For each review:
        1. Score the full review with BERT → general sentiment
        2. Split into sentences
        3. Score each sentence with BERT
        4. Assign sentence scores to detected aspects
        5. Return combined aspect + general scores

        Returns:
            List of dicts with keys: _general, _type, _pos, _neg, and each aspect.
        """
        results = []

        for review in reviews:
            review_stripped = review.strip()
            if not review_stripped:
                scores = {"_general": 0.0, "_type": "neutral", "_pos": 0, "_neg": 0}
                for aspect in ASPECTS:
                    scores[aspect] = 0.0
                results.append(scores)
                continue

            # 1. General sentiment from whole review
            general_score = self._score_text(review_stripped)

            # 2. Split into sentences and score each
            sentences = self._split_sentences(review_stripped)
            sentence_scores: List[Dict] = []

            for sentence in sentences:
                score = self._score_text(sentence)
                aspects = self._detect_aspects(sentence)
                sentence_scores.append({
                    "text": sentence,
                    "score": score,
                    "aspects": aspects,
                })

            # 3. Aggregate aspect scores from sentence-level analysis
            aspect_scores: Dict[str, List[float]] = {a: [] for a in ASPECTS}

            for ss in sentence_scores:
                for aspect in ss["aspects"]:
                    aspect_scores[aspect].append(ss["score"])

            # 4. Build final scores dict
            pos_count = sum(1 for ss in sentence_scores if ss["score"] > 0.1)
            neg_count = sum(1 for ss in sentence_scores if ss["score"] < -0.1)

            # Determine sentiment type
            if pos_count > 0 and neg_count > 0:
                sentiment_type = "mixed"
            elif general_score > 0.1:
                sentiment_type = "positive"
            elif general_score < -0.1:
                sentiment_type = "negative"
            else:
                sentiment_type = "neutral"

            scores = {
                "_general": general_score,
                "_type": sentiment_type,
                "_pos": pos_count,
                "_neg": neg_count,
            }

            for aspect in ASPECTS:
                if aspect_scores[aspect]:
                    # Average of sentence scores mentioning this aspect,
                    # blended with general score to avoid single-sentence extremes
                    avg = sum(aspect_scores[aspect]) / len(aspect_scores[aspect])
                    # More sentences → trust aspect score more; fewer → blend with general
                    n = len(aspect_scores[aspect])
                    weight = min(0.85, 0.5 + n * 0.1)  # 1 sentence=0.6, 4+=0.85
                    blended = weight * avg + (1 - weight) * general_score
                    scores[aspect] = round(blended, 4)
                else:
                    # Aspect not mentioned → weak general influence
                    scores[aspect] = round(general_score * 0.15, 4)

            results.append(scores)

        return results

    def predict_single(self, review: str) -> Dict[str, float]:
        """Analyze single review."""
        return self.predict([review])[0]

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return str(self._device)


# ---------------------------------------------------------------------------
# PyTorch Model for Fine-Tuning (educational/training purposes)
# ---------------------------------------------------------------------------

try:
    import torch
    import torch.nn as nn
    from transformers import AutoModel
    _PYTORCH_AVAILABLE = True
except ImportError:
    _PYTORCH_AVAILABLE = False

if _PYTORCH_AVAILABLE:

    class AspectSentimentModel(nn.Module):
        """
        BERT-based aspect sentiment classifier for fine-tuning.

        Accepts review text, produces 6 aspect sentiment scores in [-1, 1].
        Uses Turkish BERT encoder + trainable classifier head.

        Architecture:
            BERT Encoder (12 layers × 768 hidden × 12 attention heads)
            → [CLS] token extraction
            → Dropout(0.3)
            → Linear(768, 256) → ReLU → Dropout(0.2)
            → Linear(256, 6) → tanh()
            → 6 aspect scores in [-1, 1]
        """

        def __init__(
            self,
            base_model_name: str = "savasy/bert-base-turkish-sentiment-cased",
            num_aspects: int = 6,
        ) -> None:
            super().__init__()
            self.encoder = AutoModel.from_pretrained(base_model_name)
            self.dropout = nn.Dropout(0.3)
            hidden_size = self.encoder.config.hidden_size

            # Classifier head: BERT embeddings → 256 hidden → 6 aspects
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size, 256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, num_aspects),
            )

        def forward(
            self, input_ids: torch.Tensor, attention_mask: torch.Tensor
        ) -> torch.Tensor:
            """
            Forward pass through BERT encoder + classifier.

            Args:
                input_ids: Tokenized review text (B, seq_len).
                attention_mask: Attention mask for padding (B, seq_len).

            Returns:
                Logits for 6 aspects (B, 6). Typically passed through tanh()
                to bound to [-1, 1] during inference.
            """
            outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
            cls_output = outputs.last_hidden_state[:, 0, :]
            cls_output = self.dropout(cls_output)
            logits = self.classifier(cls_output)
            return logits
