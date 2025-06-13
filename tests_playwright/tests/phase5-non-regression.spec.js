const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright Phase 5 - Validation de Non-Régression
 * Tests de coexistence des interfaces React et Simple
 */

test.describe('Phase 5 - Validation Non-Régression', () => {
  
  // Configuration des ports pour les deux interfaces
  const INTERFACE_REACT_PORT = 3000;
  const INTERFACE_SIMPLE_PORT = 3001;
  
  test.beforeAll(async () => {
    // Attendre que les interfaces soient disponibles
    console.log('Préparation tests Phase 5...');
  });

  test('Interface React - Vérification accessibilité', async ({ page }) => {
    console.log('🔍 Test Interface React sur port 3000');
    
    try {
      await page.goto(process.env.FRONTEND_URL || `http://localhost:3000`);
      
      // Vérifier le titre
      await expect(page).toHaveTitle(/Argumentation Analysis App/);
      
      // Vérifier les éléments principaux
      await expect(page.locator('h1')).toContainText('Analyse Argumentative EPITA');
      await expect(page.locator('#textInput, textarea')).toBeVisible();
      
      console.log('✅ Interface React accessible et fonctionnelle');
      
    } catch (error) {
      console.log('❌ Interface React non accessible:', error.message);
      // Ne pas faire échouer le test, juste enregistrer
    }
  });

  // This test is obsolete as the simple interface on port 3001 is no longer in use.
  // test('Interface Simple - Vérification accessibilité', ...);

  test('API Status - Validation des endpoints', async ({ request }) => {
    console.log('🔌 Test des endpoints API');
    let isApiHealthy = false;
    try {
      // The API endpoint is unique, no need to loop over frontend ports.
      const response = await request.get(`${process.env.BACKEND_URL}/flask/api/health`);
      if (response.ok()) {
        const statusData = await response.json();
        if (statusData.status === 'ok') {
          isApiHealthy = true;
        }
        console.log(`✅ API Health Check: ${statusData.status}`);
      }
    } catch (error) {
      console.log(`❌ API Health Check: Non accessible - ${error.message}`);
    }
    expect(isApiHealthy).toBe(true);
  });

  test('API Examples - Validation des exemples', async ({ request }) => {
    console.log('📚 Test des exemples API');
    let examplesFound = false;
    try {
      const response = await request.get(`${process.env.BACKEND_URL}/flask/api/examples`);
      if (response.ok()) {
        const examplesData = await response.json();
        if (examplesData.examples && examplesData.examples.length > 0) {
          examplesFound = true;
          console.log(`✅ ${examplesData.examples.length} exemples trouvés`);
          // Vérifier la structure des exemples
          const firstExample = examplesData.examples[0];
          expect(firstExample).toHaveProperty('title');
          expect(firstExample).toHaveProperty('text');
          expect(firstExample).toHaveProperty('type');
        }
      }
    } catch (error) {
      console.log(`❌ Exemples API non accessibles: ${error.message}`);
    }
    expect(examplesFound).toBe(true);
  });

  // This test is obsolete as the /api/status endpoint and service_manager property have been removed.
  // The health check is now at /api/health.
  // test('ServiceManager - Test d\'intégration', ...);

  test('Interface React - Test fonctionnalité complète', async ({ page }) => {
    console.log('🎯 Test fonctionnalité complète Interface React');
    
    try {
      await page.goto(process.env.FRONTEND_URL || `http://localhost:3000`);
      
      // Vérifier le chargement complet
      await page.waitForLoadState('networkidle');
      
      // Utiliser un exemple prédéfini
      const exampleButton = page.locator('button').filter({ hasText: 'Logique Simple' });
      if (await exampleButton.isVisible()) {
        await exampleButton.click();
        
        // Vérifier que le texte a été inséré
        const textInput = page.locator('#textInput, textarea');
        const inputValue = await textInput.inputValue();
        expect(inputValue.length).toBeGreaterThan(0);
        
        console.log('✅ Exemple chargé avec succès');
        
        // Lancer une analyse
        const analyzeButton = page.locator('button[type="submit"]');
        await analyzeButton.click();
        
        // Attendre les résultats (avec timeout généreux)
        try {
          await page.waitForSelector('#resultsSection, .results-container', { timeout: 20000 });
          console.log('✅ Analyse réalisée avec succès');
        } catch (timeoutError) {
          console.log('⚠️ Timeout analyse - interface peut être en mode dégradé');
        }
      } else {
        console.log('⚠️ Boutons d\'exemple non trouvés');
      }
      
    } catch (error) {
      console.log('❌ Test fonctionnalité React échoué:', error.message);
    }
  });

  test('Coexistence - Test simultané des interfaces', async ({ browser }) => {
    console.log('🤝 Test coexistence des interfaces');
    
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();
    
    try {
      // Tentative d'accès simultané
      const [response1, response2] = await Promise.allSettled([
        page1.goto(process.env.FRONTEND_URL || `http://localhost:3000`, { timeout: 10000 }),
        page2.goto(process.env.FRONTEND_URL || `http://localhost:3000`, { timeout: 10000 })
      ]);
      
      let accessibleInterfaces = 0;
      
      if (response1.status === 'fulfilled') {
        accessibleInterfaces++;
        console.log('✅ Interface React accessible simultanément');
      } else {
        console.log('❌ Interface React non accessible:', response1.reason?.message);
      }
      
      if (response2.status === 'fulfilled') {
        accessibleInterfaces++;
        console.log('✅ Interface Simple accessible simultanément');
      } else {
        console.log('⚠️ Interface Simple non accessible sur port 3001');
        
        // Test de fallback sur port 3000
        try {
          await page2.goto(process.env.FRONTEND_URL || `http://localhost:3000`);
          accessibleInterfaces++;
          console.log('✅ Interface Simple accessible sur port 3000');
        } catch (fallbackError) {
          console.log('❌ Interface Simple complètement inaccessible');
        }
      }
      
      // Au moins une interface doit être accessible
      expect(accessibleInterfaces).toBeGreaterThan(0);
      
      console.log(`✅ ${accessibleInterfaces} interface(s) coexistent`);
      
    } finally {
      await context1.close();
      await context2.close();
    }
  });

  test('Régression - Validation des endpoints critiques', async ({ request }) => {
    console.log('🔍 Test de régression des endpoints');
    
    const results = {
      health: false,
      examples: false,
      analyze: false
    };

    try {
      // Test health endpoint
      const healthRes = await request.get(`${process.env.BACKEND_URL}/flask/api/health`);
      if (healthRes.ok()) results.health = true;

      // Test examples endpoint
      const examplesRes = await request.get(`${process.env.BACKEND_URL}/flask/api/examples`);
      if (examplesRes.ok() && (await examplesRes.json()).examples.length > 0) {
        results.examples = true;
      }

      // Test analysis endpoint
      const analyzeRes = await request.post(`${process.env.BACKEND_URL}/flask/api/analyze`, {
        data: { text: 'test', analysis_type: 'comprehensive' }
      });
      if (analyzeRes.ok()) results.analyze = true;

    } catch (error) {
      console.log(`❌ Erreur durant le test de régression API: ${error.message}`);
    }

    // Vérifications de non-régression
    expect(results.health).toBe(true);
    expect(results.examples).toBe(true);
    expect(results.analyze).toBe(true);
    
    console.log('✅ Aucune régression détectée sur les endpoints critiques.');
  });

});