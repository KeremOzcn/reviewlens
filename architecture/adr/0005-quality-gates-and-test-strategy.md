# ADR-0005: Test stratejisi ve kalite kapısı

- **Durum:** Accepted
- **Tarih:** 2026-07-01

## Bağlam
Öncelik test edilebilirlik ve kalite güvencesi. Geliştirme hızını düşürmeden stabilite artırılmalı.

## Karar
- Test stratejisi: **tam test piramidi** (unit + integration + e2e dengeli).
- İlk aktifleme: **unit test iskeleti + CI entegrasyonu**.
- Merge quality gate:
  - lint geçmeli
  - type-check geçmeli
  - tüm testler geçmeli
- Uygulama sırası: önce backend, sonra extension.

## Sonuçlar
- Regresyon riski erken yakalanır.
- Kod kalitesi kişisel disipline değil otomasyona bağlanır.

