from __future__ import annotations

from app.preprocessing.cleaner import clean_review, clean_reviews_batch


def test_clean_review_handles_emoji_prefixed_text_without_crashing():
    # Regression: real Trendyol reviews often start with star emoji
    # (e.g. "⭐️⭐️⭐️⭐️⭐️hızlıve harika bi ürün..."). The English
    # contractions-expansion step used to crash on this input with
    # IndexError: string index out of range.
    text = "⭐️⭐️⭐️⭐️⭐️hızlıve harika bi ürün arama ve müzikte efsane ses veriyor."

    cleaned = clean_review(text)

    assert isinstance(cleaned, str)
    assert "harika" in cleaned


def test_clean_reviews_batch_handles_mixed_emoji_and_plain_text():
    reviews = [
        "⭐️⭐️⭐️⭐️⭐️ Kesinlikle tavsiye ederim, çok memnun kaldım.",
        "Ürün kırık geldi, berbat bir deneyimdi.",
        "👍👍 Kargo hızlıydı.",
    ]

    cleaned = clean_reviews_batch(reviews)

    assert len(cleaned) == 3
    assert all(isinstance(c, str) for c in cleaned)


def test_clean_review_preserves_turkish_characters():
    text = "Çok güzel bir ürün, teşekkürler İnşaat şirketi."

    cleaned = clean_review(text)

    assert "güzel" in cleaned
    assert "teşekkürler" in cleaned
