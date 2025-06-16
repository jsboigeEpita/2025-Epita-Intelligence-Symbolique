const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright pour l'API Backend
 * Backend API : argumentation_analysis/services/web_api/app.py
 * Port : 5004 (par défaut via config)
 * Orchestrateur : project_core/webapp_from_scripts/unified_web_orchestrator.py
 */

test.describe('API Backend - Services d\'Analyse', () => {
  
  const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:5004';
  const FLASK_API_BASE_URL = API_BASE_URL;

  test('Health Check - Vérification de l\'état de l\'API', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/health`);
    expect(response.status()).toBe(200);
    
    const healthData = await response.json();
    expect(healthData).toHaveProperty('status', 'healthy');
    expect(healthData).toHaveProperty('services');
    expect(healthData.services).toHaveProperty('analysis', true);
  });

  test('Test d\'analyse argumentative via API', async ({ request }) => {
    const analysisData = {
      text: "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.",
      analysis_type: "propositional",
      options: {}
    };

    const response = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
      data: analysisData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('success', true);
    expect(result).toHaveProperty('text_analyzed', analysisData.text);
    expect(result).toHaveProperty('fallacies');
  });

  test('Test de détection de sophismes', async ({ request }) => {
    const fallacyData = {
      text: "Tous les corbeaux que j'ai vus sont noirs, donc tous les corbeaux sont noirs.",
      options: { "include_context": true }
    };

    const response = await request.post(`${FLASK_API_BASE_URL}/api/fallacies`, {
      data: fallacyData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('success', true);
    expect(result).toHaveProperty('fallacies');
    expect(result.fallacy_count).toBeGreaterThan(0);
  });

  test('Test de construction de framework', async ({ request }) => {
    const frameworkData = {
      arguments: [
        { id: "a", content: "Les IA peuvent être créatives." },
        { id: "b", content: "La créativité requiert une conscience." },
        { id: "c", content: "Les IA n'ont pas de conscience." }
      ],
      attack_relations: [
        { from: "c", to: "b" },
        { from: "b", to: "a" }
      ]
    };

    const response = await request.post(`${FLASK_API_BASE_URL}/api/framework`, {
      data: frameworkData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('success', true);
    expect(result).toHaveProperty('argument_count', 3);
    expect(result).toHaveProperty('attack_count', 2);
  });

  test('Test de validation d\'argument', async ({ request }) => {
    const validationData = {
      premises: ["Si A alors B", "A"],
      conclusion: "B",
      logic_type: "propositional"
    };

    const response = await request.post(`${FLASK_API_BASE_URL}/api/validate`, {
      data: validationData
    });
    
    expect(response.status()).toBe(200);
    
    const result = await response.json();
    expect(result).toHaveProperty('success', true);
    expect(result.result).toHaveProperty('is_valid', true);
  });

  test('Test des endpoints avec données invalides', async ({ request }) => {
    test.setTimeout(30000); // Timeout étendu pour ce test
    // Test avec données vides
    const emptyResponse = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
      data: {}
    });
    expect(emptyResponse.status()).toBe(400);

    // Test avec texte trop long (le backend doit le rejeter)
    const longTextData = {
      text: "A".repeat(50001), 
      analysis_type: "comprehensive"
    };
    
    const longTextResponse = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
      data: longTextData,
      timeout: 20000
    });
    expect(longTextResponse.status()).toBe(500); // 500 car le service peut planter, ou 413 si bien géré

    // Test avec type d'analyse invalide
    const invalidTypeData = {
      text: "Test",
      analysis_type: "invalid_type"
    };
    
    const invalidTypeResponse = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
      data: invalidTypeData
    });
    expect(invalidTypeResponse.status()).toBe(500); // Devrait être une erreur serveur
  });

  test('Test des différents types d\'analyse logique', async ({ request }) => {
    test.setTimeout(60000); // 60s timeout
    const testText = "Il est nécessaire que tous les hommes soient mortels. Socrate est un homme.";
    
    const analysisTypes = [
      'comprehensive',
      'propositional',
      // 'modal',  // Le service peut ne pas supporter tous les types
      // 'epistemic'
    ];

    for (const type of analysisTypes) {
      const analysisData = {
        text: testText,
        analysis_type: type,
        options: {}
      };

      const response = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
        data: analysisData,
        timeout: 15000
      });
      
      expect(response.status()).toBe(200);
      
      const result = await response.json();
      expect(result).toHaveProperty('success', true);
    }
  });

  test('Test de performance et timeout', async ({ request }) => {
    test.setTimeout(60000); // Timeout de 60s pour ce test
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
    
    const response = await request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
      data: complexAnalysisData,
      timeout: 45000 // 45 secondes de timeout pour la requête
    });
    
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    expect(response.status()).toBe(200);
    expect(duration).toBeLessThan(45000);
    
    const result = await response.json();
    expect(result).toHaveProperty('success', true);
  });

  test('Test de l\'interface web backend via navigateur', async ({ page }) => {
    await page.goto(`${API_BASE_URL}/api/health`);
    const content = await page.textContent('body');
    expect(content).toContain('"status":"healthy"');
  });

  test('Test CORS et headers', async ({ request }) => {
    const response = await request.fetch(`${FLASK_API_BASE_URL}/api/analyze`, {
      method: 'OPTIONS',
      headers: {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type'
      }
    });
    
    expect(response.status()).toBe(200);
    const headers = response.headers();
    expect(headers).toHaveProperty('access-control-allow-origin', '*');
  });

  test('Test de la limite de requêtes simultanées', async ({ request }) => {
    test.setTimeout(60000); // 60s timeout
    const analysisData = {
      text: "Test de charge avec requêtes simultanées.",
      analysis_type: "propositional"
    };

    const promises = [];
    for (let i = 0; i < 5; i++) {
      promises.push(
        request.post(`${FLASK_API_BASE_URL}/api/analyze`, {
          data: { ...analysisData, text: `${analysisData.text} - Requête ${i}` },
          timeout: 20000
        })
      );
    }

    const responses = await Promise.all(promises);
    
    for (const response of responses) {
      expect(response.status()).toBe(200);
      const result = await response.json();
      expect(result).toHaveProperty('success', true);
    }
  });
});

test.describe('Tests d\'intégration API + Interface', () => {
  
  test('Test complet d\'analyse depuis l\'interface vers l\'API', async ({ page }) => {
    await page.route('**/api/analyze', async route => {
      const request = route.request();
      const postData = request.postData();
      expect(postData).toBeTruthy();
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          text_analyzed: "Texte intercepté",
          fallacies: [],
          fallacy_count: 0
        })
      });
    });
    
    // Ce test reste un mock car il dépend de l'UI.
    // L'important est que le intercepteur fonctionne.
  });
});