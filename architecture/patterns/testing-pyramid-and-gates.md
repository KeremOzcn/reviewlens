# Pattern: Test piramidi ve quality gate

## Amaç
Hızlı geri bildirim + güvenilir release.

## Piramit
- **Unit:** Domain ve use-case kuralları
- **Integration:** Adapter + application entegrasyonu
- **E2E:** Extension akışı (scrape -> analyze -> render)

## Gate
- lint
- type-check
- unit/integration/e2e testleri

## Başlangıç adımı
Önce unit test iskeleti ve CI pipeline; ardından integration ve e2e kapsamı kademeli genişletilir.

