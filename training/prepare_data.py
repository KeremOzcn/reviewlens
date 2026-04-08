"""
Data preparation for fine-tuning Turkish BERT sentiment model.

Sources:
1. Local labeled_reviews.json (40 reviews)
2. Data augmentation (synonym replacement, paraphrase templates)
3. HuggingFace: turkish_product_reviews dataset (if available)

Output: training/data/train.json, val.json, test.json
"""

import json
import random
import os
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load existing labeled data
# ---------------------------------------------------------------------------

def load_local_data():
    path = Path(__file__).parent.parent / "data" / "labeled_reviews.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    
    samples = []
    for r in raw["reviews"]:
        score = r["overall_sentiment"]
        label = 1 if score > 0.1 else 0  # 1=positive, 0=negative
        if abs(score) > 0.1:  # skip near-neutral
            samples.append({"text": r["text"], "label": label, "score": score})
    
    print(f"Loaded {len(samples)} local samples")
    return samples

# ---------------------------------------------------------------------------
# 2. Data augmentation - Turkish paraphrase templates
# ---------------------------------------------------------------------------

POSITIVE_TEMPLATES = [
    "Bu ürünü kesinlikle tavsiye ederim, {reason}.",
    "Çok memnun kaldım, {reason}.",
    "Harika bir ürün, {reason}.",
    "Beklentilerimi fazlasıyla karşıladı, {reason}.",
    "Gerçekten kaliteli, {reason}.",
    "Fiyat performans açısından mükemmel, {reason}.",
    "Aldığıma hiç pişman olmadım, {reason}.",
    "Her şey yolunda, {reason}.",
]

NEGATIVE_TEMPLATES = [
    "Bu ürünü kesinlikle almayın, {reason}.",
    "Çok hayal kırıklığı yaşadım, {reason}.",
    "Berbat bir ürün, {reason}.",
    "Paramı çöpe attım, {reason}.",
    "Hiç memnun kalmadım, {reason}.",
    "İade ettim, {reason}.",
    "Aldığıma çok pişman oldum, {reason}.",
    "Kesinlikle tavsiye etmiyorum, {reason}.",
]

POSITIVE_REASONS = [
    "kalitesi gerçekten iyi",
    "kargo çok hızlı geldi",
    "fiyatına göre çok iyi",
    "dayanıklı yapılmış",
    "müşteri hizmetleri çok ilgili",
    "kullanımı çok kolay",
    "ses kalitesi harika",
    "batarya ömrü uzun",
    "tasarımı çok şık",
    "performansı mükemmel",
    "paketleme çok özenli",
    "ürün açıklamayla birebir uyuşuyor",
    "hızlı teslimat yapıldı",
    "garanti süreci sorunsuz",
    "beklentilerimi aştı",
]

NEGATIVE_REASONS = [
    "kalitesi çok düşük",
    "kargo çok geç geldi",
    "fiyatını kesinlikle hak etmiyor",
    "çok çabuk bozuldu",
    "müşteri hizmetleri ilgilenmiyor",
    "kullanımı çok zor",
    "ses kalitesi berbat",
    "batarya çok çabuk bitiyor",
    "tasarımı çok kötü",
    "performansı yetersiz",
    "paket hasarlı geldi",
    "ürün açıklamayla uyuşmuyor",
    "teslimat çok geç oldu",
    "garanti süreci çok sorunlu",
    "beklentilerimin çok altında kaldı",
]

def augment_data(n_positive=80, n_negative=80):
    samples = []
    
    for _ in range(n_positive):
        template = random.choice(POSITIVE_TEMPLATES)
        reason = random.choice(POSITIVE_REASONS)
        text = template.format(reason=reason)
        samples.append({"text": text, "label": 1, "score": 0.8, "augmented": True})
    
    for _ in range(n_negative):
        template = random.choice(NEGATIVE_TEMPLATES)
        reason = random.choice(NEGATIVE_REASONS)
        text = template.format(reason=reason)
        samples.append({"text": text, "label": 0, "score": -0.8, "augmented": True})
    
    print(f"Generated {len(samples)} augmented samples")
    return samples

# ---------------------------------------------------------------------------
# 3. Try to load HuggingFace dataset
# ---------------------------------------------------------------------------

def load_huggingface_data(max_samples=500):
    try:
        from datasets import load_dataset
        
        print("Trying to load HuggingFace dataset...")
        ds = load_dataset("turkish_product_reviews", split="train", trust_remote_code=True)
        
        pos_samples = []
        neg_samples = []
        
        for item in ds:
            text = item.get("sentence", item.get("text", ""))
            sentiment = item.get("sentiment", item.get("label", -1))
            
            if not text or len(text.strip()) < 10:
                continue
            
            if isinstance(sentiment, str):
                label = 1 if sentiment.lower() in ["positive", "pos", "1"] else 0
            else:
                label = int(sentiment)
            
            sample = {"text": text, "label": label, "score": 0.8 if label == 1 else -0.8}
            
            if label == 1 and len(pos_samples) < max_samples // 2:
                pos_samples.append(sample)
            elif label == 0 and len(neg_samples) < max_samples // 2:
                neg_samples.append(sample)
            
            if len(pos_samples) >= max_samples // 2 and len(neg_samples) >= max_samples // 2:
                break
        
        samples = pos_samples + neg_samples
        print(f"Loaded {len(samples)} samples from HuggingFace (pos={len(pos_samples)}, neg={len(neg_samples)})")
        return samples
        
    except Exception as e:
        print(f"HuggingFace dataset not available: {e}")
        return []

# ---------------------------------------------------------------------------
# 4. Split and save
# ---------------------------------------------------------------------------

def split_and_save(all_samples):
    random.shuffle(all_samples)
    
    n = len(all_samples)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    
    train = all_samples[:train_end]
    val = all_samples[train_end:val_end]
    test = all_samples[val_end:]
    
    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        path = DATA_DIR / f"{split_name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(split_data, f, ensure_ascii=False, indent=2)
        
        pos = sum(1 for s in split_data if s["label"] == 1)
        neg = sum(1 for s in split_data if s["label"] == 0)
        print(f"{split_name}: {len(split_data)} samples (pos={pos}, neg={neg}) → {path}")
    
    return train, val, test

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Preparing fine-tuning data...")
    print("=" * 60)
    
    all_samples = []
    
    # 1. Local data
    all_samples.extend(load_local_data())
    
    # 2. HuggingFace data (balanced)
    hf_samples = load_huggingface_data(max_samples=600)
    all_samples.extend(hf_samples)
    
    # 3. Check balance and augment negatives if needed
    pos_count = sum(1 for s in all_samples if s["label"] == 1)
    neg_count = sum(1 for s in all_samples if s["label"] == 0)
    print(f"\nBefore augmentation: pos={pos_count}, neg={neg_count}")
    
    # Always augment to ensure balance
    needed_neg = max(0, pos_count - neg_count)
    needed_pos = max(0, neg_count - pos_count)
    
    aug = augment_data(
        n_positive=needed_pos + 50,
        n_negative=needed_neg + 50
    )
    all_samples.extend(aug)
    
    # Final balance check
    pos_count = sum(1 for s in all_samples if s["label"] == 1)
    neg_count = sum(1 for s in all_samples if s["label"] == 0)
    print(f"After augmentation : pos={pos_count}, neg={neg_count}")
    print(f"Total samples: {len(all_samples)}")
    
    # 4. Split and save
    train, val, test = split_and_save(all_samples)
    
    print("\nData preparation complete!")
    print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
