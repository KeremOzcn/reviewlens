"use strict";

const API_BASE = "http://127.0.0.1:8001";
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

// ── Cache helpers ────────────────────────────────────────────────────────────

async function getCached(url) {
  const key = `cache_${url}`;
  const result = await chrome.storage.local.get(key);
  const entry = result[key];
  if (entry && Date.now() - entry.timestamp < CACHE_TTL_MS) return entry.data;
  return null;
}

async function setCache(url, data) {
  const key = `cache_${url}`;
  await chrome.storage.local.set({ [key]: { data, timestamp: Date.now() } });
}

// ── Content-script injection ─────────────────────────────────────────────────
// Tabs that were open before the extension was installed/reloaded don't have
// the content script running. Ping first; inject on failure.

async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { type: "PING" });
  } catch {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"],
    });
    // Brief pause so the newly injected script is ready
    await new Promise((r) => setTimeout(r, 200));
  }
}

// ── Message router ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "ANALYZE_PAGE") {
    handleAnalyzePage(message.tabId, message.tabUrl)
      .then(sendResponse)
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "PROBE_DOM") {
    handleProbe(message.tabId)
      .then(sendResponse)
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "CHECK_HEALTH") {
    handleCheckHealth()
      .then(sendResponse)
      .catch(() => sendResponse({ online: false }));
    return true;
  }
});

// ── Handlers ─────────────────────────────────────────────────────────────────

async function handleProbe(tabId) {
  await ensureContentScript(tabId);
  return chrome.tabs.sendMessage(tabId, { type: "PROBE_DOM" });
}

async function handleAnalyzePage(tabId, tabUrl) {
  if (tabUrl) {
    const cached = await getCached(tabUrl);
    if (cached) return { ...cached, fromCache: true };
  }

  await ensureContentScript(tabId);

  const scrapeResult = await chrome.tabs.sendMessage(tabId, {
    type: "SCRAPE_REVIEWS",
  });

  if (scrapeResult?.error) throw new Error(scrapeResult.error);

  if (!scrapeResult?.reviews || scrapeResult.reviews.length === 0) {
    throw new Error(
      "Bu sayfada yorum bulunamadı. Yorum içeren bir ürün sayfasına gidin."
    );
  }

  const response = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product_name: scrapeResult.productName,
      reviews: scrapeResult.reviews,
      stars: scrapeResult.stars ?? [],
      scrape_warnings: scrapeResult.warnings ?? [],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API hatası (${response.status}): ${text}`);
  }

  const data = await response.json();
  if (tabUrl) await setCache(tabUrl, data);
  return data;
}

async function handleCheckHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/health`, {
      signal: AbortSignal.timeout(3000),
    });
    return { online: response.ok };
  } catch {
    return { online: false };
  }
}
