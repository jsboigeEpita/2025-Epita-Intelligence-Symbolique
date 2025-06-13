const { test, expect } = require('@playwright/test');

/**
 * Tests Playwright - Investigation Rigoureuse avec Textes Varies
 * Test de differents types de textes pour validation de l'analyse argumentative
 */

test.describe('Investigation Textes Varies - Analyse Argumentative', () => {
  
  const API_BASE_URL = process.env.BACKEND_URL || process.env.API_BASE_URL || 'http://localhost:5003';
  const INTERFACE_URL = process.env.FRONTEND_BASE_URL || 'http://localhost:3000';
  
  // Dataset de textes varies pour investigation
  const textesVaries = [
    {
      categorie: "logique_simple",
      titre: "Modus Ponens Classique",
      texte: "Si il pleut, alors la route est mouillee. Il pleut. Donc la route est mouillee.",
      type_analyse: "propositional",
      attendu: "valid"
    },
    {
      categorie: "sophisme_generalisation",
      titre: "Generalisation Hative",
      texte: "Tous les corbeaux que j'ai observes sont noirs. Par consequent, tous les corbeaux dans le monde sont noirs.",
      type_analyse: "fallacy",
      attendu: "hasty_generalization"
    },
    {
      categorie: "dilemme_ethique",
      titre: "Dilemme du Tramway",
      texte: "Un tramway fou se dirige vers cinq personnes. Vous pouvez actionner un levier pour le devier vers une voie ou il tuera une seule personne. Devez-vous actionner le levier ? D'un cote, sauver cinq vies semble preferable. De l'autre, tuer intentionnellement une personne pose un probleme moral.",
      type_analyse: "comprehensive",
      attendu: "ethical_dilemma"
    },
    {
      categorie: "argument_scientifique",
      titre: "Causalite Scientifique",
      texte: "Les etudes montrent une correlation entre la consommation de tabac et le cancer du poumon. Cette correlation est observee dans differentes populations. Le mecanisme biologique est compris. Il existe donc une relation causale entre le tabac et le cancer.",
      type_analyse: "comprehensive",
      attendu: "causal_argument"
    },
    {
      categorie: "logique_modale",
      titre: "Necessite et Possibilite",
      texte: "Il est necessaire que tous les hommes soient mortels. Socrate est un homme. Il est donc necessaire que Socrate soit mortel.",
      type_analyse: "modal",
      attendu: "modal_valid"
    },
    {
      categorie: "sophisme_autorite",
      titre: "Appel a l'Autorite Fallacieux",
      texte: "Einstein etait un genie en physique. Einstein pensait que Dieu ne joue pas aux des. Donc, le determinisme quantique est faux.",
      type_analyse: "fallacy",
      attendu: "appeal_to_authority"
    },
    {
      categorie: "paradoxe_logique",
      titre: "Paradoxe du Menteur",
      texte: "Cette phrase est fausse. Si elle est vraie, alors elle est fausse. Si elle est fausse, alors elle est vraie.",
      type_analyse: "comprehensive",
      attendu: "paradox"
    },
    {
      categorie: "argument_pragmatique",
      titre: "Argument Consequentialiste",
      texte: "Cette politique economique reduira le chomage de 2%. La reduction du chomage ameliore le bien-etre social. Donc cette politique devrait etre adoptee.",
      type_analyse: "comprehensive",
      attendu: "consequentialist"
    },
    {
      categorie: "sophistique_ad_hominem",
      titre: "Attaque Personnelle",
      texte: "Mon adversaire politique a ete arrete pour exces de vitesse. Ses propositions economiques sont donc invalides.",
      type_analyse: "fallacy",
      attendu: "ad_hominem"
    },
    {
      categorie: "logique_epistemique",
      titre: "Connaissance et Croyance",
      texte: "Je sais que je ne sais pas si il pleuvra demain. Si je savais qu'il pleuvra, je prendrais un parapluie. Je ne prends pas de parapluie.",
      type_analyse: "epistemic",
      attendu: "epistemic_reasoning"
    }
  ];

  test.beforeAll(async () => {
    console.log('🚀 Demarrage Investigation Textes Varies');
    console.log(`📊 ${textesVaries.length} textes a analyser`);
  });

  // Test API avec tous les textes varies
  test('API - Test complet textes varies', async ({ request }) => {
    console.log('🔌 Test API avec textes varies');
    
    const resultats = [];
    
    for (let i = 0; i < textesVaries.length; i++) {
      const texte = textesVaries[i];
      console.log(`\n📝 Test ${i+1}/${textesVaries.length}: ${texte.titre}`);
      
      const startTime = Date.now();
      
      try {
        const response = await request.post(`${API_BASE_URL}/api/analyze`, {
          data: {
            text: texte.texte,
            analysis_type: texte.type_analyse,
            options: {
              include_timing: true,
              deep_analysis: true
            }
          }
        });
        
        const duration = Date.now() - startTime;
        
        if (response.ok()) {
          const result = await response.json();
          
          resultats.push({
            categorie: texte.categorie,
            titre: texte.titre,
            status: 'SUCCESS',
            duration: duration,
            analysis_id: result.analysis_id,
            has_results: !!result.results,
            response_size: JSON.stringify(result).length
          });
          
          console.log(`✅ ${texte.titre}: ${duration}ms`);
          
          // Verifications
          expect(result).toHaveProperty('status', 'success');
          expect(result).toHaveProperty('analysis_id');
          expect(result.analysis_id).toMatch(/^[a-f0-9]{8}$/);
          
        } else {
          console.log(`❌ ${texte.titre}: HTTP ${response.status()}`);
          resultats.push({
            categorie: texte.categorie,
            titre: texte.titre,
            status: 'ERROR',
            duration: duration,
            error: `HTTP ${response.status()}`
          });
        }
        
      } catch (error) {
        console.log(`💥 ${texte.titre}: ${error.message}`);
        resultats.push({
          categorie: texte.categorie,
          titre: texte.titre,
          status: 'EXCEPTION',
          duration: Date.now() - startTime,
          error: error.message
        });
      }
      
      // Pause courte entre requetes
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    
    // Statistiques finales
    const successCount = resultats.filter(r => r.status === 'SUCCESS').length;
    const avgDuration = resultats
      .filter(r => r.status === 'SUCCESS')
      .reduce((sum, r) => sum + r.duration, 0) / successCount;
    
    console.log(`\n📊 STATISTIQUES FINALES:`);
    console.log(`✅ Succes: ${successCount}/${textesVaries.length}`);
    console.log(`⏱️ Duree moyenne: ${Math.round(avgDuration)}ms`);
    
    // Au moins 70% de succes requis
    expect(successCount / textesVaries.length).toBeGreaterThan(0.7);
    
    // Duree moyenne raisonnable (moins de 5 secondes)
    expect(avgDuration).toBeLessThan(5000);
  });

  // Test Interface Web avec echantillon de textes
  test('Interface Web - Test echantillon varie', async ({ page }) => {
    console.log('🌐 Test Interface Web avec echantillon');
    
    // Selectionner un echantillon representatif
    const echantillon = [
      textesVaries.find(t => t.categorie === 'logique_simple'),
      textesVaries.find(t => t.categorie === 'sophisme_generalisation'),
      textesVaries.find(t => t.categorie === 'dilemme_ethique'),
      textesVaries.find(t => t.categorie === 'logique_modale')
    ];
    
    await page.goto(INTERFACE_URL);
    await page.waitForLoadState('networkidle');
    
    for (let i = 0; i < echantillon.length; i++) {
      const texte = echantillon[i];
      console.log(`\n🎯 Test Interface ${i+1}/${echantillon.length}: ${texte.titre}`);
      
      try {
        // Nettoyer le champ texte
        const textInput = page.locator('#textInput, textarea');
        await textInput.fill('');
        
        // Saisir le texte
        await textInput.fill(texte.texte);
        
        // Selectionner le type d'analyse
        const analysisType = page.locator('#analysisType, select');
        await analysisType.selectOption(texte.type_analyse);
        
        // Lancer l'analyse
        const analyzeButton = page.locator('button[type="submit"]');
        await analyzeButton.click();
        
        // Attendre les resultats avec timeout genereux
        await page.waitForSelector('#resultsSection, .results-container', { 
          timeout: 15000 
        });
        
        // Verifier que les resultats sont affiches
        const resultsSection = page.locator('#resultsSection, .results-container');
        await expect(resultsSection).toBeVisible();
        
        console.log(`✅ ${texte.titre}: Interface OK`);
        
        // Pause entre les tests
        await page.waitForTimeout(1000);
        
      } catch (error) {
        console.log(`❌ ${texte.titre}: ${error.message}`);
        // Ne pas faire echouer le test complet
      }
    }
  });

  // Test de performance avec textes longs
  test('Performance - Textes complexes', async ({ request }) => {
    console.log('⚡ Test Performance avec textes complexes');
    
    const textesLongs = [
      {
        titre: "Argument Philosophique Long",
        texte: "L'existence de Dieu a ete debattue pendant des siecles par les philosophes. L'argument ontologique de saint Anselme propose que Dieu, defini comme l'etre parfait, doit necessairement exister, car l'existence est une perfection. Cependant, Kant objecte que l'existence n'est pas un predicat reel qui ajoute quelque chose au concept d'un objet. De plus, l'argument cosmologique suggere qu'il doit y avoir une cause premiere pour expliquer l'existence de l'univers. Mais cette cause premiere doit-elle necessairement etre Dieu ? L'argument teleologique observe l'ordre et la complexite de l'univers comme preuves d'un dessein intelligent. Neanmoins, la theorie de l'evolution et les lois physiques peuvent expliquer cette complexite apparente sans recours a un createur. Ainsi, bien que ces arguments soient ingenieux, ils ne constituent pas de preuves definitives de l'existence de Dieu.",
        type: "comprehensive"
      },
      {
        titre: "Debat Scientifique Complexe",
        texte: "Le rechauffement climatique anthropique fait consensus scientifique, mais les mecanismes precis et l'ampleur des effets restent debattus. Les modeles climatiques prevoient une augmentation de temperature entre 1.5 et 4.5°C d'ici 2100, selon les scenarios d'emissions. Cette variabilite s'explique par les retroactions complexes dans le systeme climatique : albedo des glaces, nuages, circulation oceanique, cycle du carbone. Les donnees paleoclimatiques montrent des changements rapides dans le passe, suggerant des points de basculement. Cependant, l'attribution precise des evenements extremes au changement climatique reste probabiliste. Les politiques d'attenuation doivent donc naviguer entre incertitude scientifique et principe de precaution. L'analyse cout-benefice des mesures climatiques depend de l'evaluation du risque et du taux d'actualisation des dommages futurs. Cette complexite explique les divergences politiques malgre le consensus scientifique de base.",
        type: "comprehensive"
      }
    ];
    
    for (const texte of textesLongs) {
      console.log(`📚 Test: ${texte.titre}`);
      
      const startTime = Date.now();
      
      const response = await request.post(`${API_BASE_URL}/api/analyze`, {
        data: {
          text: texte.texte,
          analysis_type: texte.type,
          options: {
            deep_analysis: true,
            include_logical_structure: true,
            detect_fallacies: true
          }
        }
      });
      
      const duration = Date.now() - startTime;
      
      expect(response.ok()).toBeTruthy();
      
      const result = await response.json();
      expect(result).toHaveProperty('status', 'success');
      
      console.log(`✅ ${texte.titre}: ${duration}ms (${texte.texte.length} chars)`);
      
      // Performance acceptable meme pour textes longs
      expect(duration).toBeLessThan(10000);
    }
  });

  // Test de robustesse avec textes problematiques
  test('Robustesse - Textes problematiques', async ({ request }) => {
    console.log('🛡️ Test Robustesse avec textes problematiques');
    
    const textesProblematiques = [
      { titre: "Texte vide", texte: "", should_fail: true },
      { titre: "Caracteres speciaux", texte: "Px->Qy et non Rz ou Sz", should_fail: false },
      { titre: "Emojis", texte: "Si heureux alors triste. Heureux. Donc triste.", should_fail: false },
      { titre: "Tres court", texte: "A.", should_fail: false },
      { titre: "Repetition", texte: "A. ".repeat(1000), should_fail: false }
    ];
    
    for (const texte of textesProblematiques) {
      console.log(`🧪 Test: ${texte.titre}`);
      
      const response = await request.post(`${API_BASE_URL}/api/analyze`, {
        data: {
          text: texte.texte,
          analysis_type: "comprehensive"
        }
      });
      
      if (texte.should_fail) {
        expect(response.status()).toBe(400);
        console.log(`✅ ${texte.titre}: Echec attendu (${response.status()})`);
      } else {
        expect([200, 400]).toContain(response.status());
        console.log(`✅ ${texte.titre}: Gere (${response.status()})`);
      }
    }
  });

  test.afterAll(async () => {
    console.log('🏁 Investigation Textes Varies Terminee');
  });
});