# Data

## Amazon Reviews Multi (HuggingFace)

The primary training dataset is `amazon_reviews_multi` hosted on HuggingFace Hub.

```python
from datasets import load_dataset

# English Electronics reviews — training split
dataset = load_dataset("amazon_reviews_multi", "en", split="train", trust_remote_code=True)
```

Relevant columns: `review_body` (text), `stars` (1–5 integer rating).

---

## Bring Your Own CSV

For custom datasets or aspect-annotated data, prepare a CSV with:

### Star-rating format (`train_sentiment.py`)
```
review_body,stars
"Great product, fast delivery.",5
"Battery drains quickly.",2
```

### ABSA format (`train_aspect.py`)
```
review_body,quality,shipping,price,durability,customer_service,usability
"Great phone, bad delivery.",1,−1,0,1,0,1
```
Label encoding: **1** = positive, **0** = neutral/not mentioned, **−1** = negative.

---

## Downloading from Kaggle

Alternatively, download the Amazon Customer Reviews Dataset from Kaggle:

1. Install the Kaggle CLI: `pip install kaggle`
2. Place your `kaggle.json` API token in `~/.kaggle/`
3. Run:
   ```bash
   kaggle datasets download -d cynthiarempel/amazon-us-customer-reviews-dataset
   unzip amazon-us-customer-reviews-dataset.zip -d data/raw/
   ```

Then preprocess with the `app/preprocessing/cleaner.py` pipeline before training.

---

## File placement

| Path | Description |
|------|-------------|
| `data/raw/` | Raw downloaded files (not committed to git) |
| `data/absa_labels.csv` | Aspect-annotated dataset for `train_aspect.py` |
| `data/test_reviews.csv` | Hold-out test set for `evaluate.py` |
