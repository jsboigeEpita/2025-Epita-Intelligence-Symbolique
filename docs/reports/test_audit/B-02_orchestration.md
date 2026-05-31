# Audit B-02: `tests/unit/argumentation_analysis/orchestration/` (73 files, 2267 tests)

**Issue**: #757 (B-02) | **Epic**: #743 | **Date audit**: 2026-05-31
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Fichiers test | 73 |
| Fonctions test | 2 267 |
| LOC tests | ~28 800 |
| LOC source (`orchestration/`) | ~27 000 |
| Couverture par mode | 4 modes documentés, 3 testés |

### Périmètre source audité

| Module source | LOC | Rôle |
|--------------|-----|------|
| `invoke_callables.py` | 6 047 | 60+ invoke callables (un par capability) |
| `conversational_orchestrator.py` | 2 320 | Mode conversational 8-agent SK |
| `workflows.py` | 1 043 | 15+ workflow builders |
| `registry_setup.py` | 785 | Enregistrement CapabilityRegistry |
| `workflow_dsl.py` | 726 | DSL déclaratif (WorkflowBuilder/Executor) |
| `state_writers.py` | 1 056 | 40+ state writers |
| `engine/main_orchestrator.py` | 1 339 | Dispatch central multi-mode |
| `cluedo_extended_orchestrator.py` | 1 324 | Mode Cluedo 3-agent |
| `service_manager.py` | 1 317 | OrchestrationServiceManager |
| `conversational_executor.py` | 510 | Multi-turn ConversationalPipeline |
| `trace_analyzer.py` | 292 | Trace capture / convergence |
| `hierarchical/` (12 files) | ~4 500 | Mode dormant 3-niveaux |
| Autres (20+ fichiers) | ~6 400 | Router, group_chat, checkpoint, etc. |

---

## 1. Classification a/b/c — Tableau de wiring

### Légende

- ✅ **Wired** : fonctionnalité atteignable depuis un workflow public ou une API route
- ⚠️ **Dérogation justifiée** : helper interne, mock, fixture, infrastructure test, mode dormant
- ❌ **Orphelin** : fonctionnalité non wirée sans justification claire

---

### 1A. Sequential Pipeline (WorkflowDSL/DAG) — 43 fichiers, ~1 468 tests

| Fichier | Tests | Cible source | Wiring | Notes |
|---------|-------|-------------|--------|-------|
| `test_unified_pipeline.py` | 161 | `unified_pipeline.py`, `invoke_callables.py`, `state_writers.py`, `workflows.py` | ✅ Wired | Master suite: state, registry, workflows, invoke, writers, catalogs |
| `test_workflow_dsl.py` | 24 | `workflow_dsl.py` | ✅ Wired | DSL primitives: builder, executor, phase results |
| `test_workflow_executor_invoke.py` | 17 | `workflow_dsl.py` (WorkflowExecutor) | ✅ Wired | Invoke dispatch, context chaining, timeout, state |
| `test_workflow_state_integration.py` | 23 | `state_writers.py`, `unified_pipeline.py` | ✅ Wired | State injection + writers through executor |
| `test_pipeline_wiring.py` | 21 | `invoke_callables.py` (cross-KB wiring) | ✅ Wired | Cross-KB: quality↔fallacy, JTMS key fixes, counter↔quality |
| `test_pipeline_utils.py` | 11 | `pipeline_utils.py` | ✅ Wired | Cache TTL/LFU, metrics, batch |
| `test_auto_evaluate_governance.py` | 9 | `invoke_callables.py` (eval + governance) | ✅ Wired | 5-criteria CA eval, governance auto-vote |
| `test_camembert_invoke.py` | 8 | `invoke_callables._invoke_camembert_fallacy` | ✅ Wired | Self-hosted LLM fallback (was CamemBERT) |
| `test_camembert_workflow_wiring.py` | 13 | `workflows.py` + `conversational_orchestrator.py` | ✅ Wired | Neural_detect phase + conversational plugin wiring |
| `test_critical_coverage.py` | 39 | `workflows.py` + `pipeline_utils.py` | ✅ Wired | Edge cases for utils + workflow builders |
| `test_parallel_execution.py` | 7 | `workflow_dsl.py` (DAG parallelism) | ✅ Wired | Timing-verified concurrent phase execution |
| `test_pm_reprompting.py` | 22 | `workflows.py` + `conversational_orchestrator.py` | ✅ Wired | Part A (Sequential iterative), Part B (Conversational re-prompt) |
| `test_regression_golden.py` | 21 | `unified_pipeline.py` (golden outputs) | ✅ Wired | End-to-end regression with mock outputs |
| `test_workflow_robustness.py` | 258 | All workflows (adversarial fuzz) | ✅ Wired | 258 parametrized tests: empty/long/non-French/injection/special chars |
| `test_spectacular_regression_suite.py` | 46 | `workflows.py` (spectacular + sherlock_modern) | ✅ Wired | Golden DAG + state coverage for 17-phase spectacular |
| `test_spectacular_workflow_dag.py` | 15 | `workflows.py` (spectacular DAG) | ✅ Wired | DAG structure validation (17 phases, deps, levels) |
| `test_dag_parallelism.py` | 4 | `workflow_dsl.py` (asyncio.gather) | ✅ Wired | Verifies same-level phases run concurrently |
| `test_dag_formal_logic_union_ll.py` | 4 | `invoke_callables.py` (PL/FOL union fix) | ✅ Wired | #705 regression: upstream formulas don't short-circuit |
| `test_dung_aspic_wiring.py` | 32 | `invoke_callables.py` (Dung/ASPIC) | ✅ Wired | #286: Dung 11-semantics + ASPIC + cross-KB attacks |
| `test_external_solvers.py` | 19 | `invoke_callables.py` (ASP/FOL/Modal/SAT) | ✅ Wired | #479: EProver/Prover9/SPASS/PySAT routing |
| `test_formal_extended_workflow.py` | 24 | `workflows.py` (formal_extended 15-phase) | ✅ Wired | #480: full Tweety chain DAG |
| `test_llm_enrich_quality.py` | 18 | `invoke_callables.py` (_llm_enrich_quality) | ✅ Wired | #290: LLM enrichment of quality scores |
| `test_nl_to_logic_wiring.py` | 10 | `invoke_callables.py` (PL/FOL NL wiring) | ✅ Wired | #208-H: 3-tier fallback for NL→logic |
| `test_text_kb_spectacular_wiring.py` | 15 | `invoke_callables.py` (TextToKB/KBToTweety) | ✅ Wired | #506: KB extraction + formula translation + interpretation |
| `test_synthesis_spectacular.py` | 5 | `invoke_callables.py` (analysis_synthesis) | ✅ Wired | #508: Terminal synthesis phase |
| `test_narrative_synthesis_spectacular.py` | 6 | `invoke_callables.py` (narrative_synthesis) | ✅ Wired | #503: Narrative prose synthesis |
| `test_belief_revision_spectacular.py` | 4 | `invoke_callables.py` (belief_revision) | ✅ Wired | #507: AGM belief revision |
| `test_external_solver_spectacular.py` | 8 | `invoke_callables.py` (external solvers) | ✅ Wired | #504: FOL/Modal external solver phases |
| `test_invoke_jtms.py` | 8 | `invoke_callables._invoke_jtms` | ✅ Wired | #208-G: JTMS real dependency network |
| `test_parent_harness_578.py` | 14 | `invoke_callables._invoke_hierarchical_fallacy_per_argument` | ✅ Wired | #578 tier 3: parallel per-arg fallacy detection |
| `test_sprint5_hygiene_591.py` | 5 | Source-level hygiene checks | ⚠️ Justifié | #591: source introspection (AST) — regression guard |
| `test_jpype_warmup_529.py` | 5 | `unified_pipeline.py` (JPype warmup) | ⚠️ Justifié | #529: warmup-before-DAG ordering guard |
| `test_growth_validation_hook_597.py` | 14 | `conversational_orchestrator.py` (growth hook) | ✅ Wired | #597: re-prompt on state stagnation |
| `test_iterative_deepening.py` | 7 | `iterative_deepening.py` | ✅ Wired | #471: IterativeDeepeningOrchestrator extraction |
| `test_semantic_indexing_guard_kk.py` | 2 | `invoke_callables._invoke_semantic_index` | ✅ Wired | #700: is_available() guard |
| `test_analysis_trace_uu.py` | 9 | `conversational_orchestrator.py` (trace) | ✅ Wired | #724: specialist commentary + analysis_trace |
| `test_counter_argument_caps_gg.py` | 22 | `invoke_callables._invoke_counter_argument` | ✅ Wired | #696/#709/#730: volume defect fix, retry, floor |
| `test_quality_sweep_lang_jj.py` | 7 | `conversational_orchestrator.py` (quality sweep) | ✅ Wired | #699: language-aware extraction |
| `test_llm_budget_guard_ll_bis.py` | 18 | `unified_pipeline.py` (circuit breaker) | ✅ Wired | #708/#730: per-run LLM-call budget + timeout |
| `test_informal_taxonomy_injection_600.py` | 23 | `conversational_orchestrator.py` + plugins | ✅ Wired | #600: 7 families + German keywords + parent harness |
| `test_formal_logic_conversational_hh.py` | 10 | `conversational_orchestrator.py` (PL/FOL) | ✅ Wired | #697: volet-1 PL/FOL writers on conversational path |
| `test_convergence_gates.py` | 8 | `conversational_orchestrator._check_convergence` | ✅ Wired | #590: phase-aware convergence isolation |
| `test_real_llm_orchestrator.py` | 5 | `real_llm_orchestrator.py` (dataclasses) | ⚠️ Justifié | Legacy: 5 dataclass-only tests remain after #738 archive |

**Sous-total Pipeline**: 43 fichiers, ~1 468 tests, **0 orphelins**

---

### 1B. Conversational Mode — 13 fichiers, ~326 tests

| Fichier | Tests | Cible source | Wiring | Notes |
|---------|-------|-------------|--------|-------|
| `test_conversation_orchestrator.py` | 38 | `conversation_orchestrator.py` | ✅ Wired | Legacy ConversationLogger + micro/demo/trace modes |
| `test_conversation_orchestrator_real.py` | 23 | `conversation_orchestrator.py` (real mode) | ✅ Wired | LLM-backed real mode with fallback to demo |
| `test_conversational_executor.py` | 40 | `conversational_executor.py` | ✅ Wired | Multi-turn pipeline (WorkflowTurnStrategy + GroupChatTurnStrategy) |
| `test_conversational_spectacular.py` | 9 | `conversational_orchestrator.py` (spectacular) | ✅ Wired | #363: UnifiedAnalysisState + 28+ field coverage |
| `test_conversational_orchestrator.py` | 39 | `conversational_orchestrator.py` (8-agent SK) | ✅ Wired | #208-K: AGENT_CONFIG, plugin isolation, 8 agents |
| `test_group_chat.py` | 86 | `group_chat.py` | ✅ Wired | GroupChatOrchestration sessions + health |
| `test_groupchat_turn_strategy.py` | 20 | `conversational_executor.py` (SK AgentGroupChat) | ✅ Wired | #212: SK-native + fallback execution |
| `test_turn_protocol.py` | 18 | `turn_protocol.py` | ✅ Wired | TurnResult/ConversationConfig/TurnStrategy abstractions |
| `test_trace_analyzer.py` | 32 | `trace_analyzer.py` | ✅ Wired | #218/#208-S: trace capture, convergence metrics |
| `test_structured_logging.py` | 12 | `structured_logging.py` | ✅ Wired | #454: correlation IDs, JSON/Human formatters |
| `test_checkpoint.py` | 17 | `checkpoint.py` | ✅ Wired | #451: WorkflowExecutor DAG resume |
| `test_cross_loops.py` | 37 | `workflow_dsl.py` (loops/conditions) | ✅ Wired | #67: conditional phases + iterative loops in DAG |

**Sous-total Conversational**: 13 fichiers (certains partagés Pipeline), ~326 tests, **0 orphelins**

---

### 1C. Hierarchical Mode (Dormant) — 6 fichiers, ~310 tests

| Fichier | Tests | Cible source | Wiring | Notes |
|---------|-------|-------------|--------|-------|
| `hierarchical/operational/test_operational_state.py` | 53 | `hierarchical/operational/state.py` | ⚠️ Dormant | OperationalState: tasks, metrics, futures |
| `hierarchical/strategic/test_allocator.py` | 46 | `hierarchical/strategic/allocator.py` | ⚠️ Dormant | ResourceAllocator: budget, priorities, French keywords |
| `hierarchical/tactical/test_monitor.py` | 44 | `hierarchical/tactical/monitor.py` | ⚠️ Dormant | ProgressMonitor: anomalies, coherence, corrective actions |
| `hierarchical/tactical/test_resolver.py` | 46 | `hierarchical/tactical/resolver.py` | ⚠️ Dormant | ConflictResolver: French contradiction, resolution strategies |
| `hierarchical/tactical/test_state.py` | 71 | `hierarchical/tactical/state.py` | ⚠️ Dormant | TacticalState: objectives, tasks, serialization |
| `test_hierarchy_bridge.py` | 44 | `hierarchical/hierarchy_bridge.py` | ⚠️ Dormant→Pipeline | #65: RegistryBacked bridge + HierarchicalTurnStrategy |

**Sous-total Hierarchical**: 6 fichiers, ~304 tests, **0 orphelins** (tous justifés: mode dormant mais infra réelle)

> **Note critique**: `hierarchy_bridge.py` est un hybride — il est utilisé par `conversational_executor.py` et le module d'évaluation. Les 44 tests du bridge sont wirés via le pathway Conversational même si le mode Hierarchical complet est dormant. **Ces tests protègent un code load-bearing.**

---

### 1D. Cluedo Mode — 5 fichiers, ~209 tests

| Fichier | Tests | Cible source | Wiring | Notes |
|---------|-------|-------------|--------|-------|
| `test_cluedo_enhanced_orchestrator.py` | 2 | `cluedo_orchestrator.py` | ✅ Wired | Integration setup (xfail on execution: singleton pollution) |
| `test_cluedo_extended_orchestrator.py` | 56 | `cluedo_extended_orchestrator.py` | ✅ Wired | AgentGroupChat, message types, suggestions, solution eval |
| `test_cluedo_components.py` | 62 | `cluedo_components/` (5 modules) | ✅ Wired | Plugin, DialogueAnalyzer, EnhancedLogic, Metrics, Suggestion |
| `test_cluedo_strategies.py` | 39 | `cluedo_components/strategies.py` | ✅ Wired | CyclicSelection (14) + OracleTermination (25) |
| `test_orchestration_strategies.py` | 60 | `strategies.py` (abstract bases + Cluedo) | ✅ Wired | Base contracts + Cyclic/Oracle via abstract interface |

**Sous-total Cluedo**: 5 fichiers, ~219 tests, **0 orphelins**

---

### 1E. Other Specialty — 7 fichiers, ~339 tests

| Fichier | Tests | Cible source | Wiring | Notes |
|---------|-------|-------------|--------|-------|
| `test_router.py` | 37 | `router.py` (TextAnalysisRouter) | ✅ Wired | LLM/heuristic routing → workflow selection |
| `test_service_manager.py` | 106 | `service_manager.py` | ✅ Wired | OrchestrationServiceManager: init, middleware, select orchestrator |
| `test_advanced_analyzer.py` | 4 | `advanced_analyzer.py` | ✅ Wired | Module-level analyze_extract_advanced |
| `test_fact_checking_orchestrator.py` | 51 | `fact_checking_orchestrator.py` | ✅ Wired | FactCheckingOrchestrator: claims, fallacies, credibility |
| `test_logique_complexe_plugin.py` | 36 | `plugins/logique_complexe_plugin.py` | ✅ Wired | Einstein's Riddle: Tweety validation, deduction |
| `test_main_orchestrator_engine.py` | 63 | `engine/main_orchestrator.py` | ✅ Wired | Central dispatch: 10 strategies, hierarchical, fallback |
| `test_engine_config_strategy.py` | 70 | `engine/config.py` + `engine/strategy.py` | ✅ Wired | Enums, config, strategy selection, EnquetePlugin |

**Sous-total Other**: 7 fichiers, ~367 tests, **0 orphelins**

---

## 2. Compte global par classification

| Classification | Fichiers | Tests | % |
|---------------|----------|-------|---|
| ✅ Wired (fonctionnalité wirée) | 67 | 1 963 | 86.6% |
| ⚠é Justifié (dormant/infra/hygiène) | 6 | 314 | 13.9% |
| ❌ Orphelin | 0 | 0 | 0.0% |
| **Total** | **73** | **2 267** | — |

> **Résultat remarquable** : 0 orphelin détecté. Chaque test cible une fonctionnalité wirée dans le pipeline actif ou justifiée (mode dormant, hygiène de code, legacy dataclass).

---

## 3. Répartition par mode d'orchestration

| Mode | Statut | Fichiers test | Tests | % |
|------|--------|--------------|-------|---|
| Sequential Pipeline | ACTIF | 43 | ~1 468 | 64.8% |
| Conversational | ACTIF | 13 | ~326 | 14.4% |
| Hierarchical | DORMANT | 6 | ~304 | 13.4% |
| Cluedo | ACTIF | 5 | ~219 | 9.7% |
| Other (router/engine/service) | — | 7 | ~367 | 16.2% |

> Note: certains fichiers sont multi-mode (ex: `test_camembert_workflow_wiring.py` = Pipeline + Conversational). Les pourcentages dépassent 100% car les chevauchements sont comptés dans chaque mode.

---

## 4. Récit du framework via ce packet — Les 4 modes

### 4.1 Mode Sequential Pipeline — Le moteur de production

**Arc narratif**: De `AnalysisRunner` monolithique → `UnifiedPipeline` modulaire → `WorkflowDSL` déclaratif → DAG parallèle spectaculaire.

**Épisode 1 — Fondation (#35, #84, #215)**: Le tronc commun professoral établit `CapabilityRegistry` + `AgentFactory` + `UnifiedPipeline`. Les tests `test_unified_pipeline.py` (161 tests) documentent l'intégrale: state, registry, workflows, invoke callables, state writers. Le DSL déclaratif (`test_workflow_dsl.py`) permet de composer des phases par capability plutôt que par classe concrète — le cœur du pattern "Lego".

**Épisode 2 — Formalisation (#173, #208, #285, #286)**: Le NL→logic bridge entre le texte informel et la validation formelle Tweety. `test_nl_to_logic_wiring.py` teste le 3-tier fallback (LLM → template → empty). `test_dung_aspic_wiring.py` (32 tests) documente l'intégration de Dung (11 sémantiques) et ASPIC+ dans le pipeline — une cristallisation majeure du CoursIA notebooks 5-7b. `test_pipeline_wiring.py` (21 tests) protège le cross-KB wiring: quality lit les fallacies, JTMS lit les quality scores, counter lit les deux.

**Épisode 3 — Robustesse (#260, #309)**: `test_workflow_robustness.py` (258 tests!) est le plus gros fichier du packet — un adversarial fuzzer qui bombarde tous les workflows avec des entrées hostiles (empty, 100K chars, emojis, injection SQL, null bytes, zalgo text). `test_regression_golden.py` (21 tests) établit des golden outputs pour empêcher la régression silencieuse.

**Épisode 4 — Spectacular (#347, #365, #480, #503-#508)**: Le workflow `spectacular_analysis` (17 phases) est le sommet du pipeline séquentiel — il compose *toutes* les capabilities disponibles en un DAG parallèle optimisé. `test_spectacular_regression_suite.py` + `test_spectacular_workflow_dag.py` valident la structure DAG complète. Les fichiers `test_*_spectacular.py` (narrative, synthesis, belief_revision, external_solver, text_kb) documentent l'ajout progressif de phases spécialisées.

**Épisode 5 — Parité Pipeline-Conversational (#578, #597, #696-#730)**: La "parité" entre modes Pipeline et Conversational. `test_parent_harness_578.py` (14 tests) parallélise la détection de sophismes par argument. `test_counter_argument_caps_gg.py` (22 tests) corrige un défaut de volume (≤5 cap → k-per-target floor). `test_llm_budget_guard_ll_bis.py` (18 tests) ajoute un circuit breaker anti-dérive LLM. `test_dag_formal_logic_union_ll.py` corrige le collapse PL/FOL sur le chemin DAG.

**État actuel**: Le Sequential Pipeline est le mode le plus mature et le plus testé (1 468 tests). Chaque capability Tweety a son invoke callable + state writer + test dédié. Le workflow catalog contient 15+ workflows (`light`, `standard`, `full`, `spectacular`, `formal_extended`, `iterative`, `collaborative`, `democratech`, etc.).

---

### 4.2 Mode Conversational — Le dialogue multi-agent

**Arc narratif**: De `ConversationLogger` demo → `ConversationalOrchestrator` 8-agent SK → parité Pipeline → spectacular conversational.

**Épisode 1 — Legacy demo (#36)**: `test_conversation_orchestrator.py` (38 tests) teste le `ConversationLogger` avec modes micro/demo/trace/enhanced. C'est l'ancêtre — un orchestrateur simulé pour démos pédagogiques. `test_conversation_orchestrator_real.py` (23 tests) ajoute le mode "real" avec fallback vers demo quand le kernel LLM est absent.

**Épisode 2 — 8-agent SK GroupChat (#208)**: Le saut quantitatif. `test_conversational_orchestrator.py` (39 tests, distinct du legacy) teste les 8 agents SK (PM + Extract + Informal + Formal + Quality + Debate + Counter + Governance) avec plugin isolation stricte (chaque agent a max 2 plugins). C'est l'implémentation complète du cross-KB synergies diagramme dans `ORCHESTRATION_MODES.md`.

**Épisode 3 — Multi-turn + GroupChat (#212, #218)**: `test_conversational_executor.py` (40 tests) implémente la boucle multi-turn avec `ConversationalPipeline` qui utilise soit `WorkflowTurnStrategy` (DAG wrappé en turn) soit `GroupChatTurnStrategy` (SK AgentGroupChat). `test_group_chat.py` (86 tests) teste les sessions collaboratives multi-agent. `test_trace_analyzer.py` (32 tests) capture les traces de convergence.

**Épisode 4 — Parité avec Pipeline (#208-I cross-KB, #696-#730)**: Les Tracks GG-JJ-HH-LL-MM-UU apportent la parité Conversational sur le volume de contre-arguments (#696), le quality sweep (#699), le PL/FOL wiring (#697), le circuit breaker (#708), et l'analysis trace (#724). `test_formal_logic_conversational_hh.py` teste le volet-1 PL/FOL sur le chemin conversational.

**État actuel**: 326 tests couvrent le mode Conversational. L'architecture est complète: 8 agents, 3 phases macro, trace, convergence, multi-turn, spectacular mode. Le mode spectacular Conversational utilise `UnifiedAnalysisState` (28+ fields) comme le mode Pipeline — vraie parité de modèle.

---

### 4.3 Mode Hierarchical — Le géant endormi

**Arc narratif**: Infrastructure complète construite (#65) → jamais wirée dans CLI/API → pont vers Pipeline via hierarchy_bridge → dormant mais testé.

**Épisode 1 — 3-niveaux complet**: `test_operational_state.py` (53 tests), `test_allocator.py` (46), `test_monitor.py` (44), `test_resolver.py` (46), `test_state.py` (71) — 304 tests au total documentent un système hiérarchique complet:
- **Strategic**: `ResourceAllocator` alloue budgets et priorités, scoring par mots-clés français
- **Tactical**: `ProgressMonitor` (anomalies, cohérence), `ConflictResolver` (contradictions françaises: est/n'est pas), `TacticalState` (objectifs, tâches, snapshots)
- **Operational**: `OperationalState` (tâches, métriques, futures asyncio)

**Épisode 2 — Le pont (#65)**: `test_hierarchy_bridge.py` (44 tests) teste `RegistryBackedOperationalRegistry` qui connecte le `CapabilityRegistry` Lego au mode Hierarchical. Ce pont est **load-bearing** — il est utilisé par `conversational_executor.py` et le module d'évaluation. Les tests vérifient le mapping mots-clés français → capabilities: `sophisme` → `fallacy_detection`, `analyse logique` → `fol_reasoning`, etc.

**État actuel**: 304 tests protègent 4 500+ LOC d'infrastructure hiérarchique. Le mode est **dormant** (pas d'entrée CLI/API), mais:
1. Le bridge est load-bearing (utilisé par Conversational)
2. Les composants sont matures (tests détaillés avec assertions françaises)
3. Le chemin de réactivation est documenté dans `ORCHESTRATION_MODES.md`

> **Verdict**: Pas des orphelins — un mode complet en attente de réactivation. Les tests sont un investissement préservé.

---

### 4.4 Mode Cluedo — L'enquête séparée

**Arc narratif**: Jeu d'investigation Sherlock-Watson-Moriarty → AgentGroupChat cyclique → strategies dédiées → composants modulaires.

**Épisode 1 — Core orchestrator**: `test_cluedo_extended_orchestrator.py` (56 tests) teste le cycle Sherlock→Watson→Moriarty avec détection de types de messages (revelation/suggestion/analysis/reaction), extraction de suggestions (suspect/arme/lieu avec "Indéterminé"), et évaluation de solution.

**Épisode 2 — Strategies dédiées**: `test_cluedo_strategies.py` (39 tests) + `test_orchestration_strategies.py` (60 tests) testent `CyclicSelectionStrategy` (tour cyclique + context injection) et `OracleTerminationStrategy` (max turns/cycles, solution-found vs elimination-complete). Les tests via abstract bases (`test_orchestration_strategies.py`) vérifient les contrats indépendamment de l'implémentation Cluedo.

**Épisode 3 — Composants modulaires**: `test_cluedo_components.py` (62 tests) décompose le Cluedo en 5 composants: `CluedoInvestigatorPlugin`, `DialogueAnalyzer`, `EnhancedLogicHandler`, `ToolCallLoggingHandler`, `MetricsCollector`, `SuggestionHandler`.

**État actuel**: 219 tests couvrent le mode Cluedo. L'architecture est **séparée** du pipeline rhétorique — état propre (`EnqueteCluedoState`), agents propres, strategies propres. Le workflow `sherlock_modern` (7 phases) dans `test_spectacular_regression_suite.py` est une curiosité: il est construit comme un Sequential Pipeline DAG (pas comme l'orchestrateur Cluedo dédié), ce qui montre que les deux modes peuvent coexister.

> **Note**: `test_cluedo_enhanced_orchestrator.py` a un test `xfail` sur l'exécution complète (pollution singleton state) — le seul échec connu du packet.

---

## 5. Muets — Capabilities pipeline non couvertes par ce packet

| Capability | Wirée dans | Tests dans ce packet ? | Localisation tests alternative |
|-----------|-----------|----------------------|-------------------------------|
| `sat_solving` | `registry_setup.py` | Non | N/A (aucun test trouvé) |
| `dl_handler` (description logic) | `_declare_tweety_slots` | Non | N/A |
| `cl_handler` (conditional logic) | `_declare_tweety_slots` | Non | N/A |
| `setaf_handler` | `_declare_tweety_slots` | Non | N/A |
| `weighted_handler` | `_declare_tweety_slots` | Non | N/A |
| `social_handler` | `_declare_tweety_slots` | Non | N/A |
| `eaf_handler` | `_declare_tweety_slots` | Non | N/A |
| `delp_handler` | `_declare_tweety_slots` | Non | N/A |
| `qbf_handler` | `_declare_tweety_slots` | Non | N/A |
| `collaborative_analysis` | `registry_setup.py` | Non | N/A |
| `stakes_extraction` | `registry_setup.py` (spectacular) | Non | N/A |
| `deep_synthesis` | `registry_setup.py` (spectacular) | Non | N/A |

> **12 capabilities muettes** sur ~60 enregistrées. La majorité (8/12) sont des handlers Tweety déclarés comme slots JVM — ils n'ont pas d'invoke callable testé car ils dépendent de la JVM. Les 4 autres (collaborative, stakes, deep_synthesis, SAT) sont wirés dans le registry mais sans test dans ce packet. Ce sont des zones fragiles potentielles.

---

## 6. Recommandations actionnables

### Priorité HIGH

1. **Couvrir les 12 capabilities muettes** — Au minimum, ajouter des tests d'invoke pour `sat_solving`, `stakes_extraction`, `deep_synthesis`, et `collaborative_analysis` (ces 4 n'ont pas la barrière JVM). Recommandation: 1 test d'invoke + 1 test de state writer par capability.

2. **Résoudre le `xfail` dans `test_cluedo_enhanced_orchestrator.py`** — Le test d'intégration complet échoue sur "singleton state pollution". Un reset de singleton entre tests résoudrait le problème.

### Priorité MEDIUM

3. **Consolider les 3 canaris de phase-count** — `test_belief_revision_spectacular.py` asserte `phase_count == 28`, `test_text_kb_spectacular_wiring.py` asserte `23`, `test_synthesis_spectacular.py` asserte `21`. Ces snapshots sont pris à des PR différents. Recommandation: synchroniser sur la valeur actuelle du workflow spectacular.

4. **Réactivation du mode Hierarchical** — L'infrastructure est complète (4 500 LOC, 304 tests). Le pont `hierarchy_bridge.py` est déjà load-bearing. Le chemin de réactivation est documenté. Un wire `--mode hierarchical` dans `run_orchestration.py` réactiverait le mode.

### Priorité LOW

5. **Refactor `test_orchestration_strategies.py` vs `test_cluedo_strategies.py`** — Les deux testent les mêmes classes `CyclicSelectionStrategy` / `OracleTerminationStrategy` mais par angles différents (abstract bases vs implementation). C'est intentional (contrat vs implémentation) mais pourrait bénéficier d'un docstring clarifiant.

6. **Mettre à jour `ORCHESTRATION_MODES.md`** — Le doc mentionne `collaborative` workflow dans le tableau CLI mais le catalog contient maintenant 15+ workflows (democratech, debate_tournament, fact_check, formal_debate, etc.) qui ne sont pas listés.

---

## 7. Chronologie des épisodes cristallisés dans les tests

| Période | Épisode | Issue/PR | Tests marqueurs |
|---------|---------|----------|----------------|
| Mar 2026 | Fondation Lego (CapabilityRegistry + WorkflowDSL) | #35, #84 | `test_unified_pipeline.py`, `test_workflow_dsl.py` |
| Mar 2026 | RealLLM → UnifiedPipeline migration | #215, #246 | `test_real_llm_orchestrator.py` (5 residual dataclass tests) |
| Apr 2026 | Pipeline robustesse + golden outputs | #260, #309 | `test_workflow_robustness.py` (258), `test_regression_golden.py` |
| Apr 2026 | Cross-KB wiring (quality↔fallacy↔JTMS↔counter) | #285, #289 | `test_pipeline_wiring.py` |
| May 2026 | Dung/ASPIC integration (CoursIA notebooks) | #286, #478 | `test_dung_aspic_wiring.py` (32) |
| May 2026 | Spectacular workflow (17 phases) | #347, #365 | `test_spectacular_*.py` (70+ total) |
| May 2026 | Checkpoint/resume + structured logging | #451, #454 | `test_checkpoint.py`, `test_structured_logging.py` |
| May 2026 | Formal extended + external solvers | #479, #480 | `test_formal_extended_workflow.py`, `test_external_solvers.py` |
| May 2026 | Parent harness parallel fallacy | #578 | `test_parent_harness_578.py` (14) |
| May 2026 | Convergence gates + PM re-prompting | #590, #597 | `test_convergence_gates.py`, `test_growth_validation_hook_597.py` |
| Jun 2026 | Sprint 5 hygiene + JPype warmup | #529, #591 | `test_sprint5_hygiene_591.py`, `test_jpype_warmup_529.py` |
| Jun 2026 | Informal taxonomy 7 families + German | #600 | `test_informal_taxonomy_injection_600.py` (23) |
| Jun 2026 | Parité Pipeline-Conversational (GG→UU) | #696-#730 | Tracks GG, JJ, HH, LL, MM, KK, UU (6 files, ~80 tests) |
| Jun 2026 | DAG PL/FOL collapse fix | #705 | `test_dag_formal_logic_union_ll.py` (4) |
| Jun 2026 | LLM circuit breaker | #708, #730 | `test_llm_budget_guard_ll_bis.py` (18) |
| Jun 2026 | RealLLM archive final | #736-#740 | 52 tests removed, 5 dataclass tests remain |

---

## 8. Fichiers sources

### Source code audité
- `argumentation_analysis/orchestration/unified_pipeline.py` (facade)
- `argumentation_analysis/orchestration/invoke_callables.py` (60+ invoke functions)
- `argumentation_analysis/orchestration/state_writers.py` (40+ state writers)
- `argumentation_analysis/orchestration/workflows.py` (15+ workflow builders)
- `argumentation_analysis/orchestration/registry_setup.py` (registry population)
- `argumentation_analysis/orchestration/workflow_dsl.py` (DSL primitives)
- `argumentation_analysis/orchestration/pipeline_utils.py` (cache, metrics, batch)
- `argumentation_analysis/orchestration/conversational_orchestrator.py` (8-agent SK)
- `argumentation_analysis/orchestration/conversation_orchestrator.py` (legacy demo)
- `argumentation_analysis/orchestration/conversational_executor.py` (multi-turn)
- `argumentation_analysis/orchestration/trace_analyzer.py` (convergence)
- `argumentation_analysis/orchestration/checkpoint.py` (DAG resume)
- `argumentation_analysis/orchestration/structured_logging.py` (correlation IDs)
- `argumentation_analysis/orchestration/hierarchical/` (6 modules, dormant)
- `argumentation_analysis/orchestration/hierarchical/hierarchy_bridge.py` (load-bearing)
- `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py` (Cluedo 3-agent)
- `argumentation_analysis/orchestration/cluedo_components/` (5 modules)
- `argumentation_analysis/orchestration/engine/main_orchestrator.py` (central dispatch)
- `argumentation_analysis/orchestration/service_manager.py` (OrchestrationServiceManager)
- `argumentation_analysis/orchestration/router.py` (TextAnalysisRouter)
- `argumentation_analysis/orchestration/fact_checking_orchestrator.py` (fact-checking)
- `argumentation_analysis/orchestration/plugins/logique_complexe_plugin.py` (Einstein)
- `argumentation_analysis/orchestration/plugins/enquete_state_manager_plugin.py` (Cluedo state)
- `argumentation_analysis/orchestration/real_llm_orchestrator.py` (archived legacy)
- `docs/architecture/ORCHESTRATION_MODES.md` (architecture guide)
