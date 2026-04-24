import { defineConfig } from "@playwright/test";

const apiPort = 8010;
const webPort = 3100;
const webBaseUrl = `http://127.0.0.1:${webPort}`;
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [["list"], ["html", { open: "never", outputFolder: "output/playwright/report" }]],
  outputDir: "output/playwright/test-results",
  use: {
    baseURL: webBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: "python tests/e2e/scripts/run_phase3_api.py",
      cwd: ".",
      env: {
        ...process.env,
        STUDYPILOT_E2E_API_PORT: String(apiPort),
        STUDYPILOT_E2E_ALLOWED_ORIGIN: webBaseUrl,
      },
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${apiBaseUrl}/healthz`,
    },
    {
      command: `npm --prefix apps/web run dev -- --hostname 127.0.0.1 --port ${webPort}`,
      cwd: ".",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASE_URL: apiBaseUrl,
      },
      reuseExistingServer: false,
      timeout: 120_000,
      url: webBaseUrl,
    },
  ],
});
