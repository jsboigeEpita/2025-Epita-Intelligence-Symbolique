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
  workers: 1, // FORCER 1 WORKER POUR LE DEBUG
  /* Reporter à utiliser. Voir https://playwright.dev/docs/test-reporters */
  reporter: [['html', { open: 'never' }], ['list'], ['json', { outputFile: 'report.json' }]],

  /* Configuration partagée pour tous les projets */
  use: {
    /* URL de base pour les actions comme `await page.goto('/')` */
    /* URL de base pour les actions. Utilise FRONTEND_URL pour la cohérence avec le reste des tests. */
    baseURL: process.env.FRONTEND_URL || 'http://localhost:3000',

    /* Options de traçage - C'est la clé pour l'analyse ! */
    trace: 'on', // 'on' pour toujours, 'retain-on-failure' pour les échecs uniquement

    /* Ignorer les erreurs HTTPS (utile pour les environnements de dev locaux) */
    ignoreHTTPSErrors: true,

    /* Contrôle du mode Headless */
    // La valeur est lue depuis la variable d'environnement 'HEADLESS'.
    // `undefined` si non définie, ce qui laisse Playwright décider (souvent headed par défaut).
    // On force 'true' si la variable n'est pas explicitement 'false'.
    // Forcer le mode headless pour le débogage, car la variable d'environnement semble inconsistante.
    headless: true,
  },

  /* Configurer les projets pour les principaux navigateurs */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
/*
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
*/
  ],

  /* Emplacement pour les rapports de test, screenshots, etc. */
  outputDir: 'test-results/',

  // Lancement du serveur web avant les tests
  webServer: [
    {
      command: 'powershell -c "conda activate projet-is; python -m uvicorn argumentation_analysis.services.web_api.app:app --port 5004"',
      url: 'http://127.0.0.1:5004',
      timeout: 120 * 1000,
      reuseExistingServer: false,
    },
    {
      command: 'powershell -c "cd ../../services/web_api/interface-web-argumentative; npm start"',
      url: 'http://localhost:3000',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    },
/*    {
      command: 'powershell -c "cd ../../services/web_api/interface-web-argumentative; $env:PORT=3001; npm start"',
      url: 'http://localhost:3001',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    }*/
  ],
});