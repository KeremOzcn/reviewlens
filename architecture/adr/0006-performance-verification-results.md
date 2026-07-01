# ADR-0006: ≤3sn performans hedefinin doğrulanması

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
ADR-0001, birincil başarı metriğini "tek ürün ilk sonuç süresi ≤ 3 saniye" olarak tanımladı. Bu ölçüm gerçek Türkçe BERT (`savasy/bert-base-turkish-sentiment-cased`) ve sentence-transformers (`all-MiniLM-L6-v2`) modelleriyle, birim/entegrasyon testlerinde kullanılan sahte (fake) modeller olmadan yapıldı.

## Ölçüm yöntemi
`app.services.analyzer.analyze()` doğrudan çağrıldı (API katmanı atlanarak), gerçek modeller yüklü haldeyken, her seferinde daha önce görülmemiş (cache'e girmemiş) yorum metinleriyle:

| Senaryo | Yorum sayısı | Süre |
|---|---|---|
| Soğuk başlangıç (model yükleme dahil) | 3 | ~16 sn |
| Tipik ürün sayfası | 20 | 0.58 sn |
| Yoğun ürün sayfası | 50 | 0.41 sn |
| Maksimum (adapter `MAX_ITEMS` sınırı) | 100 | 0.37 sn |

## Karar
- Model yükleme (~15-25 sn, tek seferlik) `app/main.py`'deki `lifespan` içinde arka plan thread'i ile sunucu başlangıcında yapılır; istek başına maliyete dahil değildir.
- Isınmış (warm) modelle tek istek analizi, 100 yoruma kadar **0.4-0.6 saniye** aralığında kalıyor — ≤3sn hedefinin büyük marjla altında.
- Ek performans optimizasyonuna (batching, GPU, model quantization vb.) şu an ihtiyaç yok; hedef zaten karşılanıyor.

## Sonuçlar
- ADR-0001'deki performans hedefi doğrulandı, Faz 4 kapsamındaki performans doğrulama maddesi tamamlandı.
- Sunucunun trafik almadan önce modelleri önceden ısıtması (preload) kritik önemde; bu olmadan ilk istek ~15-25 sn gecikir.
