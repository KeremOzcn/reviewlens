# Pattern: Site Adapter Pattern (Extension scraping)

## Amaç
Farklı e-ticaret sitelerini ortak bir kontrat altında yönetmek.

## Kontrat
Her adapter aşağıdakileri sağlar:
- `canHandle(url): boolean`
- `extractReviews(): string[]`
- `extractStars(): number[]`
- `extractProductInfo(): { name?: string, brand?: string }`

## Resolver
- Domain bazlı adapter seçimi yapılır.
- Hiçbiri uyuşmazsa “unsupported site” sonucu döner.

## Hata yönetimi
- Eksik alanlarda mümkün olan verilerle kısmi sonuç üretilir.
- Hata nedeni `partialReason` ile üst katmana taşınır.

