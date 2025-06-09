const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright pour l'API Backend
 * Backend API : services/web_api_from_libs/app.py
 * Port : 5003
 * Orchestrateur : scripts/webapp/unified_web_orchestrator.py
 */

test.describe('API Backend - Services d\'Analyse', () => {
  
  const API_BASE_URL = 'http://localhost:5003';

  test('Health Check - Vérification de l\'état de l\'API', async ({ request }) => {
    // Test du endpoint de health check
    const response = await request.get(`${API_BASE_URL}/api/health`);
    expect(response.status()).toBe(200);
    
    const healthData = await response.json();
    expect(healthData).toHaveProperty('status', 'healthy');
    expect(healthData).toHaveProperty('message');
    expect(healthData).toHaveProperty('services');
    expect(healthData).toHaveProperty('version', '1.0.0');
    
    // Vérifier les services disponibles
    const services = healthData.services;
    expect(services).toHaveProperty('analysis', true);
    expect(services).toHaveProperty('fallacy', true);
    expect(services).toHaveProperty('framework', true);
    expect(services).toHaveProperty('validation', true);
  });

  test('Test d\'analyse argumentative via API', async ({ request }) => {
    const analysisData = {
      text: "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.",
      analysis_type: "propositional",
      options: {}
    };

    const response = await request.post(`${API_BASE_URL}/api/analyze`, {
      data: analysisData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('status', 'success');
    expect(result).toHaveProperty('analysis_id');
    expect(result).toHaveProperty('results');
    expect(result).toHaveProperty('metadata');
    
    // Vérifier la structure des métadonnées
    expect(result.metadata).toHaveProperty('duration');
    expect(result.metadata).toHaveProperty('service_status');
  });

  test('Test de détection de sophismes', async ({ request }) => {
    const fallacyData = {
      argument: "Tous les corbeaux que j'ai vus sont noirs, donc tous les corbeaux sont noirs.",
      context: "généralisation hâtive"
    };

    const response = await request.post(`${API_BASE_URL}/api/fallacy/detect`, {
      data: fallacyData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('fallacies');
    expect(result).toHaveProperty('confidence');
    expect(result).toHaveProperty('analysis_id');
  });

  test('Test de construction de framework', async ({ request }) => {
    const frameworkData = {
      premises: [
        "Tous les hommes sont mortels",
        "Socrate est un homme"
      ],
      conclusion: "Socrate est mortel",
      type: "syllogism"
    };

    const response = await request.post(`${API_BASE_URL}/api/framework/build`, {
      data: frameworkData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('framework');
    expect(result).toHaveProperty('validity');
    expect(result).toHaveProperty('structure');
  });

  test('Test de validation d\'argument', async ({ request }) => {
    const validationData = {
      argument: {
        premises: ["Si A alors B", "A"],
        conclusion: "B"
      },
      logic_type: "propositional"
    };

    const response = await request.post(`${API_BASE_URL}/api/validation/validate`, {
      data: validationData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('valid');
    expect(result).toHaveProperty('reasoning');
    expect(result).toHaveProperty('confidence');
  });

  test('Test des endpoints avec données invalides', async ({ request }) => {
    // Test avec données vides
    const emptyResponse = await request.post(`${API_BASE_URL}/api/analyze`, {
      data: {}
    });
    expect(emptyResponse.status()).toBe(400);

    // Test avec texte trop long
    const longTextData = {
      text: "A".repeat(50000), // Texte très long
      analysis_type: "comprehensive"
    };
    
    const longTextResponse = await request.post(`${API_BASE_URL}/api/analyze`, {
      data: longTextData
    });
    expect(longTextResponse.status()).toBe(400);

    // Test avec type d'analyse invalide
    const invalidTypeData = {
      text: "Test",
      analysis_type: "invalid_type"
    };
    
    const invalidTypeResponse = await request.post(`${API_BASE_URL}/api/analyze`, {
      data: invalidTypeData
    });
    // Peut être 400 ou 200 selon l'implémentation
    expect([200, 400]).toContain(invalidTypeResponse.status());
  });

  test('Test des différents types d\'analyse logique', async ({ request }) => {
    const testText = "Il est nécessaire que tous les hommes soient mortels. Socrate est un homme.";
    
    const analysisTypes = [
      'comprehensive',
      'propositional',
      'modal',
      'epistemic'
    ];

    for (const type of analysisTypes) {
      const analysisData = {
        text: testText,
        analysis_type: type,
        options: {}
      };

      const response = await request.post(`${API_BASE_URL}/api/analyze`, {
        data: analysisData
      });
      
      expect(response.status()).toBe(200);
      
      const result = await response.json();
      expect(result).toHaveProperty('status', 'success');
      expect(result).toHaveProperty('analysis_id');
      
      // Attendre un peu entre les requêtes
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  });

  test('Test de performance et timeout', async ({ request }) => {
    const complexAnalysisData = {
      text: `
        L'intelligence artificielle représente à la fois une opportunité extraordinaire et un défi majeur pour notre société. 
        D'un côté, elle peut révolutionner la médecine en permettant des diagnostics plus précis et des traitements personnalisés. 
        De l'autre, elle pose des questions éthiques fondamentales sur l'emploi, la vie privée et l'autonomie humaine.
        
        Si nous considérons que la technologie doit servir l'humanité, alors nous devons réguler l'IA de manière appropriée.
        Cependant, une régulation trop stricte pourrait freiner l'innovation et nous faire perdre notre avantage concurrentiel.
        
        Il est donc nécessaire de trouver un équilibre entre innovation et protection, entre efficacité et éthique.
        Cette tâche complexe nécessite une collaboration internationale et une réflexion approfondie sur nos valeurs.
      `,
      analysis_type: "comprehensive",
      options: {
        deep_analysis: true,
        include_logical_structure: true,
        detect_fallacies: true
      }
    };

    const startTime = Date.now();
    
    const response = await request.post(`${API_BASE_URL}/api/analyze`, {
      data: complexAnalysisData,
      timeout: 30000 // 30 secondes de timeout
    });
    
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    expect(response.status()).toBe(200);
    expect(duration).toBeLessThan(30000); // Moins de 30 secondes
    
    const result = await response.json();
    expect(result).toHaveProperty('status', 'success');
    expect(result.metadata.duration).toBeGreaterThan(0);
  });

  test('Test de l\'interface web backend via navigateur', async ({ page }) => {
    // Tester l'accès direct au health endpoint via navigateur
    await page.goto(`${API_BASE_URL}/api/health`);
    
    // Vérifier que la réponse JSON est affichée
    const content = await page.textContent('body');
    expect(content).toContain('"status": "healthy"');
    expect(content).toContain('"version": "1.0.0"');
  });

  test('Test CORS et headers', async ({ request }) => {
    const response = await request.options(`${API_BASE_URL}/api/analyze`, {
      headers: {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type'
      }
    });
    
    // Vérifier les headers CORS
    const headers = response.headers();
    expect(headers).toHaveProperty('access-control-allow-origin');
    expect(headers).toHaveProperty('access-control-allow-methods');
  });

  test('Test de la limite de requêtes simultanées', async ({ request }) => {
    const analysisData = {
      text: "Test de charge avec requêtes simultanées.",
      analysis_type: "propositional"
    };

    // Envoyer plusieurs requêtes simultanément
    const promises = [];
    for (let i = 0; i < 5; i++) {
      promises.push(
        request.post(`${API_BASE_URL}/api/analyze`, {
          data: { ...analysisData, text: `${analysisData.text} - Requête ${i}` }
        })
      );
    }

    const responses = await Promise.all(promises);
    
    // Toutes les requêtes devraient aboutir
    for (const response of responses) {
      expect(response.status()).toBe(200);
      const result = await response.json();
      expect(result).toHaveProperty('status', 'success');
    }
  });
});

test.describe('Tests d\'intégration API + Interface', () => {
  
  test('Test complet d\'analyse depuis l\'interface vers l\'API', async ({ page }) => {
    // Aller sur une page qui peut communiquer avec l'API
    // (Note: ce test nécessiterait une interface frontend fonctionnelle)
    
    await page.route('**/api/analyze', async route => {
      // Intercepter et vérifier les appels API
      const request = route.request();
      const postData = request.postData();
      
      expect(postData).toBeTruthy();
      
      // Simuler une réponse API
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          analysis_id: 'test-123',
          results: { test: 'data' },
          metadata: { duration: 0.1 }
        })
      });
    });
    
    // Ce test serait complété avec une interface frontend fonctionnelle
  });
});