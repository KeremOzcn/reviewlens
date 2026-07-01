# Pattern: Standart analiz yanıtı

## Amaç
UI tarafında tek şema ile render etmek.

## Zorunlu alanlar
- `score` (0-100)
- `label` (`good|medium|bad`)
- `summary`
- `topIssues[]`
- `processedReviewCount`
- `partial`
- `partialReason`

## Dönüşüm kuralları
- Model skoru 0-100’e normalize edilir.
- Etiket eşikleri merkezi config’te tutulur.
- Top issue oranı yüzde olarak round edilip döner.

