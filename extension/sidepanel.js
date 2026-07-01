"use strict";

const ASPECT_LABELS = {
  quality: "Kalite",
  shipping: "Kargo",
  price: "Fiyat",
  durability: "Dayanıklılık",
  customer_service: "Müşteri Hizmetleri",
  usability: "Kullanım Kolaylığı",
};

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

function setHealthStatus(online) {
  const dot = document.getElementById("healthDot");
  const label = document.getElementById("healthLabel");
  dot.className = `health-dot ${online ? "online" : "offline"}`;
  label.textContent = online ? "API Çevrimiçi" : "API Çevrimdışı";
}

function setLoadingMsg(msg) {
  document.getElementById("loadingMsg").textContent = msg;
}

// API returns MVP score in [0,100]. Fallback keeps legacy [-1,1] support.
function normalizeScore(data) {
  if (typeof data?.score === "number") return Math.round(data.score);
  return Math.round(((data?.overall_sentiment ?? 0) + 1) * 50);
}

function scoreColor(score) {
  if (score >= 67) return "green";
  if (score < 34) return "red";
  return "yellow";
}

function scoreToPct(score) {
  return Math.max(0, Math.min(100, Math.round(score)));
}

const CONFIDENCE_LABELS = { low: "Düşük", medium: "Orta", high: "Yüksek" };

function animateBar(el, targetPct) {
  el.style.width = "0%";
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      el.style.width = `${targetPct}%`;
    });
  });
}

function renderResult(data) {
  const score = normalizeScore(data);
  const color = scoreColor(score);
  const label = data.label ?? "medium";
  const labelMap = { good: "İyi", medium: "Orta", bad: "Kötü" };

  document.getElementById("scoreValue").textContent = String(score);
  document.getElementById("scoreBadge").className = `score-badge score-${color}`;

  const fill = document.getElementById("scoreBarFill");
  fill.className = `score-bar-fill bar-${color}`;
  animateBar(fill, scoreToPct(score));
  document.getElementById("scoreLabel").textContent = labelMap[label] ?? "Orta";

  const confLabel = CONFIDENCE_LABELS[data.confidence] ?? data.confidence ?? "—";
  document.getElementById("scoreMeta").textContent =
    `${data.processed_review_count ?? data.review_count ?? 0} yorum analiz edildi  •  Güven: ${confLabel}`;

  document.getElementById("buyerSummary").textContent =
    data.summary ?? data.buyer_summary ?? "";

  const issuesEl = document.getElementById("topIssuesList");
  issuesEl.innerHTML = "";
  (data.top_issue_summaries ?? []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.title} (%${item.ratio})`;
    issuesEl.appendChild(li);
  });

  const partialInfo = document.getElementById("partialInfo");
  if (data.partial && data.partial_reason) {
    partialInfo.textContent = `Kısmi sonuç: ${data.partial_reason}`;
    partialInfo.classList.remove("hidden");
  } else {
    partialInfo.classList.add("hidden");
  }

  // Aspect scores
  const aspectsEl = document.getElementById("aspectsList");
  aspectsEl.innerHTML = "";
  const aspects = data.aspect_scores ?? {};
  for (const [key, label] of Object.entries(ASPECT_LABELS)) {
    if (!(key in aspects)) continue;
    const normalized = normalizeScore(aspects[key]);
    const aColor = scoreColor(normalized);
    const pct = scoreToPct(normalized);

    const item = document.createElement("div");
    item.className = "aspect-item";
    item.innerHTML = `
      <div class="aspect-header">
        <span class="aspect-label">${label}</span>
        <span class="aspect-value score-${aColor}">${normalized > 0 ? "+" : ""}${normalized}</span>
      </div>
      <div class="aspect-track">
        <div class="aspect-fill bar-${aColor}" style="width:0%"></div>
      </div>`;
    aspectsEl.appendChild(item);
    animateBar(item.querySelector(".aspect-fill"), pct);
  }

  // Pros
  const prosEl = document.getElementById("prosList");
  prosEl.innerHTML = "";
  (data.pros ?? []).forEach((p) => {
    const li = document.createElement("li");
    li.textContent = p;
    prosEl.appendChild(li);
  });

  // Cons
  const consEl = document.getElementById("consList");
  consEl.innerHTML = "";
  (data.cons ?? []).forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c;
    consEl.appendChild(li);
  });

  // Red flags
  const flags = data.red_flags ?? [];
  const flagsCard = document.getElementById("redFlagsCard");
  flagsCard.style.display = flags.length ? "" : "none";
  const flagsEl = document.getElementById("redFlagsList");
  flagsEl.innerHTML = "";
  flags.forEach((f) => {
    const li = document.createElement("li");
    li.textContent = f;
    flagsEl.appendChild(li);
  });

  showScreen("screenResult");
}

async function analyze() {
  showScreen("screenLoading");
  setLoadingMsg("Yorumlar toplanıyor…");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("Aktif sekme bulunamadı.");

    setLoadingMsg("Analiz yapılıyor…");

    const result = await chrome.runtime.sendMessage({
      type: "ANALYZE_PAGE",
      tabId: tab.id,
      tabUrl: tab.url,
    });

    if (result?.error) throw new Error(result.error);

    renderResult(result);
  } catch (err) {
    document.getElementById("errorMsg").textContent =
      err.message ?? "Bilinmeyen bir hata oluştu.";
    showScreen("screenError");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  chrome.runtime
    .sendMessage({ type: "CHECK_HEALTH" })
    .then((res) => setHealthStatus(res?.online ?? false))
    .catch(() => setHealthStatus(false));

  document.getElementById("analyzeBtn").addEventListener("click", analyze);
  document.getElementById("analyzeAgainBtn").addEventListener("click", analyze);
  document.getElementById("retryBtn").addEventListener("click", analyze);

  document.getElementById("probeBtn").addEventListener("click", async () => {
    const out = document.getElementById("probeOutput");
    out.textContent = "Taranıyor…";
    out.classList.remove("hidden");
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const result = await chrome.runtime.sendMessage({
        type: "PROBE_DOM",
        tabId: tab.id,
      });
      out.textContent = JSON.stringify(result, null, 2);
    } catch (e) {
      out.textContent = "Hata: " + e.message;
    }
  });
});
