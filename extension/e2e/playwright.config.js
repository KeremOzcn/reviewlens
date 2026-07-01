"use strict";

const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  webServer: {
    command: "node mock-backend.js",
    url: "http://127.0.0.1:8001/api/v1/health",
    reuseExistingServer: !process.env.CI,
    timeout: 10_000,
  },
});
