# Implementation Plan (MVP)

## Faz 1 — Backend temel sözleşme
- Analiz response contract’ını tekleştir
- Score normalization (0-100) ve label eşiklerini merkezileştir
- Top 3 issue çıkarımı ve oran hesaplama standardı

## Faz 2 — Extension scraping adapter’ları
- Trendyol adapter
- Hepsiburada adapter
- URL resolver ve unsupported-site davranışı

## Faz 3 — UI çıktısı
- Popup: hızlı özet kartı
- Sidepanel: detay (score, label, top3 issues, partial reason)
- Kısmi sonuçların tutarlı gösterimi

## Faz 4 — Kalite ve hız
- Unit test iskeleti + CI gate
- Integration testler (adapter + response contract)
- E2E testler (sayfa -> extension -> sonuç)
- 3 saniye hedefi için performans iyileştirmeleri

