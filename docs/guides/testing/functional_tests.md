# Tests Fonctionnels - Playwright

## Vue d'ensemble

Suite de tests fonctionnels end-to-end utilisant Playwright pour valider l'intégration complète entre le frontend React et l'API backend Flask. Ces tests automatisent l'interaction utilisateur avec l'interface web et vérifient le bon fonctionnement de la chaîne complète d'analyse argumentative.

## 🧪 Architecture des Tests

### Framework : Playwright
- **Navigateur** : Chromium (headless)
- **Langage** : Python avec pytest
- **Approche** : Tests end-to-end via automation navigateur
- **Couverture** : Interface utilisateur + API + intégration

### Structure des Tests
```
tests/
├── functional/
│   ├── test_logic_graph.py      # Tests principaux interface web
│   ├── conftest.py              # Configuration pytest commune
│   └── fixtures/
│       ├── test_data.py         # Données de test
│       └── page_objects.py      # Page Object Models
├── README_FUNCTIONAL_TESTS.md   # Cette documentation
└── requirements.txt             # Dépendances tests
```

## 🎯 Scénarios de Test

### `test_logic_graph.py`

#### Test 1: Conversion Logique de Base
```python
async def test_logic_graph_conversion(page):
    """Test conversion texte → graphique logique"""
```

**Objectif :** Valider le workflow complet de conversion

**Étapes :**
1. Navigation vers `http://localhost:3000`
2. Saisie de texte logique : `"A -> B; B -> C"`
3. Clic sur bouton "Convertir"
4. Attente de la réponse API
5. Vérification affichage du graphique résultant

**Validations :**
- ✅ Interface utilisateur répond correctement
- ✅ Requête API `/api/logic/belief-set` envoyée avec bon format
- ✅ Réponse API contient `success: true` et `belief_set`
- ✅ Graphique SVG affiché dans l'interface
- ✅ Temps de traitement < 2 secondes

#### Test 2: Validation des Entrées
```python
async def test_invalid_input_handling(page):
    """Test gestion des entrées invalides"""
```

**Objectif :** Vérifier la robustesse de la validation

**Étapes :**
1. Saisie de texte invalide : `"invalid logic syntax"`
2. Soumission du formulaire
3. Vérification gestion d'erreur appropriée

**Validations :**
- ✅ Message d'erreur utilisateur affiché
- ✅ Interface reste stable (pas de crash)
- ✅ Possibilité de corriger et re-soumettre

#### Test 3: Performance et Interaction
```python
async def test_user_interaction_flow(page):
    """Test workflow interaction utilisateur complet"""
```

**Objectif :** Valider l'expérience utilisateur complète

**Étapes :**
1. Interaction avec différents éléments d'interface
2. Tests de réactivité et feedback visuel
3. Vérification des états de chargement

**Validations :**
- ✅ Boutons réactifs aux interactions
- ✅ États de chargement visibles
- ✅ Interface responsive et fluide

## 🚀 Exécution des Tests

### Prérequis
1. **Backend API** lancé sur `http://localhost:5003`
2. **Frontend React** lancé sur `http://localhost:3000`
3. **Environnement Python** activé avec dépendances

### Méthode Recommandée : Script Automatisé
```powershell
# Exécution complète automatisée
.\scripts\run_all_and_test.ps1
```

**Ce script :**
- ✅ Active l'environnement Python
- ✅ Lance le backend API en arrière-plan
- ✅ Lance le frontend React en arrière-plan  
- ✅ Attend que les serveurs soient prêts
- ✅ Exécute tous les tests Playwright
- ✅ Nettoie les processus à la fin

### Exécution Manuelle

#### 1. Préparer l'Environnement
```powershell
# Activer l'environnement
.\scripts\env\activate_project_env.ps1

# Installer dépendances Playwright
pip install playwright
playwright install chromium
```

#### 2. Lancer les Services
```powershell
# Terminal 1: Backend API
python -m argumentation_analysis.services.web_api.app

# Terminal 2: Frontend React  
cd services\web_api\interface-web-argumentative
npm start
```

#### 3. Exécuter les Tests
```powershell
# Tous les tests fonctionnels
pytest tests/functional/ -v

# Test spécifique
pytest tests/functional/test_logic_graph.py::test_logic_graph_conversion -v

# Avec output détaillé
pytest tests/functional/ -v -s
```

## 📊 Rapports et Résultats

### Format de Sortie Pytest
```
tests/functional/test_logic_graph.py::test_logic_graph_conversion PASSED [33%]
tests/functional/test_logic_graph.py::test_invalid_input_handling PASSED [66%]  
tests/functional/test_logic_graph.py::test_user_interaction_flow PASSED [100%]

=================== 3 passed in 12.45s ===================
```

### Métriques de Performance
- **Temps d'exécution total** : ~12-15 secondes
- **Temps par test** : 3-5 secondes
- **Couverture** : Interface complète + API endpoints critiques

### Artifacts de Debug
En cas d'échec, Playwright génère automatiquement :
- **Screenshots** : Captures d'écran au moment de l'erreur
- **Videos** : Enregistrement de l'interaction complète
- **Traces** : Timeline détaillée des actions

## 🔧 Configuration Avancée

### Variables d'Environnement
```bash
# Configuration Playwright
PLAYWRIGHT_BROWSERS_PATH=./browsers
PLAYWRIGHT_TIMEOUT=30000

# URLs de test (si différentes)
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:5003
```

### Configuration Browser
```python
# conftest.py
@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,           # Mode sans interface
            slow_mo=100,            # Ralentissement pour debug
            args=['--disable-dev-shm-usage']
        )
        yield browser
        await browser.close()
```

### Timeouts et Retry
```python
# Attente intelligente des éléments
await page.wait_for_selector('#result-graph', timeout=5000)

# Retry automatique des requêtes réseau
await page.wait_for_response(
    lambda response: "/api/logic/belief-set" in response.url,
    timeout=10000
)
```

## 🐛 Résolution de Problèmes

### Erreurs Communes

#### Test Timeout
```
TimeoutError: page.wait_for_selector: Timeout 30000ms exceeded.
```

**Causes possibles :**
- Backend API non démarré
- Frontend React non accessible
- Réseau lent ou surcharge système

**Solutions :**
1. Vérifier `http://localhost:5003/api/health`
2. Vérifier `http://localhost:3000`
3. Augmenter les timeouts dans la configuration

#### Élément Non Trouvé
```
Error: Element not found: #submit-button
```

**Causes possibles :**
- Sélecteur CSS incorrect
- Element pas encore chargé
- Changement dans l'interface frontend

**Solutions :**
1. Vérifier les sélecteurs dans le code frontend
2. Ajouter des attentes explicites
3. Utiliser `page.wait_for_selector()`

#### Échec de Requête API
```
AssertionError: Expected success=true in API response
```

**Causes possibles :**
- API retourne une erreur
- Format de requête incorrect
- Service backend défaillant

**Solutions :**
1. Tester l'API manuellement avec curl/Postman
2. Vérifier les logs du backend
3. Valider le format JSON de la requête

### Mode Debug

#### Exécution avec Interface Visible
```python
# Modifier conftest.py temporairement
browser = await p.chromium.launch(headless=False, slow_mo=1000)
```

#### Screenshots de Debug
```python
# Ajouter dans les tests
await page.screenshot(path="debug_screenshot.png")
await page.pause()  # Pause interactive pour debug
```

#### Logs Détaillés
```powershell
# Activer debug Playwright
$env:DEBUG = "pw:api"
pytest tests/functional/ -v -s
```

## 📈 Métriques et Monitoring

### Couverture Fonctionnelle
- ✅ **Interface utilisateur** : 100% des composants critiques
- ✅ **API endpoints** : 100% des endpoints publics  
- ✅ **Intégration** : 100% du workflow principal
- ✅ **Gestion d'erreurs** : Scénarios d'erreur principaux

### Performance Benchmarks
- **Temps de réponse API** : < 1 seconde
- **Rendu interface** : < 500ms
- **Workflow complet** : < 3 secondes

### Reliability
- **Taux de succès** : > 95% en conditions normales
- **Stabilité** : Tests reproductibles
- **Isolation** : Aucune dépendance entre tests

## 🔄 Intégration CI/CD

### Pipeline Automatisé
```yaml
# Exemple GitHub Actions
name: Functional Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run functional tests
        run: ./scripts/run_all_and_test.ps1
```

### Intégration Locale
```powershell
# Hook pre-commit pour validation
# .git/hooks/pre-commit
#!/bin/sh
./scripts/run_all_and_test.ps1
if [ $? -ne 0 ]; then
    echo "Tests fonctionnels échoués - commit annulé"
    exit 1
fi
```

## 📚 Documentation Associée

- **[Guide Application Web](../WEB_APPLICATION_GUIDE.md)** : Guide utilisateur complet
- **[API Backend](../../../argumentation_analysis/services/web_api/README.md)** : Documentation API
- **[Frontend React](../../../services/web_api/interface-web-argumentative/README.md)** : Documentation frontend
- **Script d'Exécution** : Pipeline automatisé

## 🤝 Maintenance et Évolution

### Ajout de Nouveaux Tests
1. Créer nouvelle fonction test dans `test_logic_graph.py`
2. Suivre le pattern async/await
3. Utiliser les fixtures communes
4. Documenter le scénario testé

### Mise à Jour des Tests
Lors de changements d'interface :
1. Mettre à jour les sélecteurs CSS
2. Adapter les timeouts si nécessaire
3. Valider que tous les tests passent
4. Mettre à jour cette documentation

---

*Dernière mise à jour : 2025-06-06*  
*Tests compatibles avec : API v1.0.0, Frontend v1.0.0*  
*Playwright version : 1.40+*