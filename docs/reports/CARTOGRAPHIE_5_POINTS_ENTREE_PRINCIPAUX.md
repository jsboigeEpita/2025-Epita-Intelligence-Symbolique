# 🗺️ CARTOGRAPHIE DES 5 POINTS D'ENTRÉE PRINCIPAUX
# Système d'Intelligence Symbolique EPITA 2025

> **Date de cartographie** : 10 juin 2025 14:35  
> **Status** : ✅ CARTOGRAPHIE COMPLÈTE VALIDÉE  
> **Révision** : v2.1 - Post-consolidation du 10/06/2025  
> **Contexte** : 420 fichiers modifiés, 110K+ insertions lors du dernier pull  

---

## 📋 SYNTHÈSE EXÉCUTIVE

Ce système d'intelligence symbolique est un **framework multi-agents** sophistiqué pour l'**analyse argumentative et rhétorique** avec intégration **TweetyProject** (Java-Python). Il propose 5 points d'entrée distincts selon les besoins utilisateur, du simple test web à la validation système complète.

### 🏗️ Architecture Globale
- **Agents spécialisés** : Logic, Informal, Extract, Oracle, PM
- **Orchestrateurs** : Cluedo, Einstein, Sherlock-Watson, Conversation
- **Pipeline unifié** : Analyse rhétorique, détection de sophismes, génération de rapports
- **Interface multi-mode** : Web (Flask), CLI, Jupyter, Scripts
- **Intégration Java** : TweetyProject via JPype pour logique formelle

---

## 🎯 POINT D'ENTRÉE #1 : INTERFACE WEB INTERACTIVE

### 📍 Fichier Principal
```bash
interface_web/app.py
```

### 🎯 Description
**Interface web Flask moderne** pour l'analyse argumentative interactive. Point d'entrée **grand public** et **étudiants**.

### 🚀 Lancement
```bash
# Depuis la racine du projet
cd interface_web
python app.py

# Ou avec Flask directement
flask run --host=0.0.0.0 --port=5000
```

### 🌐 Accès
- **URL locale** : http://localhost:5000
- **Interface** : `templates/index.html` (23.9 KB, interface complète)

### ⚡ Fonctionnalités Clés
- ✅ **Analyse de texte** en temps réel via `/analyze`
- ✅ **Détection de sophismes** automatique
- ✅ **Visualisation des résultats** avec métriques
- ✅ **Mode dégradé** si ServiceManager indisponible
- ✅ **API REST** pour intégration externe
- ✅ **Status endpoint** (`/status`) pour monitoring

### 🔧 Configuration
- **SECRET_KEY** : Variable d'environnement ou 'dev-key-EPITA-2025'
- **MAX_CONTENT_LENGTH** : 16MB maximum
- **CORS** : Activé pour tous domaines
- **ServiceManager** : Auto-détection avec fallback

### 📊 Status Technique
- ✅ **Fonctionnel** : Tests validés
- ✅ **ServiceManager** : Intégration complète
- ✅ **CORS** : Configuration appropriée
- ⚠️ **Mode dégradé** : Disponible si dépendances manquantes

---

## 🎯 POINT D'ENTRÉE #2 : DÉMO EPITA COMPLÈTE

### 📍 Fichier Principal
```bash
demos/demo_epita_diagnostic.py
```

### 🎯 Description
**Démonstration pédagogique complète** conçue spécifiquement pour le contexte **EPITA**. Showcase complet du système avec diagnostic intégré.

### 🚀 Lancement
```bash
# Depuis la racine du projet
python demos/demo_epita_diagnostic.py

# Ou pour tests spécifiques
python demos/validation_complete_epita.py
```

### 📚 Composants de Démo
1. **ServiceManager** : `demos/playwright/demo_service_manager_validated.py`
2. **Interface Web** : `demos/playwright/test_interface_demo.html`
3. **Tests Playwright** : 9 tests fonctionnels documentés
4. **Validation complète** : `demos/validation_complete_epita.py` (41.6 KB)

### ⚡ Fonctionnalités Démonstrées
- 🎭 **8 modes de démonstration** (educational, research, showcase...)
- 🔍 **Correction intelligente** des erreurs modales
- 🎯 **Orchestrateur master** de validation
- 📊 **Métriques de performance** détaillées
- 🧪 **Tests end-to-end** avec Playwright
- 📈 **Rapports JSON** structurés

### 📊 Évaluation Pédagogique
- ⭐⭐⭐⭐⭐ **Interface web** : PARFAITEMENT opérationnelle
- ⭐⭐⭐⭐⭐ **ServiceManager** : COMPLÈTEMENT fonctionnel
- ⭐⭐⭐⭐ **Documentation** : 9 tests Playwright documentés
- ⚠️ **Système unifié** : Dépendances semantic_kernel.agents

### 🔧 Configuration Requise
- **Python 3.9+** avec dépendances
- **Playwright** pour tests E2E
- **ServiceManager** pour orchestration
- **Variables d'environnement** : `.env` configuré

---

## 🎯 POINT D'ENTRÉE #3 : ORCHESTRATEUR PRINCIPAL

### 📍 Fichier Principal
```bash
argumentation_analysis/main_orchestrator.py
```

### 🎯 Description
**Orchestrateur principal** du système d'analyse rhétorique multi-agents. Point d'entrée **technique avancé** pour analyse approfondie.

### 🚀 Lancement
```bash
# Mode interactif avec UI
python argumentation_analysis/main_orchestrator.py

# Mode automatique sans UI
python argumentation_analysis/main_orchestrator.py --skip-ui

# Avec fichier texte spécifique
python argumentation_analysis/main_orchestrator.py --skip-ui --text-file=/path/to/text.txt
```

### 🔄 Flux d'Exécution
1. **Chargement environnement** : `.env` avec clés API
2. **Configuration logging** : Multi-niveaux avec filtres
3. **Initialisation JVM** : TweetyProject via JPype
4. **Service LLM** : OpenAI/Azure avec Semantic Kernel
5. **Interface utilisateur** : `ui.app.configure_analysis_task()`
6. **Analyse collaborative** : `orchestration.analysis_runner`
7. **Rapport final** : Logs et état détaillé

### ⚡ Agents Orchestrés
- 🧠 **InformalAgent** : Analyse rhétorique et sophismes
- 🔗 **LogicAgent** : Raisonnement formel (TweetyProject)
- 📑 **ExtractAgent** : Extraction d'arguments
- 🔮 **OracleAgent** : Accès aux données de référence
- 📋 **PMAgent** : Gestion de projet et synthèse

### 🔧 Prérequis Techniques
- **JDK 11+** : `JAVA_HOME` configuré
- **TweetyProject JARs** : Dans `tests/resources/libs/`
- **Variables d'environnement** : `OPENAI_API_KEY`, `TEXT_CONFIG_PASSPHRASE`
- **Fichier chiffré** : `data/extract_sources.json.gz.enc`

### 📊 Status Technique
- ✅ **Architecture modulaire** : Composants bien séparés
- ✅ **Gestion d'erreurs** : Robuste avec fallbacks
- ⚠️ **JVM optionnelle** : Mode dégradé si échec
- ✅ **Logging configuré** : Multi-niveaux avec filtres

---

## 🎯 POINT D'ENTRÉE #4 : SYSTÈME SHERLOCK-WATSON

### 📍 Fichier Principal
```bash
scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py
```

### 🎯 Description
**Système d'agents d'enquête** inspiré de Sherlock Holmes, Watson et Moriarty. Démonstration avancée du **raisonnement collaboratif** entre agents spécialisés.

### 🚀 Lancement
```bash
# Système complet avec 3 agents
python scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py

# Version simplifiée sans Tweety
python scripts/sherlock_watson/run_sherlock_watson_moriarty_no_tweety.py

# Orchestration dynamique
python scripts/sherlock_watson/orchestrate_dynamic_cases.py
```

### 🕵️ Agents Spécialisés
- 🔍 **Sherlock** : Agent d'enquête principal (`SherlockEnqueteAgent`)
- 🧠 **Watson** : Assistant logique (`WatsonLogicAssistant`)
- 😈 **Moriarty** : Interrogateur contradictoire (`MoriartyInterrogatorAgent`)

### 🎭 Cas d'Usage
- 🏛️ **Cluedo Oracle** : Résolution de mystères avec états
- 🧮 **Einstein Demo** : Problèmes logiques complexes
- 🔍 **Enquêtes dynamiques** : Cas générés automatiquement
- 📊 **Validation comportementale** : Tests des interactions

### ⚡ Fonctionnalités Avancées
- 🔄 **État partagé** : `CluedoOracleState` pour coordination
- 🎪 **Plugin system** : `EnqueteStateManagerPlugin`
- 🤖 **Semantic Kernel** : Agents conversationnels
- 📝 **Traces complètes** : Logs détaillés des raisonnements
- 🎯 **Modes de validation** : Point 1, 2, 3 avec métriques

### 🔧 Configuration Spécialisée
- **Environnement** : `projet-is` dédié
- **Logging UTF-8** : Traces multilingues
- **Variables d'environnement** : Chargement automatique
- **Gestion mémoire** : Optimisée pour agents multiples

### 📊 Status de Validation
- ✅ **Agents fonctionnels** : Import et exécution OK
- ✅ **Orchestration** : Coordination entre agents
- ✅ **Cas de test** : Crimes et énigmes variés
- ⚠️ **Dépendances complexes** : Semantic Kernel requis

---

## 🎯 POINT D'ENTRÉE #5 : VALIDATION SYSTÈME COMPLÈTE

### 📍 Fichier Principal
```bash
scripts/validation/validation_reelle_systemes.py
```

### 🎯 Description
**Suite de validation complète** avec appels **réels** aux systèmes existants. Point d'entrée **qualité et tests** pour validation exhaustive.

### 🚀 Lancement
```bash
# Validation complète avec données fraîches
python scripts/validation/validation_reelle_systemes.py

# Validation simplifiée
python scripts/validation/validation_donnees_fraiches_simple.py

# Tests avec données complètes
python scripts/validation/validation_complete_donnees_fraiches.py
```

### 🧪 Systèmes Validés
1. **Système rhétorique** : Analyse argumentative complète
2. **Sherlock-Watson** : Agents d'enquête collaboratifs
3. **Démo EPITA** : Fonctionnalités pédagogiques
4. **API Web** : Interface Flask et endpoints
5. **Intégration globale** : Tests bout-en-bout

### 📊 Métriques Collectées
- ⏱️ **Performance** : Temps d'exécution, latence
- 🎯 **Précision** : Détection sophismes, extraction arguments
- 🔧 **Robustesse** : Gestion d'erreurs, fallbacks
- 📈 **Couverture** : Tests fonctionnels et intégration
- 🌐 **Compatibilité** : Multi-plateforme, environnements

### 📝 Données de Test Fraîches
- **Texte contemporain** : Débat IA/régulation 2025
- **Crime inédit** : "Vol de l'Algorithme Quantique"
- **Données structurées** : JSON avec cas complexes
- **Scénarios réels** : Problèmes argumentatifs actuels

### 🎯 Rapports Générés
- **Trace complète** : `logs/validation_reelle_YYYYMMDD_HHMMSS.log`
- **Rapport MD** : `RAPPORT_VALIDATION_REELLE_*.md`
- **Métriques JSON** : Données structurées pour analyse
- **Dashboard** : Visualisation des résultats

### ⚡ Fonctionnalités Avancées
- 🔄 **Tests en continu** : Intégration CI/CD
- 📊 **Benchmarking** : Comparaisons historiques
- 🎛️ **Configuration flexible** : Paramètres modulaires
- 🚨 **Alertes automatiques** : Notifications si régression
- 📈 **Tendances** : Évolution qualité dans le temps

### 🔧 Configuration Requise
- **Environnement complet** : Toutes dépendances installées
- **Accès API** : Clés OpenAI/Azure configurées
- **Permissions** : Écriture logs et rapports
- **Ressources** : CPU/RAM suffisants pour tests lourds

---

## 🗺️ MATRICE DE CHOIX DU POINT D'ENTRÉE

| **Utilisateur** | **Objectif** | **Point d'Entrée Recommandé** | **Complexité** |
|-----------------|--------------|--------------------------------|----------------|
| 🎓 **Étudiant EPITA** | Découverte interactive | #1 Interface Web | ⭐ Facile |
| 👨‍🏫 **Enseignant** | Démonstration pédagogique | #2 Démo EPITA | ⭐⭐ Moyenne |
| 🔬 **Chercheur** | Analyse approfondie | #3 Orchestrateur Principal | ⭐⭐⭐ Avancée |
| 🕵️ **Développeur IA** | Agents collaboratifs | #4 Sherlock-Watson | ⭐⭐⭐⭐ Expert |
| 🧪 **QA/DevOps** | Tests et validation | #5 Validation Système | ⭐⭐⭐⭐⭐ Expert+ |

---

## 📋 DÉPENDANCES COMMUNES

### 🐍 Python (Requis)
```bash
# Version recommandée
Python 3.9+

# Dépendances principales
pip install -r requirements.txt

# Packages critiques
pip install flask semantic-kernel jpype1 playwright asyncio
```

### ☕ Java (Optionnel)
```bash
# Pour TweetyProject (agents logiques)
JDK 11+ avec JAVA_HOME configuré

# JARs automatiquement téléchargés dans:
tests/resources/libs/
```

### 🔑 Variables d'Environnement
```bash
# Fichier .env à la racine
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL_ID=gpt-4
TEXT_CONFIG_PASSPHRASE=votre_phrase_secrete
JAVA_HOME=/path/to/jdk
PYTHONIOENCODING=utf-8
```

### 📁 Structure Projet Critique
```
├── interface_web/          # Point d'entrée #1
├── demos/                  # Point d'entrée #2
├── argumentation_analysis/ # Point d'entrée #3
├── scripts/sherlock_watson/ # Point d'entrée #4
├── scripts/validation/     # Point d'entrée #5
├── data/                   # Données chiffrées
├── tests/resources/libs/   # JARs TweetyProject
└── .env                    # Configuration
```

---

## 🚀 GUIDE DE DÉMARRAGE RAPIDE

### 1️⃣ Installation Express
```bash
# Cloner et configurer
git clone [repo]
cd 2025-Epita-Intelligence-Symbolique
cp .env.example .env
# Éditer .env avec vos clés API

# Installer dépendances
pip install -r requirements.txt
```

### 2️⃣ Test Rapide (Interface Web)
```bash
cd interface_web
python app.py
# → http://localhost:5000
```

### 3️⃣ Démo Complète (EPITA)
```bash
python demos/demo_epita_diagnostic.py
# → Rapport de diagnostic complet
```

### 4️⃣ Validation (Optionnelle)
```bash
python scripts/validation/validation_donnees_fraiches_simple.py
# → Tests des 5 systèmes principaux
```

---

## 📞 SUPPORT ET RESSOURCES

### 📚 Documentation Détaillée
- **Architecture** : `argumentation_analysis/README.md`
- **API Web** : `interface_web/templates/index.html`
- **Tests** : `demos/playwright/README.md`
- **Agents** : `scripts/sherlock_watson/`
- **Configuration** : `.env.example`

### 🔧 Dépannage Commun
- **Import errors** : Vérifier PYTHONPATH et structure
- **JVM errors** : Contrôler JAVA_HOME et JARs
- **API errors** : Valider clés dans .env
- **Encoding** : Configurer PYTHONIOENCODING=utf-8

### 📊 Monitoring
- **Status Web** : http://localhost:5000/status
- **Logs système** : `logs/` dans chaque module
- **Métriques** : Rapports JSON dans `results/`

---

**🎯 Version** : 2.1 - Cartographie complète post-consolidation  
**📅 Dernière mise à jour** : 10 juin 2025  
**✅ Status** : SYSTÈME PRÊT POUR PRODUCTION EPITA 2025