import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;
const STUB_PORT = 3101;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // A stub stands in for the Python service, so the browser tests cover the
  // real routing and streaming without Tavily, Mistral or Postgres.
  webServer: [
    {
      command: `node e2e/stub-api.mjs`,
      url: `http://127.0.0.1:${STUB_PORT}/api/health`,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `npm run build && npx next start --port ${PORT}`,
      url: `http://127.0.0.1:${PORT}`,
      env: { API_PROXY: `http://127.0.0.1:${STUB_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
