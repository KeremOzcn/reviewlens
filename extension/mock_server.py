"""
Lightweight mock server for testing the ReviewLens Chrome extension.
Requires only fastapi + uvicorn (no torch/transformers needed).

Usage:
    python3 mock_server.py
    # Server starts on http://127.0.0.1:8001
"""

import random
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ReviewLens Mock Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0-mock",
        "models_loaded": {"sentiment": True, "topic": True},
    }


@app.post("/api/v1/analyze")
def analyze(body: dict):
    time.sleep(1.2)  # simulate inference delay
    review_count = len(body.get("reviews", []))

    return {
        "product_name": body.get("product_name", "Test Ürünü"),
        "overall_sentiment": 0.62,
        "aspect_scores": {
            "quality": 0.78,
            "shipping": 0.45,
            "price": 0.31,
            "durability": 0.70,
            "customer_service": -0.15,
            "usability": 0.85,
        },
        "pros": [
            "Ürün kalitesi beklentilerin üzerinde",
            "Kullanımı çok kolay ve pratik",
            "Dayanıklı malzeme, uzun ömürlü",
        ],
        "cons": [
            "Kargo süresi biraz uzun",
            "Müşteri hizmetleri yavaş yanıt veriyor",
        ],
        "red_flags": (
            []
            if random.random() > 0.4
            else ["Bazı yorumlarda garanti sorunları belirtilmiş"]
        ),
        "buyer_summary": (
            f"Bu ürün {review_count} yorum analiz edilerek değerlendirilmiştir. "
            "Genel olarak olumlu bir izlenim bırakmaktadır. "
            "Kalite ve kullanım kolaylığı öne çıkan güçlü yönlerdir. "
            "Kargo süresi ve müşteri hizmetleri konusunda bazı şikayetler mevcuttur."
        ),
        "seller_report": {
            "top_issues": [],
            "positive_highlights": ["Kalite", "Kullanım kolaylığı"],
            "overall_health": "İyi",
            "recommended_actions": [
                "Kargo süresini kısaltın",
                "Müşteri hizmetlerini iyileştirin",
            ],
        },
        "outlier_insights": [],
        "review_count": review_count,
        "confidence": "high",
        "sentiment_breakdown": {
            "positive": int(review_count * 0.65),
            "negative": int(review_count * 0.15),
            "mixed": int(review_count * 0.12),
            "neutral": int(review_count * 0.08),
        },
    }


if __name__ == "__main__":
    print("ReviewLens Mock Server — http://127.0.0.1:8001")
    print("Health: http://127.0.0.1:8001/api/v1/health")
    print("Ctrl+C to stop\n")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
