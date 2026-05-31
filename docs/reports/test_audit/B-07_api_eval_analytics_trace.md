# B-07: Audit — `tests/unit/argumentation_analysis/api/` + `evaluation/` + `analytics/` + `reporting/`

**Track**: B-07 #763 (Epic B #743)
**Date**: 2026-05-31
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 17 fichiers, 872 tests collectés

---

## Méthodologie

Même classification a/b/c que B-01 à B-06. Le wiring se vérifie par :
- **CapabilityRegistry** : grep dans `registry_setup.py`, `workflows.py`, `invoke_callables.py`
- **Orchestration imports** : grep `from argumentation_analysis.{evaluation,analytics,reporting}` dans `orchestration/`
- **Script consumers** : grep dans `scripts/`, `api/`, `interface_web/`

Pour l'évaluation (evaluation/), la catégorie naturelle est **(c) JUSTIFIÉ** pour l'infrastructure de benchmark critique (privacy, scoring, orchestration) et **(b) UNWIRED** pour les modules uniquement consommés par des scripts autonomes.

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 0 | 0 | 0% |
| **(b) Non-wiré** | 8 | ~230 | 26% |
| **(c) Justifié** | 9 | ~642 | 74% |

---

## Tableau de classification

### (a) DEAD — Composant sans consommateur

Aucun fichier dans ce packet. Tous les modules testés ont au moins un consommateur (pipeline, orchestration, ou script).

---

### (b) UNWIRED — Infrastructure scripts-only ou legacy

| # | Fichier | Composant testé | Consommateur | Tests | Pourquoi UNWIRED |
|---|---------|-----------------|--------------|-------|-------------------|
| 1 | `evaluation/test_cli_runners.py` | `run_baseline_benchmark`, `run_synergy_analysis` | Scripts CLI autonomes | 11 | CLI runners pour benchmarks. Pas dans CapabilityRegistry. Lancés manuellement. |
| 2 | `evaluation/test_multi_model_benchmark.py` | `multi_model_benchmark` (ModelWorkflowScore, ComparisonReport, rank_models, etc.) | `scripts/run_benchmark_multimodel.py` | 21 | Framework de comparaison multi-modèles. Script-only. |
| 3 | `evaluation/test_run_llm_judge.py` | `run_llm_judge` (JudgeResult, JudgeReport, load_benchmark_results) | Aucun import pipeline | 28 | Runner LLM Judge autonome. Pas wiré dans CapabilityRegistry. |
| 4 | `evaluation/test_capability_eval.py` | `capability_eval` (CapabilityConfig, FilteredRegistry, EvalCell, marginal scores) | Aucun import pipeline | 41 | Analyse de contribution par capability. Infrastructure d'évaluation standalone. |
| 5 | `evaluation/test_benchmark_conversational.py` | Conversational mode in benchmark | Teste `list_available_workflows` | 6 | Extension du multi_model_benchmark pour le mode conversationnel. Script-only. |
| 6 | `analytics/test_stats_calculator.py` | `calculate_average_scores` | `reporting_pipeline.py` (legacy), `generate_comprehensive_report.py` (script) | 7 | Utilitaire stats. Consommé uniquement par pipelines legacy (voir B-03). |
| 7 | `analytics/test_text_analyzer.py` | `perform_text_analysis` | `analysis_pipeline.py` (legacy) | 3 | Wrapper autour de AnalysisRunnerV2. Consommé uniquement par pipeline legacy. |
| 8 | `reporting/test_trace_analyzer.py` | `reporting/trace_analyzer` (ExtractMetadata, OrchestrationFlow, StateEvolution, AgentStep, ConversationCapture, InformalExploration) | Aucun import hors tests | 54 | **Dataclasses de trace non utilisées** par le pipeline. Le pipeline utilise `orchestration/trace_analyzer.py` (module différent) et `reporting/enhanced_real_time_trace_analyzer.py` pour le tracing réel. |

---

### (c) JUSTIFIÉ — Infrastructure wirée ou critique

#### api/ (1 fichier)

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_jtms_models.py` | `api/jtms_models` (BeliefInfo, CreateBeliefRequest, JTMSResponse, etc.) | Pydantic models pour l'API REST JTMS. Importé par `interface_web/routes/jtms_routes.py`. JTMS est wiré dans CapabilityRegistry comme `jtms_service`. | 47 |

#### evaluation/ (11 fichiers) — Infrastructure de benchmark

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_evaluation_module.py` | `model_registry`, `benchmark_runner`, `result_collector`, `judge` | Socle de l'évaluation : ModelConfig/ModelRegistry (config LLM), BenchmarkRunner (exécution), ResultCollector (persistance JSONL), LLMJudge (scoring 5 critères). Utilisé par `scripts/run_benchmark.py` et `scripts/run_spectacular_comparison.py`. | 57 |
| 2 | `test_benchmark_runner_advanced.py` | `BenchmarkRunner` (avancé) | Dataset loading (chiffré/non-chiffré), timeout, phase serialization. Même composant que ci-dessus. | 17 |
| 3 | `test_judge_advanced.py` | `LLMJudge` (avancé) | Timeout, JSON parsing, large result processing. Même composant. | 22 |
| 4 | `test_result_collector_advanced.py` | `ResultCollector` (avancé) | JSONL persistence, Unicode, CSV export, query filtering. Même composant. | 16 |
| 5 | `test_synergy_analyzer_advanced.py` | `SynergyAnalyzer` | Analyse de synergie inter-workflows. Utilisé par `evaluation/run_synergy_analysis.py`. | 16 |
| 6 | `test_fallacy_benchmark.py` | `FallacyBenchmarkRunner` | Benchmark de détection de sophismes (8 familles, modes free/one-shot/constrained). Utilisé par `scripts/run_fallacy_benchmark.py`. Teste la taxonomy wirée (8 familles). | 51 |
| 7 | `test_plugin_benchmark.py` | `PluginBenchmarkSuite` | Benchmark des plugins wirés : Governance, QualityScoring, ATMS, JTMS, FrenchFallacy. Ces plugins sont tous enregistrés dans CapabilityRegistry. | 53 |
| 8 | `test_conversational_benchmark.py` | `ConversationalBenchmarkRunner` | Benchmark conversational vs sequential. Utilise `UnifiedAnalysisState` (wiré). | 18 |
| 9 | `test_opaque_id.py` | `opaque_id` | Génération d'IDs opaques pour privacy. Utilisé par `scripts/dataset/run_corpus_batch.py` et `add_extract.py`. **Discipline privacy** (CLAUDE.md). | 10 |
| 10 | `test_sanitize_state.py` | `sanitize_state` | Nettoyage des state snapshots (suppression raw_text, noms). Utilisé par `scripts/dataset/run_corpus_batch.py`. **Discipline privacy**. | 16 |
| 11 | `test_pattern_mining.py` | `pattern_mining` (ATMS branching, Dung topology, cooccurrence, fallacy spectrum) | Mining de patterns formels. Utilisé par `scripts/dataset/build_pattern_report.py`. | 27 |

#### analytics/ (1 fichier)

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_effectiveness_analyzer.py` | `analyze_agent_effectiveness` | Analyse d'efficacité des agents. Importé par `reporting_pipeline.py` (legacy) et `scripts/reporting/generate_comprehensive_report.py`. | 14 |

#### reporting/ (5 fichiers) — Infrastructure wirée dans le pipeline

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `test_enhanced_real_time_trace_analyzer.py` | `EnhancedRealTimeTraceAnalyzer` | **Tracing runtime wiré**. Importé par `orchestration/analysis_runner_v2.py` et `orchestration/enhanced_pm_analysis_runner.py`. Capture ConversationMessage, StateSnapshot, EnhancedToolCall, ProjectManagerPhase. | 68 |
| 2 | `test_enhanced_trace_analyzer.py` | `EnhancedRealTimeTraceAnalyzer` (dataclasses) | Même composant — focus dataclasses et orchestration capture. **Recouvrement partiel** avec #1. | 63 |
| 3 | `test_reprompt_trace.py` | `RepromptTraceExtractor` | Extraction de traces de reprompting. **Importé par `orchestration/conversational_orchestrator.py`**. Wiré dans le pipeline conversationnel. | 11 |
| 4 | `test_document_assembler.py` | `ReportMetadata`, `UnifiedReportTemplate` | Infrastructure de rapports unifiés. Template system pour assemblage de documents. | 63 |
| 5 | `test_section_formatter.py` | `UnifiedReportTemplate` (rendering) | Rendu multi-format (markdown, console, json, html). Partie du framework de rapport. | 27 |

#### reporting/ — Scripts-only (justifiés comme infrastructure)

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 6 | `test_summary_generator.py` | `summary_generator` | Génération de synthèses rhétoriques. Importé par `scripts/reporting/generate_rhetorical_analysis_summaries.py`. | 2 |
| 7 | `test_real_time_trace_analyzer.py` | `RealTimeTraceAnalyzer` | Tracing en temps réel (RealToolCall, AgentConversationBlock). Importé par `scripts/orchestration/orchestrate_with_existing_tools.py`. Version "basique" du traceur. | 54 |
| 8 | `test_conversation_balance.py` | `ConversationBalanceAnalyzer` | Analyse d'équilibre conversationnel (entropy-based). Importé par `scripts/analysis/generate_spectacular_bundle.py`. | 16 |
| 9 | `test_cross_reference_graph.py` | `CrossReferenceGraph` | Graphe de cross-références (arguments ↔ fallacies ↔ beliefs). Importé par `scripts/analysis/generate_spectacular_bundle.py`. | 17 |
| 10 | `test_multi_format_exporter.py` | `MultiFormatExporter` | Export multi-format (JSON, CSV, XML, HTML, Markdown, LaTeX). Importé par `scripts/analysis/export_scda_state.py` et `generate_spectacular_bundle.py`. | 16 |

---

## Récit du framework — 4 épisodes

### Épisode 1 : Le socle de benchmarking monolithique (~2025-Q3)

Le module `evaluation/` cristallise le **framework de benchmarking** original. Les composants fondamentaux — `BenchmarkRunner`, `ModelRegistry`, `ResultCollector`, `LLMJudge` — forment un système complet pour mesurer les performances du pipeline : configuration LLM → exécution → collecte → scoring. Ce framework a précédé le CapabilityRegistry et a évolué en parallèle.

**Trace dans les tests** : `test_evaluation_module.py` (57 tests) couvre les 4 composants fondamentaux du benchmark. Les tests mockent `AsyncMock` pour les appels LLM, indiquant que le framework a toujours été conçu pour tourner offline. Le `ModelConfig` avec `model_id="gpt-5-mini"` montre que les tests sont alignés avec la config actuelle (OPENAI_CHAT_MODEL_ID dans `.env`).

### Épisode 2 : L'explosion du reporting spécialisé (~2025-Q4)

Le module `reporting/` a explosé en **3 générations de traceurs** qui témoignent d'une évolution architecturale :

1. **`trace_analyzer.py`** — Dataclasses statiques (ExtractMetadata, OrchestrationFlow, StateEvolution, AgentStep, ConversationCapture, InformalExploration). **Première génération**, jamais adoptée par le pipeline. Les 54 tests couvrent des structures qui n'ont pas été wirées.

2. **`real_time_trace_analyzer.py`** — Version runtime avec `RealTimeTraceAnalyzer`, decorators `tool_call_tracer`, capture globale. **Deuxième génération**, adoptée par les scripts d'orchestration (`orchestrate_with_existing_tools.py`) mais pas par le pipeline CapabilityRegistry.

3. **`enhanced_real_time_trace_analyzer.py`** — Version enrichie avec `ConversationMessage`, `StateSnapshot`, `EnhancedToolCall`, `ProjectManagerPhase`. **Troisième génération**, wirée dans `analysis_runner_v2.py` et `enhanced_pm_analysis_runner.py` — les deux runners actifs du pipeline.

**Trace** : Les 3 fichiers de test (54 + 54 + 68 = 176 tests) couvrent ces 3 générations. Les deux premiers testent des traceurs qui ne sont plus dans le pipeline actif. Le troisième teste le traceur actif.

### Épisode 3 : L'API JTMS et la discipline privacy (~2026-Q1)

Le module `api/jtms_models.py` (47 tests) cristallise l'interface REST pour le JTMS. Les 20+ Pydantic models (CreateBeliefRequest, AddJustificationRequest, ExplainBeliefResponse, etc.) définissent un contrat API complet. Le module est consommé par `interface_web/routes/jtms_routes.py` — la web app Starlette qui sert le frontend React. Le JTMS lui-même est wiré dans CapabilityRegistry (`jtms_service`).

En parallèle, `evaluation/opaque_id.py` et `sanitize_state.py` incarnent la **discipline privacy** formalisée dans CLAUDE.md : IDs opaques pour les sources, nettoyage des state snapshots avant export. Ces utilitaires sont activement utilisés par les scripts de dataset (`run_corpus_batch.py`, `add_extract.py`).

**Trace** : `test_opaque_id.py` vérifie la stabilité, le format hex et la résistance aux collisions. `test_sanitize_state.py` vérifie la suppression de `raw_text`, des noms de speakers, et l'idempotence du nettoyage. Ces tests protègent un invariant critique du projet.

### Épisode 4 : Les benchmarks spécialisés et le plugin scoring (~2026-Q1-Q2)

Les modules `fallacy_benchmark.py`, `plugin_benchmark.py`, `capability_eval.py`, `conversational_benchmark.py`, et `pattern_mining.py` représentent une **seconde couche de benchmarking** qui évalue des dimensions spécifiques du pipeline :

- `FallacyBenchmarkRunner` (51 tests) — Teste la détection de sophismes avec la taxonomy 8 familles (wirée via `FrenchFallacyPlugin` dans CapabilityRegistry)
- `PluginBenchmarkSuite` (53 tests) — Évalue directement les plugins wirés (Governance, QualityScoring, ATMS, JTMS, FrenchFallacy)
- `CapabilityEval` (41 tests) — Analyse les contributions marginales de chaque capability
- `ConversationalBenchmarkRunner` (18 tests) — Compare mode conversationnel vs séquentiel
- `PatternMining` (27 tests) — Mining de patterns formels (ATMS branching, Dung topology, cooccurrence)

**Trace** : `test_plugin_benchmark.py` référence explicitement les plugins wirés — `GovernancePlugin`, `QualityScoringPlugin`, `ATMS`, `JTMS`, `FrenchFallacy`. Les tests de scoring (`PluginBenchmarkResult`, `PluginBenchmarkReport`) valident que les plugins wirés produisent des résultats conformes. C'est le **pont direct** entre l'infrastructure de test et le CapabilityRegistry.

---

## Recouvrements et doublons détectés

### 3 générations de traceurs (recouvrement partiel)

| Génération | Module | Testé par | Wiré dans pipeline |
|-----------|--------|-----------|--------------------|
| Gen 1 | `reporting/trace_analyzer.py` | `test_trace_analyzer.py` (54) | ❌ Aucun import |
| Gen 2 | `reporting/real_time_trace_analyzer.py` | `test_real_time_trace_analyzer.py` (54) | Scripts only |
| Gen 3 | `reporting/enhanced_real_time_trace_analyzer.py` | `test_enhanced_trace_analyzer.py` (63) + `test_enhanced_real_time_trace_analyzer.py` (68) | ✅ `analysis_runner_v2.py`, `enhanced_pm_analysis_runner.py` |

**Total : 239 tests pour le tracing**, dont ~108 couvrent des traceurs non wirés dans le pipeline actif.

### Recommandation : Consolider les traceurs

Les Gen 1 et Gen 2 sont des **précurseurs** de la Gen 3. Les dataclasses de `trace_analyzer.py` (ExtractMetadata, OrchestrationFlow, etc.) ne sont pas utilisées par le pipeline — le pipeline utilise `orchestration/trace_analyzer.py` (module distinct) et `enhanced_real_time_trace_analyzer.py` pour le tracing réel.

**Option A** : Marquer les tests Gen 1 comme `@pytest.mark.skip("legacy trace analyzer — superseded by enhanced_real_time_trace_analyzer")`
**Option B** : Fusionner les dataclasses utiles de Gen 1 dans Gen 3 et supprimer Gen 1

---

## Actions recommandées

### Priorité HAUTE — Trace analyzer Gen 1 (54 tests morts)

| Action | Fichier | Impact |
|--------|---------|--------|
| Archiver ou skip | `reporting/test_trace_analyzer.py` | 54 tests couvrant un module non importé par le pipeline |

`reporting/trace_analyzer.py` n'est importé par aucun fichier hors tests. Le pipeline utilise `orchestration/trace_analyzer.py` et `enhanced_real_time_trace_analyzer.py`. Les 54 tests protègent un code mort.

### Priorité BASSE — Analytics legacy

| Action | Fichier | Impact |
|--------|---------|--------|
| Évaluer migration | `analytics/test_stats_calculator.py` | 7 tests — consommé uniquement par pipeline legacy |
| Évaluer migration | `analytics/test_text_analyzer.py` | 3 tests — consommé uniquement par pipeline legacy |

Ces modules sont les derniers consommateurs des pipelines legacy (`reporting_pipeline.py`, `analysis_pipeline.py` — voir B-03). La migration des pipelines vers le CapabilityRegistry éliminerait ces dépendances.

### Priorité BASSE — Recouvrement enhanced_trace

`test_enhanced_trace_analyzer.py` (63 tests) et `test_enhanced_real_time_trace_analyzer.py` (68 tests) couvrent le même composant. Une consolidation réduirait le packet de ~20 tests redondants.

### Priorité INFO — Evaluation scripts-only

Les 5 fichiers `evaluation/` classés UNWIRED (CLI runners, multi-model benchmark, LLM judge runner, capability eval, conversational benchmark) sont des **scripts d'évaluation autonomes**. Ils ne sont pas wirés dans CapabilityRegistry car ils évaluent le pipeline de l'extérieur. **Pas d'action recommandée** — ils sont légitimes.

---

## Matrice wiring

| Composant testé | CapabilityRegistry | Importé par (pipeline) | Importé par (scripts) |
|------------------|--------------------|------------------------|----------------------|
| `api/jtms_models` | ✅ (via jtms_service) | `interface_web/routes/jtms_routes.py` | — |
| `evaluation/benchmark_runner` | ❌ | — | `run_benchmark.py`, `run_spectacular_comparison.py` |
| `evaluation/model_registry` | ❌ | — | Mêmes scripts |
| `evaluation/result_collector` | ❌ | — | Mêmes scripts |
| `evaluation/judge` | ❌ | — | `run_llm_judge.py` |
| `evaluation/fallacy_benchmark` | ❌ | — | `run_fallacy_benchmark.py` |
| `evaluation/plugin_benchmark` | ❌ (teste les wirés) | — | Script autonome |
| `evaluation/conversational_benchmark` | ❌ | — | Script autonome |
| `evaluation/opaque_id` | ❌ | — | `run_corpus_batch.py`, `add_extract.py` |
| `evaluation/sanitize_state` | ❌ | — | `run_corpus_batch.py` |
| `evaluation/pattern_mining` | ❌ | — | `build_pattern_report.py` |
| `evaluation/synergy_analyzer` | ❌ | — | `run_synergy_analysis.py` |
| `evaluation/multi_model_benchmark` | ❌ | — | `run_benchmark_multimodel.py` |
| `evaluation/capability_eval` | ❌ | — | Script autonome |
| `analytics/stats_calculator` | ❌ | — | `reporting_pipeline.py` (legacy) |
| `analytics/text_analyzer` | ❌ | — | `analysis_pipeline.py` (legacy) |
| `analytics/effectiveness_analyzer` | ❌ | — | `reporting_pipeline.py` (legacy) |
| `reporting/trace_analyzer` | ❌ | ❌ | Aucun (code mort) |
| `reporting/real_time_trace_analyzer` | ❌ | ❌ | `orchestrate_with_existing_tools.py` |
| `reporting/enhanced_real_time_trace_analyzer` | ❌ | ✅ `analysis_runner_v2.py`, `enhanced_pm_analysis_runner.py` | — |
| `reporting/reprompt_trace` | ❌ | ✅ `conversational_orchestrator.py` | — |
| `reporting/document_assembler` | ❌ | ❌ | Framework de rapport |
| `reporting/section_formatter` | ❌ | ❌ | Framework de rapport |
| `reporting/summary_generator` | ❌ | ❌ | `generate_rhetorical_analysis_summaries.py` |
| `reporting/conversation_balance` | ❌ | ❌ | `generate_spectacular_bundle.py` |
| `reporting/cross_reference_graph` | ❌ | ❌ | `generate_spectacular_bundle.py` |
| `reporting/multi_format_exporter` | ❌ | ❌ | `export_scda_state.py`, `generate_spectacular_bundle.py` |

**Note** : L'absence de wiring dans CapabilityRegistry pour l'évaluation est **par design** — ces modules évaluent le pipeline de l'extérieur, ils ne sont pas des capabilities du pipeline.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-07 #763 — Epic B #743*
