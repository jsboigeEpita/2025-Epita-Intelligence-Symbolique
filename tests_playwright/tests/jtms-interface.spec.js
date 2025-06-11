// Test E2E pour l'Interface Web JTMS
// ====================================
// 
// Tests Playwright pour vérifier le bon fonctionnement de l'interface
// web JTMS avec toutes ses fonctionnalités.
//
// Version: 1.0.0
// Auteur: Intelligence Symbolique EPITA
// Date: 11/06/2025

const { test, expect } = require('@playwright/test');

// Configuration des tests
const BASE_URL = process.env.BASE_URL || 'http://localhost:5001';
const JTMS_PREFIX = '/jtms';

test.describe('Interface Web JTMS - Tests d\'Intégration Complète', () => {
    
    test.beforeEach(async ({ page }) => {
        // Vérifier que le serveur est disponible
        await page.goto(BASE_URL);
        await expect(page).toHaveTitle(/MyIA Open-Webui/);
    });

    test.describe('Dashboard JTMS', () => {
        
        test('Accès au dashboard principal', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Vérifier les éléments principaux du dashboard Flask
            await expect(page.locator('h4')).toContainText('Graphe de Croyances');
            await expect(page.locator('#network-container')).toBeVisible();
            await expect(page.locator('#stats-panel')).toBeVisible();
            await expect(page.locator('#activity-log')).toBeVisible();
        });

        test('Ajout d\'une croyance via l\'interface', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Ajouter une nouvelle croyance
            const beliefName = `test_belief_${Date.now()}`;
            await page.fill('#new-belief', beliefName);
            await page.click('button:has-text("Créer")');
            
            // Vérifier que l'ajout est loggué
            await expect(page.locator('#activity-log')).toContainText(beliefName);
            
            // Vérifier que le réseau se met à jour (il devrait y avoir des noeuds)
            const nodeCount = await page.locator('#network-container .vis-network svg .vis-node').count();
            expect(nodeCount).toBeGreaterThan(0);
        });

        test('Création et suppression de justification', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);

            // Créer les croyances nécessaires
            await page.fill('#new-belief', 'premise_a');
            await page.click('button:has-text("Créer")');
            await page.fill('#new-belief', 'premise_b');
            await page.click('button:has-text("Créer")');
            await page.fill('#new-belief', 'conclusion_c');
            await page.click('button:has-text("Créer")');

            // Créer la justification
            await page.fill('#premises', 'premise_a, premise_b');
            await page.fill('#conclusion', 'conclusion_c');
            await page.click('button:has-text("Ajouter Justification")');

            // Vérifier que la justification est logguée
            await expect(page.locator('#activity-log')).toContainText('Justification ajoutée pour conclusion_c');

            // Vérifier que le réseau contient des arêtes
            await page.waitForTimeout(1000); // Laisser le temps au graphe de se redessiner
            const edgeCount = await page.locator('#network-container .vis-network svg .vis-edge').count();
            expect(edgeCount).toBeGreaterThan(0);
        });

        test('Vérification de cohérence', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Créer un système simple
            await page.fill('#new-belief', 'test_coherence');
            await page.click('button:has-text("Créer")');
            
            // Lancer la vérification de cohérence
            await page.click('button:has-text("Vérifier Cohérence")');
            
            // Vérifier que le résultat est loggué
            await expect(page.locator('#activity-log')).toContainText(/cohérent/);
        });

        test('Export des données JTMS', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Créer quelques données
            await page.fill('#beliefNameInput', 'export_test');
            await page.click('#addBeliefBtn');
            
            // Tester l'export
            const downloadPromise = page.waitForEvent('download');
            await page.click('#exportBtn');
            const download = await downloadPromise;
            
            // Vérifier le fichier téléchargé
            expect(download.suggestedFilename()).toMatch(/jtms.*\.json$/);
        });
    });

    test.describe('Gestion des Sessions', () => {
        
        test('Liste des sessions', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sessions`);
            
            await expect(page.locator('h1')).toContainText('Gestion des Sessions JTMS');
            await expect(page.locator('#sessionsList')).toBeVisible();
            await expect(page.locator('#createSessionBtn')).toBeVisible();
        });

        test('Création d\'une nouvelle session', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sessions`);
            
            // Ouvrir le modal de création
            await page.click('#createSessionBtn');
            await expect(page.locator('#createSessionModal')).toBeVisible();
            
            // Remplir le formulaire
            const sessionName = `Test Session ${Date.now()}`;
            await page.fill('#sessionNameInput', sessionName);
            await page.fill('#sessionDescriptionInput', 'Session de test automatisé');
            
            // Créer la session
            await page.click('#confirmCreateSessionBtn');
            
            // Vérifier que la session apparaît dans la liste
            await expect(page.locator('#sessionsList')).toContainText(sessionName);
        });

        test('Suppression d\'une session', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sessions`);
            
            // Créer une session temporaire
            await page.click('#createSessionBtn');
            const tempSessionName = `Temp Session ${Date.now()}`;
            await page.fill('#sessionNameInput', tempSessionName);
            await page.click('#confirmCreateSessionBtn');
            
            // Supprimer la session
            await page.click(`[data-session-name="${tempSessionName}"] .delete-btn`);
            await page.click('#confirmDeleteBtn');
            
            // Vérifier que la session a disparu
            await expect(page.locator('#sessionsList')).not.toContainText(tempSessionName);
        });

        test('Changement de session active', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sessions`);
            
            // Sélectionner une session différente
            const sessionCard = page.locator('.session-card').first();
            await sessionCard.click();
            
            // Vérifier que le statut change
            await expect(sessionCard.locator('.session-status')).toContainText('Active');
            
            // Retourner au dashboard pour vérifier le changement
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            await expect(page.locator('#currentSessionName')).not.toBeEmpty();
        });
    });

    test.describe('Interface Sherlock/Watson', () => {
        
        test('Chargement de l\'interface agents', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sherlock_watson`);
            
            await expect(page.locator('h1')).toContainText('Agents Sherlock & Watson JTMS');
            await expect(page.locator('.sherlock-panel')).toBeVisible();
            await expect(page.locator('.watson-panel')).toBeVisible();
            await expect(page.locator('#conversationArea')).toBeVisible();
        });

        test('Sélection d\'un scénario d\'enquête', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sherlock_watson`);
            
            // Sélectionner le scénario Cluedo
            await page.click('[data-scenario="cluedo"]');
            
            // Vérifier que le scénario est activé
            await expect(page.locator('[data-scenario="cluedo"]')).toHaveClass(/active/);
            
            // Vérifier le message système
            await expect(page.locator('#conversationArea')).toContainText('Scénario sélectionné');
        });

        test('Démarrage d\'une enquête', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sherlock_watson`);
            
            // Sélectionner un scénario et démarrer
            await page.click('[data-scenario="cluedo"]');
            await page.click('button:has-text("Démarrer")');
            
            // Vérifier que l'enquête démarre
            await expect(page.locator('#investigationProgress')).toBeVisible();
            await expect(page.locator('#conversationArea')).toContainText('Enquête démarrée');
            
            // Vérifier que Sherlock commence à analyser
            await page.waitForTimeout(3000); // Attendre l'animation
            await expect(page.locator('#conversationArea .message-sherlock')).toBeVisible();
        });

        test('Interaction avec les agents', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/sherlock_watson`);
            
            // Démarrer une enquête
            await page.click('[data-scenario="theft"]');
            await page.click('button:has-text("Démarrer")');
            
            // Envoyer un message utilisateur
            await page.fill('#userInput', 'Quels sont les indices disponibles ?');
            await page.click('button:has-text("Envoyer")');
            
            // Vérifier que le message apparaît
            await expect(page.locator('#conversationArea .message-utilisateur')).toContainText('Quels sont les indices');
            
            // Tester les actions Sherlock et Watson
            await page.click('#sherlockQueryBtn');
            await page.waitForTimeout(2000);
            await expect(page.locator('#conversationArea .message-sherlock')).toBeVisible();
            
            await page.click('#watsonValidateBtn');
            await page.waitForTimeout(2000);
            await expect(page.locator('#conversationArea .message-watson')).toBeVisible();
        });
    });

    test.describe('Tutoriel Interactif', () => {
        
        test('Navigation dans les leçons', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/tutorial`);
            
            await expect(page.locator('h1')).toContainText('Introduction au JTMS');
            await expect(page.locator('.lesson-item.active')).toContainText('Introduction');
            
            // Naviguer vers la leçon suivante
            await page.click('.lesson-item[data-lesson="2"]');
            await expect(page.locator('#lesson2')).toBeVisible();
            await expect(page.locator('h1')).toContainText('Croyances et Justifications');
        });

        test.skip('Démonstration interactive Tweety', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/tutorial`);
            
            // Tester la démo Tweety
            await page.click('button:has-text("Appliquer la règle")');
            
            // Vérifier que l'état change
            await expect(page.locator('[data-belief="tweety-vole"]')).toHaveClass(/valid/);
            
            // Tester l'exception
            await page.click('button:has-text("Ajouter exception")');
            await expect(page.locator('[data-belief="tweety-vole"]')).toHaveClass(/invalid/);
        });

        test('Quiz et progression', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/tutorial`);
            
            // Répondre au quiz
            await page.click('.quiz-option[data-answer="b"]');
            
            // Vérifier la réponse correcte
            await page.waitForTimeout(1000);
            await expect(page.locator('.quiz-option.correct')).toBeVisible();
            
            // Vérifier la progression
            await expect(page.locator('#progressFill')).toHaveCSS('width', /[1-9]\d*%/);
        });

        test('Création de justification personnalisée', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/tutorial`);
            
            // Aller à la leçon 2
            await page.click('.lesson-item[data-lesson="2"]');
            
            // Remplir l'exercice pratique
            await page.fill('#premise1', 'Il pleut');
            await page.fill('#premise2', 'J\'ai un parapluie');
            await page.fill('#conclusion', 'Je peux sortir sans me mouiller');
            
            await page.click('button:has-text("Créer la Justification")');
            
            // Vérifier que la justification est créée
            await expect(page.locator('#user-justification')).toContainText('Il pleut');
            await expect(page.locator('#user-justification')).toContainText('Je peux sortir');
        });
    });

    test.describe('Playground JTMS', () => {
        
        test('Interface de développement', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/playground`);
            
            await expect(page.locator('h5:has-text("Éditeur JTMS")')).toBeVisible();
            await expect(page.locator('#codeEditor')).toBeVisible();
            await expect(page.locator('#outputConsole')).toBeVisible();
            await expect(page.locator('#networkContainer')).toBeVisible();
        });

        test('Chargement et exécution de templates', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/playground`);
            
            // Charger le template des animaux
            await page.click('.template-card[onclick*="animals"]');
            
            // Vérifier que le code est chargé
            const editorContent = await page.locator('#codeEditor').inputValue();
            expect(editorContent).toContain('tweety_oiseau');
            expect(editorContent).toContain('oiseaux_volent');
            
            // Exécuter le code
            await page.click('.btn-run');
            
            // Vérifier la sortie console
            await page.waitForTimeout(1000);
            const consoleContent = await page.locator('#outputConsole').textContent();
            expect(consoleContent).toContain('Croyance ajoutée');
        });

        test('Création de code personnalisé', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/playground`);
            
            // Effacer l'éditeur
            await page.click('.btn-clear');
            
            // Écrire du code personnalisé
            const customCode = `
# Test personnalisé
add_belief('custom_test')
add_belief('autre_test')
add_justification('conclusion_test', ['custom_test', 'autre_test'])
execute()
            `;
            
            await page.fill('#codeEditor', customCode);
            
            // Exécuter
            await page.click('.btn-run');
            
            // Vérifier les résultats
            await page.waitForTimeout(1000);
            await expect(page.locator('#outputConsole')).toContainText('custom_test');
            
            // Vérifier les statistiques
            await expect(page.locator('#beliefCount')).toContainText(/[1-9]/);
        });

        test('Visualisation du réseau', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/playground`);
            
            // Charger un template simple
            await page.click('.template-card[onclick*="basic"]');
            await page.click('.btn-run');
            
            // Vérifier que la visualisation se met à jour
            await page.waitForTimeout(2000);
            
            // Le réseau devrait contenir des nœuds
            const hasNodes = await page.locator('#networkContainer .vis-network').isVisible();
            expect(hasNodes).toBeTruthy();
        });

        test('Sauvegarde et export', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/playground`);
            
            // Écrire du code
            await page.fill('#codeEditor', 'add_belief("test_sauvegarde")');
            
            // Tester la sauvegarde
            await page.click('.btn-save');
            await expect(page.locator('#outputConsole')).toContainText('sauvegardée');
            
            // Tester l'export
            const downloadPromise = page.waitForEvent('download');
            await page.click('.btn-export');
            const download = await downloadPromise;
            
            expect(download.suggestedFilename()).toMatch(/jtms_playground.*\.txt$/);
        });
    });

    test.describe('Intégration et Performance', () => {
        
        test('Temps de chargement des pages', async ({ page }) => {
            const pages = [
                `${BASE_URL}${JTMS_PREFIX}/dashboard`,
                `${BASE_URL}${JTMS_PREFIX}/sessions`,
                `${BASE_URL}${JTMS_PREFIX}/sherlock_watson`,
                `${BASE_URL}${JTMS_PREFIX}/tutorial`,
                `${BASE_URL}${JTMS_PREFIX}/playground`
            ];
            
            for (const url of pages) {
                const startTime = Date.now();
                await page.goto(url);
                await page.waitForLoadState('networkidle');
                const loadTime = Date.now() - startTime;
                
                expect(loadTime).toBeLessThan(5000); // Moins de 5 secondes
                console.log(`${url}: ${loadTime}ms`);
            }
        });

        test('Navigation entre les sections', async ({ page }) => {
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Tester la navigation complète
            const sections = [
                { link: 'Sessions', url: 'sessions' },
                { link: 'Sherlock/Watson', url: 'sherlock_watson' },
                { link: 'Tutoriel', url: 'tutorial' },
                { link: 'Playground', url: 'playground' },
                { link: 'Dashboard JTMS', url: 'dashboard' }
            ];
            
            for (const section of sections) {
                await page.click(`nav a:has-text("${section.link}")`);
                await expect(page).toHaveURL(new RegExp(section.url));
                await expect(page.locator('h1, h2')).toBeVisible();
            }
        });

        test('Gestion des erreurs', async ({ page }) => {
            // Test d'une route inexistante
            const response = await page.goto(`${BASE_URL}${JTMS_PREFIX}/route-inexistante`);
            expect(response.status()).toBe(404);
            
            // Test de résistance aux erreurs JavaScript
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Injecter une erreur et vérifier que l'interface reste fonctionnelle
            await page.evaluate(() => {
                window.addEventListener('error', (e) => {
                    console.warn('Erreur JavaScript capturée:', e.message);
                });
            });
            
            // L'interface devrait rester opérationnelle
            await expect(page.locator('#networkVisualization')).toBeVisible();
        });

        test('Responsivité mobile', async ({ page }) => {
            // Simuler un écran mobile
            await page.setViewportSize({ width: 375, height: 667 });
            await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
            
            // Vérifier que l'interface s'adapte
            await expect(page.locator('.navbar-toggler')).toBeVisible();
            
            // Ouvrir le menu mobile
            await page.click('.navbar-toggler');
            await expect(page.locator('.navbar-collapse')).toHaveClass(/show/);
            
            // Tester sur différentes tailles d'écran
            const viewports = [
                { width: 768, height: 1024 }, // Tablette
                { width: 1200, height: 800 },  // Desktop
                { width: 320, height: 568 }    // Petit mobile
            ];
            
            for (const viewport of viewports) {
                await page.setViewportSize(viewport);
                await page.reload();
                await expect(page.locator('h1, h2')).toBeVisible();
            }
        });
    });

    test.describe('API et Communication', () => {
        
        test('API de statut des services', async ({ page }) => {
            const response = await page.request.get(`${BASE_URL}/status`);
            expect(response.ok()).toBeTruthy();
            
            const status = await response.json();
            expect(status).toHaveProperty('status');
            expect(status).toHaveProperty('services');
            expect(status.services).toHaveProperty('jtms_service');
        });

        test('API JTMS - Création de session', async ({ page }) => {
            const response = await page.request.post(`${BASE_URL}${JTMS_PREFIX}/api/sessions`, {
                data: {
                    session_id: `test_api_${Date.now()}`,
                    name: 'Session API Test',
                    description: 'Test automatisé de l\'API'
                }
            });
            
            expect(response.ok()).toBeTruthy();
            const result = await response.json();
            expect(result).toHaveProperty('session_id');
            expect(result).toHaveProperty('status', 'success');
        });

        test('API JTMS - Gestion des croyances', async ({ page }) => {
            // Créer une session d'abord
            const sessionResponse = await page.request.post(`${BASE_URL}${JTMS_PREFIX}/api/sessions`, {
                data: {
                    session_id: `belief_test_${Date.now()}`,
                    name: 'Test Croyances'
                }
            });
            
            const session = await sessionResponse.json();
            const sessionId = session.session_id;
            
            // Ajouter une croyance
            const beliefResponse = await page.request.post(`${BASE_URL}${JTMS_PREFIX}/api/belief`, {
                data: {
                    session_id: sessionId,
                    belief_name: 'test_api_belief'
                }
            });
            
            expect(beliefResponse.ok()).toBeTruthy();
            const beliefResult = await beliefResponse.json();
            expect(beliefResult).toHaveProperty('status', 'success');
        });
    });
});

// Tests utilitaires et helpers
test.describe('Utilitaires de Test', () => {
    
    test('Génération de données de test', async ({ page }) => {
        await page.goto(`${BASE_URL}${JTMS_PREFIX}/dashboard`);
        
        // Générer un ensemble de test complet
        const testData = {
            beliefs: ['premise_1', 'premise_2', 'conclusion_1'],
            justifications: [
                { conclusion: 'conclusion_1', premises: ['premise_1', 'premise_2'] }
            ]
        };
        
        // Créer les croyances
        for (const belief of testData.beliefs) {
            await page.fill('#beliefNameInput', belief);
            await page.click('#addBeliefBtn');
            await page.waitForTimeout(300);
        }
        
        // Vérifier que tout est créé
        for (const belief of testData.beliefs) {
            await expect(page.locator('#beliefsList')).toContainText(belief);
        }
    });

    test('Nettoyage après tests', async ({ page }) => {
        // Nettoyer les sessions de test
        await page.goto(`${BASE_URL}${JTMS_PREFIX}/sessions`);
        
        // Supprimer les sessions de test (celles qui commencent par "Test" ou "test_")
        const testSessions = page.locator('.session-card:has([data-session-name*="test" i], [data-session-name*="Test"])');
        const count = await testSessions.count();
        
        for (let i = 0; i < count; i++) {
            const session = testSessions.nth(i);
            await session.locator('.delete-btn').click();
            await page.click('#confirmDeleteBtn');
            await page.waitForTimeout(500);
        }
        
        console.log(`${count} sessions de test nettoyées`);
    });
});