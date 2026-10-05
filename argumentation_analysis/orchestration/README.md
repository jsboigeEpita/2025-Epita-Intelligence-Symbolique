# Paquet `orchestration`

Ce paquet fait collaborer les agents : il décide **qui** fait **quoi** et **quand**. La
documentation complète des modes (arbitraires d'usage, comparaison, budget) vit dans
[`docs/architecture/ORCHESTRATION_MODES.md`](../../docs/architecture/ORCHESTRATION_MODES.md) —
ce README décrit les **familles vivantes**, leur point d'entrée mesuré et leur preuve
d'intégration, sans la recopier.

## 1. Les cinq familles vivantes

| Famille | Modules | Point d'entrée mesuré | Preuve d'intégration |
|---|---|---|---|
| Pipeline déclaratif (Lego) | `workflow_dsl.py`, `unified_pipeline.py`, `workflows.py`, `registry_setup.py`, `router.py` | `run_orchestration.py` mode défaut ; `api/mobile_endpoints.py:129-137` | bande DAG ci-dessous |
| Conversationnel (`AgentGroupChat`) | `conversational_orchestrator.py`, `conversation_orchestrator.py`, `conversational_executor.py` | `run_orchestration.py --mode conversational` (l.660) ; `service_manager.py:87` | tests cités par orchestrateur |
| Hiérarchique `bridge` / `delegation` | `hierarchical/` (3 niveaux + `orchestrator.py`) | `run_orchestration.py --mode hierarchical --hierarchical-mode bridge\|delegation` (l.730+) | README enfant + tests hiérarchiques |
| Cluedo (Sherlock-Watson-Oracle) | `cluedo_extended_orchestrator.py`, `group_chat.py` | `run_orchestration.py --mode cluedo` (l.830) | `test_cluedo_extended_orchestrator.py` |
| Sherlock moderne | `sherlock_modern_orchestrator.py` | `run_orchestration.py --mode sherlock_modern` (l.609, #357) | `tests/unit/argumentation_analysis/test_sherlock_modern_orchestrator.py` |

### 1.1. Pipeline déclaratif (mode défaut)

Le moteur est le **`WorkflowExecutor`** (`workflow_dsl.py:356` — exécute un
`WorkflowDefinition` en résolvant les capabilities via un `CapabilityRegistry` au moment
de l'exécution). `unified_pipeline.py` expose `run_unified_analysis()` ; `workflows.py`
définit **12 constructeurs** (`build_light/standard/full/iterative/nl_to_logic/
quality_gated_counter/debate_governance/jtms_dung/neural_symbolic/hierarchical_fallacy/
spectacular/formal_extended` — comptés sur `^def build_`), routés par nom.
`registry_setup.setup_registry()` enregistre agents, plugins et services ;
`invoke_callables.py` porte la surface d'invocation par capability et `state_writers.py`
les écritures d'état.

Appelants mesurés : `run_orchestration.py:199-240` (`run_unified_analysis`, mode
défaut), `api/mobile_endpoints.py:129-137` (`workflow_name="light"` — l'API FastAPI
sert le workflow léger). Bande exécutée :
`test_dag_parallelism.py` + `test_critical_coverage.py` + `test_spectacular_workflow_dag.py`
→ **59 passed** (mesuré 2026-10-05 ; `test_diamond_dag_parallel` est un flake wall-clock
connu, re-exécuter au besoin).

### 1.2. Conversationnel — deux orchestrateurs distincts

- **`conversational_orchestrator.py`** — `run_conversational_analysis()` (l.831) : les
  agents dialoguent via `AgentGroupChat`. Dispatché par `run_orchestration.py --mode
  conversational` (l.660).
- **`conversation_orchestrator.py`** — `ConversationOrchestrator` (l.524) : pilotage par
  phases avec budget. Appelants mesurés : `service_manager.py:87` (l'API),
  `pipelines/unified_text_analysis.py:67`, `scripts/compare_orchestration_modes.py`
  (clés `conversation_deterministic`/`conversation_real`, #2456 — même orchestrateur,
  agents réels).
- `conversational_executor.py` — l'exécution conversationnelle exposée aux outils MCP
  (`services/mcp_server/tools/conversation_tools.py`).

### 1.3. Hiérarchique

Trois niveaux (stratégique → tactique → opérationnel), deux sous-modes :

- **`bridge`** (M2, RA-10 #1069, défaut) : le `StrategicManager` traduit ses objectifs en
  phases exécutées par le `WorkflowExecutor` Lego.
- **`delegation`** (M3) : délégation réelle à trois niveaux via
  `RegistryBackedOperationalRegistry` (BO-1 #1471) ; une chaîne dégradée lève
  `DelegationError` plutôt qu'un repli codé en dur.

Détail par couche, adaptateurs et références d'issues dans le
[README de l'architecture hiérarchique](./hierarchical/README.md).

### 1.4. Cluedo et Sherlock moderne

- **Cluedo** : `cluedo_extended_orchestrator.run_cluedo_oracle_game()` — investigation
  Sherlock-Watson-Oracle (#914) sur `group_chat.py` (le `AgentGroupChat` du paquet,
  aussi consommé par `services/flask_service_integration.py` et
  `evaluation/run_agentic_eval.py`). Tests : `test_cluedo_extended_orchestrator.py`,
  `test_cluedo_live_orchestrator_turn_2544.py`.
- **Sherlock moderne** : `sherlock_modern_orchestrator.SherlockModernOrchestrator.
  investigate()` — investigation multi-agent (#357). Test :
  `tests/unit/argumentation_analysis/test_sherlock_modern_orchestrator.py`.

## 2. Relation avec `pipelines/orchestration/`

`argumentation_analysis/pipelines/orchestration/` est **résiduel** : 4 fichiers
(`config/base_config.py`, `config/enums.py`, `execution/strategies.py`, `__init__.py`).
`execution/strategies.py` n'a **aucun appelant production** — importé par ses propres
modules de config et couvert par
`tests/unit/argumentation_analysis/pipelines/orchestration/execution/test_execution_strategies.py`.
`__init__.py` ne ré-exporte que des alias vers `orchestration.service_manager`.
L'ancien moteur (`execution/engine.py`) a été retiré en #2113 (zéro appelant, chemin
refusé en amont par `pipelines/unified_pipeline.py`) ; l'ancien doublon
`orchestration/engine/` avait été supprimé en #1962 pour la même raison. Le moteur
d'exécution vivant est celui de §1.1 — pas ici.

## 3. Autres points d'entrée

| Point d'entrée | Route mesurée |
|---|---|
| `api/main.py` (FastAPI) | routers → `mobile_endpoints.py` (`run_unified_analysis`) ; `dependencies.py` tient le `OrchestrationServiceManager` global (`orchestration/service_manager.py`) |
| `argumentation_analysis/main_orchestrator.py` (UI Tkinter) | `analysis_runner_v2` (l.209 — l'ancien `analysis_runner` a été supprimé) |
| `scripts/compare_orchestration_modes.py` | l'instrument de comparaison cross-modes (8 clés, #1747) — même corpus, mêmes métriques |

## 4. READMEs enfants

- [`hierarchical/`](./hierarchical/README.md) — l'architecture à trois niveaux (bridge
  et delegation), couches, adaptateurs, tests.
- [`plugins/`](./plugins/README.md) — les plugins propres à l'orchestration (à
  distinguer de [`argumentation_analysis/plugins/`](../plugins/), la famille SK
  principale).

Les READMEs plus profonds (`hierarchical/strategic`, `tactical`, `operational`,
`operational/adapters`, `interfaces`, `templates`) sont reliés depuis le README
hiérarchique.
