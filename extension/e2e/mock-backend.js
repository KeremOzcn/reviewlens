"use strict";

/**
 * Minimal dependency-free HTTP backend for e2e tests. Stands in for the real
 * FastAPI service on http://127.0.0.1:8001 (the URL background.js and
 * manifest.json's host_permissions are hardcoded to) so the extension flow
 * can be exercised end-to-end without needing torch/transformers installed.
 */

const http = require("node:http");

const PORT = 8001;
const HOST = "127.0.0.1";

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function buildAnalyzeResponse(payload) {
  const reviews = Array.isArray(payload.reviews) ? payload.reviews : [];
  const warnings = Array.isArray(payload.scrape_warnings) ? payload.scrape_warnings : [];
  const partialReason = warnings.filter(Boolean).join(" | ") || null;
  const reviewCount = reviews.length;

  return {
    product_name: payload.product_name ?? null,
    overall_sentiment: 0.44,
    score: 72,
    label: "good",
    summary: `${reviewCount} yorum analiz edildi. Genel izlenim olumlu.`,
    aspect_scores: {
      quality: 0.6,
      shipping: -0.2,
      price: 0.1,
      durability: 0.5,
      customer_service: 0.0,
      usability: 0.7,
    },
    top_issues: [],
    top_issue_summaries: [{ title: "Kargo gecikmesi", ratio: 20 }],
    buyer_summary: `${reviewCount} yorum analiz edildi. Genel izlenim olumlu.`,
    seller_report: {
      top_issues: [],
      positive_highlights: ["Kalite"],
      overall_health: "İyi",
      recommended_actions: [],
    },
    outlier_insights: [],
    pros: ["Kullanımı kolay", "Kaliteli malzeme"],
    cons: ["Kargo süresi uzun"],
    red_flags: [],
    review_count: reviewCount,
    processed_review_count: reviewCount,
    confidence: reviewCount >= 15 ? "medium" : "low",
    sentiment_breakdown: { positive: reviewCount, negative: 0, mixed: 0, neutral: 0 },
    partial: Boolean(partialReason),
    partial_reason: partialReason,
  };
}

const server = http.createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method === "GET" && req.url === "/api/v1/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: "ok",
        version: "e2e-mock",
        models_loaded: { sentiment_analyzer: true, topic_extractor: true },
      })
    );
    return;
  }

  if (req.method === "POST" && req.url === "/api/v1/analyze") {
    const raw = await readBody(req);
    let payload = {};
    try {
      payload = JSON.parse(raw || "{}");
    } catch {
      payload = {};
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(buildAnalyzeResponse(payload)));
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ detail: "not found" }));
});

server.listen(PORT, HOST, () => {
  console.log(`ReviewLens e2e mock backend listening on http://${HOST}:${PORT}`);
});
