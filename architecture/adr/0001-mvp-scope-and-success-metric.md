# ADR-0001: MVP kapsamı ve başarı metriği

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
Ürün hedefi: Kullanıcı ürün sayfasındayken extension ile yorumları hızlıca tarayıp kolay anlaşılır özet almak istiyor.

## Karar
- İlk release kapsamı:
  - Trendyol + Hepsiburada
  - Yorum + yıldız verisi
  - 0-100 genel skor
  - İyi/Orta/Kötü etiketi
  - Top 3 tekrar eden sorun + görülme yüzdesi
  - Popup + Sidepanel arayüzü
- Birincil başarı metriği: **tek ürün ilk sonuç süresi ≤ 3 saniye**.

## Sonuçlar
- Scope netleşti, gereksiz özellik genişlemesi engellenir.
- Performans hedefi tüm teknik tasarım kararlarını yönlendirir.

