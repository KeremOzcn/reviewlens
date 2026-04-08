"""
Fine-tune savasy/bert-base-turkish-sentiment-cased on Turkish product reviews.

Usage:
    # Local (CPU - slow):
    python training/finetune.py

    # Google Colab (GPU - fast):
    # Upload this file and run with runtime=GPU

Output:
    models/finetuned_bert/  ← fine-tuned model weights
    training/results.json   ← evaluation metrics for report
"""

import json
import os
import time
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL_NAME = "savasy/bert-base-turkish-sentiment-cased"
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "finetuned_bert"
DATA_DIR = Path(__file__).parent / "data"
RESULTS_PATH = Path(__file__).parent / "results.json"

EPOCHS = 3
BATCH_SIZE = 8          # reduce to 4 if OOM on CPU
MAX_LENGTH = 128        # shorter = faster on CPU
LEARNING_RATE = 2e-5
WARMUP_RATIO = 0.1

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class ReviewDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_length: int):
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        enc = self.tokenizer(
            item["text"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(),
            "attention_mask": enc["attention_mask"].squeeze(),
            "labels": torch.tensor(item["label"], dtype=torch.long),
        }

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model, loader, device):
    model.eval()
    correct = total = 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = outputs.logits.argmax(dim=-1)

            correct += (preds == labels).sum().item()
            total += labels.size(0)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    accuracy = correct / total

    # F1 score (binary)
    tp = sum(p == 1 and l == 1 for p, l in zip(all_preds, all_labels))
    fp = sum(p == 1 and l == 0 for p, l in zip(all_preds, all_labels))
    fn = sum(p == 0 and l == 1 for p, l in zip(all_preds, all_labels))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"accuracy": accuracy, "f1": f1, "precision": precision, "recall": recall}

# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Loading model: {MODEL_NAME}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model.to(device)

    # Datasets
    train_ds = ReviewDataset(DATA_DIR / "train.json", tokenizer, MAX_LENGTH)
    val_ds   = ReviewDataset(DATA_DIR / "val.json",   tokenizer, MAX_LENGTH)
    test_ds  = ReviewDataset(DATA_DIR / "test.json",  tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE)

    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")

    # Optimizer + scheduler
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    # Training
    history = []
    best_val_acc = 0.0
    start_time = time.time()

    print("\n" + "=" * 60)
    print("Starting fine-tuning...")
    print("=" * 60)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        epoch_start = time.time()

        for step, batch in enumerate(train_loader, 1):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

            if step % 10 == 0:
                elapsed = time.time() - epoch_start
                print(f"  Epoch {epoch} | Step {step}/{len(train_loader)} | "
                      f"Loss: {total_loss/step:.4f} | {elapsed:.0f}s")

        avg_loss = total_loss / len(train_loader)
        val_metrics = evaluate(model, val_loader, device)

        print(f"\nEpoch {epoch} Summary:")
        print(f"  Train Loss : {avg_loss:.4f}")
        print(f"  Val Acc    : {val_metrics['accuracy']:.4f}")
        print(f"  Val F1     : {val_metrics['f1']:.4f}")

        history.append({
            "epoch": epoch,
            "train_loss": round(avg_loss, 4),
            **{f"val_{k}": round(v, 4) for k, v in val_metrics.items()}
        })

        # Save best model
        if val_metrics["accuracy"] > best_val_acc:
            best_val_acc = val_metrics["accuracy"]
            model.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)
            print(f"  ✓ Best model saved (val_acc={best_val_acc:.4f})")

    # Final test evaluation
    print("\n" + "=" * 60)
    print("Final Test Evaluation")
    print("=" * 60)

    # Load best model for test
    best_model = AutoModelForSequenceClassification.from_pretrained(OUTPUT_DIR)
    best_model.to(device)
    test_metrics = evaluate(best_model, test_loader, device)

    print(f"Test Accuracy : {test_metrics['accuracy']:.4f}")
    print(f"Test F1       : {test_metrics['f1']:.4f}")
    print(f"Test Precision: {test_metrics['precision']:.4f}")
    print(f"Test Recall   : {test_metrics['recall']:.4f}")

    total_time = time.time() - start_time

    # Save results for report
    results = {
        "model": MODEL_NAME,
        "finetuned_model": str(OUTPUT_DIR),
        "training_config": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "max_length": MAX_LENGTH,
            "optimizer": "AdamW",
            "scheduler": "linear_warmup",
        },
        "training_history": history,
        "test_metrics": {k: round(v, 4) for k, v in test_metrics.items()},
        "best_val_accuracy": round(best_val_acc, 4),
        "total_training_time_seconds": round(total_time, 1),
        "device": str(device),
        "dataset_sizes": {
            "train": len(train_ds),
            "val": len(val_ds),
            "test": len(test_ds),
        }
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {RESULTS_PATH}")
    print(f"Fine-tuned model saved to {OUTPUT_DIR}")
    print(f"Total time: {total_time/60:.1f} minutes")

    return results

if __name__ == "__main__":
    train()
