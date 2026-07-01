# ADR-0002: Clean Architecture sınırları

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
Mevcut yapı hızlı geliştirme ile büyüdü; test edilebilirlik ve bakım maliyeti artırılmak isteniyor.

## Karar
Backend tarafında aşağıdaki katman sınırları uygulanacak:
- **Domain:** Saf iş kuralları, entity/value object, dış bağımlılık yok
- **Application:** Use-case orchestration, interface/port tanımları
- **Infrastructure:** Model inference, scraping client, repository/IO implementasyonları
- **Interface:** API route/DTO/extension ile konuşan uçlar

Ek kurallar:
- Dependency yönü dıştan içe değil, içten dışa bağımsız olacak.
- Interface/Application katmanları Infrastructure detaylarını bilmeyecek.
- Refactor yaklaşımı: büyük kırılım yerine iteratif küçük adımlar.

## Sonuçlar
- Unit test kapsamı domain/application’da hızlı büyütülebilir.
- Teknik borç kontrollü şekilde azaltılır.

