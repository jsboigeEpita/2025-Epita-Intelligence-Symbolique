# Tests d'Intégration

Ce dossier contient les tests d'intégration end-to-end pour valider le fonctionnement complet des démos principales du projet.

## 📋 Vue d'ensemble

Les tests d'intégration valident le comportement end-to-end des 4 démos principales dans [`examples/Sherlock_Watson/`](../../examples/Sherlock_Watson/) :

- ✅ **Fonctionnement complet** sans dépendances externes obligatoires
- ✅ **Gestion fallback** pour environnements partiels  
- ✅ **Validation conformité** des composants opérationnels
- ✅ **Tests autonomes** avec skip automatique si infrastructure manquante

## 🧪 Modules de Tests

### 1. [`test_sherlock_watson_demo_integration.py`](test_sherlock_watson_demo_integration.py)
**Tests pour `sherlock_watson_authentic_demo.py`**

```bash
pytest tests/integration/test_sherlock_watson_demo_integration.py -v
```

**Tests couverts** :
- Configuration environnement (Semantic Kernel + OpenAI)
- Chargement cas Cluedo avec structure validée
- Investigation simplifiée avec conversation multi-agents
- Tests agents logiques avec fallback
- Validation Oracle avec gestion d'erreurs
- Sauvegarde session avec données persistantes

### 2. [`test_cluedo_oracle_integration.py`](test_cluedo_oracle_integration.py)
**Tests pour `cluedo_oracle_complete.py`**

```bash
pytest tests/integration/test_cluedo_oracle_integration.py -v
```

**Tests couverts** :
- État Oracle avec solution secrète et cartes
- Validation suggestions avec révélations automatiques
- Comportement Oracle (réfutation/confirmation/neutre)
- Moteur de jeu avec configuration Semantic Kernel
- Investigation complète avec conversation structurée
- Statistiques Oracle et métriques de performance

### 3. [`test_agents_logiques_integration.py`](test_agents_logiques_integration.py)
**Tests pour `agents_logiques_production.py`**

```bash
pytest tests/integration/test_agents_logiques_integration.py -v
```

**Tests couverts** :
- Processeur données custom avec patterns sophistiques
- Détection sophistiques (ad hominem, strawman, false dilemma, etc.)
- Analyse logique modale (nécessité, possibilité, temporal, etc.)
- Extraction propositions logiques avec validation
- Calcul force d'argument avec métriques
- Analyse complète intégrée avec hash authentique

### 4. [`test_orchestration_finale_integration.py`](test_orchestration_finale_integration.py)
**Tests pour `orchestration_finale_reelle.py`**

```bash
pytest tests/integration/test_orchestration_finale_integration.py -v
```

**Tests couverts** :
- Moteur d'orchestration avec session management
- Workflows multiples (Cluedo, Einstein, Agents, Sherlock-Watson)
- Modes orchestration (séquentiel, parallèle, adaptatif)
- Métriques convergence avec calculs statistiques
- Validation environnement avec checks authentification
- Session complète avec sauvegarde résultats

### 5. [`test_einstein_tweetyproject_integration.py`](test_einstein_tweetyproject_integration.py)
**Tests spécifiques pour l'intégration TweetyProject dans Einstein**

```bash
pytest tests/integration/test_einstein_tweetyproject_integration.py -v
```

**Tests couverts** :
- Validation initialisation TweetyProject pour Einstein
- Tests formulation clauses logiques Watson
- Tests exécution requêtes TweetyProject spécifiques
- Tests validation contraintes Einstein formelles
- Tests états EinsteinsRiddleState avec TweetyProject
- Tests gestion erreurs TweetyProject (timeouts, échecs)
- Tests récupération et fallback
- Tests performance traitement contraintes
- Tests robustesse avec contraintes malformées

## 🚀 Exécution des Tests

### Tests individuels
```bash
# Test démo principale
pytest tests/integration/test_sherlock_watson_demo_integration.py -v

# Test Oracle Cluedo
pytest tests/integration/test_cluedo_oracle_integration.py -v

# Test agents logiques
pytest tests/integration/test_agents_logiques_integration.py -v

# Test orchestration finale
pytest tests/integration/test_orchestration_finale_integration.py -v

# Test Einstein TweetyProject
pytest tests/integration/test_einstein_tweetyproject_integration.py -v
```

### Suite complète
```bash
# Tous les tests d'intégration
pytest tests/integration/ -v

# Avec rapport de couverture
pytest tests/integration/ -v --cov=examples.Sherlock_Watson
```

### Tests avec infrastructure complète
```bash
# Avec clé OpenAI configurée (tests complets)
OPENAI_API_KEY=sk-your-key pytest tests/integration/ -v

# Mode verbose pour debugging
pytest tests/integration/ -v -s --tb=short
```

## ⚙️ Configuration

### Variables d'environnement optionnelles
```bash
# Pour tests avec API réelle (optionnel)
export OPENAI_API_KEY=sk-your-openai-key
export OPENAI_CHAT_MODEL_ID=gpt-4o-mini

# Configuration Python
export PYTHONPATH="${PYTHONPATH}:$(pwd)/examples/Sherlock_Watson"
```

### Gestion automatique des dépendances
Les tests gèrent automatiquement :
- ✅ **Skip automatique** si modules non disponibles
- ✅ **Fallback modes** si API/réseau indisponible  
- ✅ **Tests offline** pour validation structure
- ✅ **Timeout protection** pour éviter blocages

## 📊 Caractéristiques Techniques

### Approche de test
- **Tests end-to-end** : Validation flux complet de chaque démo
- **Isolation modules** : Chaque test fonctionne indépendamment
- **Gestion d'erreurs** : Skip intelligent si infrastructure manquante
- **Validation conformité** : Vérification absence de simulations
- **Tests spécialisés** : Focus Einstein TweetyProject avec logique formelle

### Patterns utilisés
- **Fixtures pytest** : Configuration test avec cleanup automatique
- **Temporary directories** : Isolation fichiers temporaires
- **Mock environnement** : Tests avec variables d'environnement simulées
- **Async testing** : Support tests asynchrones avec `pytest-asyncio`
- **Contraintes simulées** : Validation TweetyProject avec clauses logiques
- **Tests de robustesse** : Gestion erreurs et contraintes malformées

### Métriques validées
- **Durée exécution** : Tracking performance de chaque test
- **Taux succès** : Validation pourcentage réussite
- **Conformité** : Vérification absence mocks/simulations
- **Couverture** : Validation points d'entrée critiques
- **Performance TweetyProject** : Temps traitement contraintes < 1s
- **Robustesse logique** : Validation clauses Einstein formelles

## 🔍 Debugging

### Logs détaillés
```bash
# Activation logs détaillés
pytest tests/integration/ -v -s --log-cli-level=INFO

# Focus sur un test spécifique
pytest tests/integration/test_cluedo_oracle_integration.py::TestCluedoOracleIntegration::test_oracle_behavior_validation -v -s
```

### Debugging d'erreurs
```bash
# Mode debug avec breakpoints
pytest tests/integration/ --pdb

# Affichage stdout complet
pytest tests/integration/ -v -s --tb=long
```

---

**📝 Note** : Ces tests d'intégration complètent la suite de validation dans [`tests/finaux/`](../finaux/) en se concentrant sur le comportement end-to-end plutôt que sur la validation technique interne.