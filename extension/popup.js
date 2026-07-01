"use strict";

function mapLabel(label) {
  if (label === "good") return "İyi";
  if (label === "bad") return "Kötü";
  return "Orta";
}

function setError(message) {
  const err = document.getElementById("error");
  if (!message) {
    err.classList.add("hidden");
    err.textContent = "";
    return;
  }
  err.textContent = message;
  err.classList.remove("hidden");
}

async function runAnalyze() {
  setError("");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("Aktif sekme bulunamadı.");

    const result = await chrome.runtime.sendMessage({
      type: "ANALYZE_PAGE",
      tabId: tab.id,
      tabUrl: tab.url,
    });
    if (result?.error) throw new Error(result.error);

    document.getElementById("score").textContent = String(result.score ?? "-");
    document.getElementById("label").textContent = mapLabel(result.label);
    document.getElementById("summary").textContent = result.summary ?? "-";
    document.getElementById("result").classList.remove("hidden");
  } catch (err) {
    setError(err.message ?? "Analiz sırasında hata oluştu.");
  }
}

async function openSidePanel() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  await chrome.sidePanel.open({ tabId: tab.id });
}

document.getElementById("analyzeBtn").addEventListener("click", runAnalyze);
document.getElementById("openPanelBtn").addEventListener("click", openSidePanel);
