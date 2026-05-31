# Audit B-04: `tests/unit/argumentation_analysis/plugins/` (18 files, 502 tests)

**Issue**: #760 (B-04) | **Epic**: #743 | **Date audit**: 2026-05-31
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Fichiers test | 18 |
| Fonctions test | 502 |
| LOC tests | 6 474 |
| Fichiers source (`plugins/`) | 30 (dont 3 in-source tests) |
| LOC source | 11 328 |
| Plugins SK `@kernel_function` | 15 classes |
| Outils d'analyse (non-SK) | 5 classes |
| Ratio tests/source | 0.57 |

### Périmètre source audité

| Module source | LOC | Rôle | SK Plugin? |
|--------------|-----|------|------------|
| `fallacy_workflow_plugin.py` | 1 089 | Taxonomie hiérarchique + iterative deepening | Oui |
| `narrative_synthesis_plugin.py` | 626 | Synthèse narrative LLM prose | Oui |
| `tweety_logic_plugin.py` | 614 | 21 `@kernel_function` wrapping Tweety handlers | Oui |
| `semantic_kernel/jtms_plugin.py` | 631 | 5 `@kernel_function` JTMS belief management | Oui |
| `logic_agent_plugin.py` | 352 | 8 `@kernel_function` PL/FOL/Modal | Oui |
| `text_to_kb_plugin.py` | 369 | NL→KB extraction (iterative descent) | Oui |
| `kb_to_tweety_plugin.py` | 430 | KB→Tweety formula translation | Oui |
| `tweety_result_interpretation_plugin.py` | 323 | Formal results → French NL | Oui |
| `coordinated_logic_plugin.py` | 266 | 2-pass coordinated PL/FOL pipeline | Oui |
| `atms_plugin.py` | 224 | 4 `@kernel_function` ATMS assumption-based | Oui |
| `nl_to_logic_plugin.py` | 176 | NL→PL/FOL translation | Oui |
| `governance_plugin.py` | 163 | 4 `@kernel_function` vote/consensus | Oui |
| `french_fallacy_plugin.py` | 63 | 3 `@kernel_function` hybrid fallacy detection | Oui |
| `exploration_plugin.py` | 144 | Taxonomy navigation (slave kernel) | Oui |
| `quality_scoring_plugin.py` | 120 | 3 `@kernel_function` quality evaluation | Oui |
| `identification_models.py` | 52 | Pydantic models (IdentifiedFallacy, etc.) | Non |
| `ranking_plugin.py` | 50 | 2 `@kernel_function` ranking semantics | Oui |
| `aspic_plugin.py` | 45 | 2 `@kernel_function` ASPIC+ reasoning | Oui |
| `toulmin_plugin.py` | 45 | 1 `@kernel_function` (stub NotImplementedError) | Oui |
| `belief_revision_plugin.py` | 72 | 3 `@kernel_function` AGM belief revision | Oui |
| `analysis_tools/logic/complex_fallacy_analyzer.py` | 1 608 | Complex fallacy analysis (Enhanced) | Non |
| `analysis_tools/logic/contextual_fallacy_analyzer.py` | 975 | Context-aware fallacy detection | Non |
| `analysis_tools/logic/rhetorical_result_analyzer.py` | 817 | Rhetorical aggregation + recommendations | Non |
| `analysis_tools/logic/rhetorical_result_visualizer.py` | 568 | HTML/visualization report generation | Non |
| `analysis_tools/logic/fallacy_severity_evaluator.py` | 446 | Severity scoring with context modifiers | Non |
| `analysis_tools/logic/nlp_model_manager.py` | 157 | Singleton NLP model loader (transformers) | Non |
| `analysis_tools/plugin.py` | 127 | AnalysisToolsPlugin facade | Non |

---

## 1. Classification a/b/c — Tableau de wiring

### Légende

- ✅ **Wired** : test couvre un plugin ou outil enregistré dans `CapabilityRegistry` / utilisé par un workflow
- ⚠️ **Dérogation justifiée** : helper interne, modèle Pydantic, analyse tool non-wiré mais testé
- ❌ **Orphelin** : source sans test OU test sans source correspondante

---

### 1A. SK Plugins Core (kernel_function) — 12 fichiers test, ~370 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_governance_plugin.py` | 15 | `governance_plugin.py` (GovernancePlugin) | ✅ Wired | 4 `@kernel_function`: detect_conflicts, resolve_conflict, compute_consensus_metrics, list_governance_methods |
| `test_quality_scoring_plugin.py` | 13 | `quality_scoring_plugin.py` (QualityScoringPlugin) | ✅ Wired | 3 `@kernel_function`: evaluate_argument_quality, get_quality_score, list_virtues |
| `test_jtms_sk_plugin.py` | 41 | `semantic_kernel/jtms_plugin.py` (JTMSSemanticKernelPlugin) | ✅ Wired | 5 `@kernel_function`: create_belief, add_justification, explain_belief, query_beliefs, get_jtms_state. Mocks JTMSService + SessionManager. Paramétré (5-way filter). |
| `test_fallacy_workflow_plugin.py` | 44 | `fallacy_workflow_plugin.py` + `exploration_plugin.py` + `identification_models.py` | ✅ Wired | Master suite: construction, taxonomy, kernel creation, exploration, one-shot, iterative deepening, trace logging, error handling |
| `test_fallacy_workflow_calibration.py` | 3 | `fallacy_workflow_plugin.py` (calibration) | ✅ Wired | Context-aware mock LLM: 8-fallacy, EPITA 2-fallacy, neutral false-positive guard. Uses real `taxonomy_medium.csv`. |
| `test_atms_plugin.py` | 17 | `atms_plugin.py` (ATMSPlugin) | ✅ Wired | 4 `@kernel_function`: create_assumption, add_justification, check_environment, enumerate_labels. Multi-instance isolation. |
| `test_tweety_plugins.py` | 16 | `ranking_plugin.py` + `aspic_plugin.py` + `belief_revision_plugin.py` + `toulmin_plugin.py` | ✅ Wired | Composite test file. 4 plugins, handlers mocked. ToulminPlugin is intentional stub (NotImplementedError). |
| `test_nl_to_logic_plugin.py` | 11 | `nl_to_logic_plugin.py` (NLToLogicPlugin) | ✅ Wired | translate_to_pl/fol + batch variants. Factory/registry integration tested. |
| `test_logic_agent_plugin.py` | 31 | `logic_agent_plugin.py` (LogicAgentPlugin) | ✅ Wired | 8 `@kernel_function`: PL/FOL/Modal parse/execute/check + validate. JVM-unavailable guards. Registry/factory integration. |
| `test_kb_to_tweety_plugin.py` | 28 | `kb_to_tweety_plugin.py` (KBToTweetyPlugin) | ✅ Wired | PL/FOL/Modal translation, batch, Dung/ASPIC translation, write_to_state. Pydantic models tested. Registry/factory integration. |
| `test_text_to_kb_plugin.py` | 29 | `text_to_kb_plugin.py` (TextToKBPlugin) | ✅ Wired | NL→KB extraction, chunk splitting, heuristic extraction, FOL signature, write_to_state. Registry/factory integration. |
| `test_tweety_result_interpretation_plugin.py` | 46 | `tweety_result_interpretation_plugin.py` | ✅ Wired | Dung/FOL/ASPIC/ranking/belief_revision interpretation to French NL. Full analysis. Write_to_state. Registry/factory. |
| `test_narrate_convergence.py` | 19 | `narrative_synthesis_plugin.py` (NarrativeSynthesisPlugin) | ✅ Wired | LLM prose layer, fallback template, mock kernel, `@requires_api` real LLM test. Track CC #636. |
| `test_track_qq_convergent_insight.py` | 9 | `narrative_synthesis_plugin.py` (convergent insight) | ✅ Wired | Substantive insight for ≥3 methods, standard insight for 2. Track QQ #667. |

**Sous-total SK Plugins Core**: 14 fichiers test, ~322 tests, **0 orphelins**

---

### 1B. Analysis Tools (non-SK) — 4 fichiers test, ~180 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `analysis_tools/logic/test_enhanced_contextual_fallacy_analyzer.py` | 55 | `analysis_tools/logic/contextual_fallacy_analyzer.py` | ⚠️ Justifié | Non-SK tool. Context classification, complementary fallacies, deep analysis, filtering, feedback learning. Comprehensive heuristics tests. |
| `analysis_tools/logic/test_enhanced_severity_evaluator.py` | 37 | `analysis_tools/logic/fallacy_severity_evaluator.py` | ⚠️ Justifié | Non-SK tool. Severity levels, context/audience/domain modifiers, overall severity formula. Pure-Python, no mocks. |
| `analysis_tools/logic/test_nlp_model_manager.py` | 12 | `analysis_tools/logic/nlp_model_manager.py` | ⚠️ Justifié | Singleton pattern, transformers-optional, class-state save/restore. Graceful degradation. |
| `analysis_tools/logic/test_rhetorical_result_analyzer.py` | 76 | `analysis_tools/logic/rhetorical_result_analyzer.py` | ⚠️ Justifié | Master suite: RecommendationGenerator (22 tests) + EnhancedRhetoricalResultAnalyzer (54 tests). Fallacy distribution, coherence, persuasion (ethos/pathos/logos), strengths/weaknesses, context relevance, rhetorical appeals, strategies. |

**Sous-total Analysis Tools**: 4 fichiers test, ~180 tests, **0 orphelins**

---

## 2. Sources sans test dédié — Angle morts

| Source | LOC | SK Plugin? | Raison | Priorité |
|--------|-----|------------|--------|----------|
| `tweety_logic_plugin.py` | 614 | Oui | 21 `@kernel_function` — le plus volumineux. Testé indirectement via `test_pipeline_wiring.py` (B-02) et workflows, mais **aucun test unitaire dédié** | HIGH |
| `french_fallacy_plugin.py` | 63 | Oui | 3 `@kernel_function` hybrid fallacy. Testé via workflows (B-02 invoke_callables), pas de test unitaire dédié | MEDIUM |
| `coordinated_logic_plugin.py` | 266 | Oui | 4 `@kernel_function` 2-pass PL/FOL. Testé via `test_nl_to_logic_wiring.py` (B-02), pas de test unitaire dédié | MEDIUM |
| `analysis_tools/logic/complex_fallacy_analyzer.py` | 1 608 | Non | Plus volumineux fichier du packet. Tests in-source (`analysis_tools/tests/test_enhanced_complex_fallacy_analyzer.py`, 187 LOC) existent mais pas dans `tests/unit/` | LOW |
| `analysis_tools/logic/rhetorical_result_visualizer.py` | 568 | Non | Visualisation HTML. Pas de test unitaire (génération de fichiers HTML visuels) | LOW |
| `analysis_tools/plugin.py` | 127 | Oui (AnalysisToolsPlugin) | Facade wrapper. Pas de test dédié | LOW |

### Note sur les tests in-source

Le répertoire `argumentation_analysis/plugins/analysis_tools/tests/` contient 3 fichiers de test (776 LOC total) qui prédatent la migration vers `tests/unit/`. Ceux-ci sont des **doublons partiels** des tests dans `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/`:
- `test_enhanced_complex_fallacy_analyzer.py` (187 LOC) — pas de pendant dans `tests/unit/`
- `test_enhanced_contextual_fallacy_analyzer.py` (318 LOC) — doublon de `tests/unit/.../test_enhanced_contextual_fallacy_analyzer.py` (555 LOC)
- `test_enhanced_fallacy_severity_evaluator.py` (271 LOC) — doublon de `tests/unit/.../test_enhanced_severity_evaluator.py` (288 LOC)

**Recommandation**: Les 2 doublons dans `analysis_tools/tests/` devraient être archivés. Le fichier `test_enhanced_complex_fallacy_analyzer.py` est le seul à ne pas avoir de pendant et devrait être migré.

---

## 3. Récit du framework — Évolution cristallisée dans les tests

### Épisode 1: Les plugins Tweety originaux (commits ~7734 — Sprint 1-2)
`test_tweety_plugins.py` teste les 4 plugins historiques (`RankingPlugin`, `ASPICPlugin`, `BeliefRevisionPlugin`, `ToulminPlugin`) qui encapsulent les Handlers Tweety via JPype. Chaque test patche le handler correspondant. `ToulminPlugin` est un **stub intentionnel** (`NotImplementedError`), jamais complété — ce pattern de "coquille déclarative" est un marqueur du framework early-stage où les `@kernel_function` servaient de contrat d'interface avant implémentation.

### Épisode 2: Gouvernance + Qualité — Les premiers plugins complets (Sprint 2-3)
`test_governance_plugin.py` (15 tests) et `test_quality_scoring_plugin.py` (13 tests) sont les premiers plugins à avoir une implémentation complète dès le départ — pas de stubs. GovernancePlugin wrappe `SocialChoiceModule` (7 méthodes de vote), QualityScoringPlugin wrappe `ArgumentQualityEvaluator` (9 vertus). Pattern: constructeur injecte le service, `@kernel_function` prend/retourne JSON string. Ce contrat "JSON-in/JSON-out" est devenu la norme pour tous les plugins suivants.

### Épisode 3: FallacyWorkflow — Le plugin le plus complexe (Issue #84, #158, #259, #269)
`test_fallacy_workflow_plugin.py` (44 tests) cristallise l'évolution la plus riche:
1. **Construction simple** (5 tests) → taxonomy load from CSV/data/empty
2. **Kernel creation** (5 tests) → master/slave kernel pattern (unique à ce plugin)
3. **ExplorationPlugin** (8 tests) → navigation hiérarchique, leaf detection, confirm/conclude
4. **Modèles Pydantic** (4 tests) → IdentifiedFallacy, FallacyAnalysisResult avec confidence clamping
5. **One-shot mode** (4 tests) → fallback quand iterative deepening échoue
6. **Iterative deepening** (3 tests) → fallback vers one-shot sur erreur
7. **Trace logging** (2 tests) → file handler creation/cleanup avec defensive guards (None/"null"/""/"null" string — 4 tests!)
8. **Calibration** (3 tests dans fichier séparé) → Issue #259: detection multi-branches calibrée

L'évolution de #84 (initial) → #158 (unify language) → #259 (calibrate multi-branch) → #269 (fix async mock) montre un plugin qui a mûri de "proof of concept" à "production-ready".

### Épisode 4: ATMS — Plugin pur Python sans JVM (Issue #292)
`test_atms_plugin.py` (17 tests) est remarquable car c'est le seul plugin logic qui ne dépend PAS de JPype/Tweety. L'ATMS (Assumption-based Truth Maintenance System) est implémenté en pur Python. Les tests vérifient la dérivation, les nogoods, les environnements minimaux, et **l'isolation multi-instance** (2 tests dédiés) — une préoccupation qui n'apparaît que pour ce plugin.

### Épisode 5: NL→Logic + LogicAgent — Deux couches de formalisation (Issues #477, #285/#287)
`test_nl_to_logic_plugin.py` (11 tests) et `test_logic_agent_plugin.py` (31 tests) représentent deux approches complémentaires de NL→formal:
- **NLToLogicPlugin**: traduction NL→PL/FOL via LLM, avec batch et validation retry
- **LogicAgentPlugin**: 8 `@kernel_function` pour PL/FOL/Modal parse+execute+check+validate, déléguant à `TweetyBridge`

LogicAgentPlugin a le pattern le plus complet de guards JVM: 7 tests `test_*_no_jvm` qui vérifient que chaque fonction retourne `{"error": "JVM..."}` sans crasher. Ce pattern "graceful degradation" a été établi ici et propagé aux autres plugins Tweety.

### Épisode 6: KB Pipeline — L'arc TextToKB → KBToTweety → Interpretation (Issues #474, #475, #476)
Trois plugins complémentaires testés par trois fichiers dédiés (103 tests total):
1. `test_text_to_kb_plugin.py` (29 tests) — NL→KB: chunk splitting, heuristic extraction, FOL signature
2. `test_kb_to_tweety_plugin.py` (28 tests) — KB→Tweety: PL/FOL/Modal formula builders, Dung/ASPIC translation, write_to_state
3. `test_tweety_result_interpretation_plugin.py` (46 tests) — Formal→French NL: Dung extensions, FOL queries, ASPIC rules, ranking, belief revision

Ces 3 plugins forment un **pipeline complet** (extraction → formalisation → interprétation) et sont les seuls à tester systématiquement:
- Les **modèles Pydantic** (`TweetyTranslationResult`, `DungTranslationResult`, `AspicTranslationResult`, etc.)
- L'**intégration registry/factory** (`TestRegistryIntegration`, `TestFactoryIntegration`)
- Le **write_to_state** (interaction avec `UnifiedAnalysisState`)

### Épisode 7: Narrative Synthesis — De la template à l'LLM (Tracks CC #636, QQ #667)
`test_narrate_convergence.py` (19 tests) et `test_track_qq_convergent_insight.py` (9 tests) documentent l'évolution du NarrativeSynthesisPlugin:
- **Track CC**: LLM prose layer avec fallback template. Teste 4 niveaux (kernel=None, no verdicts, LLM exception, empty LLM response, bad JSON, mocked kernel)
- **Track QQ**: Substantive insight paragraph pour ≥3 méthodes ("sur-determinee"), standard insight pour 2 méthodes. Distingue les niveaux de convergence.

### Épisode 8: Analysis Tools — L'outil qui a grandi au-delà du plugin (Sprint 3-5)
Les 4 fichiers `analysis_tools/logic/test_*.py` (180 tests) testent des **classes non-SK** qui ont évolué en dehors du framework de plugins:
- **ContextualFallacyAnalyzer** (55 tests): classification de contexte (politique/scientifique/commercial/juridique), fallacies complémentaires, feedback learning
- **FallacySeverityEvaluator** (37 tests): scoring de sévérité avec modificateurs contexte/audience/domaine. Formule documentée: `(1-severity)*0.3 + coherence*0.3 + persuasion*0.4`
- **NLPModelManager** (12 tests): singleton transformers-optional avec graceful degradation. Pattern `try/finally` pour restaurer l'état de classe entre tests.
- **RhetoricalResultAnalyzer** (76 tests): le plus gros test du packet. Sépare RecommendationGenerator (22 tests) de l'analyseur (54 tests). Teste ethos/pathos/logos, persuasion strategies, context relevance.

### Épisode 9: JTMS SK Plugin — Le pont entre service et kernel (Sprint 4)
`test_jtms_sk_plugin.py` (41 tests) est le seul plugin à tester des **méthodes async** et un **session management** complexe:
- Auto-création session/instance (4 tests)
- Guards quand auto-create disabled (2 tests)
- Paramétrage 5-way de query_beliefs filter
- Enrichissement session_info (timestamps, checkpoint_count)

---

## 4. Patterns transversaux

### 4.1 Contrat JSON-in/JSON-out
Presque tous les `@kernel_function` suivent le même contrat: input = JSON string, output = JSON string. Les tests font systématiquement `json.loads()` et vérifient la forme du dict/list retourné. Les erreurs retournent `{"error": "..."}` plutôt que des exceptions (sauf Tweety plugins historiques qui laissent `json.JSONDecodeError` propager).

### 4.2 Isolation du backend
| Plugin | Backend mocké | Pattern |
|--------|--------------|---------|
| JTMS | `JTMSService` + `JTMSSessionManager` (AsyncMock) | Mock injecté |
| FallacyWorkflow | LLM (AsyncMock) + taxonomy CSV | Mock kernel |
| Tweety (4 plugins) | Handlers JPype | `patch()` sur handler |
| NLToLogic | `NLToLogicTranslator` | Mock injecté |
| LogicAgent | `TweetyBridge` + `_jvm_available` | `patch()` sur bridge |
| ATMS | Aucun (pur Python) | Pas de mock |
| Governance | Aucun (pure logic) | Pas de mock |
| QualityScoring | Aucun (wraps evaluator) | Pas de mock |

### 4.3 Integration testing via registry/factory
Les plugins de l'Épisode 6 (KB pipeline) + LogicAgentPlugin + NLToLogicPlugin testent explicitement:
- `_PLUGIN_REGISTRY` → registration
- `AGENT_SPECIALITY_MAP` → speciality wiring
- `setup_registry()` → capability strings

Cette couverture d'intégration est absente des plugins historiques (Tweety 4-pack, Governance, QualityScoring).

---

## 5. Recommandations

| # | Recommandation | Priorité | Justification |
|---|---------------|----------|---------------|
| R1 | Créer `test_tweety_logic_plugin.py` — tests unitaires pour les 21 `@kernel_function` | **HIGH** | 614 LOC, plus gros plugin, aucun test dédié. Testé indirectement via B-02 invoke_callables mais pas au niveau unitaire. |
| R2 | Créer `test_french_fallacy_plugin.py` — 3 `@kernel_function` | **MEDIUM** | 63 LOC mais plugin wiré dans registry. Pas de test unitaire dédié. |
| R3 | Créer `test_coordinated_logic_plugin.py` — 4 `@kernel_function` | **MEDIUM** | 266 LOC, pattern 2-pass unique. Pas de test unitaire dédié. |
| R4 | Archiver les tests in-source doublons (`analysis_tools/tests/`) | **LOW** | 2 doublons (589 LOC). Migrer `test_enhanced_complex_fallacy_analyzer.py` vers `tests/unit/`. |
| R5 | Ajouter registry/factory integration tests aux plugins historiques | **LOW** | Governance, QualityScoring, ATMS n'ont pas de `TestRegistryIntegration`/`TestFactoryIntegration`. |
| R6 | Tester `analysis_tools/plugin.py` (AnalysisToolsPlugin facade) | **LOW** | 127 LOC, wiré dans registry, pas de test dédié. |

---

## 6. Synthèse

| Classification | Fichiers test | Tests | % |
|---------------|--------------|-------|---|
| ✅ Wired | 14 | ~322 | 64% |
| ⚠️ Justifié (analysis tools) | 4 | ~180 | 36% |
| ❌ Orphelin | 0 | 0 | 0% |
| **Sources sans test** | 6 sources non-testées | — | — |

**Key finding**: 0 orphelins dans les tests — chaque fichier test a un source correspondante. Le packet plugins est le mieux couvert des packets audités (B-02 avait aussi 0 orphelins mais avec plus d'angles morts sources).

**Angle mort principal**: `tweety_logic_plugin.py` (614 LOC, 21 kernel functions) est le plus gros fichier source sans test unitaire dédié. Il est testé indirectement via `test_pipeline_wiring.py` et `test_text_kb_spectacular_wiring.py` (B-02), mais mérite son propre fichier de test.

**Doublon à nettoyer**: Les tests in-source dans `argumentation_analysis/plugins/analysis_tools/tests/` (2 doublons sur 3 fichiers) devraient être archivés au profit des tests unifiés dans `tests/unit/`.
