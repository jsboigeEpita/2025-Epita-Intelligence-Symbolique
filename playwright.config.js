// Configuration Playwright pour le projet d'analyse argumentative
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests_playwright/tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['list'],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  outputDir: 'test-results/',
  
  use: {
    baseURL: 'http://localhost:5001',
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'always',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // webServer: [
  //   {
  //     command: 'cd services/web_api/interface-web-argumentative && npm start',
  //     port: 3000,
  //     reuseExistingServer: !process.env.CI,
  //     timeout: 120000,
  //     stdout: 'pipe',
  //     stderr: 'pipe',
  //   }
  // ],
});