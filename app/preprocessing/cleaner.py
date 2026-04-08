"""
Text cleaning and normalization pipeline for product reviews.

Handles HTML stripping, contraction expansion, regex-based normalization,
and sentence segmentation for aspect-level analysis.
"""

import re
import unicodedata
from typing import List

import contractions
import nltk
from bs4 import BeautifulSoup

# Download required NLTK data on first import
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("tokenizers/punkt_tab")
except (LookupError, OSError):
    nltk.download("punkt_tab", quiet=True)

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize

# Turkish stopwords list (common Turkish words)
_TURKISH_STOP_WORDS = {
    "ve", "ile", "bir", "bu", "da", "de", "ki", "mi", "mu", "mü",
    "ama", "fakat", "ise", "için", "gibi", "daha", "çok", "en",
    "ne", "o", "şu", "ben", "sen", "biz", "siz", "onlar",
    "var", "yok", "oldu", "olan", "kadar", "sonra", "önce", "sadece",
    "herkes", "hiç", "böyle", "doğru", "eğer", "hangi", "nasıl",
    "neden", "neresi", "nerde", "nerede", "niçin", "öyle", "tarafından",
    "tüm", "yaşanan", "yoluyla", "yüksek", "züya"
}
_STOP_WORDS = _TURKISH_STOP_WORDS

# Regex patterns compiled once for efficiency
_RE_HTML_ENTITY = re.compile(r"&[a-z]+;")
_RE_URL = re.compile(r"https?://\S+|www\.\S+")
_RE_EMAIL = re.compile(r"\S+@\S+\.\S+")
_RE_REPEATED_CHARS = re.compile(r"(.)\1{3,}")          # aaaaa → aaa
_RE_WHITESPACE = re.compile(r"\s+")
_RE_PUNCTUATION_EXCESS = re.compile(r"[!?]{2,}")       # !!! → !
_RE_NON_ASCII_PUNCT = re.compile(r"[^\x00-\x7F]+")
_RE_SPECIAL_CHARS = re.compile(r"[^a-zA-Z0-9\s.,!?'\"-çğışöüÇĞİŞÖÜ]")


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ")
    cleaned = _RE_HTML_ENTITY.sub(" ", cleaned)
    return cleaned


def expand_contractions(text: str) -> str:
    """Expand English contractions (e.g. don't → do not)."""
    return contractions.fix(text)


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters (preserves Turkish characters)."""
    return unicodedata.normalize("NFKC", text)


def remove_urls_and_emails(text: str) -> str:
    """Strip URLs and email addresses from text."""
    text = _RE_URL.sub(" ", text)
    text = _RE_EMAIL.sub(" ", text)
    return text


def normalize_punctuation(text: str) -> str:
    """Reduce repeated punctuation and special characters."""
    text = _RE_REPEATED_CHARS.sub(r"\1\1\1", text)  # keep up to 3 repetitions
    text = _RE_PUNCTUATION_EXCESS.sub(lambda m: m.group(0)[0], text)
    return text


def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
    """
    Remove non-alphanumeric characters.

    Args:
        text: Input string.
        keep_punctuation: If True, preserve common punctuation marks.
    """
    if not keep_punctuation:
        return re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return _RE_SPECIAL_CHARS.sub(" ", text)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace into a single space and strip."""
    return _RE_WHITESPACE.sub(" ", text).strip()


def clean_review(
    text: str,
    lowercase: bool = True,
    remove_urls: bool = True,
    remove_stopwords: bool = False,
) -> str:
    """
    Full cleaning pipeline for a single review.

    Steps:
        1. Strip HTML tags
        2. Expand contractions
        3. Normalize unicode
        4. Remove URLs / emails (optional)
        5. Normalize punctuation
        6. Lowercase
        7. Remove special characters
        8. Remove stopwords (optional)
        9. Normalize whitespace

    Args:
        text: Raw review string.
        lowercase: Convert to lowercase if True.
        remove_urls: Strip URLs and emails if True.
        remove_stopwords: Remove stopwords if True (not recommended for sentiment).

    Returns:
        Cleaned review string.
    """
    if not text or not isinstance(text, str):
        return ""

    text = strip_html(text)
    text = expand_contractions(text)
    text = normalize_unicode(text)

    if remove_urls:
        text = remove_urls_and_emails(text)

    text = normalize_punctuation(text)

    if lowercase:
        text = text.lower()

    text = remove_special_characters(text, keep_punctuation=True)

    if remove_stopwords:
        tokens = text.split()
        tokens = [t for t in tokens if t not in _STOP_WORDS]
        text = " ".join(tokens)

    text = normalize_whitespace(text)
    return text


def segment_sentences(text: str) -> List[str]:
    """
    Split a review into sentences for aspect-level analysis.

    Args:
        text: Cleaned or raw review string.

    Returns:
        List of sentence strings (non-empty).
    """
    if not text:
        return []
    sentences = sent_tokenize(text)
    return [s.strip() for s in sentences if s.strip()]


def clean_reviews_batch(
    reviews: List[str],
    lowercase: bool = True,
    remove_urls: bool = True,
    remove_stopwords: bool = False,
) -> List[str]:
    """
    Apply clean_review to a list of review strings.

    Args:
        reviews: List of raw review texts.
        lowercase: Passed to clean_review.
        remove_urls: Passed to clean_review.
        remove_stopwords: Passed to clean_review.

    Returns:
        List of cleaned review strings.
    """
    return [
        clean_review(r, lowercase=lowercase, remove_urls=remove_urls, remove_stopwords=remove_stopwords)
        for r in reviews
    ]
