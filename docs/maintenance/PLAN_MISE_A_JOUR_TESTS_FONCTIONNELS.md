# 📋 Plan Détaillé de Mise à Jour des Tests Fonctionnels

## Application Web d'Analyse Argumentative - Intelligence Symbolique 2025

---

## 🎯 **Objectif**

Créer une suite complète de tests fonctionnels Playwright pour valider automatiquement les 6 onglets opérationnels de l'application web avant démonstration, en se concentrant sur les fonctionnalités critiques de chaque composant.

---

## 🔍 **1. Analyse de l'Infrastructure Existante**

### ✅ **Points Forts Identifiés**
- **Framework Playwright** déjà configuré et opérationnel
- **Tests existants** pour 2 onglets : Analyseur et Graphe Logique  
- **Architecture robuste** avec data-testid pour sélecteurs stables
- **Infrastructure API** fonctionnelle avec gestion d'état de connexion
- **Documentation** complète dans README_FUNCTIONAL_TESTS.md

### ⚠️ **Lacunes Actuelles**
- **4 onglets non couverts** : Sophismes, Reconstructeur, Validation, Framework
- **Scénarios d'erreur insuffisants** pour les onglets existants
- **Tests de navigation** entre onglets manquants
- **Validation end-to-end** du workflow complet absente

---

## 🎯 **2. Plan de Tests Essentiels par Onglet**

### **🔍 Analyseur (ArgumentAnalyzer)** *(Existant - À compléter)*
**Status :** ✅ Couverture de base existante

**Tests critiques identifiés :**
- ✅ Analyse réussie d'argument simple
- ✅ Gestion du bouton désactivé (champ vide)
- ✅ Fonction de réinitialisation
- ⚠️ **À ajouter :** Test des options d'analyse (checkboxes)

**Fichier :** `tests/functional/test_argument_analyzer.py`

---

### **⚠️ Sophismes (FallacyDetector)** *(Nouveau - Priorité haute)*
**Status :** ❌ Aucun test existant

**Tests essentiels à créer :**

```python
# test_fallacy_detector.py

def test_fallacy_detection_basic_workflow(page):
    """Test principal : détection d'un sophisme Ad Hominem"""
    # 1. Navigation + activation onglet Sophismes
    # 2. Saisie exemple Ad Hominem prédéfini 
    # 3. Soumission avec options par défaut
    # 4. Vérification détection + niveau de sévérité
    # 5. Validation affichage explications

def test_severity_threshold_adjustment(page):
    """Test curseur seuil de sévérité"""
    # 1. Chargement exemple sophisme modéré
    # 2. Test avec seuil élevé (pas de détection)
    # 3. Réduction seuil + nouvelle détection
    # 4. Vérification impact sur résultats

def test_fallacy_example_loading(page):
    """Test chargement des exemples prédéfinis"""
    # 1. Clic sur exemple "Ad Hominem"
    # 2. Vérification remplissage automatique
    # 3. Test bouton "Tester" sur carte exemple
    # 4. Validation workflow complet
```

**Sélecteurs clés :**
- `[data-testid="fallacy-text-input"]`
- `[data-testid="fallacy-submit-button"]`
- `[data-testid="fallacy-results-container"]`

---

### **🔄 Reconstructeur (ArgumentReconstructor)** *(Nouveau - Priorité haute)*
**Status :** ❌ Aucun test existant

**Tests essentiels à créer :**

```python
# test_argument_reconstructor.py

def test_argument_reconstruction_workflow(page):
    """Test principal : reconstruction d'un argument simple"""
    # 1. Navigation + activation onglet Reconstructeur
    # 2. Saisie argument déductif classique
    # 3. Soumission pour reconstruction
    # 4. Vérification extraction prémisses/conclusion
    # 5. Validation structure résultat

def test_reconstructor_error_handling(page):
    """Test gestion d'erreur API"""
    # 1. Simulation erreur 500 via route interception
    # 2. Soumission argument valide
    # 3. Vérification affichage message d'erreur
    # 4. Validation stabilité interface

def test_reconstructor_reset_functionality(page):
    """Test bouton réinitialisation"""
    # 1. Reconstruction réussie d'un argument
    # 2. Vérification présence résultats
    # 3. Clic bouton Reset
    # 4. Validation nettoyage complet interface
```

**Sélecteurs clés :**
- `[data-testid="reconstructor-text-input"]`
- `[data-testid="reconstructor-submit-button"]`
- `[data-testid="reconstructor-results-container"]`

---

### **📊 Graphe Logique (LogicGraph)** *(Existant - Complet)*
**Status :** ✅ Couverture complète

**Tests actuels :**
- ✅ Génération réussie de graphique
- ✅ Gestion d'erreur API  
- ✅ Bouton de réinitialisation
- ✅ **Aucune action requise**

**Fichier :** `tests/functional/test_logic_graph.py`

---

### **✅ Validation (ValidationForm)** *(Nouveau - Priorité moyenne)*
**Status :** ❌ Aucun test existant

**Tests essentiels à créer :**

```python
# test_validation_form.py

def test_argument_validation_workflow(page):
    """Test principal : validation d'argument déductif valide"""
    # 1. Navigation + activation onglet Validation
    # 2. Saisie prémisses et conclusion valides
    # 3. Sélection type "déductif"
    # 4. Validation argument
    # 5. Vérification statut "valide" + score

def test_premise_management(page):
    """Test ajout/suppression de prémisses"""
    # 1. Ajout de plusieurs prémisses
    # 2. Vérification interface dynamique
    # 3. Suppression prémisse intermédiaire
    # 4. Validation intégrité données

def test_validation_types_selection(page):
    """Test types d'arguments (déductif/inductif/abductif)"""
    # 1. Test même argument avec types différents
    # 2. Vérification impact sur validation
    # 3. Validation descriptions types
    # 4. Test changement dynamique type
```

**Sélecteurs à ajouter :**
- `[data-testid="validation-tab"]` ⚠️ (à ajouter au composant)
- Sélecteurs pour prémisses, conclusion, type d'argument

---

### **🏗️ Framework (FrameworkBuilder)** *(Nouveau - Priorité moyenne)*
**Status :** ❌ Aucun test existant

**Tests essentiels à créer :**

```python
# test_framework_builder.py

def test_framework_construction_workflow(page):
    """Test principal : construction framework simple"""
    # 1. Navigation + activation onglet Framework
    # 2. Ajout de 3 arguments simples
    # 3. Définition d'attaques entre arguments
    # 4. Construction avec sémantique "preferred"
    # 5. Vérification calcul extensions

def test_argument_attack_management(page):
    """Test gestion des arguments et attaques"""
    # 1. Ajout arguments avec IDs personnalisés
    # 2. Création relations d'attaque
    # 3. Suppression argument + vérification cleanup
    # 4. Validation intégrité des attaques

def test_semantics_selection(page):
    """Test sélection de sémantiques"""
    # 1. Construction framework identique
    # 2. Test avec sémantiques différentes
    # 3. Vérification impact sur extensions
    # 4. Validation changement résultats
```

**Sélecteurs à ajouter :**
- `[data-testid="framework-tab"]` ⚠️ (à ajouter au composant)
- Sélecteurs pour arguments, attaques, sémantiques

---

## 🏗️ **3. Architecture des Nouveaux Tests**

### **Structure de Fichiers Recommandée**
```
tests/functional/
├── test_argument_analyzer.py      # ✅ Existant
├── test_logic_graph.py           # ✅ Existant  
├── test_webapp_homepage.py       # ✅ Existant
├── test_fallacy_detector.py      # 🆕 À créer (Priorité 1)
├── test_argument_reconstructor.py # 🆕 À créer (Priorité 1)
├── test_validation_form.py       # 🆕 À créer (Priorité 2)
├── test_framework_builder.py     # 🆕 À créer (Priorité 2)
├── test_tabs_navigation.py       # 🆕 À créer (Priorité 3)
└── conftest.py                   # 🔧 À améliorer
```

### **Pattern de Test Standard**
```python
@pytest.mark.playwright
def test_[onglet]_[fonctionnalite]_workflow(page: Page):
    """Description du scénario testé"""
    # 1. Navigation et attente API connectée
    page.goto("http://localhost:3000/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    # 2. Activation de l'onglet
    tab = page.locator('[data-testid="[onglet]-tab"]')
    tab.click()
    
    # 3. Interaction avec les éléments critiques
    # [Actions spécifiques à l'onglet]
    
    # 4. Vérification des résultats attendus
    # [Assertions sur les éléments de résultat]
```

---

## 📈 **4. Stratégie d'Implémentation**

### **Phase 1 : Tests Critiques (Priorité Haute)**
**Objectif :** Couverture des onglets sans tests
**Durée estimée :** 2-3 heures

1. **test_fallacy_detector.py** - 3 tests essentiels
   - Test workflow de base
   - Test seuil de sévérité  
   - Test chargement exemples

2. **test_argument_reconstructor.py** - 3 tests essentiels
   - Test workflow de reconstruction
   - Test gestion d'erreurs
   - Test fonctionnalité reset

3. **Amélioration conftest.py** - fixtures communes
   - Fixture page avec API connectée
   - Fixture activation onglet
   - Configuration browser debug

### **Phase 2 : Tests Complémentaires (Priorité Moyenne)**
**Objectif :** Couverture onglets complexes
**Durée estimée :** 2-3 heures

4. **test_validation_form.py** - 3 tests essentiels
   - Test validation arguments
   - Test gestion prémisses
   - Test types d'arguments

5. **test_framework_builder.py** - 3 tests essentiels
   - Test construction framework
   - Test gestion arguments/attaques
   - Test sémantiques

### **Phase 3 : Tests Intégration (Priorité Basse)**
**Objectif :** Tests transversaux
**Durée estimée :** 1-2 heures

6. **test_tabs_navigation.py** - navigation entre onglets
   - Test passage d'un onglet à l'autre
   - Test préservation données lors navigation
   - Test désactivation si API déconnectée

7. **Tests d'options** - compléments pour onglets existants
   - Test options analyse (Analyseur)
   - Test paramètres avancés

### **Estimation d'Effort Total**
- **Phase 1 :** 2-3 heures de développement
- **Phase 2 :** 2-3 heures de développement  
- **Phase 3 :** 1-2 heures de développement
- **Total :** 5-8 heures pour une couverture complète

---

## 🔧 **5. Améliorations Infrastructure**

### **conftest.py Enrichi**
```python
# Fixtures communes pour tous les tests
@pytest.fixture
async def api_connected_page(page):
    """Page avec API connectée"""
    page.goto("http://localhost:3000/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    return page

@pytest.fixture
async def tab_activated_page(api_connected_page, tab_name):
    """Page avec onglet spécifique activé"""
    tab = api_connected_page.locator(f'[data-testid="{tab_name}-tab"]')
    tab.click()
    return api_connected_page

@pytest.fixture
def browser_config():
    """Configuration browser (headless par défaut, headfull pour debug)"""
    return {
        "headless": True,   # False pour mode debug/démo
        "slow_mo": 0,       # 1000 pour ralentissement démo
    }
```

### **Data-testid Manquants à Ajouter**
**Composants Frontend à modifier :**

```javascript
// App.js - Onglets manquants
{ id: 'validation', label: '✅ Validation', component: ValidationForm },
{ id: 'framework', label: '🏗️ Framework', component: FrameworkBuilder }

// À ajouter dans le rendu des boutons :
data-testid={
  tab.id === 'validation' ? 'validation-tab' :
  tab.id === 'framework' ? 'framework-tab' : undefined
}
```

---

## 📊 **6. Tableau de Couverture des Tests**

| Onglet | Fonctionnalité Critique | Test Existant | Test À Créer | Priorité | Status |
|--------|-------------------------|---------------|--------------|----------|---------|
| 🔍 Analyseur | Analyse complète | ✅ | Compléments options | Basse | ✅ OK |
| ⚠️ Sophismes | Détection sophismes | ❌ | ✅ 3 tests | **Haute** | 🔄 Phase 1 |
| 🔄 Reconstructeur | Reconstruction arguments | ❌ | ✅ 3 tests | **Haute** | 🔄 Phase 1 |
| 📊 Graphe Logique | Visualisation | ✅ | ❌ | - | ✅ OK |
| ✅ Validation | Validation logique | ❌ | ✅ 3 tests | Moyenne | 🔄 Phase 2 |
| 🏗️ Framework | Construction Dung | ❌ | ✅ 3 tests | Moyenne | 🔄 Phase 2 |

**Légende :**
- ✅ : Complété
- 🔄 : En cours / À faire
- ❌ : Absent

---

## 🚀 **7. Stratégie Headless → Headfull**

### **Tests Headless (par défaut)**
- **Usage :** Exécution rapide et automatisée
- **Avantages :** Intégration CI/CD, tests de régression
- **Configuration :** `headless: True` dans conftest.py

### **Tests Headfull (debug/démo)**
- **Usage :** Debug, démonstration, validation visuelle
- **Avantages :** Observation du comportement en temps réel
- **Activation :** `pytest --headed` ou modifier conftest.py

```python
# Configuration dans conftest.py pour mode démo
@pytest.fixture
def browser_config():
    return {
        "headless": False,  # Mode visible pour démo
        "slow_mo": 1000,    # Ralentissement pour visualisation
        "devtools": True,   # Outils développeur ouverts
    }
```

---

## 📋 **8. Plan d'Exécution Recommandé**

### **Commandes de Test par Phase**

```powershell
# Phase 1 - Tests critiques (Priorité Haute)
pytest tests/functional/test_fallacy_detector.py -v
pytest tests/functional/test_argument_reconstructor.py -v

# Phase 2 - Tests complémentaires (Priorité Moyenne)
pytest tests/functional/test_validation_form.py -v
pytest tests/functional/test_framework_builder.py -v

# Phase 3 - Tests intégration (Priorité Basse)
pytest tests/functional/test_tabs_navigation.py -v

# Suite complète
pytest tests/functional/ -v

# Mode démo (headfull + ralenti)
pytest tests/functional/ -v --headed --slowmo=1000

# Tests spécifiques pour débogage
pytest tests/functional/test_fallacy_detector.py::test_fallacy_detection_basic_workflow -v -s
```

### **Pipeline de Validation Avant Démonstration**

```powershell
# Script de validation complète (recommandé)
.\scripts\run_all_and_test.ps1 --functional-only

# Ou validation manuelle étape par étape :
# 1. Démarrage des services
python -m argumentation_analysis.services.web_api.app  # Terminal 1
cd services\web_api\interface-web-argumentative && npm start  # Terminal 2

# 2. Attente stabilisation (30 secondes)

# 3. Exécution tests critiques
pytest tests/functional/test_fallacy_detector.py tests/functional/test_argument_reconstructor.py -v

# 4. Si Phase 1 OK → Tests complémentaires
pytest tests/functional/test_validation_form.py tests/functional/test_framework_builder.py -v

# 5. Si tout OK → Suite complète
pytest tests/functional/ -v
```

### **Métriques de Succès**
- **Phase 1 :** 6 tests passent (3 Sophismes + 3 Reconstructeur)
- **Phase 2 :** 6 tests supplémentaires passent (3 Validation + 3 Framework)
- **Phase 3 :** Tests navigation + compléments passent
- **Total :** 15+ tests fonctionnels pour validation complète

---

## 🎯 **9. Critères de Validation**

### **Critères de Réussite par Onglet**

**✅ Onglet validé si :**
- Navigation réussie vers l'onglet
- Saisie de données fonctionne
- Soumission declenche appel API correct
- Résultats s'affichent correctement
- Gestion d'erreur appropriée
- Reset/nettoyage fonctionnel

### **Critères de Validation Globale**

**🏆 Application validée si :**
- Tous les 6 onglets ont au moins 1 test critique passant
- Navigation entre onglets fonctionnelle
- État API correctement géré
- Aucune régression sur tests existants
- Temps d'exécution < 2 minutes pour suite complète

---

## 📚 **10. Documentation Associée**

### **Fichiers de Référence**
- **[README_FUNCTIONAL_TESTS.md](../tests/README_FUNCTIONAL_TESTS.md)** - Documentation framework existant
- **[test_argument_analyzer.py](../tests/functional/test_argument_analyzer.py)** - Exemple de tests existants
- **[test_logic_graph.py](../tests/functional/test_logic_graph.py)** - Pattern de test à reproduire

### **Ressources API**
- **Documentation API :** `http://localhost:5000/api/endpoints`
- **Health Check :** `http://localhost:5000/api/health`
- **Frontend :** `http://localhost:3000`

### **Scripts Utiles**
- **Lancement automatisé :** `.\scripts\run_all_and_test.ps1`
- **Activation environnement :** `.\scripts\env\activate_project_env.ps1`

---

## 🤝 **11. Prochaines Étapes**

### **Actions Immédiates**
1. **Validation du plan** par l'équipe
2. **Ajout data-testid manquants** dans composants frontend
3. **Implémentation Phase 1** (tests critiques)
4. **Validation fonctionnement** avec pipeline existant

### **Actions de Suivi**
5. **Implémentation Phase 2** (tests complémentaires)
6. **Intégration CI/CD** pour exécution automatique
7. **Documentation maintenance** pour évolution future

---

**📅 Dernière mise à jour :** 2025-01-07  
**🏷️ Version :** 1.0  
**👥 Contributeurs :** Équipe Intelligence Symbolique 2025  
**🎯 Objectif :** Tests fonctionnels complets avant démonstration

---

*Ce plan garantit une couverture complète des 6 onglets avec des tests essentiels focalisés sur les fonctionnalités critiques, permettant une validation automatisée fiable avant démonstration.*