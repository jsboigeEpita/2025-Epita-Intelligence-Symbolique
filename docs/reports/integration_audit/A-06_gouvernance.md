# Audit A-06: 2.1.6 Gouvernance Multi-Agents

**Issue**: #751 (OPEN) | **SUIVI**: Score 85% (intégré) | **Date audit**: 2026-06-01
**Ré-audit R292**: DoD enrichi intent-fix (Epic A #742, Track A-06 #751)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique

## Status: 🟢 Integrated — Pas de gap pipeline

Le projet étudiant `2.1.6_multiagent_governance_prototype/` est **entièrement intégré** dans `argumentation_analysis/agents/core/governance/`. Les 7 méthodes de vote, les 3 types d'agents, la simulation de coalition, la résolution de conflits, et les métriques sont wirés dans CapabilityRegistry, workflows, invoke callable, SK plugin, et API.

## What exists in `2.1.6_multiagent_governance_prototype/`

### Structure du projet étudiant

| Fichier | Lignes | Contenu |
|---------|--------|---------|
| `governance/methods.py` | 133 | 7 méthodes de vote (majority, plurality, borda, condorcet, quadratic, byzantine, raft) |
| `governance/simulation.py` | 269 | Moteur de simulation (Shapley value, gossip consensus, coalition, manipulation) |
| `governance/conflict_resolution.py` | 74 | Détection + résolution de conflits (3 stratégies : collaborative, competitive, compromise) |
| `agents/base_agent.py` | 244 | Agent (Q-learning), BDIAgent, ReactiveAgent (3 types) |
| `agents/agent_factory.py` | 45 | AgentFactory.create_agents() |
| `metrics/metrics.py` | 132 | consensus_rate, gini, fairness_index, efficiency, satisfaction, stability |
| `runner.py` | 45 | run_simulation(), batch_run() avec CLI argparse |
| `cli.py` | 226 | CLI Click (7 commandes : list-methods, run, compare-all, manipulability-analysis, etc.) |
| `scenarios/loader.py` | 12 | Chargeur de scénarios JSON |
| `reporting/visualize.py` | 187 | Plots matplotlib/seaborn (5 fonctions) |
| **Python SLOC total** | **~1367** | Code étudiant |

### Classes clés livrées

| Classe | Module | Rôle |
|--------|--------|------|
| `Agent` | `agents/base_agent.py` | Agent base avec personnalités (4), Q-learning, trust, mémoire, argumentation |
| `BDIAgent(Agent)` | `agents/base_agent.py` | Agent Belief-Desire-Intention |
| `ReactiveAgent(Agent)` | `agents/base_agent.py` | Agent réactif (règles condition/action) |
| `AgentFactory` | `agents/agent_factory.py` | Factory pour créer des agents depuis config |
| `GOVERNANCE_METHODS` | `governance/methods.py` | Dict des 7 méthodes de vote |

### Fonctions clés livrées

| Fonction | Module | Rôle |
|----------|--------|------|
| `majority_voting` | `methods.py` | Vote à la majorité |
| `borda_count` | `methods.py` | Compte Borda (classement) |
| `condorcet_method` | `methods.py` | Condorcet (pairwise, fallback Borda) |
| `quadratic_voting` | `methods.py` | Vote quadratique (budget) |
| `byzantine_consensus` | `methods.py` | Consensus byzantin (fautes) |
| `raft_consensus` | `methods.py` | Consensus Raft (leader election) |
| `simulate_governance` | `simulation.py` | Simulation principale (coalition/gossip) |
| `simulate_manipulation` | `simulation.py` | Simulation sous manipulation |
| `manipulability_analysis` | `simulation.py` | Suite de tests de manipulation |
| `shapley_value` | `simulation.py` | Valeur de Shapley pour coalitions |
| `detect_conflicts` | `conflict_resolution.py` | Détection de conflits pairwise |
| `resolve_conflict` | `conflict_resolution.py` | Résolution par médiation |
| `consensus_rate` | `metrics.py` | Taux de consensus |
| `fairness_index` | `metrics.py` | Indice de fairness (1 - Gini) |
| `summarize_results` | `metrics.py` | Agrégation multi-métriques |

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|-------|------|--------|
| Agent | `agents/core/governance/governance_agent.py` | `Agent` (base), `BDIAgent`, `ReactiveAgent`, `AgentFactory` — refactor du code étudiant |
| Methods | `agents/core/governance/governance_methods.py` | 7 méthodes de vote — refactor de `methods.py` |
| Simulation | `agents/core/governance/simulation.py` | `simulate_governance`, `shapley_value`, `distributed_gossip_consensus`, `manipulability_analysis` — refactor de `simulation.py` |
| Conflict | `agents/core/governance/conflict_resolution.py` | `detect_conflicts`, `resolve_conflict` — refactor de `conflict_resolution.py` |
| Metrics | `agents/core/governance/metrics.py` | `consensus_rate`, `fairness_index`, `satisfaction`, `summarize_results` — refactor de `metrics.py` |
| Social choice | `agents/core/governance/social_choice.py` | **Extension** : approval, STV, Copeland, Kemeny-Young, Schulze — 5 méthodes supplémentaires |
| Exports | `agents/core/governance/__init__.py` | `register_with_capability_registry()` — enregistrement Lego |
| SK Plugin | `plugins/governance_plugin.py` | `GovernancePlugin` — 6 `@kernel_function` (conflicts, resolution, consensus, methods, social_choice, condorcet) |
| Capability Registry | `orchestration/registry_setup.py:149-168` | `governance_agent` → capabilities `governance_simulation`, `multi_method_voting`, `preference_aggregation` |
| Invoke callable | `orchestration/invoke_callables.py:1323-1470` | `_invoke_governance()` — intégration pipeline complète avec cross-phase deps |
| State writer | `orchestration/state_writers.py:291-343` | `_write_governance_to_state()` |
| Workflow (light) | `orchestration/workflows.py:129-130` | Phase `governance` dans workflow light |
| Workflow (standard) | `orchestration/workflows.py:183-184` | Phase `governance` dans workflow standard |
| Workflow (full) | `orchestration/workflows.py:358-362` | Phase `governance` dans pipeline full (L8) |
| Workflow (loop) | `orchestration/workflows.py:449-470` | `build_debate_governance_loop_workflow()` — Loop 1 (vote-contest-revote) |
| Workflow (collaborative) | `orchestration/workflows.py:728-731` | Phase governance dans pipeline collaboratif |

**Tests**: 214 tests au total (6 fichiers governance + 1 plugin + 1 orchestration)
- `test_governance.py`: 42 tests (import, registration, methods, agents, metrics, conflict, simulation)
- `test_governance_methods.py`: 27 tests (7 méthodes individuelles)
- `test_governance_metrics.py`: 42 tests (consensus, gini, fairness, efficiency, satisfaction, stability, summarize, validate)
- `test_governance_simulation.py`: 20 tests (Shapley, neighbors, gossip, simulate)
- `test_conflict_resolution.py`: 25 tests (detect, resolve, mediation, integration)
- `test_social_choice.py`: 37 tests (approval, STV, Copeland, Kemeny-Young, Schulze, Condorcet, pairwise, registry)
- `test_governance_plugin.py`: 15 tests (6 @kernel_function)
- `test_auto_evaluate_governance.py`: 6 tests (pipeline integration)

## Preservation Assessment

### Governance Methods (from `methods.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| majority_voting | ✅ | `governance_methods.py` |
| plurality_voting | ✅ | `governance_methods.py` |
| borda_count | ✅ | `governance_methods.py` |
| condorcet_method | ✅ | `governance_methods.py` |
| quadratic_voting | ✅ | `governance_methods.py` |
| byzantine_consensus | ✅ | `governance_methods.py` |
| raft_consensus | ✅ | `governance_methods.py` |
| GOVERNANCE_METHODS dict | ✅ | `governance_methods.py` |

### Agents (from `base_agent.py` + `agent_factory.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| Agent (personality, Q-learning, trust, memory) | ✅ | `governance_agent.py` |
| BDIAgent(Agent) | ✅ | `governance_agent.py` |
| ReactiveAgent(Agent) | ✅ | `governance_agent.py` |
| AgentFactory.create_agents() | ✅ | `governance_agent.py` |

### Simulation (from `simulation.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| shapley_value | ✅ | `simulation.py` |
| distributed_gossip_consensus | ✅ | `simulation.py` |
| simulate_governance | ✅ | `simulation.py` |
| simulate_manipulation | ✅ | `simulation.py` |
| manipulability_analysis | ✅ | `simulation.py` |
| Coalition formation (trust > 0.8) | ✅ | `simulation.py` |

### Conflict Resolution (from `conflict_resolution.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| detect_conflicts | ✅ | `conflict_resolution.py` |
| resolve_conflict | ✅ | `conflict_resolution.py` |
| collaborative_mediation | ✅ | `conflict_resolution.py` |
| competitive_mediation | ✅ | `conflict_resolution.py` |
| compromise_mediation | ✅ | `conflict_resolution.py` |

### Metrics (from `metrics.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| consensus_rate | ✅ | `metrics.py` |
| gini | ✅ | `metrics.py` |
| fairness_index | ✅ | `metrics.py` |
| efficiency | ✅ | `metrics.py` |
| satisfaction | ✅ | `metrics.py` |
| stability | ✅ | `metrics.py` |
| per_agent_satisfaction | ✅ | `metrics.py` |
| summarize_results | ✅ | `metrics.py` |
| validate_scenario | ✅ | `metrics.py` |

### Extensions au-delà du code étudiant

| Feature | Source |
|---------|--------|
| Social choice methods (5 nouvelles) | `social_choice.py` — approval, STV, Copeland, Kemeny-Young, Schulze |
| SK Plugin (6 @kernel_function) | `plugins/governance_plugin.py` |
| CapabilityRegistry registration | `registry_setup.py` |
| Pipeline invoke callable avec cross-phase deps | `invoke_callables.py:1323-1470` |
| State writer | `state_writers.py:291-343` |
| 5 workflow references (light, standard, full, loop, collaborative) | `workflows.py` |
| LLM-powered deliberation assessment | `invoke_callables.py` |
| Auto social choice vote (Copeland) | `invoke_callables.py` |

### Ce qui n'a PAS été intégré (normal)

| Élément | Pourquoi |
|---------|----------|
| `cli.py` (CLI Click, 7 commandes) | CLI remplacée par `api/` routes + orchestration CLI |
| `runner.py` (batch_run, CSV output) | Remplacé par CapabilityRegistry + pipelines |
| `reporting/visualize.py` (5 plots) | Visualization non-wired dans le pipeline headless |
| `scenarios/loader.py` | Scénarios gérés par configuration pipeline |
| `scenarios/validate_scenarios.py` | Validation intégrée dans `metrics.py:validate_scenario` |
| Config YAML / JSON scenarios | Remplacé par configuration CapabilityRegistry |

## Gap Analysis

**No gap.** L'intégration couvre :

1. **Agents**: `Agent`, `BDIAgent`, `ReactiveAgent` + `AgentFactory` — même logique étudiante
2. **Méthodes**: 7 méthodes de vote originales + 5 méthodes social choice ajoutées
3. **Simulation**: Coalition, Shapley, gossip consensus, manipulation — tout refactoré
4. **Conflict**: 3 stratégies de médiation (collaborative, competitive, compromise)
5. **Metrics**: 8 métriques + agrégation + validation scénarios
6. **CapabilityRegistry**: `governance_agent` (3 capabilities)
7. **SK Plugin**: 6 `@kernel_function` exposant governance au kernel
8. **Invoke callable**: `_invoke_governance()` avec cross-phase deps (extract, debate, counter, quality, fallacy, jtms)
9. **Workflows**: 5 références (light L5, standard L6, full L8, debate-governance loop, collaboratif)
10. **State writer**: `_write_governance_to_state()` vers `UnifiedAnalysisState`
11. **Tests**: 214 tests (8 fichiers)

Le projet **dépasse** significativement le scope étudiant : 5 nouvelles méthodes social choice, SK plugin, intégration pipeline avec cross-phase deps, LLM deliberation assessment.

Note : Le code étudiant original a ~1367 SLOC. Le code intégré dans `argumentation_analysis/` représente ~1500+ SLOC à travers 8 fichiers de gouvernance + plugin (164 lignes) + invoke callable (~150 lignes) — expansion modeste en SLOC mais extension fonctionnelle significative (+5 méthodes, +SK plugin, +pipeline wiring).

## Fix-intents

**Aucun fix-intent ouvert.** L'intégration est complète, wirée, testée (214 tests), et documentée.

## Recommended Action

**No work needed.** Le SUIVI est partiellement conservateur :
- Score: 85% — pourrait être mis à jour à **95%** (l'intégration couvre 100% du code étudiant + extensions significatives)
- Les 5% restants correspondent à la visualization matplotlib/seaborn (non-wired dans le pipeline headless — normal).

## Source Files

- `argumentation_analysis/agents/core/governance/governance_agent.py`
- `argumentation_analysis/agents/core/governance/governance_methods.py`
- `argumentation_analysis/agents/core/governance/simulation.py`
- `argumentation_analysis/agents/core/governance/conflict_resolution.py`
- `argumentation_analysis/agents/core/governance/metrics.py`
- `argumentation_analysis/agents/core/governance/social_choice.py`
- `argumentation_analysis/plugins/governance_plugin.py`
- `argumentation_analysis/orchestration/registry_setup.py`
- `argumentation_analysis/orchestration/invoke_callables.py`

---

*Ré-audit R292 — Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track A-06 #751 — Epic A #742*
