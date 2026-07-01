# Pattern: Clean Architecture kuralları (Backend)

## Amaç
İş kurallarını framework/IO bağımlılıklarından ayırmak.

## Kurallar
1. Domain katmanı dış dünyayı bilmez.
2. Application sadece port/interface görür.
3. Infrastructure, Application portlarını implemente eder.
4. Interface katmanı DTO/HTTP/extension köprüsünü yönetir.

## Pratik kontrol listesi
- Yeni use-case eklendiğinde önce Application katmanında kontrat açılır.
- Model/scraping erişimi doğrudan route içinde yapılmaz.
- Domain fonksiyonları framework nesnesi almaz.

