# 🕵️ Système Sherlock-Watson-Moriarty
## Index Principal - Documentation Complète

> **Système multi-agents de raisonnement collaboratif avec Oracle Enhanced**
> Version actuelle : Oracle Enhanced + Intégrité Cluedo Certifiée (Janvier 2025)

---

## 🎯 **ACCÈS RAPIDE**

| 🚀 **Je veux...** | 📖 **Document** | ⏱️ **Temps** |
|-------------------|-----------------|---------------|
| **Comprendre le système** | [📋 Vue d'ensemble](#-vue-densemble) | 5 min |
| **Installer et utiliser** | [🛠️ Guide Utilisateur](#️-guide-utilisateur-complet) | 15 min |
| **Comprendre l'architecture** | [🏗️ Architecture Technique](#️-architecture-technique) | 30 min |
| **Démarrer rapidement** | [⚡ Démarrage Express](#-démarrage-express) | 2 min |

---

## 📋 **VUE D'ENSEMBLE**

### Qu'est-ce que Sherlock-Watson-Moriarty ?

Le système **Sherlock-Watson-Moriarty** est une plateforme de **raisonnement collaboratif multi-agents** qui simule l'enquête de Sherlock Holmes assisté par le Dr. Watson et challengé par l'Oracle Moriarty.

#### 🎭 **Les 3 Agents Principaux**

| 🕵️ **Sherlock** | 🧪 **Watson** | 🎭 **Moriarty** |
|------------------|---------------|------------------|
| **Rôle :** Enquêteur principal | **Rôle :** Assistant logique | **Rôle :** Oracle détenteur de secrets |
| **Spécialité :** Hypothèses et déductions | **Spécialité :** Logique formelle (Tweety) | **Spécialité :** Révélations stratégiques |
| **Actions :** Suggestions, solutions | **Actions :** Validation, formalisation | **Actions :** Révélations, réfutations |

#### 🎮 **Types de Problèmes Supportés**

1. **🎲 Énigmes Cluedo** - Révélations progressives de cartes (🆕 Oracle Enhanced)
2. **🧩 Énigmes d'Einstein** - Indices progressifs pour déduction logique (🆕 Nouveau)
3. **🔗 Problèmes de Logique** - Contraintes formelles complexes
4. **🚧 Extensions Futures** - Enquêtes policières, puzzles mathématiques

---

## ⚡ **DÉMARRAGE EXPRESS**

### Installation Rapide (2 minutes)

```powershell
# 1. Activer l'environnement
powershell -c "& .\scripts\activate_project_env.ps1"

# 2. Démo Cluedo Oracle Enhanced
python scripts\sherlock_watson\run_cluedo_oracle_enhanced.py

# 3. Démo Einstein avec indices progressifs  
python scripts\sherlock_watson\run_einstein_oracle_demo.py
```

### 🎯 **Nouveautés Oracle Enhanced + Intégrité Certifiée**

- ✅ **Moriarty Oracle authentique** : Révélations automatiques vs suggestions triviales
- ✅ **Démo Einstein** : Indices progressifs pour résolution logique
- ✅ **Workflow 3-agents** : Sherlock → Watson → Moriarty avec orchestration cyclique
- ✅ **Scripts dédiés** : Exécution simplifiée des différentes démos
- 🛡️ **INTÉGRITÉ CLUEDO** : Tests 100% AVEC respect strict des règles
- 🔒 **ANTI-TRICHE** : CluedoIntegrityError et protections renforcées

---

## 🛠️ **GUIDE UTILISATEUR COMPLET**

### 📖 [GUIDE_UTILISATEUR_COMPLET.md](GUIDE_UTILISATEUR_COMPLET.md)

**Contenu détaillé :**
- 🔧 **Installation complète** - Environnement Conda epita_symbolic_ai_sherlock
- 🚀 **Configuration** - Scripts activate_project_env.ps1 et dépendances
- 📋 **Guide d'utilisation** - Exemples pour chaque type de démo
- 🔍 **Exemples concrets** - Captures de logs et résultats attendus  
- 🚨 **Troubleshooting** - Solutions aux problèmes courants

**Sections principales :**
1. [Installation et Configuration](GUIDE_UTILISATEUR_COMPLET.md#installation-et-configuration)
2. [Démo Cluedo Oracle Enhanced](GUIDE_UTILISATEUR_COMPLET.md#démo-cluedo-oracle-enhanced) 
3. [Démo Einstein Oracle](GUIDE_UTILISATEUR_COMPLET.md#démo-einstein-oracle)
4. [Scripts Avancés](GUIDE_UTILISATEUR_COMPLET.md#scripts-avancés)
5. [Dépannage](GUIDE_UTILISATEUR_COMPLET.md#dépannage)

---

## 🏗️ **ARCHITECTURE TECHNIQUE**

### 📐 [DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md)

**Architecture système complète :**
- 🏛️ **Vue d'ensemble multi-agents** - Rôles, interactions, orchestration
- 🔄 **Pattern Oracle Enhanced** - Révélations automatiques vs suggestions
- 🎯 **Workflows supportés** - 2-agents (Sherlock+Watson) vs 3-agents (+Moriarty)
- 📊 **États partagés** - EnqueteCluedoState, EinsteinsRiddleState, etc.
- 🔧 **Extensibilité** - Framework pour nouveaux types d'enquêtes

**Sections techniques :**
1. [Architecture Multi-Agents](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md#architecture-multi-agents)
2. [Pattern Oracle Enhanced](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md#pattern-oracle-enhanced)
3. [États et Orchestration](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md#états-et-orchestration)
4. [Extensibilité](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md#extensibilité)

### 🔧 [ARCHITECTURE_TECHNIQUE_DETAILLEE.md](ARCHITECTURE_TECHNIQUE_DETAILLEE.md)

**Intégrations techniques approfondies :**
- ⚙️ **Semantic Kernel v1.29.0** - Orchestration des agents et plugins
- ☕ **Tweety JVM Integration** - 35+ JAR files pour logique propositionnelle
- 🔄 **Workarounds Pydantic** - Contournements avec object.__setattr__()
- 🎯 **Stratégies d'orchestration** - Cyclique, adaptative, ML-driven (futur)
- 🔐 **Gestion d'erreurs** - Timeouts OpenAI, recovery JVM, validation entrées

**Sections détaillées :**
1. [Intégration Semantic Kernel](ARCHITECTURE_TECHNIQUE_DETAILLEE.md#intégration-semantic-kernel)
2. [Bridge Tweety JVM](ARCHITECTURE_TECHNIQUE_DETAILLEE.md#bridge-tweety-jvm)  
3. [Workarounds Techniques](ARCHITECTURE_TECHNIQUE_DETAILLEE.md#workarounds-techniques)
4. [Performance et Optimisation](ARCHITECTURE_TECHNIQUE_DETAILLEE.md#performance-et-optimisation)

---

## 📊 **ANALYSE ET MÉTRIQUES**

### 📈 [analyse_orchestrations_sherlock_watson.md](../analyse_orchestrations_sherlock_watson.md)

**Analyse des performances et patterns :**
- 📊 **Métriques de performance** - Temps de résolution, taux de succès
- 🔄 **Patterns d'orchestration** - Séquentiel, cyclique, adaptatif
- ⚖️ **Comparaison workflows** - 2-agents vs 3-agents avec Oracle
- 🎯 **Optimisations** - TweetyBridge pool, caching, stratégies ML
- 🚀 **Roadmap évolution** - Extensions futures et innovations

### 📋 [RAPPORT_MISSION_ORACLE_ENHANCED.md](RAPPORT_MISSION_ORACLE_ENHANCED.md)

**Rapport de mission Oracle Enhanced :**
- 🎯 **Problème identifié** - Moriarty suggestions triviales vs révélations Oracle
- ✅ **Solutions implémentées** - Révélations automatiques + démo Einstein
- 📄 **Livrables créés** - Scripts dédiés et orchestrateur étendu
- 🧪 **Tests et validation** - Démonstrations conceptuelles réussies

---

## 🗂️ **STRUCTURE DOCUMENTAIRE COMPLÈTE**

```
docs/sherlock_watson/
├── README.md                                    📖 Index principal (ce document)
├── DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md   🏗️ Architecture complète  
├── GUIDE_UTILISATEUR_COMPLET.md                🛠️ Installation et usage
├── ARCHITECTURE_TECHNIQUE_DETAILLEE.md         🔧 Intégrations techniques
├── RAPPORT_MISSION_ORACLE_ENHANCED.md          📋 Rapport mission Oracle
└── Historique/
    ├── documentation_phase_a_personnalites_distinctes.md
    ├── documentation_phase_b_naturalite_dialogue.md  
    ├── documentation_phase_c_fluidite_transitions.md
    ├── documentation_phase_d_trace_ideale.md
    ├── GUIDE_DEMARRAGE_RAPIDE.md
    └── MISSION_SHERLOCK_WATSON_COMPLETE.md
```

### 📚 **Documentation Projet Globale**

- 📐 [DOC_CONCEPTION_SHERLOCK_WATSON.md](../DOC_CONCEPTION_SHERLOCK_WATSON.md) - Conception originale
- 🔄 [DOC_CONCEPTION_SHERLOCK_WATSON_MISE_A_JOUR.md](../DOC_CONCEPTION_SHERLOCK_WATSON_MISE_A_JOUR.md) - Évolutions et roadmap
- 📊 [analyse_orchestrations_sherlock_watson.md](../analyse_orchestrations_sherlock_watson.md) - Analyse performances

---

## 🛡️ **AUDIT D'INTÉGRITÉ CLUEDO (JANVIER 2025)**

### ✅ **CERTIFICATION INTÉGRITÉ**
- **4 violations critiques** détectées et corrigées
- **Tests à 100%** maintenus AVEC respect strict des règles
- **CluedoIntegrityError** pour protections anti-triche
- **Permissions renforcées** dans le système Oracle

### 📋 **Documentation Audit**
- 📊 [AUDIT_INTEGRITE_CLUEDO.md](AUDIT_INTEGRITE_CLUEDO.md) - Rapport complet d'audit
- 🧪 Tests d'intégrité : `test_validation_integrite_apres_corrections.py` (8/8 ✅)
- 🎮 Tests fonctionnels : `test_cluedo_dataset_simple.py` (5/5 ✅)

### 🔒 **Mécanismes de Sécurité**
- **Violation #1** : `get_autres_joueurs_cards()` → Méthode sécurisée
- **Violation #2** : `get_solution()` → Accès bloqué avec PermissionError
- **Violation #3** : `simulate_other_player_response()` → Simulation légitime
- **Violation #4** : Permissions système renforcées

---

## 🎯 **PROCHAINES ÉTAPES**

### Phase 1 - Consolidation (✅ TERMINÉE)
- ✅ **Oracle Enhanced** - Moriarty révélations authentiques
- ✅ **Démo Einstein** - Indices progressifs
- ✅ **Intégrité Cluedo** - Audit complet et corrections
- ✅ **Documentation complète** - Suite documentaire structurée
- ✅ **Tests intégration** - Validation workflows 2-agents et 3-agents

### Phase 2 - Extensions (2-4 mois)
- 🚀 **Oracle multi-datasets** - Support différents types d'enquêtes
- 🎨 **Interface utilisateur** - Dashboard de visualisation
- 📊 **Métriques avancées** - Performance monitoring temps réel
- 🔧 **API standardisée** - Framework extensible

### Phase 3 - Innovation (4-6 mois)  
- 🤖 **ML-driven orchestration** - Sélection adaptative d'agents
- 🔬 **Capacités émergentes** - Raisonnement causal, méta-raisonnement
- 🌐 **Systèmes multi-agents** - Équipes spécialisées collaboratives

---

## 🤝 **CONTRIBUTION ET SUPPORT**

### Comment Contribuer
- 📝 **Documentation** - Améliorations et corrections
- 🧪 **Tests** - Nouveaux scénarios et cas d'usage  
- 🚀 **Fonctionnalités** - Extensions et optimisations
- 🐛 **Bugs** - Signalement et corrections

### Support Technique
- 📧 **Équipe Projet** - Sherlock/Watson Development Team
- 📚 **Documentation** - Guides utilisateur et architecture
- 🔧 **Troubleshooting** - Solutions aux problèmes courants

---

**🎉 Bienvenue dans l'écosystème Sherlock-Watson-Moriarty !**

*Explorez, expérimentez et contribuez à l'avenir du raisonnement collaboratif multi-agents.*