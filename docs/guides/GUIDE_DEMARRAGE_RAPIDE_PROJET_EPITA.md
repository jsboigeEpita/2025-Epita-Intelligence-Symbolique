# 🚀 Guide de Démarrage Rapide - Projet Intelligence Symbolique EPITA

> Guide consolidé - Setup opérationnel en 5 minutes | Documentation complète pour tous niveaux

---

## 🎯 INSTALLATION EXPRESS (5 minutes)

### 1. Installation Base (2 minutes)

```bash
# Cloner le projet
git clone <repository-url>
cd 2025-Epita-Intelligence-Symbolique

# Environnement Python (nom peut varier selon version)
# Option A : Nom recommandé actuel
conda create --name epita_symbolic_ai python=3.9
conda activate epita_symbolic_ai

# Option B : Nom alternatif (versions antérieures)
# conda create --name projet-is python=3.9
# conda activate projet-is

# Installation dépendances
pip install -r requirements.txt
```

> **💡 Note Environnement** : Le projet accepte les deux noms d'environnement (`epita_symbolic_ai` ou `projet-is`). Utilisez celui que vous préférez ou qui correspond à votre documentation locale.

### 2. Configuration API OpenRouter (1 minute)

```bash
# Créer fichier .env à la racine du projet
echo "OPENROUTER_API_KEY=sk-or-v1-VOTRE_CLE_ICI" > .env
echo "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1" >> .env
echo "OPENROUTER_MODEL=gpt-4o-mini" >> .env
```

**Obtenir une clé** : [OpenRouter.ai](https://openrouter.ai) → S'inscrire → Générer clé API

### 3. Test de Validation (2 minutes)

```bash
# Test système complet - Point d'entrée principal
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

**Résultat attendu** : Confirmation que tous les composants critiques fonctionnent correctement.

---

## 🏆 5 POINTS D'ENTRÉE VALIDÉS - USAGE PRATIQUE

### 🎭 Point 1 : Démonstrations Sherlock/Watson & Epita

**Mode Interactif (RECOMMANDÉ pour découverte)** :
```bash
python examples/scripts_demonstration/demonstration_epita.py --interactive
```
**Résultat** : Menu interactif avec 5 catégories d'exploration du système

**Autres modes** :
```bash
# Démarrage rapide avec suggestions
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# Menu catégorisé (mode par défaut)
python examples/scripts_demonstration/demonstration_epita.py

# Tests complets avec métriques LLM
python examples/scripts_demonstration/demonstration_epita.py --all-tests
```

**📁 Structure Démo** :
```
examples/scripts_demonstration/
├── demonstration_epita.py           # ⭐ POINT D'ENTRÉE PRINCIPAL
├── demonstration_epita_README.md    # Documentation détaillée
├── RAPPORT_FINAL_COMPLET.md        # Rapport de validation
└── modules/                         # Modules démo spécialisés
```

**Agents Sherlock/Watson/Moriarty** :
```bash
# Démo Cluedo complète
python examples/cluedo_demo/demo_cluedo_workflow.py

# Agents authentiques
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# Oracle Moriarty complet
python examples/Sherlock_Watson/cluedo_oracle_complete.py

# Orchestration finale réelle
python examples/Sherlock_Watson/orchestration_finale_reelle.py
```

### ⚙️ Point 2 : Système d'Analyse Rhétorique

```bash
# Orchestration complète (point d'entrée principal)
python argumentation_analysis/run_orchestration.py --interactive

# Analyse avec architecture hiérarchique
python argumentation_analysis/run_analysis.py --text "Votre texte argumentatif"

# Éditeur d'extraits
python argumentation_analysis/run_extract_editor.py

# Tests système
python argumentation_analysis/run_tests.py
```

**🏗️ Architecture Hiérarchique 3 Niveaux** :
```
argumentation_analysis/
├── orchestration/hierarchical/
│   ├── strategic/              # Niveau stratégique (vision globale)
│   ├── tactical/               # Niveau tactique (coordination)
│   └── operational/            # Niveau opérationnel (exécution)
├── pipelines/                  # Pipelines d'analyse
├── services/                   # Services complets
└── agents/                     # Agents logiques spécialisés
```

### 🌐 Point 3 : Applications Web

```bash
# 🧪 VALIDATION JTMS WEB (RECOMMANDÉ)
python validate_jtms.py

# 🚀 Runner avancé (asynchrone non-bloquant)
python validation/web_interface/validate_jtms_web_interface.py

# Démarrage système web complet
python services/web_api/start_full_system.py

# Application React complète (Port 3001)
cd services/web_api/interface-web-argumentative
npm install && npm start

# API complète (Port 5003)
python services/web_api_from_libs/app.py

# Interface simple (Port 3000)
python interface_web/app.py
```

**🌐 Composants Web Sophistiqués** :
```
services/web_api/interface-web-argumentative/
└── src/components/
    ├── ArgumentAnalyzer.js     # Analyseur d'arguments
    ├── FallacyDetector.js      # Détecteur de sophismes
    ├── FrameworkBuilder.js     # Constructeur de frameworks
    ├── LogicGraph.js           # Graphiques logiques interactifs
    └── ValidationForm.js       # Formulaires de validation
```

### 🧪 Point 4 : Tests Unitaires & Validation

**Tests Mocks Système (critiques)** :
```bash
python -m pytest tests/unit/mocks/ -v
```

**Tests Validation Agents (25+ tests)** :
```bash
python -m pytest tests/validation_sherlock_watson/ -v

# Test spécifique avec LLM réel
python -m pytest tests/validation_sherlock_watson/test_phase_a_personnalites_distinctes.py -v
```

**Tests Orchestration Hiérarchique** :
```bash
python -m pytest tests/unit/orchestration/hierarchical/ -v
```

**Suite Complète (400+ tests)** :
```bash
python -m pytest tests/unit/ -v

# Avec coverage
python -m pytest tests/unit/ --cov=argumentation_analysis --cov-report=html
```

**📁 Structure des Tests** :
```
tests/
├── unit/mocks/                    # ⭐ Mocks système identifiés
├── validation_sherlock_watson/     # ⭐ 25+ tests validation agents
├── unit/orchestration/hierarchical/ # ⭐ Tests architecture 3 niveaux
├── integration/                   # Tests d'intégration
└── tests_playwright/              # Tests interfaces web
```

### 🧪 Point 5 : Tests avec LLMs Réels

```bash
# Tests unitaires avec vrais appels LLM
python -m pytest tests/unit/argumentation_analysis/test_strategies_real.py -v

# Tests agents avec LLM configuré
python -m pytest tests/validation_sherlock_watson/ -v
```

---

## 🎓 PARCOURS D'APPRENTISSAGE RECOMMANDÉS

### 🚀 Découverte Rapide (15 minutes)

1. **Configuration** (5 min) : Installation + configuration API
2. **Test Express** (5 min) : `python examples/scripts_demonstration/demonstration_epita.py --quick-start`
3. **Exploration** (5 min) : Mode interactif de la démo Epita

**Pour qui** : Étudiants débutants, première découverte du projet

### 🎯 Développeurs (1 heure)

1. **Architecture** (20 min) : Explorer `argumentation_analysis/run_orchestration.py --interactive`
2. **Agents** (20 min) : Tester `examples/Sherlock_Watson/sherlock_watson_authentic_demo.py`
3. **Web** (15 min) : Lancer `services/web_api/start_full_system.py`
4. **Tests** (5 min) : Exécuter `python -m pytest tests/unit/mocks/ -v`

**Pour qui** : Développeurs découvrant l'architecture technique

### 🔬 Chercheurs & Contributeurs (2 heures)

1. **Architecture Technique** (30 min) : Étudier [`docs/architecture/README.md`](../architecture/README.md)
2. **Code Source** (30 min) : Explorer modules core et patterns
3. **Tests Complets** (30 min) : Suite validation avec `tests/validation_sherlock_watson/`
4. **Composants React** (30 min) : Analyser `services/web_api/interface-web-argumentative/`
5. **Contribution** : Patterns dans [`docs/guides/GUIDE_PATTERNS_ORCHESTRATION_MODES.md`](GUIDE_PATTERNS_ORCHESTRATION_MODES.md)

**Pour qui** : Contributeurs avancés, recherche approfondie

---

## 🔧 CONFIGURATIONS AVANCÉES

### 💻 Environnement Développement

```bash
# Variables d'environnement
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export JAVA_HOME="/path/to/java"

# Vérification configuration
python -c "import os; print('API configurée:', 'OPENROUTER_API_KEY' in os.environ)"

# Test basic sans LLM
python -c "from argumentation_analysis.core import ArgumentationAnalyzer; print('Core OK')"
```

### 🌐 Configuration Web Multi-Composants

```bash
# Terminal 1 : Backend API (Port 5003)
cd services/web_api_from_libs
python app.py

# Terminal 2 : Frontend React (Port 3001)
cd services/web_api/interface-web-argumentative
npm install && npm start

# Terminal 3 : Tests Playwright
cd tests_playwright
npm install
npm test
```

### 🧪 Linting et Qualité Code

```bash
# Vérification qualité
flake8 argumentation_analysis/
black argumentation_analysis/

# Tests spécifiques
python -m pytest tests/unit/mocks/test_numpy_rec_mock.py -v
```

---

## 📊 VALIDATION & PERFORMANCE

### ✅ Checklist Système Fonctionnel

- [ ] Python 3.9+ installé avec Conda
- [ ] Environnement `epita_symbolic_ai` (ou `projet-is`) créé et activé
- [ ] Dépendances installées : `pip install -r requirements.txt`
- [ ] API OpenRouter configurée dans `.env`
- [ ] Test de base réussi : `python examples/scripts_demonstration/demonstration_epita.py --quick-start`

### 📈 Performance Attendue

- **Setup complet** : < 5 minutes
- **Tests unitaires** : < 3 minutes pour suite complète
- **Analyses LLM** : 2-3 secondes par requête
- **Applications web** : < 30 secondes de démarrage
- **Suite tests complète (400+)** : 5-10 minutes

### 🔍 Validation Installation

```bash
# Test complet système
python examples/scripts_demonstration/demonstration_epita.py --all-tests

# Test mocks système
python -m pytest tests/unit/mocks/ -v

# Test agents authentiques
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# Vérification API
python test_api_validation.py
```

---

## 🛠️ RÉSOLUTION DE PROBLÈMES

### ❌ Erreurs Communes

**Problème** : `ModuleNotFoundError` lors du démarrage
```bash
# Solution : Vérifier PYTHONPATH et environnement
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
conda activate epita_symbolic_ai  # ou projet-is
pip install -r requirements.txt
```

**Problème** : Erreur JPype avec TweetyProject
```bash
# Solution : Vérifier JAVA_HOME
export JAVA_HOME="/path/to/java"
java -version  # doit afficher Java 8+
```

**Problème** : API OpenRouter non configurée
```bash
# Solution : Créer .env avec clés valides
echo "OPENROUTER_API_KEY=sk-or-v1-votre-clé-ici" > .env
echo "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1" >> .env
echo "OPENROUTER_MODEL=gpt-4o-mini" >> .env
```

**Problème** : Erreur au démarrage des applications web
```bash
# Solution 1 : Vérifier les ports disponibles
lsof -i :3000  # ou netstat sur Windows
lsof -i :5003

# Solution 2 : Réinstaller dépendances Node.js
cd services/web_api/interface-web-argumentative
rm -rf node_modules package-lock.json
npm install
```

**Problème** : Tests échouent avec timeout
```bash
# Solution : Augmenter timeout dans pytest.ini ou désactiver tests lents
python -m pytest tests/unit/ -v --timeout=300 -m "not slow"
```

---

## 📚 DOCUMENTATION COMPLÉMENTAIRE

### 🎓 Pour Débutants
- **[README.md](../../README.md)** : Guide complet du projet (381 lignes optimisées)
- **[Documentation Projets](../projets/README.md)** : Sujets de projets étudiants
- **[Guide d'Accompagnement](../projets/ACCOMPAGNEMENT_ETUDIANTS.md)** : Support et ressources

### 🏗️ Pour Développeurs
- **[Architecture Système](../architecture/README.md)** : Documentation technique détaillée
- **[Guide des Composants](../composants/README.md)** : Modules réutilisables
- **[Patterns d'Orchestration](GUIDE_PATTERNS_ORCHESTRATION_MODES.md)** : Bonnes pratiques

### 🔬 Pour Chercheurs
- **[Rapports de Validation](../../docs/archives/validation_legacy_317/)** : Résultats complets 5/5 points d'entrée
- **[Documentation Technique](../technical/)** : Spécifications avancées
- **[Analyses d'Architecture](../architecture/)** : Architecture hiérarchique 3 niveaux

---

## 🚀 DÉMARRAGE IMMÉDIAT

**Commandes essentielles à retenir** :

```bash
# 1. Activation environnement
conda activate epita_symbolic_ai

# 2. Test rapide système
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# 3. Exploration interactive
python examples/scripts_demonstration/demonstration_epita.py --interactive

# 4. Lancement web
python services/web_api/start_full_system.py

# 5. Tests validation
python -m pytest tests/unit/mocks/ -v
```

---

**🎯 Ce guide vous permet de démarrer, tester et explorer le projet en moins de 5 minutes !**

**📧 Support** : Consulter [README.md](../../README.md) ou [documentation technique](../README.md) pour aide avancée