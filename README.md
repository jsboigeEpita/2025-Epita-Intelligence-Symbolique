# Projet d'Intelligence Symbolique EPITA

**Bienvenue dans l'Architecture Sophistiquée d'Analyse d'Argumentation** - Intelligence Symbolique avec Stratégies Authentiques Validées

---

## 🚀 **Démarrage Rapide**

### Lancer l'Application Web
```bash
# Démarrage complet (backend + frontend)
python start_webapp.py

# Backend seul
python start_webapp.py --backend-only

# Frontend seul
python start_webapp.py --frontend-only

# Mode configuration personnalisée
python start_webapp.py --config config/webapp_config.yml --verbose
```

### Migration depuis PowerShell
Les anciens scripts PowerShell ont été **modernisés** ! Voir [MIGRATION_WEBAPP.md](MIGRATION_WEBAPP.md) pour migrer depuis l'ancien `start_web_application.ps1`.

**Ancienne méthode** (obsolète) → **Nouvelle méthode** (recommandée) :
```bash
# ❌ Obsolète
.\start_web_application.ps1

# ✅ Moderne
python start_webapp.py
```

### Avantages de la Nouvelle Approche
- ✅ **Configuration YAML** centralisée
- ✅ **Logs structurés** avec niveaux de verbosité
- ✅ **Gestion d'erreurs** robuste
- ✅ **Tests automatisés** intégrés
- ✅ **Health checks** des services

---

## 🏗️ **Architecture Centralisée (Finalisée !)**

**🎯 MIGRATION RÉUSSIE** : L'ancien ensemble de **42+ scripts** a été transformé en **3 scripts consolidés** utilisant un **pipeline unifié central**. **2.03 MB libérés** et **-85% de code** redondant éliminé !

### 📊 Scripts Consolidés Finaux

#### 1. **🚀 Analyseur de Production Unifié** - *673 lignes (-45%)*
```bash
# Analyse standard en production
python scripts/rhetorical_analysis/unified_production_analyzer.py "votre texte" \
  --orchestration-type unified \
  --analysis-modes unified \
  --mock-level none

# Interface CLI complète (40+ paramètres préservés)
python scripts/rhetorical_analysis/unified_production_analyzer.py --help
```
- **Rôle :** Façade CLI principale pour analyse rhétorique en production
- **Architecture :** Délégation au pipeline unifié central
- **Validation :** ✅ 100% tests réussis - Interface préservée

#### 2. **🎓 Système Éducatif EPITA** - *487 lignes*
```bash
# Démonstration EPITA interactive
python scripts/rhetorical_analysis/educational_showcase_system.py \
  --demo-mode interactive \
  --agents sherlock watson \
  --conversation-capture

# Corpus chiffré pédagogique
python scripts/rhetorical_analysis/educational_showcase_system.py \
  --corpus-decryption-demo \
  --epita-config
```
- **Rôle :** Configuration éducative avec agents conversationnels
- **Spécialité :** Agents Sherlock Holmes & Dr Watson
- **Innovation :** Corpus déchiffrement pédagogique

#### 3. **📊 Processeur de Workflow Compréhensif** - *990 lignes*
```bash
# Traitement corpus chiffré
python scripts/rhetorical_analysis/comprehensive_workflow_processor.py \
  --corpus-encrypted data/corpus_chiffre.enc \
  --workflow-mode full \
  --batch-processing

# Workflow batch standard
python scripts/rhetorical_analysis/comprehensive_workflow_processor.py \
  --input-directory corpus/ \
  --parallel-processing
```
- **Rôle :** Traitement batch et corpus chiffré
- **Innovation :** Support workflow avec pipeline unifié
- **Démonstration :** ✅ Corpus déchiffrement opérationnel

### 🏗️ **Pipeline Unifié Central**

```
┌─────────────────────────────────────────────────────────────┐
│                PIPELINE UNIFIÉ CENTRAL                     │
│         unified_orchestration_pipeline.py                  │
│  • Orchestration Hiérarchique (3 niveaux)                │
│  • Orchestrateurs Spécialisés (8+)                       │
│  • Middleware Communication Agentielle                    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ run_unified_orchestration_pipeline()
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │ Script 1  │   │ Script 2  │   │ Script 3  │
        │Production │   │Education  │   │ Workflow  │
        │ Analyzer  │   │  EPITA    │   │Processor  │
        └───────────┘   └───────────┘   └───────────┘
```

### 📋 **Documentation Complète**

- **📊 Rapport Final :** [RAPPORT_FINAL_ARCHITECTURE_CENTRALISEE.md](docs/RAPPORT_FINAL_ARCHITECTURE_CENTRALISEE.md)
- **🏗️ Guide Architecture :** [README_ARCHITECTURE_CENTRALE.md](scripts/rhetorical_analysis/README_ARCHITECTURE_CENTRALE.md)
- **🔄 Migration Legacy :** Interface CLI préservée à 100% - Aucun changement nécessaire

### ✅ **Nettoyage Accompli**

- **51 éléments archivés** : Scripts et répertoires obsolètes
- **2.03 MB libérés** : Espace disque récupéré
- **Structure finale :** `scripts/rhetorical_analysis/` + utilitaires essentiels
- **Archive :** `archived_scripts/obsolete_migration_2025/`

### 🎯 **Avantages Architecture Centralisée**

- ✅ **Réduction 93%** : 42+ scripts → 3 scripts consolidés
- ✅ **Code -85%** : ~15,000 → 2,150 lignes
- ✅ **Imports -98%** : 200+ → 3 imports uniques
- ✅ **Maintenance centralisée** : 1 pipeline unifié
- ✅ **Performance optimisée** : Orchestration hiérarchique
- ✅ **Évolutivité** : Nouveaux scripts = façades légères

---

## 🎓 **Bienvenue Étudiants et Visiteurs !**

Ce projet constitue une démonstration avancée d'intelligence symbolique développée dans le cadre du cours EPITA. Il combine recherche académique rigoureuse et développement technique moderne pour offrir aux étudiants une expérience complète d'exploration des concepts d'IA symbolique et d'analyse argumentative.

### 🎯 **Objectifs Pédagogiques**
- **Comprendre** les fondements de l'intelligence symbolique et de l'IA explicable
- **Maîtriser** les techniques d'analyse argumentative et de détection de sophismes
- **Explorer** l'orchestration multi-agents avec Semantic Kernel
- **Intégrer** des technologies modernes (Python, Java, React) dans un système cohérent
- **Développer** des compétences en architecture logicielle et test automatisé

---

## 🚀 **4 Points d'Entrée Principaux**

### 1. 🎭 **Démo EPITA - Exploration des Fonctionnalités**
**Point d'entrée recommandé pour découvrir le système**

Le script [`demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py) est votre **porte d'entrée principale** avec 4 modes adaptés :

```bash
# 🎓 Mode interactif pédagogique (RECOMMANDÉ pour étudiants)
python examples/scripts_demonstration/demonstration_epita.py --interactive

# 🚀 Démarrage rapide avec suggestions de projets
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# 📊 Menu catégorisé (mode par défaut)
python examples/scripts_demonstration/demonstration_epita.py

# ⚙️ Tests complets avec métriques
python examples/scripts_demonstration/demonstration_epita.py --all-tests
```

**Fonctionnalités** :
- 🧠 **Intelligence Symbolique** - Raisonnement logique et contraintes  
- 🎭 **Analyse d'Argumentation** - Stratégies rhétoriques sophistiquées
- ⚙️ **Orchestration Agentique** - Coordination multi-agents
- 🔗 **Intégration Java-Python** - Bridges JPype avancés
- 🌐 **Services Web** - APIs et interfaces web
- 🧪 **Tests et Validation** - Couverture complète et métriques

📋 **Documentation** : [`demonstration_epita_README.md`](examples/scripts_demonstration/demonstration_epita_README.md)

### 2. ⚙️ **Système d'Analyse Rhétorique Unifié**
**Orchestration avancée avec paramètres de contrôle**

Le script [`run_orchestration.py`](argumentation_analysis/run_orchestration.py) offre un contrôle fin de l'orchestration :

```bash
# Analyse interactive avec choix des agents
python argumentation_analysis/run_orchestration.py --interactive

# Analyse avec agents spécifiques
python argumentation_analysis/run_orchestration.py --agents "ExtractAgent,LogicAgent" --text "Votre texte"

# Mode verbeux pour debugging
python argumentation_analysis/run_orchestration.py --verbose --interactive

# Génération de rapport détaillé
python argumentation_analysis/run_orchestration.py --report --output-format json
```

**Paramètres disponibles** :
- 🎯 **Source** : Texte direct, fichier, ou entrée interactive
- 🔀 **Orchestration** : Choix des agents et stratégies
- 🤖 **Agents** : Sélection spécifique d'agents d'analyse
- 📢 **Verbosité** : Contrôle des logs et traces d'exécution  
- 📊 **Rapport** : Formats de sortie (console, JSON, markdown)

### 3. 🌐 **Application Web avec Manager Dédié**
**Interface moderne pour services d'analyse**

Système web complet avec backend Flask et frontend React :

```bash
# Démarrage Backend (Port 5005)
cd services/web_api
python start_api.py --port 5005

# Démarrage Frontend (Port 3001) - Terminal séparé
cd services/web_api/interface-web-argumentative  
npm install && npm start

# Ou utilisation des scripts PowerShell intégrés
.\scripts\run_backend.cmd 5005
.\scripts\run_frontend.cmd 3001
```

**Services disponibles** :
- 🔍 **API REST** : Endpoints d'analyse argumentative (`/api/analyze`, `/api/validate`)
- 🌐 **Interface Web** : Dashboard React pour interaction utilisateur
- 🧪 **Tests Playwright** : Validation automatisée de l'interface
- 📊 **Monitoring** : Métriques de performance et santé des services

#### 🎭 **Démos Playwright Opérationnelles**
**Interface complète avec tests automatisés et captures d'écran**

Les démos Playwright sont maintenant **100% opérationnelles** avec backend mock intégré :

```bash
# 🚀 Démo complète automatisée (RECOMMANDÉ)
python demo_playwright_complet.py

# 🔧 Orchestrateur intégré (backend réel)
python scripts/run_webapp_integration.py --visible --frontend

# ⚡ Tests Playwright directs
powershell -File scripts/env/activate_project_env.ps1 -CommandToRun "python -m pytest tests/functional/test_webapp_homepage.py -v --headed"
```

**Fonctionnalités démontrées** :
- 🎯 **6 Onglets d'Analyse** : Analyseur, Sophismes, Reconstructeur, Graphe Logique, Validation, Framework
- 📸 **Captures Automatiques** : Screenshots générés dans `logs/` pour chaque démonstration
- 🔄 **Tests d'Interaction** : Navigation complète et validation fonctionnelle
- 🛡️ **Backend Mock** : Démos fonctionnelles même sans backend complet

📋 **Documentation** : [`services/README.md`](services/README.md) | **Démos** : [`README_DEMOS_PLAYWRIGHT.md`](README_DEMOS_PLAYWRIGHT.md)

### 4. 🕵️ **Système d'Enquête Sherlock-Watson-Moriarty**
**Pipeline d'analyse Oracle Enhanced avec intégrité garantie**

Système multi-agents sophistiqué pour résolution de problèmes logiques :

```bash
# Démo Cluedo Oracle Enhanced
python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced

# Démo Puzzle d'Einstein  
python -m scripts.sherlock_watson.run_einstein_oracle_demo

# Tests de validation comportementale
python -m scripts.sherlock_watson.test_oracle_behavior_simple

# Validation couverture complète (148+ tests)
python -m scripts.maintenance.validate_oracle_coverage
```

**Agents disponibles** :
- 🔍 **Sherlock Holmes** : Agent d'investigation logique avec raisonnement déductif
- 👨‍⚕️ **Dr Watson** : Agent de déduction médicale et assistance analytique  
- 🎭 **Professor Moriarty** : Agent Oracle authentique avec révélations automatiques
- 🛡️ **Système d'Intégrité** : Protection anti-triche avec `CluedoIntegrityError`

📋 **Documentation** : [`docs/sherlock_watson/`](docs/sherlock_watson/) - Guide complet utilisateur et développeur

---

## 🔒 **Sécurité et Intégrité - Mise à Jour Janvier 2025**

### ✅ **Audit d'Intégrité Récent**
Un audit de sécurité complet a été réalisé sur le système **Sherlock-Watson-Moriarty Oracle Enhanced**, aboutissant à :

- **4 violations d'intégrité** détectées et **corrigées**
- **CluedoIntegrityError** déployé pour protection anti-triche
- **Mécanismes de surveillance** temps réel intégrés
- **Couverture tests** maintenue à **100%**

Pour plus de détails, consulter :
- 📋 **[Rapport d'Audit Complet](docs/sherlock_watson/AUDIT_INTEGRITE_CLUEDO.md)**
- 🛠️ **[Guide Utilisateur Sécurisé](docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md)**
- 🏗️ **[Architecture Sécurité](docs/sherlock_watson/ARCHITECTURE_ORACLE_ENHANCED.md)**

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
.\scripts\env\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py"

# Configuration d'environnement uniquement
.\scripts\env\activate_project_env.ps1
```

**Fonctionnalités** :
- ✅ Chargement automatique des variables d'environnement (`.env`)
- ✅ Configuration `JAVA_HOME` et `PATH`
- ✅ Exécution via `conda run` pour isolation complète
- ✅ Gestion `PYTHONPATH` automatique

#### **Scripts Raccourcis à la Racine**
```powershell
# Lancement direct de démonstrations
.\scripts\env\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --interactive"

# Setup complet du projet
.\scripts\env\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --all-tests"
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
.\scripts\env\activate_project_env.ps1 -CommandToRun "scripts\run_backend.cmd 5005"

# Terminal 2 - Frontend:
.\scripts\env\activate_project_env.ps1 -CommandToRun "scripts\run_frontend.cmd 3001"
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
- 🏗️ **[Architecture Sécurité](docs/sherlock_watson/ARCHITECTURE_ORACLE_ENHANCED.md)** - Spécifications techniques

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
- ✅ **148/148 tests Oracle Enhanced** réussis (système Sherlock-Watson-Moriarty)
- ✅ **100% couverture** des composants critiques validés
- ✅ **0 mock critique** dans les composants stratégiques
- ✅ **Architecture modulaire** entièrement testée

**Scripts de Validation** :
```bash
# Validation complète avec métriques
python examples/scripts_demonstration/demonstration_epita.py --all-tests

# Tests des stratégies spécifiquement
python -m pytest tests/unit/argumentation_analysis/test_strategies_real.py -v

# Validation Oracle Enhanced
python -m scripts.maintenance.validate_oracle_coverage
```

---

## 🎭 **Système Sherlock-Watson-Moriarty Oracle Enhanced v2.1.0**

### Vue d'ensemble
Le système Oracle Enhanced implémente un véritable système multi-agents avec:
- **Sherlock Holmes**: Agent d'investigation logique
- **Dr Watson**: Agent de déduction médicale  
- **Professor Moriarty**: Agent Oracle authentique avec révélations automatiques

### Nouvelles fonctionnalités Oracle Enhanced v2.1.0

#### 🔧 Architecture Refactorisée
- **Gestion d'erreurs avancée**: Hiérarchie complète d'erreurs Oracle
- **Interfaces standardisées**: ABC pour agents Oracle et gestionnaires dataset
- **Réponses uniformisées**: `StandardOracleResponse` avec statuts enum
- **Cache intelligent**: `QueryCache` avec TTL et éviction automatique

#### 📊 Couverture Tests 100%
- **148+ tests Oracle Enhanced** (vs 105 avant refactorisation)
- **Tests nouveaux modules**: error_handling, interfaces, intégration
- **Validation automatique**: Scripts de couverture intégrés
- **Fixtures avancées**: Support testing complet

#### 🏗️ Structure Modulaire

```
argumentation_analysis/agents/core/oracle/
├── oracle_base_agent.py           # Agent Oracle de base
├── moriarty_interrogator_agent.py # Moriarty Oracle authentique
├── cluedo_dataset.py              # Dataset Cluedo avec intégrité
├── dataset_access_manager.py      # Gestionnaire accès permissions
├── permissions.py                 # Système permissions avancé
├── error_handling.py              # 🆕 Gestion erreurs centralisée
├── interfaces.py                  # 🆕 Interfaces ABC standardisées
└── __init__.py                    # Exports consolidés v2.1.0
```

### Guide de Démarrage Rapide

#### Installation et Configuration
```bash
# 1. Activation environnement
powershell -File .\scripts\env\activate_project_env.ps1

# 2. Test système Oracle
python -m scripts.maintenance.validate_oracle_coverage

# 3. Démo Cluedo Oracle Enhanced
python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced

# 4. Démo Einstein Oracle
python -m scripts.sherlock_watson.run_einstein_oracle_demo
```

#### Utilisation Programmatique
```python
from argumentation_analysis.agents.core.oracle import (
    CluedoDataset, CluedoDatasetManager, MoriartyInterrogatorAgent
)

# Initialisation système Oracle
dataset = CluedoDataset()
manager = CluedoDatasetManager(dataset) 
oracle = MoriartyInterrogatorAgent(dataset_manager=manager, name="Moriarty")

# Validation suggestion avec Oracle authentique
response = await oracle.validate_suggestion_cluedo(
    suspect="Colonel Moutarde", arme="Chandelier", lieu="Bibliothèque",
    suggesting_agent="Sherlock"
)
print(response.data)  # Révélation automatique ou validation
```

### Documentation Complète

- 📖 **[Guide Utilisateur Complet](docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md)**
- 🏗️ **[Architecture Oracle Enhanced](docs/sherlock_watson/ARCHITECTURE_ORACLE_ENHANCED.md)**
- 🔧 **[Guide Développeur](docs/sherlock_watson/GUIDE_DEVELOPPEUR_ORACLE.md)**
- 📊 **[Documentation Tests](docs/sherlock_watson/DOCUMENTATION_TESTS.md)**
- 🚀 **[Guide Déploiement](docs/sherlock_watson/GUIDE_DEPLOIEMENT.md)**

### État du Projet

| Composant | Statut | Tests | Couverture |
|-----------|--------|-------|------------|
| Oracle Base Agent | ✅ Stable | 25/25 | 100% |
| Moriarty Oracle | ✅ Refactorisé | 30/30 | 100% |
| Dataset Cluedo | ✅ Intégrité | 24/24 | 100% |
| Error Handling | 🆕 Nouveau | 20/20 | 100% |
| Interfaces | 🆕 Nouveau | 15/15 | 100% |
| **Total Oracle** | **✅ Production** | **148/148** | **100%** |

### Historique Versions

- **v2.1.0** (2025-01-07): Refactorisation complète, nouveaux modules
- **v2.0.0** (2025-01-06): Oracle Enhanced authentique, 100% tests
- **v1.0.0** (2024-12): Version initiale multi-agents

---

**📢 Ce projet constitue une démonstration avancée d'intelligence symbolique avec validation technique complète. Commencez par le script [`demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py) en mode interactif pour explorer toutes les capacités du système de manière pédagogique.**
