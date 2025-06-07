# Projet d'Intelligence Symbolique EPITA

**Architecture Sophistiquée d'Analyse d'Argumentation** - Intelligence Symbolique avec Stratégies Authentiques Validées

## 🎯 **Quick Start - Point d'Entrée Principal**

### ⚡ **Démonstration Immédiate**
Le script [`demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py) est votre **point d'entrée principal** pour découvrir toutes les capacités du système :

```bash
# 🚀 Démarrage rapide pour étudiants
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# 🎓 Mode interactif avec pauses pédagogiques
python examples/scripts_demonstration/demonstration_epita.py --interactive

# 📊 Menu catégorisé (mode par défaut)
python examples/scripts_demonstration/demonstration_epita.py

# 📈 Métriques du projet uniquement
python examples/scripts_demonstration/demonstration_epita.py --metrics

# ⚙️ Exécution complète de tous les tests
python examples/scripts_demonstration/demonstration_epita.py --all-tests
```

### 🎯 **Modules de Démonstration Disponibles**
Le script `demonstration_epita.py` intègre **6 catégories modulaires** :

- 🧠 **Intelligence Symbolique** - Raisonnement logique et contraintes
- 🎭 **Analyse d'Argumentation** - Stratégies rhétoriques sophistiquées
- ⚙️ **Orchestration Agentique** - Coordination multi-agents
- 🔗 **Intégration Java-Python** - Bridges JPype avancés
- 🌐 **Services Web** - APIs et interfaces web
- 🧪 **Tests et Validation** - Couverture complète et métriques

## 🏆 **Certification d'Authenticité - Post-Audit Anti-Mock**

### ✅ **Validation Critique Réussie (Juin 2025)**
Suite à l'audit critique anti-mock, le système a été **100% validé** avec des composants entièrement authentiques :

**🎯 Résultats de l'Audit** :
- **📊 106/106 tests authentiques** réussis (100% de succès)
- **🚫 0 mock critique** dans les composants stratégiques
- **⚡ 3 stratégies sophistiquées** intégrées avec Semantic Kernel
- **🎯 État partagé innovant** pour coordination inter-stratégies

**🔍 Stratégies Authentiques Découvertes** :
- ✅ **[`SimpleTerminationStrategy`](docs/architecture/strategies/strategies_architecture.md#1-simpleterminationstrategy)** : Terminaison intelligente basée sur conclusion + max_steps
- ✅ **[`DelegatingSelectionStrategy`](docs/architecture/strategies/strategies_architecture.md#2-delegatingselectionstrategy)** : Sélection avec désignation explicite via état partagé
- ✅ **[`BalancedParticipationStrategy`](docs/architecture/strategies/strategies_architecture.md#3-balancedparticipationstrategy)** : Équilibrage algorithmique sophistiqué

**📋 Documentation Technique Complète** :
- 🏗️ **[Architecture des Stratégies](docs/architecture/strategies/strategies_architecture.md)** - Spécifications techniques détaillées
- 🔍 **[Audit Anti-Mock](docs/architecture/strategies/audit_anti_mock.md)** - Rapport de validation complet (106/106 tests)
- 🔗 **[Intégration Semantic Kernel](docs/architecture/strategies/semantic_kernel_integration.md)** - Conformité aux interfaces standard
- 📊 **[État Partagé](docs/architecture/strategies/shared_state_architecture.md)** - Architecture de coordination

## 🔒 **Sécurité et Intégrité - Audit Sherlock-Watson (Janvier 2025)**

### ✅ **Audit d'Intégrité Cluedo Réussi**
Un audit de sécurité complet a été réalisé sur le système **Sherlock-Watson-Moriarty Oracle Enhanced** :

- **4 violations d'intégrité** détectées et **corrigées**
- **CluedoIntegrityError** déployé pour protection anti-triche
- **Mécanismes de surveillance** temps réel intégrés
- **Couverture tests** maintenue à **100%**

**Documentation Sécurité** :
- 📋 **[Rapport d'Audit Complet](docs/sherlock_watson/AUDIT_INTEGRITE_CLUEDO.md)**
- 🛠️ **[Guide Utilisateur Sécurisé](docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md)**
- 🏗️ **[Architecture Sécurité](docs/sherlock_watson/ARCHITECTURE_TECHNIQUE_DETAILLEE.md)**

## 🔧 **Configuration et Prérequis**

### ⚡ **Installation Rapide**
```bash
# 1. Cloner et naviguer dans le projet
git clone <repository-url>
cd 2025-Epita-Intelligence-Symbolique

# 2. Environnement Python (recommandé : Conda)
conda create --name projet-is python=3.9
conda activate projet-is
pip install -r requirements.txt

# 3. Test de l'installation
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

### 📋 **Prérequis Détaillés**

**Core System** :
- Python 3.9+ (avec Conda recommandé)
- Java 8+ (pour JPype et intégration Tweety)
- Git (pour clonage et mises à jour)

**Application Web** (optionnel) :
- Node.js 16+ (pour le frontend React)
- NPM ou Yarn

**APIs Externes** (optionnel) :
- OpenAI API Key (pour les agents conversationnels)

### 🛠️ **Configuration Avancée avec Scripts PowerShell**

Le projet inclut des **scripts d'environnement automatisés** pour simplifier la configuration :

#### **Script Principal : `scripts\env\activate_project_env.ps1`**
```powershell
# Exécution avec commande (recommandé)
.\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py"

# Configuration d'environnement uniquement
.\activate_project_env.ps1
```

**Fonctionnalités** :
- ✅ Chargement automatique des variables d'environnement (`.env`)
- ✅ Configuration `JAVA_HOME` et `PATH`
- ✅ Exécution via `conda run` pour isolation complète
- ✅ Gestion `PYTHONPATH` automatique

#### **Scripts Raccourcis à la Racine**
```powershell
# Lancement direct de démonstrations
.\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --interactive"

# Setup complet du projet
.\setup_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --all-tests"
```

### 🌐 **Configuration Application Web** (Optionnel)

Si vous souhaitez utiliser l'interface web complète :

```bash
# 1. Installation frontend
cd services/web_api/interface-web-argumentative
npm install

# 2. Configuration backend/frontend
echo "REACT_APP_API_BASE_URL=http://localhost:5005" > .env

# 3. Lancement (2 terminaux)
# Terminal 1 - Backend:
.\activate_project_env.ps1 -CommandToRun "scripts\run_backend.cmd 5005"

# Terminal 2 - Frontend:
.\activate_project_env.ps1 -CommandToRun "scripts\run_frontend.cmd 3001"
```

## 📚 **Documentation Technique Complète**

### 🎯 **Documentation Post-Audit (Recommandée)**

**Architecture des Stratégies Authentiques** (Post-Audit Anti-Mock) :
- 🏗️ **[Architecture des Stratégies](docs/architecture/strategies/strategies_architecture.md)** - Spécifications techniques des 3 stratégies validées
- 🔍 **[Audit Anti-Mock](docs/architecture/strategies/audit_anti_mock.md)** - Rapport de validation complet (106/106 tests)
- 🔗 **[Intégration Semantic Kernel](docs/architecture/strategies/semantic_kernel_integration.md)** - Conformité aux interfaces standard
- 📊 **[État Partagé](docs/architecture/strategies/shared_state_architecture.md)** - Architecture de coordination inter-stratégies

**Sécurité et Intégrité Sherlock-Watson** :
- 📋 **[Audit d'Intégrité Cluedo](docs/sherlock_watson/AUDIT_INTEGRITE_CLUEDO.md)** - Rapport de sécurité complet
- 🛠️ **[Guide Utilisateur Sécurisé](docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md)** - Utilisation sécurisée
- 🏗️ **[Architecture Sécurité](docs/sherlock_watson/ARCHITECTURE_TECHNIQUE_DETAILLEE.md)** - Spécifications techniques

### 📖 **Documentation Générale**

**Points d'Entrée** :
- **[Documentation Complète](docs/README.md)** - Index général de la documentation
- **[Architecture du Système](docs/architecture/README.md)** - Architecture hiérarchique et patterns
- **[Guides d'Utilisation](docs/guides/README.md)** - Tutoriels et guides pratiques

**Orchestration Agentique Avancée** :
- **[Analyse Orchestrations Sherlock/Watson](docs/architecture/analyse_orchestrations_sherlock_watson.md)** - Flux d'orchestration dans les conversations agentiques incluant interactions, outils et solvers Tweety
- **[Guide Patterns d'Orchestration](docs/guides/GUIDE_PATTERNS_ORCHESTRATION_MODES.md)** - Patterns reproductibles avec 5 types d'orchestration distincts, templates de communication et bonnes pratiques

### 🔍 **Validation et Tests**

**Couverture de Tests** :
- ✅ **106/106 tests authentiques** réussis (stratégies d'argumentation)
- ✅ **100% couverture** des composants critiques validés
- ✅ **0 mock critique** dans les composants stratégiques
- ✅ **Architecture modulaire** entièrement testée

**Scripts de Validation** :
```bash
# Validation complète avec métriques
python examples/scripts_demonstration/demonstration_epita.py --all-tests

# Tests des stratégies spécifiquement
python -m pytest tests/unit/argumentation_analysis/test_strategies_real.py -v
```

---

**📢 Ce projet constitue une démonstration avancée d'intelligence symbolique avec validation technique complète. Le script [`demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py) est votre point d'entrée idéal pour explorer toutes les capacités du système.**

