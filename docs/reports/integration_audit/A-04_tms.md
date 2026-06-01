# Audit A-04: 1.4.1 Systèmes Maintenance Vérité (TMS)

**Issue**: #164 (CLOSED) + #748 | **SUIVI**: Score 85% (intégré) | **Date audit**: 2026-06-01
**Ré-audit R291**: DoD enrichi intent-fix (Epic A #742, Track A-04 #748)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique

## Status: 🟢 Integrated — Pas de gap pipeline

Le projet étudiant `1.4.1-JTMS/` est **entièrement intégré** dans `argumentation_analysis/services/jtms/`. Les deux systèmes (JTMS + ATMS) sont wirés dans CapabilityRegistry, workflows, invoke callables, agents, API, et plugins.

## What exists in `1.4.1-JTMS/`

### Structure du projet étudiant

| Fichier | Lignes | Contenu |
|---------|--------|---------|
| `jtms.py` | 185 | Core JTMS — `Belief`, `Justification`, `JTMS` avec propagation, SCC détection, visualisation pyvis |
| `atms.py` | 122 | ATMS — `Node`, `Justification`, `ATMS` avec environnements, contradictions, pruning |
| `tests.py` | 148 | 16 tests (6 JTMS + 8 ATMS + fixtures) |
| `analyse_complete.py` | 133 | Script de validation manuelle (7 catégories) |
| `main.py` | 18 | Demo avec justification circulaire + visualisation |
| `belifs_loader.py` | 17 | Chargeur JSON de croyances |
| `Beliefs/*.json` | 16 | 2 fixtures de croyances |
| `jtms_graph.html` | 1 | Output de visualisation |
| `lib/` | — | Librairies JS (vis-network, tom-select) pour visualisation |
| **Python SLOC total** | **~614** | Code étudiant |

### Classes clés livrées

| Classe | Module | Rôle |
|--------|--------|------|
| `Belief` | `jtms.py` | Nœud de croyance avec validité, justifications, implications |
| `Justification` | `jtms.py` | Règle in-list/out-list → conclusion |
| `JTMS` | `jtms.py` | TMS justification-based avec propagation, SCC, strict mode, pyvis |
| `Node` | `atms.py` | Nœud ATMS avec label (set d'environnements) |
| `ATMS` | `atms.py` | TMS assumption-based avec environnements, contradictions, pruning |
| `load_beliefs()` | `belifs_loader.py` | Chargeur JSON |

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|-------|------|--------|
| Core service | `services/jtms/jtms_core.py` | `Belief`, `Justification`, `JTMS` — refactor du code étudiant |
| Core service | `services/jtms/atms_core.py` | `Node`, `Justification`, `ATMS` — refactor du code étudiant |
| Extension | `services/jtms/extended_belief.py` | `JTMSSession` — session management avec tracing |
| Extension | `services/jtms/conflict_resolution.py` | Résolution de conflits entre croyances |
| Service wrapper | `services/jtms_service.py` | Service wrapper pour le pipeline |
| Session manager | `services/jtms_session_manager.py` | Gestionnaire de sessions JTMS |
| Plugin SK | `plugins/semantic_kernel/jtms_plugin.py` | Plugin SK avec fonctions JTMS |
| Plugin ATMS | `plugins/atms_plugin.py` | Plugin ATMS |
| Plugin narrative | `plugins/narrative_synthesis_plugin.py` | Référence les croyances JTMS |
| Agent base | `agents/jtms_agent_base.py` | Base agent pour agents JTMS |
| Agent Sherlock | `agents/sherlock_jtms_agent.py` | Agent Sherlock avec JTMS |
| Agent Watson | `agents/watson_jtms/agent.py` | Agent Watson JTMS (4 fichiers) |
| Communication | `agents/jtms_communication_hub.py` | Hub de communication inter-agents JTMS |
| Factory | `agents/factory.py` | Création d'agents JTMS |
| State manager | `core/state_manager_plugin.py` | Gestion d'état JTMS |
| Phase state | `core/phase_scoped_state.py` | État scoped par phase (JTMS) |
| Oracle tracker | `agents/core/oracle/hypothesis_tracker.py` | Tracker d'hypothèses oracle → JTMS |
| Capability Registry | `orchestration/registry_setup.py:172-205` | `jtms_service` (capabilities: belief_maintenance, truth_maintenance, jtms_reasoning) + `atms_service` (capability: atms_reasoning) |
| Invoke callable | `orchestration/invoke_callables.py:1547-1871` | `_invoke_jtms()` + `_invoke_atms()` — intégration pipeline complète |
| State writer | `orchestration/state_writers.py` | Writer pour résultats JTMS/ATMS |
| Workflow | `orchestration/workflows.py:474-491` | `build_jtms_dung_loop_workflow()` — Loop 2 (beliefs ↔ Dung extensions) |
| Workflow | `orchestration/workflows.py:300-355` | `iterative_jtms_fallacy_reanalysis_workflow()` — re-analyse fallacies après rétractions |
| Workflow phases | `orchestration/workflows.py:708-725` | Phase `jtms` (L6) + `atms` (L7) dans le pipeline principal |
| Cross-phase deps | `orchestration/invoke_callables.py` | debate réagit à jtms, synthesis lit phase_jtms_output, governance réagit à jtms |
| API REST | `api/jtms_endpoints.py` | Routes JTMS |
| API models | `api/jtms_models.py` | Modèles Pydantic pour API JTMS |
| SK integration | `integrations/semantic_kernel_integration.py` | Intégration SK JTMS |
| Conversational | `orchestration/conversational_orchestrator.py` | Orchestrateur conversationnel avec JTMS |

**Tests**: 4 fichiers tests dédiés JTMS + tests dans les suites orchestration/workflows.

## Preservation Assessment

### JTMS Core (from `jtms.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| Belief (name, valid, justifications, implications) | ✅ | `jtms_core.py` |
| Justification (in-list, out-list, conclusion) | ✅ | `jtms_core.py` |
| JTMS.add_belief() | ✅ | `jtms_core.py` |
| JTMS.set_belief_validity() | ✅ | `jtms_core.py` + invoke callable |
| JTMS.add_justification() | ✅ | `jtms_core.py` |
| Truth propagation | ✅ | `jtms_core.py` |
| Non-monotonic detection (SCC) | ✅ | `jtms_core.py` |
| Strict mode | ✅ | `jtms_core.py` |
| JSON belief loader | ✅ | Via `extended_belief.py` session loading |
| Pyvis visualization | ✅ | `jtms_core.py` visualize() |
| Cycle detection (networkx) | ✅ | `jtms_core.py` |

### ATMS Core (from `atms.py`)

| Feature | Préservé | Où |
|---------|----------|-----|
| Node (name, label, justifications) | ✅ | `atms_core.py` |
| ATMS.add_node() / add_assumption() | ✅ | `atms_core.py` |
| ATMS.add_justification() | ✅ | `atms_core.py` |
| Environment propagation | ✅ | `atms_core.py` |
| Contradiction detection | ✅ | `atms_core.py` |
| Environment pruning | ✅ | `atms_core.py` |
| ATMS.invalidate_environment() | ✅ | `atms_core.py` |

### Extensions au-delà du code étudiant

| Feature | Source |
|---------|--------|
| JTMSSession (session management + tracing) | `extended_belief.py` |
| Conflict resolution | `conflict_resolution.py` |
| Agent JTMS base | `jtms_agent_base.py` |
| Sherlock/Watson JTMS agents | `sherlock_jtms_agent.py`, `watson_jtms/` |
| Communication hub inter-agents | `jtms_communication_hub.py` |
| SK Plugin (5 kernel functions) | `plugins/semantic_kernel/jtms_plugin.py` |
| ATMS Plugin | `plugins/atms_plugin.py` |
| API REST + WebSocket | `api/jtms_endpoints.py` |
| Retraction cascade tracing | invoke callable `_invoke_jtms()` |
| JTMS-Dung feedback loop | `build_jtms_dung_loop_workflow()` |
| Iterative fallacy reanalysis | `iterative_jtms_fallacy_reanalysis_workflow()` |

## Gap Analysis

**No gap.** L'intégration couvre :

1. **Core**: JTMS + ATMS entièrement refactorés dans `services/jtms/`
2. **CapabilityRegistry**: `jtms_service` (3 capabilities) + `atms_service` (1 capability)
3. **Invoke callables**: `_invoke_jtms()` et `_invoke_atms()` avec intégration pipeline complète
4. **Workflows**: 2 workflows dédiés + phases dans pipeline principal (L6 jtms, L7 atms)
5. **Cross-phase deps**: debate, synthesis, governance réagissent aux outputs JTMS
6. **Agents**: Sherlock-JTMS, Watson-JTMS, base agent JTMS, communication hub
7. **Plugins**: SK plugin (5 fonctions) + ATMS plugin
8. **API**: Routes REST + WebSocket + modèles Pydantic
9. **Tests**: 4 fichiers tests dédiés + tests intégration workflow

Le projet **dépasse** significativement le scope étudiant : session management, agents collaboratifs, SK plugins, feedback loop Dung, re-analyse fallacy itérative, API REST.

Note : Le code étudiant original a ~614 SLOC. Le code intégré dans `argumentation_analysis/` représente ~3000+ SLOC à travers 30+ fichiers — un facteur d'expansion ~5x.

## Fix-intents

**Aucun fix-intent ouvert.** L'intégration est complète, wirée, testée, et documentée.

## Recommended Action

**No work needed.** Issue #164 est correctement fermée. Le SUIVI est partiellement conservateur :
- Score: 85% — pourrait être mis à jour à **95%** (l'intégration couvre 100% du code étudiant + extensions significatives)
- Les 5% restants correspondent à l'outil de validation manuelle `analyse_complete.py` (non intégré, normal).

## Source Files

- `argumentation_analysis/services/jtms/jtms_core.py`
- `argumentation_analysis/services/jtms/atms_core.py`
- `argumentation_analysis/services/jtms/extended_belief.py`
- `argumentation_analysis/services/jtms/conflict_resolution.py`
- `argumentation_analysis/orchestration/registry_setup.py`
- `argumentation_analysis/orchestration/invoke_callables.py`
- `argumentation_analysis/plugins/semantic_kernel/jtms_plugin.py`

---

*Ré-audit R291 — Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track A-04 #748 — Epic A #742*
