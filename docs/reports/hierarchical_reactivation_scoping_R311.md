# Hierarchical Reactivation Scoping — R311

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `e6c7003b` (main, post-R311)
**Nature**: READ-ONLY investigation — go/no-go diagnostic
**Trigger**: Pivot user — objectif = orchestrateurs sélectionnables et comparables (M3 du menu R310)

---

## Verdict

**GO PARTIEL** — l'infra hiérarchique est structurellement complète (18 modules, ~6000 LOC, imports propres), mais **5 casses concrets** bloquent la chaîne de délégation. La réactivation n'est pas un « flip a switch » (les tests passeraient si on retirait les skips). Un sprint ciblé de **3 sessions** peut réparer les adaptateurs et créer le `HierarchicalOrchestrator` manquant. Le chemin moderne (`hierarchy_bridge.py` → `CapabilityRegistry`) est déjà vivant ; c'est la chaîne standalone qui est cassée.

**Conclusion** : faisable à coût modéré, risque maîtrisé. Les 5 casses sont identifiés et bornés. La réactivation produit un 3e mode d'orchestration comparable (Pipeline / Conversational / **Hierarchical**).

---

## 1. État des skips (302 tests dormants)

| Catégorie | Fichiers | Tests | Mécanisme | Raison |
|-----------|:--------:|:-----:|-----------|--------|
| A — Dormancy batch | 10 | 302 | `pytestmark = pytest.mark.skip(...)` | `"Hierarchical mode dormant — not in active pipeline (B-09 #798)"` |
| B — Import guard | 1 | 12 | `except ImportError` → skip | `"Gestionnaires hiérarchiques non disponibles"` |
| **Total** | **11** | **314** | | |

Les 10 fichiers Catégorie A sont dans `tests/unit/orchestration/hierarchical/{strategic,tactical,operational,templates}/`. Le skip a été posé par commit `d95c46ff` (PR #873, audit B-09 #798) — décision de dormance documentée, pas une défaillance.

La Catégorie B (`test_hierarchical_managers.py`) est un import guard conditionnel — probablement actif si les imports résolvent (les 3 modules cibles existent).

**Autres tests hiérarchiques actifs** : ~80+ fichiers mentionnent "hierarchical/tactical/strategic" sans skip — notamment `tests/orchestration/hierarchical/` (coordinator, adapters), interfaces de communication, et `hierarchy_bridge`.

---

## 2. Cartographie de l'infrastructure

### 2.1 Modules hiérarchiques (`orchestration/hierarchical/`)

| Module | LOC | Statut | Rôle |
|--------|:---:|--------|------|
| `strategic/manager.py` | 371 | Imports OK | Goal init, délégation, synthèse |
| `strategic/planner.py` | 611 | Imports OK | Décomposition de plan |
| `strategic/allocator.py` | 482 | Imports OK | Allocation de ressources |
| `strategic/state.py` | 245 | Imports OK | Plan/objectifs/métriques |
| `tactical/coordinator.py` | 355 | Imports OK | Décomposition objectifs→tâches |
| `tactical/monitor.py` | 712 | Imports OK | Monitoring de progrès |
| `tactical/resolver.py` | 707 | Imports OK | Résolution de conflits |
| `tactical/state.py` | 645 | Imports OK | État tactique |
| `operational/manager.py` | 322 | Imports OK | Queue async, délègue au registry |
| `operational/agent_registry.py` | 283 | **CASSE** | Registry hardcodé 4 adaptateurs |
| `operational/agent_interface.py` | 554 | Imports OK | ABC pour adaptateurs |
| `operational/state.py` | 428 | Imports OK | Statut tâche + result Futures |
| `operational/feedback_mechanism.py` | 443 | Imports OK | Rétroaction |
| `hierarchy_bridge.py` | 393 | **VIVANT** | Bridge vers CapabilityRegistry |
| `interfaces/strategic_tactical.py` | 643 | Imports OK | Objectif→directive |
| `interfaces/tactical_operational.py` | 387 | Imports OK | Tâche→commande |

### 2.2 Adaptateurs opérationnels (les 4 agents)

| Adaptateur | Cible réelle | Statut | Problème |
|------------|-------------|--------|----------|
| `extract_agent_adapter.py` | `ExtractAgent` | ✅ **FONCTIONNEL** | Signatures match |
| `informal_agent_adapter.py` | Informal/Fallacy | ❌ **STUB MOCK** | `MagicMock(spec=Agent)` — jamais câblé |
| `pl_agent_adapter.py` | `PropositionalLogicAgent` | ❌ **CASSÉ** | Méthodes inexistantes (`formalize_to_pl`, `check_pl_validity`) |
| `rhetorical_tools_adapter.py` | `AnalysisToolsPlugin` | ❌ **CASSÉ** | `NameError: get_fallacy_detector` (non importé) |

### 2.3 Communication (6 modules, tous OK)

`hierarchical_channel.py`, `strategic_adapter.py`, `tactical_adapter.py`, `operational_adapter.py`, `middleware.py`, `channel_interface.py` — imports propres, connectés au `service_manager.py`.

---

## 3. Casses concrets (go/no-go blockers)

### B1 — `rhetorical_tools_adapter.py:73` — NameError

`get_fallacy_detector()` appelé mais jamais importé. Vit dans `core/bootstrap.py`. **Fix : 1 ligne** (ajouter import). Impact : `OperationalAgentRegistry.initialize_all_agents()` échoue silencieusement sur cet adaptateur.

### B2 — `pl_agent_adapter.py:178,191,196` — method mismatch

Appelle `formalize_to_pl()`, `check_pl_validity()`, `check_pl_consistency()` qui n'existent pas sur `PropositionalLogicAgent`. L'API réelle est `text_to_belief_set`, `generate_queries`, `execute_query`, `is_consistent`. **Fix : réécriture modérée** (mapping méthode→API + cycle de vie belief-set/JVM).

### B3 — `informal_agent_adapter.py` — stub mock

`initialize()` assigne `MagicMock(spec=Agent)` au lieu de créer un vrai agent via `AgentFactory`. **Fix : modéré** (câblage AgentFactory déjà importé).

### B4 — Pas de `HierarchicalOrchestrator`

La classe référencée dans `ORCHESTRATION_MODES.md` n'existe pas. Le `service_manager._run_operational_analysis` bypass la chaîne de délégation avec un appel OpenAI inline. **Fix : L** — écrire l'orchestrateur ou rebrancher `service_manager`.

### B5 — Doc obsolète

`ORCHESTRATION_MODES.md` référence `HierarchicalOrchestrator` (inexistant) et `examples/orchestration/run_hierarchical_orchestration.py` (inexistant). **Fix : S** — mettre à jour après B4.

---

## 4. Risques ordonnés

| # | Risque | Sévérité | Mitigation |
|---|--------|----------|------------|
| 1 | B4 — Pas d'orchestrateur → effort principal | **HAUT** | Réutiliser `service_manager` existant + rebrancher le chemin délégation |
| 2 | B2 — PL adapter réécriture → cycle JVM/belief-set | **MOYEN** | Pattern existant dans `_invoke_propositional_logic` (invoke_callables.py) |
| 3 | B3 — Informal adapter stub → wiring AgentFactory | **MOYEN** | Factory déjà importée + testable indépendamment |
| 4 | Singletons TweetyBridge/CluedoOracleState → pollution cross-test | **FAIBLE** | Déjà mitigé par les tests skip ; réactivation progressive |
| 5 | SK API drift (1.35→1.40) → signatures obsolètes | **FAIBLE** | Imports vérifiés OK ; risque limité au runtime |

---

## 5. Plan de réactivation (si GO)

| Étape | Portée | Effort | Livrable |
|-------|--------|--------|----------|
| **E1** | Fix B1 (import rhetorical) | 0.1 session | 1 ligne |
| **E2** | Fix B3 (de-stub informal) | 0.5 session | Adapter câblé + tests |
| **E3** | Fix B2 (rewrite PL adapter) | 0.5 session | Adapter réécrit + tests |
| **E4** | Fix B4 (orchestrateur) | 1.5 session | `HierarchicalOrchestrator` + CLI `--mode hierarchical` |
| **E5** | Retirer skips + smoke test | 0.2 session | 302 tests dé-skippés |
| **E6** | Fix B5 (doc) | 0.2 session | `ORCHESTRATION_MODES.md` à jour |
| **Total** | | **~3 sessions** | 3e mode d'orchestration comparable |

---

## 6. Note — chemin moderne vs legacy

Le mode hiérarchique a **deux chemins d'intégration** :

1. **Chemin moderne** (vivant) : `hierarchy_bridge.py` → `CapabilityRegistry` → `ConversationalExecutor`. `HierarchicalTurnStrategy` est déjà consommé par le mode conversationnel. Ce n'est PAS la chaîne de délégation stratégique→tactique→opérationnelle, mais un bridge vers le Lego Architecture.

2. **Chemin legacy** (cassé) : `StrategicManager` → `TacticalCoordinator` → `OperationalManager` → adaptateurs → agents réels. C'est la chaîne de délégation 3 niveaux, jamais testée E2E.

La réactivation peut choisir de (a) réparer le chemin legacy pour le mode standalone, ou (b) étendre le bridge moderne pour supporter la délégation 3 niveaux via le Lego Architecture. L'option (b) est plus alignée avec l'architecture actuelle mais plus complexe.

---

## À valider par l'utilisateur

1. **Go/no-go** : le scoping recommande **GO PARTIEL** (3 sessions). Confirmez-vous ?
2. **Chemin** : réparer le chemin legacy (a) ou étendre le bridge moderne (b) ? Le bridge est plus aligné mais plus lourd.
3. **Priorité dans le menu** : ce scoping valide M3 (effort L dans le menu). Les 3 sessions sont-elles acceptables, ou préférez-vous M1 (durcissement S) en préalable ?
