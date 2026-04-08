"""
Fine-tuned modeli sisteme entegre et.
Fine-tune tamamlandıktan sonra bu script'i çalıştır.

Usage:
    python training/use_finetuned.py
"""

from pathlib import Path
import json

FINETUNED_PATH = Path(__file__).parent.parent / "models" / "finetuned_bert"
ENV_PATH = Path(__file__).parent.parent / ".env"

def integrate():
    if not FINETUNED_PATH.exists():
        print("Fine-tuned model bulunamadı. Önce finetune.py çalıştırın.")
        return

    # .env dosyasını güncelle
    env_content = ENV_PATH.read_text(encoding="utf-8")
    
    finetuned_str = str(FINETUNED_PATH).replace("\\", "/")
    
    if "SENTIMENT_MODEL_NAME" in env_content:
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("SENTIMENT_MODEL_NAME"):
                new_lines.append(f"SENTIMENT_MODEL_NAME={finetuned_str}")
            else:
                new_lines.append(line)
        ENV_PATH.write_text("\n".join(new_lines), encoding="utf-8")
    else:
        with open(ENV_PATH, "a", encoding="utf-8") as f:
            f.write(f"\nSENTIMENT_MODEL_NAME={finetuned_str}\n")

    print(f"✓ .env updated: SENTIMENT_MODEL_NAME={finetuned_str}")

    # Results göster
    results_path = Path(__file__).parent / "results.json"
    if results_path.exists():
        with open(results_path, encoding="utf-8") as f:
            results = json.load(f)
        print("\n=== Fine-tune Results ===")
        print(f"Test Accuracy : {results['test_metrics']['accuracy']:.4f}")
        print(f"Test F1       : {results['test_metrics']['f1']:.4f}")
        print(f"Best Val Acc  : {results['best_val_accuracy']:.4f}")
        print(f"Training Time : {results['total_training_time_seconds']/60:.1f} min")

    print("\nBackend'i yeniden başlatın:")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8001")

if __name__ == "__main__":
    integrate()
