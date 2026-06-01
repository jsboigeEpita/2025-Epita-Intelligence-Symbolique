# B-13: Audit — tests/integration/ (framework crystallisation)

**Track**: B-13 #770 (Epic B #743)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 69 fichiers de test, ~408 tests collectes

---

## Methodologie

Classification Wired / Derogation / Orphelin selon le cahier des charges B-13.
Enrichissement mandate user R281c : identification des episodes du framework cristallises dans ces tests, narration par arc temporel, et detection des capabilities muettes (peu/pas couvertes).

Le wiring se verifie par :
- **CapabilityRegistry** : grep dans `registry_setup.py` (noms snake_case)
- **Pipeline imports** : grep dans `argumentation_analysis/`
- **Workflows DSL** : light/standard/full + specialty workflows
- **Invoke callables** : 44 fonctions `_invoke_*` dans `invoke_callables.py`
- **State writers** : 42 fonctions `_write_*_to_state` dans `state_writers.py`

---

## Scoreboard

| Categorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) DEAD** | 11 | ~26 | 6% |
| **(b) UNWIRED** | 5 | ~34 | 8% |
| **(c) WIRED / DEROGATION** | 53 | ~348 | 85% |

---

## Recit du framework via ce packet

### Episode 1 : JVM/Tweety foundational (2025-09 a 2026-02)

Les 8 fichiers `tests/integration/jpype_tweety/` (8 tests, 1 test/file) sont les **premiers tests d'integration** ecrits pour le projet. Chacun teste une fonctionnalite Tweety specifique dans un **sous-processus JVM isole** (fixture `run_in_jvm_subprocess`) : demarrage JVM minimal, operations logiques, syntaxe d'argumentation, raisonnement avance, QBF, theorie, dialogue, stabilite JVM.

**Arc temporel** : ces tests sont anterieurs a l'architecture Lego (CapabilityRegistry/UnifiedPipeline). Ils sont le **substrat** sur lequel toute l'integration logique a ete construite. Les invoke callables pour ranking, bipolar, ABA, ADF, ASPIC, probabilistic, dialogue, DL, CL, SETAF, weighted, social, EAF, DeLP, QBF, ASP ont ete ecrits APRES, en se basant sur ces tests de validation. **Etat actuel : WIRED** — tous les handlers Tweety sont registres dans `registry_setup.py` (section `_declare_tweety_slots`) avec invoke callables et state writers.

### Episode 2 : Cluedo/Sherlock-Watson-Moriarty (2026-01 a 2026-03)

Le cluster Cluedo (6 fichiers, ~49 tests) cristallise l'evolution la plus turbulente du framework :
- `test_cluedo_orchestration_integration.py` (7 tests, 23 skip markers) — veritable integration 3-agents avec SK
- `test_cluedo_extended_workflow_recovered1.py` (13 tests, 1 skip) — recovery d'un fichier efface, 2-agent vs 3-agent
- `test_cluedo_oracle_enhanced_real.py` (9 tests, 1 skip) — oracle enhanced avec revelations automatiques
- `test_cluedo_oracle_integration.py` (17 tests, 4 skip) — oracle 100% authentique, purge mocks
- `test_cluedo_extended_workflow.py` (1 test) — comparaison 2 vs 3 agents
- `test_orchestration_agentielle_complete_reel.py` (3 tests) — integration reelle sherlock/watson

**Arc temporel** : Cluedo a ete le **premier cas d'usage concret** de l'orchestration multi-agents. L'evolution se lit dans les markers skip — de nombreux tests sont skippees (`@pytest.mark.skip(reason="requires API key")`) et servent de **guard rails** pour les executions avec credit. La v2.1.0 "Oracle Enhanced" a introduit les revelations automatiques et les metriques de performance, marquee par `_recovered1` (fichier restaure apres suppression accidentelle). **Etat actuel : WIRED** — le mode orchestration `cluedo` est le plus profondement cable du systeme (audit A-17 : 634 LOC agent + 1708 LOC OracleState + 3-agent workflow + mode dedie).

### Episode 3 : Pipeline unifie et Lego Architecture (2026-02 a 2026-04)

`test_unified_system_integration.py` (18 tests, 6 skip), `test_conversational_orchestration_integration.py` (22 tests), `test_workflow_execution.py` (3 tests), `test_capability_duality_invariant.py` (4 tests) — ces tests cristallisent la **transition majeure** vers l'architecture Lego :
- UnifiedPipeline + CapabilityRegistry + WorkflowDSL
- Orchestration conversationnelle (AgentGroupChat SK)
- Workflows declaratifs light/standard/full
- Invariant de dualite des capabilities

**Arc temporel** : cette periode voit l'emergence du CapabilityRegistry comme **source de verite** pour le wiring. `test_capability_duality_invariant.py` verifie que chaque capability a un invoke callable et un provider, capturant la regle "verify wiring by snake_case name". `test_conversational_orchestration_integration.py` est le **plus grand fichier de test integration** (22 tests, 605 LOC) et documente l'orchestration conversationnelle complete avec mock LLM. **Etat actuel : WIRED** — le pipeline unifie est l'entree canonique du systeme.

### Episode 4 : Fallacy detection evolution (2026-01 a 2026-05)

`test_fallacy_agent_workflow.py` (1 test), `test_informal_agent_tool_choice.py` (1 test), `test_enrichment_workflow.py` (15 tests), `test_tweety_fallbacks.py` (59 tests), `test_pattern_report.py` (18 tests) — cristallisent l'evolution de la detection de sophismes :
- V1 : agent informel basique
- V2 : taxonomie 1408 sophismes + FrenchFallacyPlugin + 3-tier hybrid
- V3 : hierarchical fallacy detection + enrichment workflow
- V4 : pattern mining + rapport SVG + privacy guard

**Arc temporel** : `test_tweety_fallbacks.py` (59 tests, 573 LOC) est le **plus grand fichier de test de fallback** du projet — il verifie que le pipeline fonctionne **sans JVM** (fallbacks Python purs). `test_pattern_report.py` (18 tests) valide le pipeline de mining post-analysis avec heatmaps SVG et privacy guard. `test_enrichment_workflow.py` (15 tests) verifie l'infrastructure CLI d'enrichment. **Etat actuel : WIRED** — fallacy_detection, hierarchical_fallacy_detection, per_argument_fallacy_detection sont toutes registrees.

### Episode 5 : Logic agents before factory (2026-01 a 2026-03)

`test_agents_logiques_integration.py` (14 tests, 3 skip), `test_logic_agents_integration.py` (4 tests, tous commentaires), `test_fol_pipeline_integration.py` (1 test), `test_fol_tweety_integration.py` (1 test), `test_logic_demos.py` (2 tests), `test_logic_api_integration.py` (1 test), `test_logic_puzzles_hardening.py` (1 test) — cristallisent l'evolution des agents logiques **avant** l'unification par `AgentFactory` :
- LogicProcessor (custom, pre-SK) → BaseLogicAgent → FOLLogicAgent / PropositionalLogicAgent / ModalLogicAgent
- Demo integration (Einstein, Cluedo) → pipeline formel
- JTMS integration (pre-retraction fix)

**Arc temporel** : `test_logic_agents_integration.py` est un **fossile** — tous les tests sont commentaires (4 `async def` commented out), preservant l'intention de tests de chaine logique complete qui n'ont jamais ete finalises. `test_agents_logiques_integration.py` (14 tests) teste un `LogicProcessor` qui etait l'interface pre-SK pour les agents logiques, depuis remplace par les `*LogicAgent` (SK). **Etat actuel : MIXED** — certains tests sont UNWIRED (LogicProcessor pre-SK) ou DEAD (tests commentes), mais les agents logiques modernes sont WIRED.

### Episode 6 : Infrastructure web et API (2026-02 a 2026-05)

`tests/integration/api/test_openapi_contract.py` (6 tests), `test_wsgi_compatibility.py` (1 test, 1 skip), `test_api_connectivity.py` (1 test, 1 skip), `tests/integration/argumentation_analysis/api/test_main_api.py` (2 tests), `tests/integration/webapp/` (4 fichiers, 1 test) — cristallisent l'evolution web :
- Flask → Starlette → FastAPI (audit A-14 Option 1)
- OpenAPI contract testing
- WSGI/ASGI compatibility
- Playwright integration (placeholder)
- Webapp lifecycle

**Arc temporel** : `test_wsgi_compatibility.py` (1 test skipe) est un artefact de la transition Flask→ASGI. Les 3 fichiers webapp vides (`test_playwright_integration.py`, `test_port_failover_integration.py`, `test_signal_handling.py`, 0 tests) sont des **stubs** pour des tests d'infrastructure non implementes. **Etat actuel : MIXED** — les tests API contract et main_api sont WIRED (FastAPI router actif) ; les tests WSGI et webapp vides sont DEAD/DEROGATION.

### Episode 7 : Authentic/anti-mock movement (2026-03 a 2026-04)

`test_authentic_components.py` (15 tests, 9 skip), `test_authentic_components_integration.py` (11 tests, 18 skip), `test_authenticite_finale_gpt4o.py` (2 tests), `test_trace_intelligence_reelle.py` (5 tests), `test_realite_pure_jtms.py` (6 tests) — cristallisent le **mouvement "100% authentique"** :
- Purge des mocks au profit de composants reels (GPT-4o, Tweety JAR)
- Validation de l'absence de mocks dans le pipeline
- Tests de trace intelligence (imports reels, orchestration reelle)
- "Realite pure JTMS" — validation que les composants JTMS sont authentiques

**Arc temporel** : ce mouvement est contemporain de la campagne Sprint 2 et cristallise la tension entre "tests deterministes avec mocks" et "tests reels avec API keys". Les markers `@pytest.mark.skip` et `requires_api` sont la **trace** de cette tension — les tests existent mais ne tournent que sur machines avec credits. La **convergence** (audit A-14 Option 1) a resole cette tension : le pipeline moderne utilise des **services registres** avec invoke callables et state writers, et les tests d'integration authentiques servent de **validation end-to-end** au-dessus du wiring. **Etat actuel : WIRED** — les composants testes (GPT-4o, Tweety, JTMS) sont tous cables dans le pipeline.

### Episode 8 : Workers and batch processing (2026-04 a 2026-05)

`tests/integration/workers/test_simple.py` (1 test), `tests/integration/workers/test_worker_fol_tweety.py` (16 tests, 20 skip), `test_corpus_batch_runner.py` (11 tests), `test_growth_hook_corpus_a_597.py` (2 tests), `test_add_extract.py` (11 tests) — cristallisent le **traitement batch et workers** :
- Worker FOL/Tweety (16 tests avec compatibilite reelle)
- Corpus batch runner (classification metadonnees, flattening documents)
- Growth hook corpus A (regression #597)
- Add extract (privacy guard, git tracking)

**Arc temporel** : `test_worker_fol_tweety.py` (16 tests, 20 skip markers, 780 LOC) est le **fichier de test worker le plus etoffe** — il verifie la compatibilite FOL/Tweety avec tests reels et skippees, incluant la generation de formules, la creation de belief sets programmatiques, la detection d'inconsistance, et les measures de performance FOL vs Modal. `test_corpus_batch_runner.py` cristallise l'infrastructure de traitement corpus (classification metadonnees, document flattening, regression hooks). **Etat actuel : WIRED** — FOL/Tweety est registre, corpus runner est infrastructure de production.

---

## Tableau de classification

### (a) DEAD — Source inexistante, jamais importee, ou fossile

| # | Fichier | Composant teste | Tests | Pourquoi DEAD |
|---|---------|-----------------|-------|---------------|
| 1 | `test_logic_agents_integration.py` | Tests logiques (4 `async def` commentes) | 0 | **Fossile** — tous les tests sont commentes. L'intention etait une chaine prop->FOL->modal, mais les tests n'ont jamais ete finalises. |
| 2 | `webapp/test_playwright_integration.py` | Playwright integration | 0 | **Stub vide** — aucun test, aucun contenu fonctionnel. Placeholder pour tests Playwright non implementes. |
| 3 | `webapp/test_port_failover_integration.py` | Port failover | 0 | **Stub vide** — idem. |
| 4 | `webapp/test_signal_handling.py` | Signal handling | 0 | **Stub vide** — idem. |
| 5 | `test_sprint2_improvements.py` | Sprint 2 improvements (Flask, LogicProcessor) | 11 | **Fossile Sprint 2** — teste `FlaskServiceIntegration`, `LogicProcessor` pre-SK, `AsyncManager`. Flask est remplace par FastAPI (#844). LogicProcessor est remplace par `*LogicAgent` (SK). La plupart des tests mockent des composants qui n'existent plus dans leur forme originale. |
| 6 | `test_authenticite_finale_gpt4o.py` | Validation GPT-4o "finale" | 2 | **Fossile validation** — classe sans nom (test functions dans un `if __name__`), `print()` au lieu d'assertions. Ni classe pytest, ni fixture. Non detecte par collection pytest. |
| 7 | `test_notebooks_structure.py` | Structure notebooks | 2 | **Derogation** — verifie l'existence de fichiers notebook, pas le wiring pipeline. Notebooks = artefacts pedagogiques. |
| 8 | `test_einstein_demo_real.py` | Demo Einstein reelle | 9 | **Demo pedagogique** — teste un script de demo (`einstein_demo.py`), pas le wiring pipeline. La demo est un entry point standalone, pas une capability registree. |
| 9 | `test_run_demo_epita.py` | Script validation demo | 1 | **Demo pedagogique** — verifie que le script de demo s'execute, pas le wiring pipeline. |
| 10 | `test_argument_analyzer_client.py` | Client Flask analyse | 3 | **Fossile Flask** — teste un client Flask (fixture `flask_client`). Flask est remplace par FastAPI. |
| 11 | `test_integration_quick.py` | Quick import checks | 4 | **Smoke tests triviaux** — 4 tests d'import (sherlock, watson, hub, base). Pas de logique de test, juste verification d'import. |

### (b) UNWIRED — Source existe mais pas pleinement cablee

| # | Fichier | Composant teste | Tests | Pourquoi UNWIRED |
|---|---------|-----------------|-------|-------------------|
| 1 | `test_agents_logiques_integration.py` | LogicProcessor pre-SK | 14 | `LogicProcessor` est un composant pre-SK qui ne correspond pas aux agents logiques modernes (FOLLogicAgent, PropositionalLogicAgent, ModalLogicAgent). Les 3 tests skippes testent un composant depasse. Les 11 tests non-skippees mockent heavivement. |
| 2 | `workers/test_simple.py` | Always-passes | 1 | `test_always_passes()` — assertion `True == True`. Aucun wiring teste. Placeholder worker. |
| 3 | `test_cluedo_extended_workflow.py` | Comparaison 2 vs 3 agents | 1 | Test minimal (1 test) — comparaison de workflows Cluedo. Le mode Cluedo est WIRED, mais ce test specifique est un **doublon** de `test_cluedo_extended_workflow_recovered1.py` (13 tests plus complets). |
| 4 | `test_orchestration_finale_integration.py` | OrchestrationEngine finale | 19 | `OrchestrationEngine` (teste via fixture `engine_instance`) n'est pas un composant du pipeline Lego. C'est un wrapper d'orchestration de plus haut niveau qui n'est pas registre dans CapabilityRegistry. Invoque des workflows Cluedo/agents logiques via des chemins paralleles au pipeline unifie. |
| 5 | `test_argument_analyzer.py` | Argument analyzer Playwright | 6 | **Test d'interface** — teste le frontend via Playwright (health check, malformed request, successful analysis, UI reset). Le backend teste est l'interface web Starlette, pas le pipeline Lego. La transition A-14 Option 1 (Starlette->proxy) rend ces tests partiellement perimes. |

### (c) WIRED / DEROGATION — Pipeline actif, composants cables

#### tests/integration/jpype_tweety/ — Substrat Tweety (8 fichiers, 8 tests)

| # | Fichier | Composant teste | Capability | Role | Tests |
|---|---------|-----------------|-----------|------|-------|
| 1 | `test_minimal_jvm_startup.py` | JVM startup | (infrastructure) | Validation demarrage JVM minimal | 1 |
| 2 | `test_logic_operations.py` | Tweety logic | `tweety_logic` | PL/FOL/Modal operations via Tweety | 1 |
| 3 | `test_argumentation_syntax.py` | AF syntax | `dung_extensions` | Syntaxe cadre d'argumentation Dung | 1 |
| 4 | `test_advanced_reasoning.py` | ASP reasoner | `asp_reasoning` | Consistance raisonneur ASP | 1 |
| 5 | `test_qbf.py` | QBF solver | `qbf_reasoning` | Formules quantifies | 1 |
| 6 | `test_theory_operations.py` | Theory | `belief_revision` | Operations de theorie | 1 |
| 7 | `test_dialogical_argumentation.py` | Dialogue | `dialogue_protocols` | Argumentation dialogique | 1 |
| 8 | `test_jvm_stability.py` | JVM stability | (infrastructure) | Stabilite JVM multi-operations | 1 |

**Derogation** : ces tests tournent dans un sous-processus isole (pas dans le pipeline unifie) mais valident les memes composants Tweety que le pipeline utilise via les invoke callables.

#### tests/integration/argumentation_analysis/ — Tests API et agents (5 fichiers, 12 tests)

| # | Fichier | Composant teste | Capability | Role | Tests |
|---|---------|-----------------|-----------|------|-------|
| 1 | `api/test_openapi_contract.py` | OpenAPI contract | (infrastructure) | Verifie que l'API ne casse pas le contrat | 6 |
| 2 | `api/test_main_api.py` | FastAPI main | (infrastructure) | End-to-end analysis + plugin not found | 2 |
| 3 | `agents/core/extract/test_extract_agent.py` | ExtractAgent | `fact_extraction` | Extraction depuis nom/texte | 2 |
| 4 | `agents/core/logic/test_fol_handler_config.py` | FOL handler | `fol_reasoning` | FOL query/solver dispatch | 2 |
| 5 | `test_hardening_cases.py` | API hardening | (infrastructure) | Edge cases (empty, non-arg, complex) | 3 |
| 6 | `test_jvm_example.py` | JVM example | (infrastructure) | Validation JVM active | 1 |

#### tests/integration/ — Pipeline unifie et orchestration (42 fichiers, ~318 tests)

| # | Fichier | Composant teste | Capability | Role | Tests |
|---|---------|-----------------|-----------|------|-------|
| 1 | `test_unified_system_integration.py` | UnifiedPipeline | Multi | Pipeline complet 18 tests, 6 skip | 18 |
| 2 | `test_conversational_orchestration_integration.py` | ConversationalOrchestrator | `collaborative_analysis` | Orchestration conversationnelle 22 tests | 22 |
| 3 | `test_capability_duality_invariant.py` | CapabilityRegistry | Multi | Invariant dualite capabilities | 4 |
| 4 | `test_workflow_execution.py` | WorkflowExecutor | Multi | Workflows simples + erreur | 3 |
| 5 | `test_tweety_fallbacks.py` | Fallbacks Python | Multi Tweety | 59 tests fallback sans JVM | 59 |
| 6 | `test_pattern_report.py` | PatternReport | `fallacy_detection` | Mining + rapport SVG + privacy | 18 |
| 7 | `test_enrichment_workflow.py` | Enrichment CLI | `fallacy_detection` | CLI tasks + doc + privacy | 15 |
| 8 | `test_cluedo_oracle_integration.py` | CluedoOracle | `cluedo` | Oracle 100% authentique | 17 |
| 9 | `test_cluedo_extended_workflow_recovered1.py` | CluedoExtended | `cluedo` | 2 vs 3 agents (recupere) | 13 |
| 10 | `test_cluedo_oracle_enhanced_real.py` | OracleEnhanced | `cluedo` | Oracle enhanced + revelations | 9 |
| 11 | `test_cluedo_orchestration_integration.py` | CluedoOrchestrator | `cluedo` | SK integration 3-agents | 7 |
| 12 | `test_sherlock_watson_demo_integration.py` | Demo S-W | `cluedo` | Demo Sherlock-Watson | 10 |
| 13 | `test_orchestration_agentielle_complete_reel.py` | Orchestration reelle | `cluedo` | Sher-Wat-Mori reels | 3 |
| 14 | `test_fallacy_agent_workflow.py` | FallacyAgent | `fallacy_detection` | Agent factory configs | 1 |
| 15 | `test_informal_agent_tool_choice.py` | InformalAgent | `fallacy_detection` | Forced tool choice | 1 |
| 16 | `test_corpus_batch_runner.py` | CorpusRunner | (infrastructure) | Classification + batch | 11 |
| 17 | `test_growth_hook_corpus_a_597.py` | GrowthHook | (regression #597) | Regression hook | 2 |
| 18 | `test_add_extract.py` | AddExtract | (infrastructure) | Privacy guard + git tracking | 11 |
| 19 | `workers/test_worker_fol_tweety.py` | Worker FOL/Tweety | `fol_reasoning` | Compatibilite FOL reelle | 16 |
| 20 | `test_fol_pipeline_integration.py` | FOL pipeline | `fol_reasoning` | FOL en sous-processus | 1 |
| 21 | `test_fol_tweety_integration.py` | FOL Tweety | `fol_reasoning` | Integration FOL/Tweety | 1 |
| 22 | `test_jtms_imports.py` | JTMS imports | `jtms_reasoning` | Import validation axe B | 1 |
| 23 | `test_realite_pure_jtms.py` | JTMS reel | `jtms_reasoning` | 6 tests sans mocks | 6 |
| 24 | `test_trace_intelligence_reelle.py` | Trace reelle | Multi | Imports + orchestration reelle | 5 |
| 25 | `test_authentic_components.py` | Authenticite | Multi | 15 tests (9 skip) | 15 |
| 26 | `test_authentic_components_integration.py` | Authentic integration | Multi | 11 tests (18 skip) | 11 |
| 27 | `test_dung_agent.py` | Dung agent | `dung_extensions` | Self-attacking argument | 1 |
| 28 | `test_agent_family.py` | Agent family | Multi | Agent performance (parametrise) | 2 |
| 29 | `test_agents_tools_integration.py` | Agents + tools | Multi | Fallacy + analysis workflow | 4 |
| 30 | `test_einstein_tweetyproject_integration.py` | Einstein Tweety | `propositional_reasoning` | Integration Einstein/Tweety | 1 |
| 31 | `test_logic_demos.py` | Logic demos | `propositional_reasoning` | Demos Einstein + Cluedo | 2 |
| 32 | `test_logic_puzzles_hardening.py` | Logic puzzles | `propositional_reasoning` | Hardening scenarios | 1 |
| 33 | `test_logic_api_integration.py` | Logic API | `propositional_reasoning` | API integration sous-processus | 1 |
| 34 | `test_oracle_integration.py` | Oracle Tweety | `propositional_reasoning` | Oracle integration sous-processus | 1 |
| 35 | `test_minimal_jvm_startup.py` | JVM startup | (infrastructure) | Demarrage JVM minimal (racine) | 1 |
| 36 | `test_wsgi_compatibility.py` | WSGI/ASGI | (infrastructure) | Compatibilite WSGI | 1 |
| 37 | `test_api_connectivity.py` | API connectivity | (infrastructure) | Connectivite API (skipe) | 1 |
| 38 | `webapp/test_full_webapp_lifecycle.py` | Webapp lifecycle | (infrastructure) | Backend lifecycle | 1 |
| 39 | `services/test_mcp_server_integration.py` | MCP server | (infrastructure) | Import MCP client/session | 5 |
| 40 | `logical_agents/test_logic_puzzles.py` | Logic puzzles | `propositional_reasoning` | Puzzle solving | 2 |
| 41 | `logical_agents/test_logic_puzzles_hardening.py` | Puzzles hardening | `propositional_reasoning` | Hardening scenarios | 2 |
| 42 | `test_unified_investigation.py` | (vide) | — | Pas de tests | 0 |

---

## Capabilities muettes (signal de zone fragile)

Les capabilities suivantes sont registrees dans `registry_setup.py` mais **non couvertes** (ou peu couvertes) par les tests d'integration de ce packet :

| Capability | Registree dans | Tests integration dans ce packet | Couverture |
|-----------|-----------------|----------------------------------|------------|
| `counter_argument_generation` | agent `counter_argument_agent` | 0 | **MUETTE** — aucun test integration ne teste la generation de contre-arguments end-to-end |
| `adversarial_debate` | agent `debate_agent` | 0 | **MUETTE** — debat adversarial non teste en integration |
| `governance_simulation` | agent `governance_agent` | 0 | **MUETTE** — simulation de gouvernance non testee |
| `ranking_semantics` | handler `ranking_semantics_handler` | Couvert par `test_tweety_fallbacks.py` (fallback) | **Partielle** — fallback Python teste, raisonnement reel non teste |
| `bipolar_argumentation` | handler `bipolar_handler` | idem | **Partielle** |
| `aba_reasoning` | handler `aba_handler` | idem | **Partielle** |
| `adf_reasoning` | handler `adf_handler` | idem | **Partielle** |
| `aspic_plus_reasoning` | handler `aspic_handler` | idem | **Partielle** |
| `belief_revision` | handler `belief_revision_handler` | idem | **Partielle** |
| `probabilistic_argumentation` | handler `probabilistic_handler` | idem | **Partielle** |
| `description_logic` | handler `dl_handler` | idem | **Partielle** |
| `conditional_logic` | handler `cl_handler` | idem | **Partielle** |
| `setaf_reasoning` | handler `setaf_handler` | idem | **Partielle** |
| `weighted_argumentation` | handler `weighted_handler` | idem | **Partielle** |
| `social_argumentation` | handler `social_handler` | idem | **Partielle** |
| `epistemic_argumentation` | handler `eaf_handler` | idem | **Partielle** |
| `defeasible_logic` | handler `delp_handler` | idem | **Partielle** |
| `deep_synthesis` | service `deep_synthesis_service` | 0 | **MUETTE** — synthese profonde non testee en integration |
| `stakes_extraction` | service `stakes_extractor_service` | 0 | **MUETTE** — extraction enjeux non testee en integration |
| `speech_transcription` | service `speech_transcription_service` | 0 | **MUETTE** — transcription non testee (invoke = stub mort, audit A-16) |
| `local_llm` | service `local_llm_service` | 0 | **MUETTE** — LLM local non teste en integration |
| `narrative_synthesis` | service `narrative_synthesis_service` | 0 | **MUETTE** — synthese narrative non testee |
| `analysis_synthesis` | service `analysis_synthesis_service` | 0 | **MUETTE** — synthese analytique non testee |
| `collaborative_analysis` | service `collaborative_debate_service` | Couvert par `test_conversational_orchestration_integration.py` | **OK** |
| `nl_to_logic_translation` | service `nl_to_logic_service` | 0 | **MUETTE** — NL->logique non teste en integration |

**Bilan** : sur ~40 capabilities registrees, **15 sont muettes** en integration (0 test), **15 sont partielles** (fallbacks seulement), **10 sont couvertes** (WIRED avec tests reels ou mocks). Les 3 capabilities agent les plus critiques sans couverture integration sont `counter_argument_generation`, `adversarial_debate`, et `governance_simulation` — toutes les trois sont des agents complets avec invoke callables et state writers mais sans validation end-to-end.

---

## Narratif global

### Sante globale — 85% justifie

Le ratio 85% WIRED/Derogation est bon pour des tests d'integration — ces tests valident des chaines end-to-end qui par nature touchent des composants cables. Les 6% DEAD sont principalement des artefacts historiques (stubs vides, fossiles Sprint 2, tests Flask perimes). Les 8% UNWIRED sont des composants qui existent en dehors du pipeline Lego strict (LogicProcessor pre-SK, OrchestrationEngine wrapper).

### Points d'attention

1. **`test_sprint2_improvements.py`** (11 tests) : fossile du Sprint 2. Teste `FlaskServiceIntegration` (Flask->FastAPI deja fait via #844), `LogicProcessor` (remplace par `*LogicAgent` SK), `AsyncManager`. La plupart des tests mockent des composants depasses. **Candidat a l'archivage.**

2. **`test_authenticite_finale_gpt4o.py`** (2 tests) : classe sans nom, `print()` au lieu d'assertions, non-collecte par pytest. **Pas un vrai test** — script de validation manuelle.

3. **`test_logic_agents_integration.py`** (0 tests actifs) : 4 `async def` commentes. Fossile pur. **Candidat a la suppression.**

4. **3 stubs webapp vides** (`test_playwright_integration.py`, `test_port_failover_integration.py`, `test_signal_handling.py`) : 0 tests, 0 LOC fonctionnel. **Candidats a la suppression.**

5. **`test_argument_analyzer_client.py`** (3 tests) : client Flask. La transition A-14 (Starlette->proxy) et le router FastAPI rendent ce test perime. **Candidat a la reecriture pour FastAPI/TestClient.**

6. **`test_orchestration_finale_integration.py`** (19 tests, 9 skip) : teste `OrchestrationEngine` qui n'est pas registre dans CapabilityRegistry. C'est un wrapper de plus haut niveau — les invoke callables qu'il utilise sont cables, mais l'orchestrateur lui-meme est un chemin parallele. **A surveiller** — si `OrchestrationEngine` est amene a etre l'entree canonique, il devrait etre registre.

7. **Capabilities muettes critiques** : `counter_argument_generation`, `adversarial_debate`, `governance_simulation` ont des tests unitaires robustes (audit B-12) mais **aucun test d'integration end-to-end**. Le gap est significatif car ces agents interagissent avec le LLM et le pipeline de maniere complexe.

### Fix-intents proposes

| # | Issue proposee | Priorite | Action |
|---|----------------|----------|--------|
| F1 | `fix(b-13): remove dead integration test stubs and fossils` | **LOW** | Supprimer 5 fichiers morts (3 stubs webapp + `test_logic_agents_integration.py` fossile + `test_authenticite_finale_gpt4o.py` non-pytest). Pas de perte de couverture. |
| F2 | `fix(b-13): rewrite test_argument_analyzer_client for FastAPI` | **MEDIUM** | Recrire les 3 tests Flask pour FastAPI TestClient (post A-14 Option 1). |
| F3 | `fix(b-13): add integration tests for 3 mute agent capabilities` | **MEDIUM** | Ajouter des tests d'integration pour `counter_argument_generation`, `adversarial_debate`, `governance_simulation` avec mock LLM (patron `test_conversational_orchestration_integration.py`). |

### A valider par l'utilisateur

- RAS — audit read-only, pas de modification de code. Les 3 fix-intents sont des propositions d'enrichissement du consolide.
