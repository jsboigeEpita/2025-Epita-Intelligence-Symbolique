# 🚀 Guide de Démarrage Rapide

Guide pratique pour découvrir et utiliser le système d'Intelligence Symbolique EPITA.

## 🎯 **Configuration Initiale (5 minutes)**

### **1. Installation de Base**
```bash
# Cloner le projet
git clone <repository-url>
cd 2025-Epita-Intelligence-Symbolique

# Environnement Python (OBLIGATOIRE : nom exact)
conda create --name epita_symbolic_ai python=3.9
conda activate epita_symbolic_ai
pip install -r requirements.txt
```

### **2. Configuration API (Recommandée)**
```bash
# Créer fichier .env à la racine
echo "OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE" > .env
echo "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1" >> .env
echo "OPENROUTER_MODEL=gpt-4o-mini" >> .env
```

### **3. Test de Validation**
```bash
# Test avec le VRAI point d'entrée Epita
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

---

## 🏆 **5 Points d'Entrée Validés - Usage Pratique**

### **🧪 Point 1 : Tests Unitaires**
```bash
# Tests mocks système (critiques)
python -m pytest tests/unit/mocks/ -v

# Tests validation agents (25+)
python -m pytest tests/validation_sherlock_watson/ -v

# Tests orchestration hiérarchique
python -m pytest tests/unit/orchestration/hierarchical/ -v

# Suite complète (400+ tests)
python -m pytest tests/unit/ -v
```

**📁 Structure des Tests :**
```
tests/
├── unit/mocks/                    # ⭐ Mocks système identifiés
├── validation_sherlock_watson/     # ⭐ 25+ tests validation agents
├── unit/orchestration/hierarchical/ # ⭐ Tests architecture 3 niveaux
└── tests_playwright/              # Tests interfaces web
```

### **🎭 Point 2 : Démo Epita (Point d'entrée principal)**
```bash
# Mode interactif (RECOMMANDÉ pour découverte)
python examples/scripts_demonstration/demonstration_epita.py --interactive

# Démarrage rapide avec suggestions
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# Menu catégorisé (mode par défaut)
python examples/scripts_demonstration/demonstration_epita.py

# Tests complets avec métriques LLM
python examples/scripts_demonstration/demonstration_epita.py --all-tests
```

**📁 Structure Démo Epita :**
```
examples/scripts_demonstration/
├── demonstration_epita.py           # ⭐ VRAI POINT D'ENTRÉE
├── demonstration_epita_README.md    # Documentation
├── RAPPORT_FINAL_COMPLET.md        # Rapport validation
├── modules/                        # Modules démo
│   ├── demo_agents_logiques.py     # Démo agents
│   ├── demo_cas_usage.py           # Cas d'usage
│   └── demo_services_core.py       # Services core
└── configs/demo_categories.yaml    # Configuration
```

### **⚙️ Point 3 : Système d'Analyse Rhétorique**
```bash
# Orchestration complète (point d'entrée principal)
python argumentation_analysis/run_orchestration.py --interactive

# Analyse avec architecture hiérarchique
python argumentation_analysis/run_analysis.py --text "Votre texte"

# Éditeur d'extraits
python argumentation_analysis/run_extract_editor.py

# Tests système
python argumentation_analysis/run_tests.py
```

**🏗️ Architecture Hiérarchique 3 Niveaux :**
```
argumentation_analysis/
├── orchestration/
│   ├── hierarchical/
│   │   ├── strategic/              # Niveau stratégique
│   │   ├── tactical/               # Niveau tactique
│   │   └── operational/            # Niveau opérationnel
│   ├── service_manager.py          # Gestionnaire services
│   └── real_llm_orchestrator.py    # Orchestrateur LLM
├── pipelines/                      # Pipelines d'analyse
├── services/                       # Services complets
└── agents/                         # Agents logiques
```

### **🕵️ Point 4 : Agents Sherlock/Watson/Moriarty**
```bash
# Démo Cluedo complète
python examples/cluedo_demo/demo_cluedo_workflow.py

# Démo Einstein
python examples/Sherlock_Watson/agents_logiques_production.py --scenario examples/Sherlock_Watson/einstein_scenario.json

# Agents authentiques Sherlock/Watson
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# Oracle Moriarty complet
python examples/Sherlock_Watson/cluedo_oracle_complete.py

# Orchestration finale réelle
python examples/Sherlock_Watson/orchestration_finale_reelle.py
```

**🎭 Agents Authentiques :**
```
examples/
├── cluedo_demo/demo_cluedo_workflow.py         # ⭐ Cluedo
# (Le workflow Einstein est maintenant géré par le script de production)
└── Sherlock_Watson/                            # ⭐ Agents authentiques
    ├── sherlock_watson_authentic_demo.py
    ├── cluedo_oracle_complete.py
    └── orchestration_finale_reelle.py
```

### **🌐 Point 5 : Applications Web**
```bash
# 🧪 VALIDATION JTMS WEB (RECOMMANDÉ)
python validate_jtms.py

# 🚀 Runner avancé (asynchrone non-bloquant)
python validation/web_interface/validate_jtms_web_interface.py

# Démarrage système complet
python services/web_api/start_full_system.py

# Application React complète (Port 3001)
cd services/web_api/interface-web-argumentative
npm install && npm start

# API complète (Port 5003)
python services/web_api_from_libs/app.py

# Interface simple (Port 3000)
python interface_web/app.py

# API racine
python api/main.py
```

**🌐 Composants Web Sophistiqués :**
```
services/web_api/
├── interface-web-argumentative/    # ⭐ Application React complète
│   └── src/components/
│       ├── ArgumentAnalyzer.js     # Analyseur arguments
│       ├── FallacyDetector.js      # Détecteur sophismes
│       ├── FrameworkBuilder.js     # Constructeur frameworks
│       ├── LogicGraph.js           # Graphiques logiques
│       └── ValidationForm.js       # Formulaires validation
├── start_full_system.py           # ⭐ Démarrage complet
└── interface-simple/               # Interface Flask simple
```

---

## 🔧 **Configurations Spécialisées**

### **💻 Environnement Développement**
```bash
# Variables d'environnement développement
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export JAVA_HOME="/path/to/java"

# Tests avec coverage
python -m pytest tests/unit/ --cov=argumentation_analysis --cov-report=html

# Linting et qualité code
flake8 argumentation_analysis/
black argumentation_analysis/
```

### **🌐 Configuration Web Avancée**
```bash
# Backend API complet (Port 5003)
cd services/web_api_from_libs
python app.py

# Frontend React (Port 3001) - Terminal séparé
cd services/web_api/interface-web-argumentative
npm install
npm start

# Tests Playwright
cd tests_playwright
npm test
```

### **🧪 Tests et Validation**
```bash
# Tests mocks critiques
python -m pytest tests/unit/mocks/test_numpy_rec_mock.py -v

# Tests agents avec LLM réel
python -m pytest tests/validation_sherlock_watson/test_phase_a_personnalites_distinctes.py -v

# Tests orchestration
python -m pytest tests/unit/orchestration/test_la classe `UnifiedPipeline` du module `argumentation_analysis/pipelines/unified_pipeline.py` -v
```

---

## 🎯 **Parcours d'Apprentissage Recommandés**

### **🚀 Découverte Rapide (15 min)**
1. **Configuration** (5 min) : Installation + configuration API
2. **Test rapide** (5 min) : `python examples/scripts_demonstration/demonstration_epita.py --quick-start`
3. **Exploration** (5 min) : Mode interactif de la démo Epita

### **🎓 Apprentissage Approfondi (1h)**
1. **Architecture** (20 min) : Explorer `argumentation_analysis/run_orchestration.py --interactive`
2. **Agents** (20 min) : Tester `examples/Sherlock_Watson/sherlock_watson_authentic_demo.py`
3. **Web** (15 min) : Lancer `services/web_api/start_full_system.py`
4. **Tests** (5 min) : Exécuter `python -m pytest tests/unit/mocks/ -v`

### **⚙️ Développement Avancé (2h)**
1. **Architecture technique** : Étudier `docs/architecture/README.md`
2. **Composants React** : Explorer `services/web_api/interface-web-argumentative/`
3. **Tests complets** : Suite validation avec `tests/validation_sherlock_watson/`
4. **Contribution** : Patterns dans `docs/guides/GUIDE_PATTERNS_ORCHESTRATION_MODES.md`

---

## 🛠️ **Résolution de Problèmes**

### **❌ Erreurs Communes**

**Problème** : `ModuleNotFoundError` lors du démarrage
```bash
# Solution : Vérifier PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
conda activate epita_symbolic_ai
```

**Problème** : Erreur JPype avec TweetyProject
```bash
# Solution : Vérifier JAVA_HOME
export JAVA_HOME="/path/to/java"
java -version
```

**Problème** : API OpenRouter non configurée
```bash
# Solution : Créer .env avec clés valides
echo "OPENROUTER_API_KEY=sk-or-v1-your-key" > .env
```

### **✅ Validation Installation**
```bash
# Test complet validation
python examples/scripts_demonstration/demonstration_epita.py --all-tests

# Test mocks système
python -m pytest tests/unit/mocks/ -v

# Test agents authentiques
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py
```

---

## 📋 **Checklist Démarrage**

### **Configuration Minimale** ✅
- [ ] Python 3.9+ installé avec Conda
- [ ] Environnement `epita_symbolic_ai` créé et activé
- [ ] Dépendances installées avec `pip install -r requirements.txt`
- [ ] Test de base : `python examples/scripts_demonstration/demonstration_epita.py --quick-start`

### **Configuration Complète** ✅
- [ ] Fichier `.env` créé avec clés API OpenRouter
- [ ] Java 8+ installé pour TweetyProject
- [ ] Node.js 16+ pour interfaces web (optionnel)
- [ ] Tests validation : `python -m pytest tests/unit/mocks/ -v`

### **Validation Fonctionnelle** ✅
- [ ] Démo Epita fonctionne : Mode interactif testé
- [ ] Architecture hiérarchique : `argumentation_analysis/run_orchestration.py`
- [ ] Agents authentiques : Tests Sherlock/Watson
- [ ] Application web : Interface React démarrée
- [ ] Tests complets : Mocks et validation agents

---

## 🏆 **Conclusion**

Ce guide présente les points d'entrée principaux du système avec les chemins et commandes vers les composants opérationnels.

### **✅ Points Clés**
- 🎯 **5 points d'entrée** avec vrais chemins validés
- 🏗️ **Architecture 3 niveaux** documentée et accessible
- 🧪 **Tests avec mocks** identifiés et fonctionnels
- 🌐 **Composants React** sophistiqués découverts
- 🕵️ **Agents authentiques** Sherlock/Watson/Moriarty

**📢 Guide pratique pour une prise en main efficace du système.**
