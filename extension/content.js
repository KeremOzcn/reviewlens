(function () {
  "use strict";

  const MAX_ITEMS = 100;

  class BaseSiteAdapter {
    constructor(config) {
      this.config = config;
    }

    canHandle(url) {
      return this.config.hosts.some((host) => url.hostname.includes(host));
    }

    trySelect(selectors) {
      for (const selector of selectors) {
        try {
          const el = document.querySelector(selector);
          if (el) return el;
        } catch {}
      }
      return null;
    }

    trySelectAll(selectors) {
      let best = [];
      for (const selector of selectors) {
        try {
          const els = Array.from(document.querySelectorAll(selector));
          if (els.length > best.length) best = els;
        } catch {}
      }
      return best;
    }

    async waitForAny(selectors, timeout = 8000) {
      return new Promise((resolve, reject) => {
        const found = this.trySelect(selectors);
        if (found) {
          resolve(found);
          return;
        }

        const observer = new MutationObserver(() => {
          const el = this.trySelect(selectors);
          if (el) {
            clearTimeout(timer);
            observer.disconnect();
            resolve(el);
          }
        });

        const timer = setTimeout(() => {
          observer.disconnect();
          reject(new Error("timeout"));
        }, timeout);

        observer.observe(document.body, { childList: true, subtree: true });
      });
    }

    parseStarValue(element) {
      const candidates = [
        element?.getAttribute("data-rating"),
        element?.getAttribute("data-score"),
        element?.getAttribute("aria-label"),
        element?.getAttribute("title"),
        element?.textContent,
      ];

      for (const raw of candidates) {
        if (!raw) continue;
        const normalized = String(raw).replace(",", ".");
        const match = normalized.match(/([1-5](?:\.\d+)?)/);
        if (!match) continue;
        const parsed = parseFloat(match[1]);
        if (!Number.isNaN(parsed) && parsed >= 1 && parsed <= 5) return parsed;
      }
      return null;
    }

    extractReviews() {
      const containers = this.trySelectAll(this.config.reviewContainer).slice(0, MAX_ITEMS);
      return containers
        .map((el) => {
          for (const txtSel of this.config.reviewText) {
            try {
              const textEl = el.querySelector(txtSel);
              if (textEl) return textEl.innerText.trim();
            } catch {}
          }
          return el.innerText.trim().split("\n")[0] ?? "";
        })
        .filter((t) => t.length > 5);
    }

    extractStars() {
      const containers = this.trySelectAll(this.config.reviewContainer).slice(0, MAX_ITEMS);
      const stars = [];
      for (const container of containers) {
        let value = null;
        for (const starSelector of this.config.starValue) {
          try {
            const starEl = container.querySelector(starSelector);
            if (!starEl) continue;
            value = this.parseStarValue(starEl);
            if (value !== null) break;
          } catch {}
        }
        if (value !== null) stars.push(value);
      }
      return stars;
    }

    extractProductMeta() {
      const productNameEl = this.trySelect(this.config.productName);
      return {
        name: productNameEl ? productNameEl.innerText.trim() : document.title,
      };
    }
  }

  class TrendyolAdapter extends BaseSiteAdapter {}
  class HepsiburadaAdapter extends BaseSiteAdapter {}

  const ADAPTERS = [
    new TrendyolAdapter({
      hosts: ["trendyol.com"],
      reviewContainer: [
        ".ry-comment-card",
        ".comment-card-container",
        "[class*='comment-card']",
        "[class*='review-card']",
        ".pr-rnf-wrp li",
        "[data-testid='comment-card']",
      ],
      reviewText: [
        ".comment-text",
        ".ry-pb p",
        "[class*='comment-text']",
        "p.ry-p",
        ".description",
      ],
      starValue: [
        "[class*='star-w']",
        "[class*='rating']",
        "[aria-label*='puan']",
        "[title*='puan']",
      ],
      productName: [
        "h1.pr-new-br > span",
        ".pr-new-br span",
        "[class*='product-name'] h1",
        "h1",
      ],
    }),
    new HepsiburadaAdapter({
      hosts: ["hepsiburada.com"],
      reviewContainer: [
        "[data-component-type='ReviewItem']",
        ".customer-review-item",
        "[class*='review-item']",
        "[data-testid='review-item']",
      ],
      reviewText: [
        ".comment-content",
        ".review-content",
        "[class*='comment-content']",
        ".review-text",
      ],
      starValue: [
        "[class*='star']",
        "[class*='rating']",
        "[aria-label*='puan']",
        "[title*='puan']",
      ],
      productName: [
        "h1[itemprop='name']",
        "[itemprop='name']",
        "h1[class*='product']",
        "h1",
      ],
    }),
  ];

  function resolveAdapter() {
    const url = new URL(window.location.href);
    return ADAPTERS.find((adapter) => adapter.canHandle(url)) ?? null;
  }

  function genericReviewFallback() {
    const candidates = document.querySelectorAll(
      '[data-hook="review"], [data-type="review"], [itemtype*="Review"], ' +
        '[class*="yorum"], [id*="yorum"], [class*="comment"][class*="item"], [class*="review"][class*="item"]'
    );
    return Array.from(candidates)
      .map((el) => el.innerText.trim())
      .filter((t) => t.length > 20 && t.length < 2000)
      .slice(0, MAX_ITEMS);
  }

  async function scrapeWithAdapter(adapter) {
    const warnings = [];
    try {
      await adapter.waitForAny(adapter.config.reviewContainer, 8000);
    } catch {
      warnings.push("Yorum kapsayıcıları zamanında yüklenemedi, genel fallback kullanıldı.");
    }

    let reviews = adapter.extractReviews();
    if (reviews.length === 0) {
      reviews = genericReviewFallback();
      if (reviews.length > 0) {
        warnings.push("Siteye özel seçicilerle yorum bulunamadı, fallback seçiciler kullanıldı.");
      }
    }

    const stars = adapter.extractStars();
    if (reviews.length > 0 && stars.length === 0) {
      warnings.push("Yıldız puanları çıkarılamadı; analiz sadece yorum metnine dayalı üretildi.");
    }

    const productMeta = adapter.extractProductMeta();
    return {
      platform: adapter.config.hosts[0],
      reviews,
      stars,
      productName: productMeta.name ?? document.title,
      warnings,
    };
  }

  function probeDom() {
    const report = { url: location.href, found: [] };
    const probes = [
      "[class*='comment']",
      "[class*='review']",
      "[class*='yorum']",
      "[data-hook]",
      "[itemtype*='Review']",
      "[class*='rating']",
      "[class*='star']",
    ];

    for (const selector of probes) {
      try {
        const nodes = document.querySelectorAll(selector);
        if (nodes.length > 0) {
          report.found.push({
            selector,
            count: nodes.length,
            sample: nodes[0].className,
            text: nodes[0].innerText.trim().slice(0, 80),
          });
        }
      } catch {}
    }
    return report;
  }

  async function scrapeReviews() {
    const adapter = resolveAdapter();
    if (!adapter) {
      return {
        error: "Bu platform henüz desteklenmiyor. Şu an Trendyol ve Hepsiburada aktif.",
        reviews: [],
        stars: [],
        productName: "",
        warnings: [],
      };
    }

    const result = await scrapeWithAdapter(adapter);
    if (result.reviews.length === 0) {
      return {
        error:
          "Yorum metinleri bulunamadı.\n\n" +
          "Lütfen şunları deneyin:\n" +
          "• Ürün sayfasını açın ve yorum sekmesine gelin\n" +
          "• Biraz aşağı kaydırıp yorum kartlarının yüklenmesini bekleyin\n" +
          "• Sayfayı yenileyip tekrar analiz edin",
        reviews: [],
        stars: result.stars,
        productName: result.productName,
        warnings: result.warnings,
      };
    }

    return result;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "PING") {
      sendResponse({ ok: true });
      return;
    }

    if (message.type === "SCRAPE_REVIEWS") {
      scrapeReviews()
        .then(sendResponse)
        .catch((err) =>
          sendResponse({
            error: err.message,
            reviews: [],
            stars: [],
            productName: "",
            warnings: [],
          })
        );
      return true;
    }

    if (message.type === "PROBE_DOM") {
      sendResponse(probeDom());
      return true;
    }
  });
})();
