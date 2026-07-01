# ADR-0004: Analiz çıktı sözleşmesi

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
Extension UI (popup + sidepanel) ve backend arasında sabit, anlaşılır bir çıktı şeması gerekiyor.

## Karar
Tek bir standart response şeması kullanılacak:
- `score`: 0-100
- `label`: `good | medium | bad`
- `summary`: kısa kullanıcı özeti
- `topIssues`: en fazla 3 öğe
  - `title`
  - `ratio` (0-100)
- `processedReviewCount`
- `partial`: boolean
- `partialReason`: null veya açıklama

Kurallar:
- `partial=true` ise `partialReason` zorunlu.
- `topIssues` boş olabilir, ama alan her zaman döner.
- UI kararları sadece bu kontrattan beslenecek.

## Sonuçlar
- Frontend/backend uyumu güçlenir.
- Kısmi sonuç senaryoları deterministik yönetilir.

