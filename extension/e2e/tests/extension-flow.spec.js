"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { test, expect } = require("../support/extension-fixtures");

const PAGES_DIR = path.resolve(__dirname, "..", "pages");

function serveFixture(page, urlPattern, fixtureFile) {
  const html = fs.readFileSync(path.join(PAGES_DIR, fixtureFile), "utf-8");
  return page.route(urlPattern, (route) =>
    route.fulfill({ contentType: "text/html; charset=utf-8", body: html })
  );
}

test("Trendyol page is scraped and the popup renders the analysis result", async ({
  context,
  extensionId,
}) => {
  const productPage = await context.newPage();
  await serveFixture(productPage, "https://www.trendyol.com/**", "trendyol-product-page.html");
  await productPage.goto("https://www.trendyol.com/test-marka/kablosuz-kulaklik-p-123");
  await expect(productPage.locator(".ry-comment-card")).toHaveCount(4);

  const popupPage = await context.newPage();
  await popupPage.goto(`chrome-extension://${extensionId}/popup.html`);

  // Opening the popup as a regular tab would otherwise steal "active tab"
  // status from the product page. Bringing the product page back to front
  // mirrors real browser-action popup behaviour, where the popup itself is
  // never a tab and chrome.tabs.query({active:true}) still resolves to the
  // page the user was looking at.
  await productPage.bringToFront();

  await popupPage.click("#analyzeBtn");

  await expect(popupPage.locator("#result")).toBeVisible();
  await expect(popupPage.locator("#score")).toHaveText("72");
  await expect(popupPage.locator("#label")).toHaveText("İyi");
  await expect(popupPage.locator("#summary")).toContainText("4 yorum analiz edildi");
  await expect(popupPage.locator("#error")).toBeHidden();
});

test("Hepsiburada page without star ratings produces a partial result in the sidepanel", async ({
  context,
  extensionId,
}) => {
  const productPage = await context.newPage();
  await serveFixture(
    productPage,
    "https://www.hepsiburada.com/**",
    "hepsiburada-product-page.html"
  );
  await productPage.goto("https://www.hepsiburada.com/test-marka/akilli-saat-x200-p-456");
  await expect(productPage.locator("[data-component-type='ReviewItem']")).toHaveCount(3);

  const sidepanelPage = await context.newPage();
  await sidepanelPage.goto(`chrome-extension://${extensionId}/sidepanel.html`);

  await productPage.bringToFront();

  await sidepanelPage.click("#analyzeBtn");

  await expect(sidepanelPage.locator("#screenResult")).toBeVisible();
  await expect(sidepanelPage.locator("#scoreValue")).toHaveText("72");
  await expect(sidepanelPage.locator("#scoreLabel")).toHaveText("İyi");
  await expect(sidepanelPage.locator("#scoreMeta")).toContainText("3 yorum analiz edildi");
  await expect(sidepanelPage.locator("#buyerSummary")).toContainText("3 yorum analiz edildi");

  // No star ratings on the fixture page -> content.js appends a scrape
  // warning -> the mock backend echoes it back as partial_reason -> the
  // sidepanel surfaces it in #partialInfo.
  await expect(sidepanelPage.locator("#partialInfo")).toBeVisible();
  await expect(sidepanelPage.locator("#partialInfo")).toContainText(
    "Yıldız puanları çıkarılamadı"
  );

  const issueItems = sidepanelPage.locator("#topIssuesList li");
  await expect(issueItems).toHaveCount(1);
  await expect(issueItems.first()).toContainText("Kargo gecikmesi (%20)");
});
