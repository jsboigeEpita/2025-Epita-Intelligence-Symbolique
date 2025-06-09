const { defineConfig, devices } = require('@playwright/test');

/**
 * Configuration Playwright spécifique pour la Phase 5 - Tests de Non-Régression
 * Ne démarre pas automatiquement les serveurs pour éviter les conflits
 */
module.exports = defineConfig({
  testDir: './tests',
  testMatch: '**/phase5-non-regression.spec.js',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['line'],
    ['json', { outputFile: 'test-results-phase5.json' }],
    ['html', { outputFolder: 'playwright-report-phase5' }]
  ],
  
  use: {
    actionTimeout: 10000,
    navigationTimeout: 15000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    }
  ],

  // Pas de webServer automatique - les interfaces peuvent être lancées manuellement
  // ou être déjà en cours d'exécution
});