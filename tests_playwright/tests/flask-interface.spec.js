const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright pour l'Interface Flask Simple
 * Interface Web : interface_web/app.py
 * Port : 3000
 */

test.describe('Interface Flask - Analyse Argumentative', () => {
  
  test.beforeEach(async ({ page }) => {
    // Naviguer vers l'interface Flask
    await page.goto('http://localhost:3000');
  });

  test('Chargement de la page principale', async ({ page }) => {
    // Vérifier le titre de la page
    await expect(page).toHaveTitle(/Argumentation Analysis App/);
    
    // Vérifier la présence des éléments principaux
    await expect(page.locator('h1')).toContainText('Analyse Argumentative EPITA');
    await expect(page.locator('[data-testid="text-input"], #textInput')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Lancer l\'Analyse');
  });

  test('Vérification du statut système', async ({ page }) => {
    // Attendre le chargement du statut
    await page.waitForTimeout(2000);
    
    // Vérifier l'indicateur de statut
    const statusIndicator = page.locator('#statusIndicator, .status-indicator');
    await expect(statusIndicator).toBeVisible();
    
    // Vérifier l'affichage du statut dans le panneau
    const systemStatus = page.locator('#systemStatus');
    await expect(systemStatus).toBeVisible();
    
    // Le statut doit être soit "Opérationnel" soit "Mode Dégradé"
    const statusText = await systemStatus.textContent();
    expect(statusText).toMatch(/(Opérationnel|Mode Dégradé|Système)/);
  });

  test('Interaction avec les exemples prédéfinis', async ({ page }) => {
    // Cliquer sur l'exemple "Logique Simple"
    const logicButton = page.locator('button').filter({ hasText: 'Logique Simple' });
    await logicButton.click();
    
    // Vérifier que le texte a été inséré
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    const inputValue = await textInput.inputValue();
    expect(inputValue).toContain('pleut');
    expect(inputValue).toContain('route');
    
    // Vérifier que le type d'analyse a été ajusté
    const analysisType = page.locator('#analysisType, select[id="analysisType"]');
    const selectedValue = await analysisType.inputValue();
    expect(selectedValue).toBe('propositional');
  });

  test('Test d\'analyse avec texte simple', async ({ page }) => {
    // Saisir un texte d'analyse
    const testText = 'Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.';
    
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    await textInput.fill(testText);
    
    // Sélectionner le type d'analyse
    const analysisType = page.locator('#analysisType, select[id="analysisType"]');
    await analysisType.selectOption('propositional');
    
    // Lancer l'analyse
    const analyzeButton = page.locator('button[type="submit"]');
    await analyzeButton.click();
    
    // Attendre les résultats (timeout plus long car l'analyse peut prendre du temps)
    await page.waitForSelector('#resultsSection, .results-container', { timeout: 15000 });
    
    // Vérifier que les résultats sont affichés
    const resultsSection = page.locator('#resultsSection, .results-container');
    await expect(resultsSection).toBeVisible();
    
    // Vérifier la présence d'éléments de résultats
    const successMessage = page.locator('.alert-success, .success');
    await expect(successMessage).toBeVisible();
    
    // Vérifier que l'ID d'analyse est affiché
    const analysisId = page.locator('text=/ID:.*[a-f0-9]{8}/');
    await expect(analysisId).toBeVisible();
  });

  test('Test du compteur de caractères', async ({ page }) => {
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    const charCount = page.locator('#charCount, .char-count');
    
    // Vérifier l'état initial
    await expect(charCount).toContainText('0');
    
    // Saisir du texte et vérifier la mise à jour
    await textInput.type('Test de caractères');
    await expect(charCount).toContainText('17');
    
    // Tester avec un texte plus long
    const longText = 'A'.repeat(100);
    await textInput.fill(longText);
    await expect(charCount).toContainText('100');
  });

  test('Test de validation des limites', async ({ page }) => {
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    const analyzeButton = page.locator('button[type="submit"]');
    
    // Test avec texte vide
    await textInput.fill('');
    await analyzeButton.click();
    
    // Attendre une alerte ou un message d'erreur
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Veuillez saisir');
      await dialog.accept();
    });
    
    // Test avec texte très long (plus de 10000 caractères)
    const veryLongText = 'A'.repeat(10001);
    await textInput.fill(veryLongText);
    
    const charCount = page.locator('#charCount, .char-count');
    // Le compteur devrait indiquer que c'est trop long
    const countText = await charCount.textContent();
    expect(countText).toContain('10000'); // Limité à 10000
  });

  test('Test des différents types d\'analyse', async ({ page }) => {
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    const analysisType = page.locator('#analysisType, select[id="analysisType"]');
    const analyzeButton = page.locator('button[type="submit"]');
    
    // Texte de test
    const testText = 'Il est nécessaire que tous les hommes soient mortels.';
    await textInput.fill(testText);
    
    // Tester différents types d'analyse
    const analysisTypes = [
      'comprehensive',
      'propositional', 
      'modal',
      'epistemic',
      'fallacy'
    ];
    
    for (const type of analysisTypes) {
      await analysisType.selectOption(type);
      await analyzeButton.click();
      
      // Attendre les résultats
      await page.waitForSelector('#resultsSection, .results-container', { timeout: 15000 });
      
      // Vérifier que l'analyse s'est bien déroulée
      const resultsSection = page.locator('#resultsSection, .results-container');
      await expect(resultsSection).toBeVisible();
      
      // Attendre un peu avant le test suivant
      await page.waitForTimeout(1000);
    }
  });

  test('Test de la récupération d\'exemples via API', async ({ page }) => {
    // Intercepter les appels API
    let examplesLoaded = false;
    
    page.on('response', response => {
      if (response.url().includes('/api/examples')) {
        expect(response.status()).toBe(200);
        examplesLoaded = true;
      }
    });
    
    // Recharger la page pour déclencher l'appel API
    await page.reload();
    
    // Attendre que les exemples soient chargés
    await page.waitForTimeout(3000);
    expect(examplesLoaded).toBe(true);
    
    // Vérifier que les boutons d'exemples sont fonctionnels
    const exampleButtons = page.locator('.example-btn, button[onclick*="loadExample"]');
    const buttonCount = await exampleButtons.count();
    expect(buttonCount).toBeGreaterThan(0);
  });

  test('Test responsive et accessibilité', async ({ page }) => {
    // Test responsive - taille mobile
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Vérifier que les éléments principaux sont toujours visibles
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('#textInput, textarea[id="textInput"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    
    // Test responsive - taille desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Vérifier que le layout s'adapte
    await expect(page.locator('.col-lg-8, .main-container')).toBeVisible();
    
    // Test accessibilité basique
    const textInput = page.locator('#textInput, textarea[id="textInput"]');
    await expect(textInput).toHaveAttribute('maxlength', '10000');
    
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toHaveAttribute('type', 'submit');
  });
});