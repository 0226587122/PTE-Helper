import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke test against a running stack. Start the API first (docker compose up -d db api),
 * then run `npm run e2e`. The Vite dev server is started automatically if it isn't already running.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5174",
    trace: "retain-on-failure",
    permissions: ["microphone"],
    // A fake microphone so speaking items can record without real hardware.
    launchOptions: {
      args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-capture"],
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5174",
        reuseExistingServer: true,
        timeout: 60_000,
      },
});
