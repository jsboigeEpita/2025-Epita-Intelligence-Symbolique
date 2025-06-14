const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright pour l'Interface React
 * Interface Web : argumentation_analysis/services/web_api/interface-web-argumentative
 * Port : 3000
 */

test.describe('Interface React - Analyse Argumentative', () => {

  const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
  
  test.beforeEach(async ({ page }) => {
    await page.goto(FRONTEND_URL);
  });

  test('Chargement de la page principale', async ({ page }) => {
    await expect(page).toHaveTitle(/React App|Argumentation Analysis/);
    await expect(page.locator('h1, h2')).toContainText(/Analyse Argumentative/);
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('Vérification du statut système', async ({ page }) => {
    await page.waitForTimeout(1000); 
    const statusIndicator = page.locator('#status-indicator, [data-testid="status-indicator"]');
    await expect(statusIndicator).toBeVisible();
    const statusText = await statusIndicator.textContent();
    expect(statusText).toMatch(/(healthy|issues|unknown)/i);
  });

  test('Interaction avec les exemples prédéfinis', async ({ page }) => {
    const exampleButton = page.locator('button:has-text("Exemple")').first();
    await expect(exampleButton).toBeVisible();
    await exampleButton.click();
    
    const textInput = page.locator('textarea');
    const inputValue = await textInput.inputValue();
    expect(inputValue.length).toBeGreaterThan(10);
  });

  test('Test d\'analyse avec texte simple', async ({ page }) => {
    test.setTimeout(30000);
    const testText = 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.';
    
    await page.locator('textarea').fill(testText);
    await page.locator('select[name="analysisType"]').selectOption('propositional');
    await page.locator('button[type="submit"]').click();

    const resultsSection = page.locator('#results, [data-testid="results-section"]');
    await expect(resultsSection).toBeVisible({ timeout: 20000 });
    
    await expect(resultsSection).toContainText(/Analyse terminée/);
    await expect(resultsSection).toContainText(/Structure de l'argument/);
  });

  test('Test du compteur de caractères', async ({ page }) => {
    const textInput = page.locator('textarea');
    const charCount = page.locator('[data-testid="char-counter"]');
    
    await expect(charCount).toHaveText('0 / 10000');
    
    await textInput.type('Test');
    await expect(charCount).toHaveText('4 / 10000');
    
    const longText = 'A'.repeat(500);
    await textInput.fill(longText);
    await expect(charCount).toHaveText('500 / 10000');
  });

  test('Test de validation des limites', async ({ page }) => {
    const analyzeButton = page.locator('button[type="submit"]');    
    
    // Test avec texte vide, le bouton devrait être désactivé
    await expect(analyzeButton).toBeDisabled();

    // Test avec texte trop long
    const textInput = page.locator('textarea');
    const veryLongText = 'A'.repeat(10001);
    await textInput.fill(veryLongText);

    // Le bouton peut devenir désactivé ou afficher une erreur, on vérifie les deux
    const isButtonDisabled = await analyzeButton.isDisabled();
    if (!isButtonDisabled) {
        // Si le bouton n'est pas désactivé, une erreur devrait être visible
        const errorMessage = page.locator('.error-message, [data-testid="error-message"]');
        await expect(errorMessage).toContainText(/trop long/);
    } else {
        expect(isButtonDisabled).toBe(true);
    }
  });

  test('Test des différents types d\'analyse', async ({ page }) => {
    test.setTimeout(60000);
    const textInput = page.locator('textarea');
    const analysisTypeSelect = page.locator('select[name="analysisType"]');
    const analyzeButton = page.locator('button[type="submit"]');
    
    const testText = 'Il est nécessaire que tous les hommes soient mortels.';
    await textInput.fill(testText);
    
    const analysisTypes = [
      'comprehensive', 'propositional', 'fallacy'
    ];
    
    for (const type of analysisTypes) {
      await analysisTypeSelect.selectOption(type);
      await analyzeButton.click();
      
      const resultsSection = page.locator('#results, [data-testid="results-section"]');
      await expect(resultsSection).toBeVisible({ timeout: 20000 });
      
      await expect(resultsSection).toContainText(/Analyse terminée/, { timeout: 10000 });
    }
  });

  test('Test de la récupération d\'exemples via API', async ({ page }) => {
    let examplesApiCalled = false;
    
    page.on('response', response => {
      if (response.url().includes('/api/examples')) {
        expect(response.status()).toBe(200);
        examplesApiCalled = true;
      }
    });

    await page.reload();
    await page.waitForTimeout(3000);
    expect(examplesApiCalled).toBe(true);
    
    const exampleButton = page.locator('button:has-text("Exemple")').first();
    await expect(exampleButton).toBeVisible();
  });

  test('Test responsive et accessibilité', async ({ page }) => {
    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('h1, h2')).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // Desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('main')).toBeVisible();

    // Accessible attributes
    await expect(page.locator('textarea')).toHaveAttribute('aria-label', /texte à analyser/i);
  });
});