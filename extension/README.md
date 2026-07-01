# ReviewLens Chrome Extension

AI destekli Türkçe ürün yorum analizi. Trendyol ve Hepsiburada ürün sayfalarından yorum + yıldız verisini toplayarak ReviewLens backend API'si üzerinden analiz eder.

## Kurulum

### 1. Backend'i Başlat

```bash
cd /path/to/reviewlens
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

API `http://127.0.0.1:8001/health` adresinden sağlık kontrolü yapılabilir.

### 2. Extension'ı Yükle

1. Chrome'da `chrome://extensions` adresine git
2. Sağ üstteki **Geliştirici modu** anahtarını aç
3. **Paketlenmemiş öğe yükle** düğmesine tıkla
4. Bu `extension/` klasörünü seç

Extension yüklendikten sonra adres çubuğu yanında ReviewLens ikonu görünür.

## Test

1. Backend başlatıldıktan sonra yan panelde API durum göstergesi yeşile döner
2. Trendyol'da herhangi bir ürün sayfasına git
3. Extension ikonuna tıkla — popup açılmalıdır
4. **Hızlı Analiz** düğmesine bas
5. Popup'ta skor/etiket/özet görünmeli
6. **Sidepanel Detayı Aç** ile detay ekranına geç

**Hızlı test URL'si (Trendyol):** Herhangi bir ürün sayfasına gidip yorum bölümüne kaydır, ardından analiz et.

## Desteklenen Platformlar

| Platform | Yorum Seçici | Yıldız Seçici | Ürün Adı Seçici |
|---|---|---|---|
| Trendyol | `.ry-comment-card` | `[class*='star-w']` | `h1.pr-new-br > span` |
| Hepsiburada | `[data-component-type='ReviewItem']` | `[class*='star']` | `h1[itemprop='name']` |

Her platformdan en fazla 100 yorum toplanır. SPA sayfalar için MutationObserver ile 8 saniye beklenir.

## Dosya Yapısı

```
extension/
├── manifest.json       # MV3 extension tanımı
├── background.js       # Service worker — mesajlaşma, API çağrısı, önbellek
├── content.js          # DOM scraping, MutationObserver
├── popup.html          # Hızlı özet popup arayüzü
├── popup.js            # Popup iş akışı (hızlı analiz + panel açma)
├── popup.css           # Popup stilleri
├── sidepanel.html      # Yan panel detay arayüzü (Türkçe)
├── sidepanel.js        # Arayüz mantığı ve durum yönetimi
├── sidepanel.css       # Stiller (dark theme, animasyonlar)
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

## Mesaj Akışı

```
popup.js / sidepanel.js
  → chrome.runtime.sendMessage(ANALYZE_PAGE)
    → background.js
      → chrome.tabs.sendMessage(SCRAPE_REVIEWS)
        → content.js (adapter tabanlı scraping)
      ← { reviews, stars, productName, warnings }
      → fetch POST /api/v1/analyze
      ← API response
    ← result
  → renderResult()
```

## Önbellek

`chrome.storage.local` kullanılarak URL bazlı 10 dakikalık önbellek uygulanır. Aynı ürün sayfasında tekrar analiz başlatılırsa API çağrısı yapılmaz.

## Sorun Giderme

| Hata | Çözüm |
|---|---|
| "İçerik betiği çalışmıyor" | Sayfayı yenile ve tekrar dene |
| "Yorum bölümü yüklenemedi" | Yorumlar bölümüne kadar sayfayı kaydır |
| "Bu platform desteklenmiyor" | Yalnızca desteklenen 4 platformda çalışır |
| API Çevrimdışı göstergesi | `uvicorn` sunucusunun çalıştığını kontrol et |

## Güvenlik

- `eval()` kullanılmamıştır
- `content.js` doğrudan API çağrısı yapmaz; tüm ağ istekleri service worker üzerinden geçer
- Yalnızca belirtilen `host_permissions` kapsamındaki kaynaklara erişilir
