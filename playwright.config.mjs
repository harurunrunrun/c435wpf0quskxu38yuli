import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'browser.spec.mjs',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: 'list',
  outputDir: '.cache/browser-test-results',
  use: {
    baseURL: 'http://127.0.0.1:4323/flowchartcp/',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } }],
  webServer: process.env.FLOWCHARTCP_QA_OFFLINE === '1' ? undefined : {
    command: 'npm run preview:local -- --port 4323',
    url: 'http://127.0.0.1:4323/flowchartcp/',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
