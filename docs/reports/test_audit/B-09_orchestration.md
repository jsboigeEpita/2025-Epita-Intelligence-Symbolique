# B-09: Audit — `tests/unit/orchestration/`

**Track**: B-09 #765 (Epic B #743)
**Date**: 2026-05-31
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 15 fichiers de test, 360 tests collectés (1 fichier `conftest.py`)

---

## Méthodologie

Même classification a/b/c que B-01 à B-07. Le wiring se vérifie par :
- **CapabilityRegistry** : grep dans `registry_setup.py` et `invoke_callables.py`
- **Workflows** : grep dans `workflows.py` pour les 16+ workflows définis
- **Pipeline actif** : `unified_pipeline.py` + `run_unified_analysis()`

**Note contextuelle** : `tests/unit/orchestration/` teste les composants d'orchestration — c'est le cœur du pipeline. Cependant, une grande partie teste l'**architecture hiérarchique** (Strategic/Tactical/Operational) qui est un mode **dormant** (non activé dans les workflows CapabilityRegistry). Le seul composant "hierarchical" wiré est `hierarchical_fallacy_detection` (capability invoke, pas l'architecture complète).

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 0 | 0 | 0% |
| **(b) Non-wiré** | 13 | ~330 | 91% |
| **(c) Justifié** | 2 | ~30 | 9% |

---

## Tableau de classification

### (a) DEAD — Composant sans consommateur

Aucun fichier. Tous les modules testés ont au moins des scripts de validation comme consumers.

---

### (b) UNWIRED — Architecture hiérarchique (dormant) + orchestrateurs legacy

#### Architecture hiérarchique (10 fichiers, ~306 tests)

Le système hiérarchique (Strategic → Tactical → Operational) est un mode d'orchestration **DORMANT**. Les 3 niveaux et leurs composants (managers, states, planners, resolvers, monitors, feedback) existent dans `argumentation_analysis/orchestration/hierarchical/` mais ne sont pas wirés dans le CapabilityRegistry. Le pipeline actif utilise le mode **Sequential** (WorkflowExecutor + invoke_callables) et le mode **Conversational** (AgentGroupChat SK).

| # | Fichier | Composant testé | Importé par | Tests | Rôle |
|---|---------|-----------------|-------------|-------|------|
| 1 | `hierarchical/operational/test_operational_state.py` | `OperationalState` | Modules hiérarchiques (internes) | 43 | State du niveau opérationnel |
| 2 | `hierarchical/strategic/test_strategic_planner.py` | `StrategicPlanner` | Modules hiérarchiques (internes) | 40 | Planification stratégique |
| 3 | `hierarchical/operational/test_feedback_mechanism.py` | `FeedbackMechanism` | Modules hiérarchiques (internes) | 40 | Mécanisme de feedback opérationnel |
| 4 | `hierarchical/tactical/test_progress_monitor.py` | `ProgressMonitor` | Modules hiérarchiques (internes) | 39 | Monitoring progression tactique |
| 5 | `hierarchical/strategic/test_resource_allocator.py` | `ResourceAllocator` | Modules hiérarchiques (internes) | 34 | Allocation de ressources |
| 6 | `hierarchical/templates/test_templates.py` | Templates hiérarchiques | Modules hiérarchiques (internes) | 32 | Templates de tâches |
| 7 | `hierarchical/strategic/test_strategic_state.py` | `StrategicState` | Modules hiérarchiques (internes) | 29 | State du niveau stratégique |
| 8 | `hierarchical/tactical/test_tactical_state.py` | `TacticalState` | Modules hiérarchiques (internes) | 22 | State du niveau tactique |
| 9 | `hierarchical/tactical/test_tactical_resolver.py` | `TacticalResolver` | Modules hiérarchiques (internes) | 16 | Résolution de conflits tactique |
| 10 | `hierarchical/tactical/test_tactical_resolver_advanced.py` | `TacticalResolver` (avancé) | Modules hiérarchiques (internes) | 7 | Résolution avancée |

**Pourquoi UNWIRED** : L'architecture hiérarchique est auto-consommée (les modules hiérarchiques s'importent entre eux) mais n'est pas activée dans le CapabilityRegistry. Le seul composant "hierarchical" wiré est `hierarchical_fallacy_detection` — un invoke callable qui utilise la taxonomy hiérarchique pour la détection de sophismes, mais **ne délègue pas** au StrategicManager/TacticalState/OperationalState. Les tests couvrent une architecture complète qui n'est pas le chemin d'exécution actif.

#### Orchestrateurs legacy (3 fichiers, ~43 tests)

| # | Fichier | Composant testé | Importé par | Tests | Pourquoi UNWIRED |
|---|---------|-----------------|-------------|-------|-------------------|
| 11 | `test_unified_orchestrations.py` | `ConversationOrchestrator`, `RealLLMOrchestrator` | `service_manager.py`, scripts validation | 23 | ConversationOrchestrator importé par l'ancien système (service_manager, main_orchestrator, unified_text_analysis). RealLLMOrchestrator déprécié Sprint 13. Pas dans CapabilityRegistry. |
| 12 | `test_hierarchical_managers.py` | `StrategicManager`, `TaskCoordinator`, `OperationalManager` | Modules hiérarchiques (internes) | 12 | 3 managers hiérarchiques — mode dormant. |
| 13 | `test_specialized_orchestrators.py` | `CluedoOrchestrator`, `ConversationOrchestrator`, `LogiqueComplexeOrchestrator` | `service_manager.py`, scripts validation | 8 | Orchestrators spécialisés pré-CapabilityRegistry. Pas enregistrés dans le registry. |

---

### (c) JUSTIFIÉ — Composants wirés dans le pipeline

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `engine/test_main_orchestrator.py` | `MainOrchestrator` | **Orchestrateur principal** avec stratégie selection. Importé par `service_manager.py` et scripts de validation. Point d'entrée CLI (`run_orchestration.py`). C'est le routeur d'orchestrateurs — il délègue au mode pipeline/conversational/legacy. | 12 |
| 2 | `engine/test_strategies.py` | `OrchestrationStrategy` | **Stratégies d'orchestration** (modes pipeline/conversational/legacy). Utilisées par `MainOrchestrator` pour sélectionner le mode d'exécution. | 3 |

**Note sur `MainOrchestrator`** : Bien qu'il ne soit pas dans le CapabilityRegistry (il est le routeur AU-DESSUS du registry), c'est un composant actif de l'architecture — le CLI `run_orchestration.py` l'utilise pour router vers le CapabilityRegistry. Sa classification JUSTIFIÉ reflète son rôle de façade.

---

## Récit du framework — 3 épisodes

### Épisode 1 : L'architecture hiérarchique ambitieuse (~2025-Q2)

Le répertoire `hierarchical/` cristallise une **architecture hiérarchique complète** à 3 niveaux :
- **Stratégique** : `StrategicPlanner` (planification), `ResourceAllocator` (allocation), `StrategicState` (state), `StrategicManager` (coordination)
- **Tactique** : `ProgressMonitor` (monitoring), `TacticalState` (state), `TacticalResolver` (résolution conflits)
- **Opérationnel** : `OperationalState` (state), `FeedbackMechanism` (feedback), adapters (rhetorical, informal, PL, extract)

Cette architecture est auto-consommée (les niveaux s'importent entre eux via les interfaces `strategic_tactical.py` et `tactical_operational.py`). Le `MainOrchestrator` peut théoriquement router vers ce mode hiérarchique. Mais en pratique, le pipeline actif utilise le mode **Sequential** (WorkflowExecutor + DAG de phases) ou **Conversational** (SK AgentGroupChat).

**Trace dans les tests** : 306 tests couvrent les 10 composants hiérarchiques (43+40+40+39+34+32+29+22+16+7). Chaque niveau a son propre state, manager, et logique de communication. Les tests mockent systématiquement les niveaux adjacents, indiquant une architecture conçue pour l'isolation.

### Épisode 2 : Les orchestrateurs spécialisés pré-Lego (~2025-Q2-Q3)

Les 3 orchestrateurs spécialisés (`CluedoOrchestrator`, `ConversationOrchestrator`, `LogiqueComplexeOrchestrator`) représentent l'architecture **pré-CapabilityRegistry** où chaque mode d'analyse avait son propre orchestrateur monolithique. Le `MainOrchestrator` servait de routeur pour sélectionner entre ces modes.

**Trace** : `test_specialized_orchestrators.py` (8 tests) mockent le Kernel SK et testent l'initialisation de chaque orchestrateur. `test_unified_orchestrations.py` (23 tests) teste `ConversationOrchestrator` et `RealLLMOrchestrator` ensemble — une suite d'intégration pré-Lego. Le `CluedoOrchestrator` est référencé dans le `MainOrchestrator` comme mode "cluedo" mais le pipeline Cluedo actif passe par `sherlock_modern_workflow` (CapabilityRegistry).

### Épisode 3 : La cohabitation Legacy/Registry (~2025-Q4 → 2026)

Les orchestrateurs legacy cohabitent avec le CapabilityRegistry. Le `MainOrchestrator` est le **dernier pont** — il route vers les modes pipeline/conversational/legacy. Mais le pipeline actif (`unified_pipeline.py` + CapabilityRegistry) ne passe PAS par le `MainOrchestrator`. Il est appelé directement par :
- `api/main.py` (FastAPI)
- `argumentation_analyzer.py` (façade)
- Scripts d'évaluation et de benchmark

Le `MainOrchestrator` reste le point d'entrée CLI (`run_orchestration.py --mode pipeline|conversational|legacy`), justifiant sa classification (c).

**Trace** : `test_main_orchestrator.py` (12 tests) mocke le Kernel et teste la sélection de stratégie. Le `MainOrchestrator` importe les orchestrateurs spécialisés mais les initialise uniquement si le mode est sélectionné. C'est un routeur lazy — il ne charge pas l'architecture hiérarchique par défaut.

---

## Capabilities muettes détectées

Ce packet couvre le cœur du pipeline. Les capabilities suivantes, bien que wirées dans le CapabilityRegistry, ont une **couverture test indirecte** (testée via les invoke_callables mais pas via des tests d'orchestration dédiés) :

| Capability | Wirée dans | Testée via | Gap |
|-----------|------------|------------|-----|
| `hierarchical_fallacy_detection` | registry_setup.py + workflows.py | invoke_callables (B-02) | Pas de test orchestration dédié |
| Mode hierarchical complet | — | 306 tests (dormant) | Mode jamais activé |

---

## Actions recommandées

### Priorité HAUTE — Architecture hiérarchique dormante (306 tests)

| Action | Fichiers | Impact |
|--------|----------|--------|
| Décision architecture | 10 fichiers hierarchical/ | 306 tests couvrant un mode jamais activé |

**Options** :
- **Option A (Archiver)** : Marquer `@pytest.mark.skip("hierarchical mode dormant — not in active pipeline")` sur les 10 fichiers. Réduit le packet de 85%.
- **Option B (Wirer)** : Activer le mode hierarchical comme 4ème mode d'orchestration dans `MainOrchestrator` et le CapabilityRegistry. Travail significatif.
- **Option C (Documenter)** : Ajouter un README dans `hierarchical/` documentant le statut dormant et les prérequis pour l'activation.

**Recommandation** : Option A (archiver) + Option C (documenter). L'architecture hiérarchique est bien conçue mais n'a jamais été intégrée dans le CapabilityRegistry. Les 306 tests protègent un code qui n'est jamais exécuté en production.

### Priorité MOYENNE — Orchestrateurs legacy

| Action | Fichiers | Impact |
|--------|----------|--------|
| Évaluer migration | `test_unified_orchestrations.py` | 23 tests (ConversationOrchestrator + RealLLMOrchestrator déprécié) |
| Évaluer migration | `test_specialized_orchestrators.py` | 8 tests (3 orchestrateurs pré-Registry) |

`RealLLMOrchestrator` est déprécié (Sprint 13). `ConversationOrchestrator` est encore importé par `service_manager.py` et `main_orchestrator.py` — mais le pipeline actif ne passe pas par ces modules. La migration vers le CapabilityRegistry éliminerait ces dépendances.

### Priorité BASSE — MainOrchestrator comme façade

| Action | Fichiers | Impact |
|--------|----------|--------|
| Maintenir | `engine/test_main_orchestrator.py` + `test_strategies.py` | 15 tests |

Le `MainOrchestrator` reste le point d'entrée CLI. Tant que `run_orchestration.py` existe, ces tests sont justifiés.

---

## Fix-intents ouverts

| Issue | Priorité | Fichier rapporté | Action |
|-------|----------|------------------|--------|
| fix(b-09): archive hierarchical dormant tests | HAUTE | 10 fichiers `hierarchical/` | Skip ou archive 306 tests couvrant le mode dormant |
| fix(b-09): evaluate ConversationOrchestrator migration | MOYENNE | `test_unified_orchestrations.py` | Évaluer migration vers CapabilityRegistry ou archiver |

---

## Matrice wiring

| Composant testé | CapabilityRegistry | Mode actif | Importé par |
|------------------|--------------------|------------|-------------|
| `OperationalState` | ❌ | Dormant | Modules hiérarchiques |
| `StrategicPlanner` | ❌ | Dormant | Modules hiérarchiques |
| `FeedbackMechanism` | ❌ | Dormant | Modules hiérarchiques |
| `ProgressMonitor` | ❌ | Dormant | Modules hiérarchiques |
| `ResourceAllocator` | ❌ | Dormant | Modules hiérarchiques |
| Templates hiérarchiques | ❌ | Dormant | Modules hiérarchiques |
| `StrategicState` | ❌ | Dormant | Modules hiérarchiques |
| `TacticalState` | ❌ | Dormant | Modules hiérarchiques |
| `TacticalResolver` | ❌ | Dormant | Modules hiérarchiques |
| `StrategicManager` | ❌ | Dormant | Modules hiérarchiques |
| `ConversationOrchestrator` | ❌ | Legacy | `service_manager.py`, `main_orchestrator.py` |
| `RealLLMOrchestrator` | ❌ | Déprécié | Scripts validation |
| `CluedoOrchestrator` | ❌ | Legacy | `main_orchestrator.py` |
| `LogiqueComplexeOrchestrator` | ❌ | Legacy | `main_orchestrator.py` |
| `MainOrchestrator` | ❌ | Actif (CLI) | `run_orchestration.py` (CLI) |
| `OrchestrationStrategy` | ❌ | Actif (CLI) | `MainOrchestrator` |

**Contraste** : Le CapabilityRegistry wiré 47+ services, agents, plugins, invoke callables — mais **aucun** composant de l'architecture hiérarchique n'est enregistré. Les 306 tests hiérarchiques couvrent un système parallèle qui n'est pas connecté au pipeline actif.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-09 #765 — Epic B #743*
