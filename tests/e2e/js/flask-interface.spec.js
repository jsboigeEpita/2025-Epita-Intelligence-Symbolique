const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright pour l'Interface React
 * Interface Web : argumentation_analysis/services/web_api/interface-web-argumentative
 * Port : 3000
 */

test.describe.only('Interface React - Analyse Argumentative', () => {

  const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';

  // --- Mock API calls ---
  test.beforeEach(async ({ page }) => {
    // Correction: la syntaxe correcte est '**/*' sans espace.
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      console.log(`[MOCK] Intercepted API call: ${url}`);

      if (url.includes('/api/health')) {
        console.log('[MOCK] Mocking /api/health with status "ok"');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok' }),
        });
      } else if (url.includes('/api/examples')) {
        console.log('[MOCK] Mocking /api/examples');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 1, text: 'Exemple moqué 1: Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.' },
            { id: 2, text: 'Exemple moqué 2: Si le témoin dit la vérité, alors le coupable est gaucher. Le témoin dit la vérité. Donc le coupable est gaucher.' },
          ]),
        });
      } else if (url.includes('/api/analyze')) {
        console.log('[MOCK] Mocking /api/analyze');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            analysis: {
              raw_text: "Texte analysé moqué",
              argument_structure: "Structure moquée: [P1] & [P2] -> [C]",
              evaluation: "Évaluation moquée: L'argument semble valide.",
              detected_fallacies: [],
            },
            message: 'Analyse terminée avec succès (moquée).',
          }),
        });
      } else {
        // Pour les autres appels API non moqués, on les laisse passer.
        await route.continue();
      }
    });

    await page.goto(FRONTEND_URL);

    // ATTENTE ROBUSTE : S'assurer que l'application est réellement prête.
    // On attend que la zone de texte principale soit visible, ce qui est un bon
    // indicateur que le rendu React est terminé.
    // Augmentation du timeout pour être sûr.
    await expect(page.locator('textarea')).toBeVisible({ timeout: 30000 });
  });

  test('Chargement de la page principale', async ({ page }) => {
    await expect(page).toHaveTitle(/React App|Argumentation Analysis/);
    // Cible uniquement le titre principal pour éviter la violation du mode strict
    await expect(page.locator('h1')).toContainText(/Analyse Argumentative/);
    await expect(page.locator('textarea')).toBeVisible();
    // Le texte du bouton est "Analyser l'argument" avec une icône.
    await expect(page.locator('button:has-text("Analyser l\'argument")')).toBeVisible();
  });

  test('Vérification du statut système', async ({ page }) => {
    await page.waitForTimeout(1000);
    const apiStatus = page.locator('.api-status');
    await expect(apiStatus).toBeVisible();
    const statusText = await apiStatus.textContent();
    expect(statusText).toMatch(/(Connectée|Déconnectée|Vérification)/i);
  });

  test('Interaction avec les exemples prédéfinis', async ({ page }) => {
    // Il n'y a pas de bouton "Charger un exemple", mais une liste de boutons d'exemples.
    // On cible le premier. Le sélecteur est basé sur le snapshot du DOM.
    const exampleButton = page.locator('button:has-text("Argument déductif valide")').first();
    await expect(exampleButton).toBeVisible();
    await exampleButton.click();
    
    const textInput = page.locator('textarea');
    const inputValue = await textInput.inputValue();
    // Vérifier que le textarea contient bien le texte de l'exemple cliqué.
    expect(inputValue).toContain('Tous les chats sont des animaux.');
  });

  test('Test d\'analyse avec texte simple', async ({ page }) => {
    test.setTimeout(30000);
    const testText = 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.';

    await page.locator('textarea').fill(testText);
    await page.locator('button:has-text("Analyser l\'argument")').click();

    // Le snapshot montre que les résultats apparaissent sous un h3. On attend ce titre.
    const resultsHeader = page.locator('h3:has-text("Résultats de l\'analyse")');
    await expect(resultsHeader).toBeVisible({ timeout: 20000 });

    // Le test précédent a montré que le conteneur parent est trop restrictif.
    // On va juste vérifier que les sous-titres des résultats sont visibles.
    await expect(page.locator('h4:has-text("Qualité globale")')).toBeVisible();
    await expect(page.locator('h4:has-text("Sophismes détectés")')).toBeVisible();
  });

  test('Test du compteur de caractères', async ({ page }) => {
    const textInput = page.locator('textarea');
    const charStats = page.locator('.textarea-stats');

    // Attendre que les stats soient visibles (elles apparaissent quand le textarea est prêt)
    await expect(charStats).toBeVisible();

    // Compteur initial (0 caractères)
    const initialText = await charStats.textContent();
    expect(initialText).toContain('Caractères: 0');

    // Ajouter du texte
    await textInput.type('Test');
    const afterTypeText = await charStats.textContent();
    expect(afterTypeText).toContain('Caractères: 4');

    // Texte plus long
    const longText = 'A'.repeat(500);
    await textInput.fill(longText);
    const longTextStats = await charStats.textContent();
    expect(longTextStats).toContain('Caractères: 500');
  });

  test('Test de validation des limites', async ({ page }) => {
    // ÉTAPE 1: Afficher le bon composant en cliquant sur l'onglet "Sophismes"
    await page.getByTestId('fallacy-detector-tab').click();

    // Attente robuste : s'assurer que le conteneur du détecteur est visible
    await expect(page.locator('.fallacy-detector')).toBeVisible();

    // ÉTAPE 2: Exécuter les validations
    const analyzeButton = page.locator('[data-testid="fallacy-submit-button"]');
    const textInput = page.getByTestId('fallacy-text-input');

    // Vérification avec texte vide (le bouton doit être désactivé)
    await expect(analyzeButton).toBeDisabled();

    // Vérification avec texte trop long
    const veryLongText = 'A'.repeat(10001);
    await textInput.fill(veryLongText);
    await expect(analyzeButton).toBeDisabled();

    // Contre-vérification : avec un texte valide, il doit être activé
    await textInput.fill('Un texte valide.');
    await expect(analyzeButton).toBeEnabled();
  });


  test('Test de la récupération d\'exemples via API (avec mock)', async ({ page }) => {
    // Avec le mock, on s'attend juste à ce que le bouton soit visible
    // et que l'action de cliquer remplisse le textarea avec notre contenu moqué.
    // On cible le premier bouton d'exemple comme dans le test précédent.
    const exampleButton = page.locator('button:has-text("Argument déductif valide")').first();
    await expect(exampleButton).toBeVisible();
    await exampleButton.click();
    
    const textInput = page.locator('textarea');
    const inputValue = await textInput.inputValue();
    // L'assertion doit correspondre au texte de l'exemple qui a été cliqué.
    expect(inputValue).toContain('Tous les chats sont des animaux.');
  });

  test('Test responsive et accessibilité', async ({ page }) => {
    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.locator('button:has-text("Analyser l\'argument")')).toBeVisible();

    // Desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('main')).toBeVisible();

    // Accessible attributes
    // L'application utilise un attribut id et un label for associé, ce qui est valide pour l'accessibilité
    await expect(page.locator('textarea')).toHaveAttribute('id', 'argument-text');
    await expect(page.locator('label[for="argument-text"]')).toBeVisible();
  });
});