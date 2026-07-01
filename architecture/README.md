# ReviewLens Architecture Workspace

Bu klasör, ReviewLens için mimari kararların ve pattern’lerin tek kaynağıdır.

## Dizin yapısı
- `adr/`: Karar kayıtları (Architecture Decision Records)
- `patterns/`: Uygulama pattern’leri ve referans uygulama kuralları
- `diagrams/`: Mimari diyagramlar (ilerleyen fazlarda)

## Çalışma prensibi
1. Önce ilgili ADR/Pattern güncellenir.
2. Sonra kod değişikliği yapılır.
3. PR açıklamasında ilgili ADR numarası referans verilir.

## Mevcut hedef (MVP)
- Trendyol + Hepsiburada desteği
- Yorum + yıldız scraping
- 0-100 skor + iyi/orta/kötü etiketi
- Top 3 tekrar eden sorun + görülme yüzdesi
- Popup + sidepanel sonuç gösterimi
- Hata durumunda kısmi sonuç + neden

