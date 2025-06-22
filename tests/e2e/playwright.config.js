// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './js',
  /* Exécuter les tests en parallèle */
  fullyParallel: true,
  /* Ne pas relancer les tests en cas d'échec */
  retries: 0,
  /* Nombre de workers pour l'exécution parallèle */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter à utiliser. Voir https://playwright.dev/docs/test-reporters */
  reporter: [['html', { open: 'never' }], ['list']],

  /* Configuration partagée pour tous les projets */
  use: {
    /* URL de base pour les actions comme `await page.goto('/')` */
    /* URL de base pour les actions. Utilise FRONTEND_URL pour la cohérence avec le reste des tests. */
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',

    /* Options de traçage - C'est la clé pour l'analyse ! */
    trace: 'on', // 'on' pour toujours, 'retain-on-failure' pour les échecs uniquement

    /* Ignorer les erreurs HTTPS (utile pour les environnements de dev locaux) */
    ignoreHTTPSErrors: true,
  },

  /* Configurer les projets pour les principaux navigateurs */
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
  ],

  /* Emplacement pour les rapports de test, screenshots, etc. */
  outputDir: 'test-results/',

});