# ADR-0003: Çoklu e-ticaret kaynağı için Site Adapter Pattern

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
Kullanıcı farklı sitelerde (Trendyol/Hepsiburada) aynı extension deneyimini istiyor. DOM yapıları farklı olduğu için tek generic scraper kırılgan kalıyor.

## Karar
- Her site için ayrı adapter uygulanacak.
- Ortak bir `ReviewSourceAdapter` kontratı tanımlanacak.
- Adapter seçimi URL/domain bazlı resolver ile yapılacak.
- İlk faz adapter’ları:
  - `TrendyolAdapter`
  - `HepsiburadaAdapter`

Örnek sorumluluklar:
- `canHandle(url): boolean`
- `extractReviews(): Review[]`
- `extractRatings(): number[]`
- `extractProductMeta(): ProductMeta`

## Sonuçlar
- Siteye özgü kırılmalar diğer kaynakları etkilemez.
- Yeni platform ekleme maliyeti tek adapter ile sınırlı olur.

