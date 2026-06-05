import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e-browser',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:8765',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Start the app before tests, stop after
  webServer: {
    command: `cd /home/ubuntu/worx/finally/backend && uv --cache-dir $TMPDIR/uv-cache run uvicorn app.main:app --host 0.0.0.0 --port 8765`,
    url: 'http://localhost:8765/api/health',
    reuseExistingServer: process.env.CI !== 'true',
    timeout: 30000,
    env: {
      LLM_MOCK: 'true',
      DB_PATH: '/tmp/finally_e2e_playwright.db',
    },
  },
});
