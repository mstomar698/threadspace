import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = 3100;
const BACKEND_PORT = 8001;
const BASE_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const API_URL = `http://127.0.0.1:${BACKEND_PORT}`;

/**
 * Real-stack e2e: Playwright boots the actual Django backend (sqlite, seeded,
 * GitHub stubbed) and the Next.js app, then drives the browser against both.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : [["list"]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "bash ./e2e/backend.sh",
      url: `${API_URL}/api/v1/github/repos/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        E2E_BACKEND_PORT: String(BACKEND_PORT),
        E2E_FRONTEND_PORT: String(FRONTEND_PORT),
      },
    },
    {
      // Run a production build, not `next dev` — Turbopack dev mode hangs the
      // client-side auth bootstrap under headless Chromium, and prod is what we
      // actually ship anyway.
      command: `npm run build && npm run start -- --port ${FRONTEND_PORT}`,
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        NEXT_PUBLIC_API_URL: API_URL,
      },
    },
  ],
});
