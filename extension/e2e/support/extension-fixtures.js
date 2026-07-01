"use strict";

const path = require("node:path");
const { test: base, chromium } = require("@playwright/test");

const EXTENSION_PATH = path.resolve(__dirname, "..", "..");

/**
 * Playwright fixtures that load the unpacked ReviewLens extension into a
 * persistent Chromium context, matching Playwright's documented recipe for
 * testing Manifest V3 extensions.
 */
const test = base.extend({
  context: async ({}, use) => {
    // Extensions do not load under chrome-headless-shell (Playwright's
    // default headless binary has no extension system at all). headless:
    // false forces the full Chromium binary; run under xvfb-run in CI/other
    // headless Linux environments to provide a virtual display.
    const context = await chromium.launchPersistentContext("", {
      headless: false,
      args: [
        `--disable-extensions-except=${EXTENSION_PATH}`,
        `--load-extension=${EXTENSION_PATH}`,
      ],
    });
    await use(context);
    await context.close();
  },

  extensionId: async ({ context }, use) => {
    let [background] = context.serviceWorkers();
    if (!background) {
      background = await context.waitForEvent("serviceworker");
    }
    const extensionId = background.url().split("/")[2];
    await use(extensionId);
  },
});

module.exports = { test, expect: base.expect };
