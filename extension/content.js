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

    trySelect(selectors, doc = document) {
      for (const selector of selectors) {
        try {
          const el = doc.querySelector(selector);
          if (el) return el;
        } catch {}
      }
      return null;
    }

    trySelectAll(selectors, doc = document) {
      let best = [];
      for (const selector of selectors) {
        try {
          const els = Array.from(doc.querySelectorAll(selector));
          if (els.length > best.length) best = els;
        } catch {}
      }
      return best;
    }

    async waitForAny(selectors, timeout = 8000, doc = document) {
      return new Promise((resolve, reject) => {
        const found = this.trySelect(selectors, doc);
        if (found) {
          resolve(found);
          return;
        }

        const observer = new MutationObserver(() => {
          const el = this.trySelect(selectors, doc);
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

        observer.observe(doc.body, { childList: true, subtree: true });
      });
    }

    // Hook for adapters whose review widgets only start loading once
    // scrolled into view (lazy IntersectionObserver-based rendering).
    async prepare() {}

    // Hook for adapters whose reviews don't live in the current page's DOM
    // at all (e.g. moved to a separate sub-page). Default: scrape the live
    // page. `warnings` may be pushed to if a fallback had to be used.
    async resolveReviewsDocument(_warnings) {
      return document;
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

    extractReviews(doc = document) {
      const containers = this.trySelectAll(this.config.reviewContainer, doc).slice(0, MAX_ITEMS);
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

    extractStars(doc = document) {
      const containers = this.trySelectAll(this.config.reviewContainer, doc).slice(0, MAX_ITEMS);
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

    extractProductMeta(doc = document) {
      const productNameEl = this.trySelect(this.config.productName, doc);
      return {
        name: productNameEl ? productNameEl.innerText.trim() : doc.title,
      };
    }
  }

  // ---------------------------------------------------------------------
  // Trendyol: reviews live on a separate `<product-url>/yorumlar` page
  // (client-side rendered — a plain fetch() of that URL returns an empty
  // shell, so it's loaded in a hidden same-origin iframe to get a real
  // rendered DOM without navigating the user's visible tab). Star ratings
  // are encoded as a CSS `padding-inline-end` cutoff on a fixed-width bar
  // rather than an attribute, so parseStarValue is overridden.
  // ---------------------------------------------------------------------
  class TrendyolAdapter extends BaseSiteAdapter {
    async resolveReviewsDocument(warnings) {
      if (this.trySelectAll(this.config.reviewContainer, document).length > 0) {
        return document;
      }
      if (/\/yorumlar(\/|$|\?)/.test(location.pathname)) {
        return document;
      }

      const reviewsUrl = location.pathname.replace(/\/$/, "") + "/yorumlar" + location.search;
      const iframe = document.createElement("iframe");
      iframe.style.cssText =
        "position:fixed;top:-9999px;left:-9999px;width:1200px;height:2000px;border:0;";
      this._reviewsFrame = iframe;

      try {
        await new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error("iframe timeout")), 9000);
          iframe.onload = () => {
            clearTimeout(timer);
            resolve();
          };
          iframe.onerror = () => {
            clearTimeout(timer);
            reject(new Error("iframe error"));
          };
          iframe.src = reviewsUrl;
          document.body.appendChild(iframe);
        });
        await this.waitForAny(this.config.reviewContainer, 6000, iframe.contentDocument).catch(
          () => {}
        );
        return iframe.contentDocument;
      } catch {
        warnings.push("Yorumlar sayfası ayrıca yüklenemedi, ana ürün sayfası kullanıldı.");
        this.cleanup();
        return document;
      }
    }

    cleanup() {
      if (this._reviewsFrame && this._reviewsFrame.parentNode) {
        this._reviewsFrame.parentNode.removeChild(this._reviewsFrame);
      }
      this._reviewsFrame = null;
    }

    parseStarValue(element) {
      const fullStar = element?.querySelector?.(".star-rating-full-star");
      if (fullStar) {
        const view = element.ownerDocument?.defaultView;
        if (view) {
          const containerWidth = parseFloat(view.getComputedStyle(element).width);
          const padding = parseFloat(view.getComputedStyle(fullStar).paddingInlineEnd);
          if (containerWidth > 0 && !Number.isNaN(padding)) {
            const rating = 5 * (1 - padding / containerWidth);
            return Math.max(0, Math.min(5, Math.round(rating * 2) / 2));
          }
        }
      }
      return super.parseStarValue(element);
    }
  }

  // ---------------------------------------------------------------------
  // Hepsiburada: reviews render inline but lazily (IntersectionObserver-
  // gated) — scrolling the comments area into view is required to trigger
  // it, and it can take several seconds even after that.
  // ---------------------------------------------------------------------
  class HepsiburadaAdapter extends BaseSiteAdapter {
    async prepare() {
      const anchor = document.querySelector(
        "[class*='Comments-module'], [class*='ReviewList-module']"
      );
      if (anchor) {
        anchor.scrollIntoView({ block: "center" });
      } else {
        window.scrollTo(0, document.body.scrollHeight * 0.6);
      }
    }
  }

  const ADAPTERS = [
    new TrendyolAdapter({
      hosts: ["trendyol.com"],
      reviewContainer: [".review-list .review", ".ry-comment-card", ".comment-card-container"],
      reviewText: [".review-comment", ".comment-text"],
      starValue: [".star-rating-star-container", "[class*='star-w']"],
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
        ".paginationContentHolder > div",
        "[data-component-type='ReviewItem']",
        ".customer-review-item",
      ],
      reviewText: ["[class*='ReviewCard-module-KaU17BbDowCWcTZ9zzxw']"],
      starValue: ["[class*='RatingPointer-module']", "[class*='star']", "[class*='rating']"],
      productName: [
        "h1[itemprop='name']",
        "[itemprop='name']",
        "h1[class*='product']",
        "h1:not([class*='ProductRate'])",
        "h1",
      ],
    }),
  ];

  function resolveAdapter() {
    const url = new URL(window.location.href);
    return ADAPTERS.find((adapter) => adapter.canHandle(url)) ?? null;
  }

  function genericReviewFallback(doc = document) {
    const candidates = doc.querySelectorAll(
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

    await adapter.prepare();
    await adapter.waitForAny(adapter.config.reviewContainer, 12000).catch(() => {});

    const reviewsDoc = await adapter.resolveReviewsDocument(warnings);

    let reviews = adapter.extractReviews(reviewsDoc);
    if (reviews.length === 0) {
      reviews = genericReviewFallback(reviewsDoc);
      if (reviews.length > 0) {
        warnings.push("Siteye özel seçicilerle yorum bulunamadı, fallback seçiciler kullanıldı.");
      }
    }

    const stars = adapter.extractStars(reviewsDoc);
    if (reviews.length > 0 && stars.length === 0) {
      warnings.push("Yıldız puanları çıkarılamadı; analiz sadece yorum metnine dayalı üretildi.");
    }

    const productMeta = adapter.extractProductMeta();
    adapter.cleanup?.();

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
