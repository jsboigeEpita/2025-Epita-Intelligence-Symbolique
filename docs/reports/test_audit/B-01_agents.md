# B-01: Audit — `tests/unit/argumentation_analysis/agents/`

**Track**: B-01 #756 (Epic B #743)
**Date**: 2026-05-31
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 67 fichiers, 2231 tests collectés

---

## Méthodologie

Chaque fichier de test a été classé selon 3 catégories :

| Catégorie | Sigle | Définition |
|-----------|-------|------------|
| **(a) Mort** | DEAD | Teste un composant qui n'existe PAS dans le registre (`registry_setup.py`) ni dans la factory (`factory.py`) |
| **(b) Non-wiré** | UNWIRED | Teste un composant qui EXISTE dans le code source mais n'est PAS utilisé dans aucun workflow (`workflows.py`) |
| **(c) Justifié** | WIRED | Teste un composant qui EST wiré dans au moins un workflow via `add_phase(capability=...)` |

**Sources croisées :**
- `argumentation_analysis/orchestration/registry_setup.py` — 47+ enregistrements (agents, services, plugins, handlers Tweety)
- `argumentation_analysis/agents/factory.py` — `AGENT_SPECIALITY_MAP` (10 types d'agents)
- `argumentation_analysis/orchestration/workflows.py` — 16 workflows pré-définis (`build_*_workflow`)
- `argumentation_analysis/orchestration/workflow_dsl.py` — `WorkflowPhase(capability=...)`

---

## Scoreboard

| Catégorie | Fichiers | Tests (estimé) | % |
|-----------|----------|----------------|---|
| **(a) DEAD** | 3 | ~80 | 4% |
| **(b) UNWIRED** | 19 | ~550 | 28% |
| **(c) WIRED** | 45 | ~1600 | 67% |

---

## Tableau de classification

### (a) DEAD — Composant absent du registre ET de la factory

| # | Fichier | Composant testé | Pourquoi DEAD |
|---|---------|-----------------|---------------|
| 1 | `core/oracle/test_oracle_agent_behavior_consolidated.py` | Oracle agent behavior | L'oracle n'est pas enregistré dans `registry_setup.py`. Pas de `capability="oracle_*"` dans aucun workflow. Module `agents.core.oracle.*` existe mais n'est pas wiré. |
| 2 | `core/oracle/test_oracle_enhanced_behavior.py` | Oracle enhanced behavior | Idem — oracle non wiré. |
| 3 | `test_plugins_active_in_kernel.py` | Plugins actifs dans kernel (cross-plugin check) | Test d'intégration qui vérifie qu'un ensemble de plugins sont loadés. Le test référence des combinaisons qui ne correspondent pas au wiring actuel du CapabilityRegistry. |

### (b) UNWIRED — Composant existe, mais pas dans les workflows

| # | Fichier | Composant testé | Registre | Pourquoi UNWIRED |
|---|---------|-----------------|----------|-------------------|
| 1 | `core/extract/test_extract_definitions.py` | ExtractAgent definitions | `fact_extraction_service` (capability: `fact_extraction`) | Teste les data classes de `extract_definitions.py` (pas le service wiré). Les definitions existent, le service est wiré, mais le test est sur les structures internes. **Borderline (c)** — justifié si on considère que les structures sont le contrat du service. |
| 2 | `core/oracle/test_cluedo_dataset.py` | Cluedo dataset | Non enregistré | Le dataset Cluedo est utilisé par l'oracle (non wiré) mais existe dans le code. Pas de workflow `cluedo_*`. |
| 3 | `core/oracle/test_dataset_access_manager.py` | Dataset access manager | Non enregistré | Manager d'accès au dataset oracle. Utilitaire interne non wiré. |
| 4 | `core/oracle/test_error_handling.py` | Oracle error handling | Non enregistré | Module d'erreur oracle. Utilitaire interne. |
| 5 | `core/oracle/test_new_modules_integration.py` | Oracle new modules | Non enregistré | Test d'intégration interne oracle. |
| 6 | `core/oracle/test_permissions.py` | Oracle permissions | Non enregistré | Système de permissions oracle. |
| 7 | `core/oracle/test_hypothesis_tracker.py` | Hypothesis tracker | Non enregistré | Tracker d'hypothèses (utilitaire oracle). |
| 8 | `core/oracle/test_interfaces.py` | Oracle interfaces | Non enregistré | ABC/interfaces oracle. |
| 9 | `test_watson_jtms.py` | Watson JTMS agent | `watson` dans factory (tweety_logic, logic_agents) | L'agent Watson est wiré dans factory (specialité `watson`) mais pas comme phase dans un workflow séquentiel. Utilisé dans le mode conversationnel uniquement. |
| 10 | `test_watson_jtms_models.py` | Watson JTMS models | Idem Watson | Data models pour le Watson JTMS. |
| 11 | `test_watson_jtms_utils.py` | Watson JTMS utils | Idem Watson | Utilitaires pour le Watson JTMS. |
| 12 | `tools/analysis/new/test_argument_coherence_evaluator.py` | ArgumentCoherenceEvaluator | Non enregistré | Outil d'analyse `agents/tools/analysis/new/`. Pas dans le registre. |
| 13 | `tools/analysis/new/test_contextual_fallacy_detector.py` | ContextualFallacyDetector | Non enregistré | Outil `agents/tools/analysis/new/`. Pas dans le registre. |
| 14 | `tools/analysis/test_rhetorical_result_visualizer.py` | RhetoricalResultVisualizer | Non enregistré | Visualiseur de résultats rhétoriques. Pas dans le registre. |
| 15 | `tools/analysis/test_fallacy_severity_evaluator.py` | FallacySeverityEvaluator | Non enregistré | Évaluateur de sévérité des sophismes. Pas dans le registre. |
| 16 | `tools/support/test_shared_services.py` | SharedServices | Non enregistré | Services partagés (utilitaire interne). Pas dans le registre. |
| 17 | `tools/test_analysis_tools.py` | Analysis tools | Non enregistré | Tests génériques d'outils d'analyse. |
| 18 | `tools/test_fallacy_analyzers.py` | Fallacy analyzers | `hierarchical_fallacy_detector` wiré | Teste les analyseurs de sophismes indirectement. **Borderline (c)** — les analyzers sont utilisés par le hierarchical_fallacy_detector wiré. |
| 19 | `core/test_orchestration_service.py` | OrchestrationService | Non enregistré (ancien orchestrateur) | Teste un service d'orchestration qui pré-date le CapabilityRegistry. Pas wiré dans le nouveau système. |

### (c) WIRED — Composant actif dans au moins un workflow

| # | Fichier | Composant testé | Capability wirée | Workflows |
|---|---------|-----------------|-------------------|-----------|
| 1 | `core/abc/test_agent_bases.py` | BaseAgent / BaseLogicAgent | Base de tous les agents wirés | (infrastructure transversale) |
| 2 | `core/counter_argument/test_counter_argument.py` | CounterArgumentAgent | `counter_argument_generation` | light, standard, full, spectacular, iterative, quality_gated, hierarchical_fallacy |
| 3 | `core/counter_argument/test_counter_argument_definitions.py` | Counter-argument definitions | (data models pour counter_argument) | Idem |
| 4 | `core/counter_argument/test_counter_argument_evaluator.py` | CounterArgumentEvaluator | `counter_argument_generation` | Idem |
| 5 | `core/counter_argument/test_counter_argument_parser.py` | CounterArgumentParser | `counter_argument_generation` | Idem |
| 6 | `core/counter_argument/test_evaluator.py` | Evaluator | `counter_argument_generation` | Idem |
| 7 | `core/counter_argument/test_evaluator_extended.py` | Evaluator extended | `counter_argument_generation` | Idem |
| 8 | `core/counter_argument/test_parser.py` | Parser | `counter_argument_generation` | Idem |
| 9 | `core/counter_argument/test_strategies.py` | Strategies (5 rhetorical) | `counter_argument_generation` | Idem |
| 10 | `core/counter_argument/test_strategies_extended.py` | Strategies extended | `counter_argument_generation` | Idem |
| 11 | `core/debate/test_debate.py` | DebateAgent + DebatePlugin | `adversarial_debate` | standard, full, spectacular, iterative, debate_governance |
| 12 | `core/debate/test_knowledge_base.py` | KnowledgeBase (debate) | `adversarial_debate` | Idem |
| 13 | `core/debate/test_debate_definitions.py` | Debate definitions | `adversarial_debate` | Idem |
| 14 | `core/debate/test_debate_scoring.py` | ArgumentAnalyzer / scoring | `debate_scoring` | Idem |
| 15 | `core/debate/test_protocols.py` | Walton-Krabbe protocols | `adversarial_debate` | Idem |
| 16 | `core/extract/test_extract_agent.py` | ExtractAgent | `fact_extraction` | Tous les workflows |
| 17 | `core/governance/test_governance.py` | Governance module import | `governance_simulation` | standard, full, spectacular, iterative, debate_governance |
| 18 | `core/governance/test_governance_methods.py` | 7 voting methods | `multi_method_voting` | Idem |
| 19 | `core/governance/test_governance_metrics.py` | Governance metrics | `governance_simulation` | Idem |
| 20 | `core/governance/test_governance_simulation.py` | Governance simulation | `governance_simulation` | Idem |
| 21 | `core/governance/test_social_choice.py` | Social choice theory | `preference_aggregation` | Idem |
| 22 | `core/governance/test_conflict_resolution.py` | Conflict resolution | `governance_simulation` | Idem |
| 23 | `core/informal/test_informal_definitions.py` | Informal fallacy definitions | `fallacy_detection` (via `informal_fallacy` factory) | hierarchical_fallacy, neural_symbolic |
| 24 | `core/informal/test_informal_agent_adapter.py` | InformalAnalysisAgent adapter | `fallacy_detection` | Idem |
| 25 | `core/logic/test_belief_set.py` | BeliefSet (PL/FOL/Modal) | `propositional_logic`, `fol_reasoning`, `modal_logic` | nl_to_logic, standard, full, spectacular, formal_extended |
| 26 | `core/logic/test_cl_handler.py` | Conditional Logic handler | `conditional_logic` | formal_extended |
| 27 | `core/logic/test_dl_handler.py` | Description Logic handler | `description_logic` | formal_extended |
| 28 | `core/logic/test_eprover_spass_integration.py` | EProver/SPASS external solvers | `external_fol_solving`, `external_modal_solving` | spectacular |
| 29 | `core/logic/test_sat_handler.py` | SAT/MaxSAT/MUS handler | `sat_solving` | (dans `logic_capabilities` du registre) |
| 30 | `core/logic/test_af_handler_extended.py` | AF handler (Dung) | `dung_extensions` | standard, full, spectacular, formal_extended, jtms_dung |
| 31 | `core/logic/test_fol_signature_predeclaration.py` | FOL signature predeclaration | `fol_reasoning` | spectacular, standard, full, formal_extended |
| 32 | `core/logic/test_track_a_handlers.py` | Track A Tweety handlers | `ranking_semantics`, `bipolar_argumentation`, `aba_reasoning`, etc. | spectacular, formal_extended |
| 33 | `core/pm/test_pm_agent.py` | ProjectManager agent | `project_manager` factory | (mode conversationnel) |
| 34 | `core/pm/test_sherlock_enquete_agent.py` | SherlockEnqueteAgent | `sherlock` factory | sherlock_modern workflow |
| 35 | `core/quality/test_quality_evaluator.py` | ArgumentQualityEvaluator | `argument_quality` | light, standard, full, spectacular, iterative, neural_symbolic, hierarchical_fallacy |
| 36 | `core/quality/test_quality_virtue_detectors.py` | 9 virtue detectors | `virtue_detection` | Idem |
| 37 | `core/synthesis/test_synthesis_agent.py` | SynthesisAgent | `analysis_synthesis` | spectacular |
| 38 | `core/synthesis/test_synthesis_data_models.py` | Synthesis data models | `analysis_synthesis` | spectacular |
| 39 | `core/test_plugin_loader.py` | PluginLoader | (infrastructure transversale) | Tous les workflows |
| 40 | `core/test_exceptions.py` | Exceptions module | (infrastructure transversale) | Tous les workflows |
| 41 | `tools/analysis/test_complex_fallacy_analyzer.py` | ComplexFallacyAnalyzer | Utilisé par `informal_fallacy` factory | hierarchical_fallacy |
| 42 | `tools/analysis/test_contextual_fallacy_analyzer.py` | ContextualFallacyAnalyzer | Utilisé par `informal_fallacy` factory | hierarchical_fallacy |
| 43 | `utils/test_taxonomy_navigator.py` | TaxonomyNavigator | Utilisé par `FallacyWorkflowPlugin` | hierarchical_fallacy |
| 44 | `test_fol_signature_extraction.py` | FOL signature extraction | `fol_reasoning` | spectacular, standard, full |
| 45 | `tools/analysis/test_fallacy_severity_evaluator.py` | FallacySeverityEvaluator | Utilisé par `fallacy_detection` pipeline | hierarchical_fallacy |

> **Note sur la catégorie (b)** : les fichiers borderline `(b→c)` comme `test_extract_definitions.py` et `test_fallacy_analyzers.py` testent des structures/utilitaires internes qui servent les capabilities wirées. Ils sont techniquement non-wirés en tant que service indépendant, mais leur code est appelé par un composant wiré. Ils restent précieux.

---

## Récit du framework — 4 épisodes de l'évolution cristallisée dans les tests

### Épisode 1 : L'ère pré-Lego (agents isolés, ~2025-Q1)

Les tests les plus anciens dans `core/oracle/`, `core/test_orchestration_service.py`, et `test_watson_jtms.py` témoignent d'une architecture où chaque agent était un module autonome avec son propre orchestrateur. L'`OrchestrationService` (testé dans `core/test_orchestration_service.py`) était un service centralisé qui coordonnait les agents séquentiellement — avant l'introduction du `CapabilityRegistry`. Les 8 fichiers de test oracle (`test_cluedo_dataset.py`, `test_oracle_enhanced_behavior.py`, etc.) montrent un module complet et autonome (Moriarty interrogator, Cluedo dataset, hypothesis tracker, permissions) qui n'a jamais été intégré dans le pipeline unifié. Le Watson JTMS (`test_watson_jtms*.py`) suit le même pattern : un agent sophistiqué avec models/utils dédiés, wiré dans la factory (`sherlock`/`watson` specialities) mais pas comme phase de workflow.

**Trace dans les tests** : `test_orchestration_service.py` importe `OrchestrationService` qui est l'ancêtre du `UnifiedPipeline`. Les 3 fichiers `test_watson_jtms*.py` montrent un agent avec une couche models/utils distincte — pattern qui a été abandonné au profit des `@kernel_function` plugins.

### Épisode 2 : L'intégration étudiante (Epic #35, ~2025-Q2)

Les sous-répertoires `counter_argument/`, `debate/`, `governance/`, `quality/` correspondent aux 12 projets étudiants intégrés. Chaque projet a apporté son propre agent avec ses data models, ses strategies/evaluators, et ses tests. Le pattern est visible :

- **Counter-argument** (`2.3.3`) : 9 fichiers de test couvrant definitions, evaluator, parser, strategies — reflétant l'architecture originale du projet étudiant avant normalisation via `CounterArgumentPlugin`
- **Debate** (`1.2.7`) : 5 fichiers (knowledge_base, definitions, scoring, protocols) — Walton-Krabbe protocols, personnalités multiples
- **Governance** (`2.1.6`) : 6 fichiers (methods, metrics, simulation, social_choice, conflict_resolution) — 7 méthodes de vote
- **Quality** (`2.3.5`) : 2 fichiers (evaluator + virtue detectors) — 9 vertus

**Trace dans les tests** : La densité des tests dans `counter_argument/` (9 fichiers) contraste avec les tests synthétiques des modules plus récents. Les fichiers dupliqués (`test_evaluator.py` + `test_counter_argument_evaluator.py`, `test_parser.py` + `test_counter_argument_parser.py`) montrent l'évolution : les fichiers sans préfixe `counter_argument_` sont probablement les originaux étudiants, les préfixés sont les versions normalisées.

### Épisode 3 : La normalisation Lego (Epic #208, #310, ~2025-Q3)

L'introduction du `CapabilityRegistry` + `AgentFactory` + `WorkflowDSL` a transformé l'architecture. Les tests `test_agent_bases.py`, `test_plugin_loader.py` valident cette infrastructure. Les workflows pré-définis (`build_*_workflow()`) ont normalisé comment les capabilities sont composées. Le `AGENT_SPECIALITY_MAP` dans factory.py a introduit le concept de "specialité" où chaque agent reçoit uniquement les plugins pertinents.

**Trace dans les tests** : `test_plugins_active_in_kernel.py` tente de valider ce wiring — mais il test un état qui n'est plus celui du pipeline actuel, ce qui en fait un test (a) DEAD. Les fichiers `test_extract_agent.py` et `test_synthesis_agent.py` montrent des agents qui héritent de `BaseAgent(ChatCompletionAgent)` — le pattern post-normalisation.

### Épisode 4 : L'expansion formelle (Track A #55-#90, Track LL #705, ~2026-Q1-Q2)

Les handlers Tweety (`test_track_a_handlers.py`, `test_cl_handler.py`, `test_dl_handler.py`, `test_sat_handler.py`) témoignent de l'intégration massive des extensions Tweety (ranking, bipolar, ABA, ADF, ASPIC+, etc.). Le `build_formal_extended_workflow()` chaîne 14 phases formelles. Les tests `test_fol_signature_predeclaration.py` et `test_fol_signature_extraction.py` valident le mécanisme de pré-déclaration FOL qui a résolu le problème de génération de formules FOL vides (issue connue dans le scoreboard DAG). Le handler SAT (`test_sat_handler.py`) est le seul qui n'utilise PAS la JVM (PySAT+Z3), ce qui en fait un cas particulier dans l'écosystème Tweety.

**Trace dans les tests** : `test_eprover_spass_integration.py` montre le routing vers des solveurs externes (EProver, Prover9, SPASS) — une couche d'abstraction au-dessus de Tweety pour les cas où le solveur Java est insuffisant. `test_af_handler_extended.py` étend les tests Dung avec les 11 sémantiques d'extension.

---

## Actions recommandées

### Priorité HAUTE — Nettoyage (a) DEAD

| Action | Fichier | Impact |
|--------|---------|--------|
| Supprimer ou archiver | `core/oracle/test_oracle_agent_behavior_consolidated.py` | ~30 tests morts |
| Supprimer ou archiver | `core/oracle/test_oracle_enhanced_behavior.py` | ~20 tests morts |
| Réécrire ou supprimer | `test_plugins_active_in_kernel.py` | ~30 tests obsolètes |

### Priorité MOYENNE — Oracle non-wiré (b)

Le module oracle (8 fichiers de test, ~200 tests) est complet mais déconnecté du pipeline. Deux options :
1. **Wirer l'oracle** dans un workflow dédié (ex: `build_sherlock_investigation_workflow`)
2. **Archiver** les tests oracle avec un tag `@pytest.mark.oracle` et les exclure du run par défaut

### Priorité BASSE — Outils non-wirés (b)

Les outils dans `tools/analysis/new/` et `tools/analysis/` (severity evaluator, coherence evaluator, contextual detector, visualizer) ne sont pas dans le registre. Si ils sont appelés indirectement par des plugins wirés → reclasser en (c). Sinon → évaluer l'intérêt et potentiellement wirer ou archiver.

### Infrastructure

- Les fichiers dupliqués dans `counter_argument/` (`test_evaluator.py` vs `test_counter_argument_evaluator.py`) méritent une consolidation — un seul des deux suffit.
- `core/test_orchestration_service.py` teste l'ancien orchestrateur pré-CapabilityRegistry. À archiver une fois que le CapabilityRegistry sera l'unique chemin.

---

## Annexe : Wiring complet des capabilities par workflow

| Capability | Workflows où elle apparaît |
|------------|---------------------------|
| `fact_extraction` | light, standard, full, spectacular, iterative, quality_gated, hierarchical_fallacy, nl_to_logic, formal_extended |
| `argument_quality` | light, standard, full, spectacular, iterative, quality_gated, neural_symbolic, hierarchical_fallacy |
| `counter_argument_generation` | light, standard, full, spectacular, iterative, quality_gated |
| `neural_fallacy_detection` | standard, full, spectacular, neural_symbolic |
| `hierarchical_fallacy_detection` | standard, full, spectacular, iterative, neural_symbolic, hierarchical_fallacy |
| `nl_to_logic_translation` | standard, full, spectacular, nl_to_logic, formal_extended |
| `propositional_logic` | standard, full, spectacular, nl_to_logic, formal_extended |
| `fol_reasoning` | standard, full, spectacular, nl_to_logic, formal_extended |
| `modal_logic` | full, spectacular, formal_extended |
| `dung_extensions` | standard, full, spectacular, formal_extended, jtms_dung |
| `aspic_plus_reasoning` | standard, full, spectacular, formal_extended, jtms_dung |
| `belief_maintenance` (JTMS) | standard, full, spectacular, iterative, jtms_dung |
| `governance_simulation` | standard, full, spectacular, iterative, debate_governance |
| `adversarial_debate` | standard, full, spectacular, iterative, debate_governance |
| `ranking_semantics` | spectacular, formal_extended |
| `bipolar_argumentation` | spectacular, formal_extended |
| `probabilistic_argumentation` | spectacular, formal_extended |
| `atms_reasoning` | spectacular |
| `formal_synthesis` | spectacular |
| `narrative_synthesis` | full, spectacular |
| `analysis_synthesis` | spectacular |
| `deep_synthesis` | spectacular |
| `belief_revision` | spectacular, formal_extended |
| `external_fol_solving` | spectacular |
| `external_modal_solving` | spectacular |
| `aba_reasoning` | formal_extended |
| `adf_reasoning` | formal_extended |
| `dialogue_protocols` | formal_extended |
| `conditional_logic` | formal_extended |
| `description_logic` | formal_extended |
| `sat_solving` | (registre seulement) |
| `stakes_extraction` | spectacular |
| `nl_extraction` | spectacular |
| `kb_to_tweety` | spectacular |
| `formal_result_interpretation` | spectacular, formal_extended |
| `speech_transcription` | full |
| `semantic_indexing` | full |
| `collaborative_analysis` | collaborative |

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-01 #756 — Epic B #743*
