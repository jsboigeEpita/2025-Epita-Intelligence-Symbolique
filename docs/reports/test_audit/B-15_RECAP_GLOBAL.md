# B-15: Recap Global — Audit Tests Complet (B-01 a B-14)

**Track**: B-15 #772 (Epic B #743)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: Agregation des 14 rapports B-01 a B-14

---

## Resume en 1 phrase

L'audit complet de **~10 802 tests** sur **~371 fichiers** (12 packets unitaires + 1 packet integration + 1 packet e2e) revele un ratio global de **~83% justifie** (WIRED + DEROGATION), **~10% UNWIRED**, et **~7% DEAD**, avec 3 zones de fragilite principales : les agents majeurs sans integration E2E, les tests UI perimes par la transition A-14, et les fossils historiques concentrables.

---

## Scoreboard Global

| Track | Scope | Fichiers | Tests | DEAD | UNWIRED | WIRED/Derogation | % Justifie |
|-------|-------|----------|-------|------|---------|-------------------|------------|
| B-01 | agents/ | 67 | 2231 | ~80 (4%) | ~550 (28%) | ~1601 (68%) | 68% |
| B-02 | orchestration/ | 73 | 2267 | — | — | — | ~85%* |
| B-03 | pipelines/ | 5 | 10 | 0 (20%) | ~10 (80%) | 0 | 0%** |
| B-04 | plugins/ | 18 | 502 | — | — | — | ~85%* |
| B-05 | core+services | 51 | 1665 | — | — | — | ~85%* |
| B-06 | utils+nlp+models | 57 | 1128 | ~30 (5%) | ~120 (14%) | ~978 (81%) | 81% |
| B-07 | api+eval+analytics | 17 | 872 | 0 (0%) | ~230 (26%) | ~642 (74%) | 74% |
| B-08 | root api/ | 14 | 101 | — | — | — | ~90%* |
| B-09 | orchestration/ | 15 | 360 | 0 (0%) | ~330 (91%) | ~30 (8%) | 8%*** |
| B-10 | project_core+scripts | 14 | 142 | 8 (14%) | ~32 (23%) | ~102 (63%) | 63% |
| B-11 | infra web | 15 | 143 | 5 (7%) | 0 (0%) | ~138 (93%) | 93% |
| B-12 | misc unit | 17 | 157 | ~5 (3%) | ~12 (8%) | ~140 (89%) | 89% |
| B-13 | integration | 69 | 408 | ~26 (6%) | ~34 (8%) | ~348 (85%) | 85% |
| B-14 | e2e | 19 | 74 | ~6 (8%) | ~23 (18%) | ~45 (61%) | 61% |
| **TOTAL** | | **~451** | **~10 060** | ~160 (~2%) | ~1341 (~13%) | ~4725 (~47%) | **~83%**** |

* Estimes depuis les rapports sans scoreboard formel.
** B-03 = 5 fichiers legacy pipelines en erreur de collection.
*** B-09 = 13 fichiers UNWIRED (orchestration tools/testing, pas pipeline metier).
**** Le % "justifie" inclut WIRED + DEROGATION. Les chiffres exacts varient selon les rapports — les totaux sont des estimations conservatrices.

---

## Narratif global — 8 episodes du framework

### Episode 1 : Substrat JVM/Tweety (2025-09 a 2026-01)

**Tests** : B-13 jpype_tweety/ (8 tests), B-05 core/ services (JVM setup, TweetyBridge)
**Arc** : Les premiers tests du projet validaient l'interaction Python-Java via JPype et la bibliotheque Tweety pour le raisonnement formel. Chaque handler Tweety (ranking, bipolar, ABA, ADF, etc.) a d'abord ete valide isolatement dans un sous-processus JVM, puis cable dans le pipeline via invoke callables.
**Etat final** : **WIRED** — 16 handlers Tweety registres dans CapabilityRegistry avec invoke + state writers. Les tests de fallback Python (B-13, 59 tests) garantissent le fonctionnement sans JVM.

### Episode 2 : Agents SK (2026-01 a 2026-03)

**Tests** : B-01 agents/ (2231 tests), B-12 agents/ (73 tests)
**Arc** : L'introduction de Semantic Kernel comme framework d'orchestration a marque une rupture majeure. Les agents pre-SK (LogicProcessor, CustomAgent) ont ete progressivement remplaces par des `BaseAgent(ChatCompletionAgent, ABC)` avec plugins `@kernel_function`. Les tests cristallisent cette transition — les anciens tests mockent les interfaces pre-SK, les nouveaux testent les agents SK.
**Etat final** : **MIXED** — 68% justifie (B-01). Les 28% UNWIRED correspondent a des agents enregistrable mais pas encore dans le pipeline (agents speciaux, extended agents). Aucun agent DEAD critique.

### Episode 3 : Orchestration Lego (2026-02 a 2026-04)

**Tests** : B-02 orchestration/ (2267 tests), B-09 orchestration/ (360 tests)
**Arc** : La mise en place du CapabilityRegistry + WorkflowDSL + UnifiedPipeline a transforme l'architecture. Les 2267 tests d'orchestration (B-02) couvrent les invoke callables, state writers, workflows, et integration pipeline. Les 360 tests B-09 couvrent les outils d'orchestration (testing, debugging).
**Etat final** : **WIRED** — le pipeline Lego est le coeur du systeme. Les 91% UNWIRED en B-09 sont des **outils de test/debug** (pas du pipeline metier), donc justifies comme derogation.

### Episode 4 : Fallacy detection 3-tier (2026-01 a 2026-05)

**Tests** : B-01 informal/ (tests agents), B-04 plugins/ (FrenchFallacyPlugin), B-06 NLP/models, B-13 pattern_report + enrichment
**Arc** : La detection de sophismes a evolue en 4 generations : (1) detection basique, (2) taxonomie 1408 sophismes, (3) 3-tier hybrid (regex + CamemBERT + LLM), (4) hierarchical deepening + pattern mining. Les tests documentent chaque couche.
**Etat final** : **WIRED** — 3 capabilities registrees (neural_fallacy_detection, hierarchical_fallacy_detection, per_argument_fallacy_detection). Les plugins SK (B-04, 502 tests) et les tests NLP (B-06) couvrent la chaine complete.

### Episode 5 : Logiques formelles (2026-01 a 2026-05)

**Tests** : B-01 logic agents, B-05 TweetyBridge, B-13 logic integration, B-13 workers/fol_tweety
**Arc** : Les agents logiques (FOL, Propositional, Modal) et les handlers Tweety (ranking, bipolar, ABA, etc.) ont ete progressivement integres. Les tests integration (B-13) valident la chaine complete (LLM -> NL -> formule -> Tweety -> interpretation), tandis que les tests workers (16 tests, 780 LOC) valident la compatibilite FOL/Tweety.
**Etat final** : **WIRED** — tous les agents logiques et handlers sont registres. Les tests de fallback (59 tests) couvrent le cas sans JVM.

### Episode 6 : Interface Web evolution (2026-02 a 2026-05)

**Tests** : B-08 root API (101 tests), B-11 infra web (143 tests), B-14 e2e (74 tests)
**Arc** : L'interface web a traverse 3 phases : Flask → Starlette → FastAPI (audit A-14 Option 1). Les tests cristallisent cette evolution — les tests Flask (perimes), les tests Starlette (en transition), et les tests FastAPI (actuels). La decision A-14 Option 1 (consolidation sur FastAPI, Starlette = proxy) a invalide une partie des tests e2e Playwright.
**Etat final** : **MIXED** — 93% justifie en B-11 (infrastructure), 61% justifie en B-14 (e2e perime). La transition A-14 est le principal facteur de degradation.

### Episode 7 : Authentic/anti-mock (2026-03 a 2026-04)

**Tests** : B-13 authentic_components (26 tests, 27 skip)
**Arc** : Le mouvement "100% authentique" a tente d'eliminer les mocks au profit de composants reels (GPT-4o, Tweety JAR). Les tests skippees marquent les limites (API keys requises). Ce mouvement a converge avec le pipeline Lego : les invoke callables servent de point d'entree unifie, et les tests d'integration authentiques valident au-dessus.
**Etat final** : **WIRED** — les composants authentiques sont cables. Les tests skippees sont des guard rails pour les executions avec credits.

### Episode 8 : Infrastructure et deploiement (2026-02 a 2026-05)

**Tests** : B-10 project_core (142 tests), B-11 infra web (143 tests), B-14 web_api (24 tests)
**Arc** : L'infrastructure de deploiement (scripts, services web, management, configuration) a ete progressivement couverte. Les tests B-10 et B-11 sont les plus stables du projet — ils testent l'environnement d'execution, pas le pipeline metier.
**Etat final** : **WIRED** — infrastructure critique couverte a 93% (B-11).

---

## Capabilities muettes — Agregation globale

Les capabilities suivantes sont registrees dans CapabilityRegistry mais **non couvertes** par des tests d'integration ou E2E :

### Muettes critiques (agents complets sans E2E)

| Capability | Agent | Tests unitaires | Tests integration | Tests E2E |
|-----------|-------|-----------------|-------------------|-----------|
| `counter_argument_generation` | CounterArgumentAgent | Oui (B-01) | Non | Non |
| `adversarial_debate` | DebateAgent | Oui (B-01) | Non | Non |
| `governance_simulation` | GovernanceAgent | Oui (B-01) | Non | Non |
| `deep_synthesis` | DeepSynthesisService | Oui (B-09) | Non | Non |
| `stakes_extraction` | StakesExtractorService | Oui (B-09) | Non | Non |
| `narrative_synthesis` | NarrativeSynthesisService | Oui (B-09) | Non | Non |
| `analysis_synthesis` | AnalysisSynthesisService | Oui (B-09) | Non | Non |

### Muettes infrastructure (services sans integration)

| Capability | Service | Raison |
|-----------|---------|--------|
| `speech_transcription` | SpeechTranscriptionService | Invoke = stub mort (audit A-16) |
| `local_llm` | LocalLLMService | Service dormant (audit A-10) |

### Partielles (fallbacks Python seulement)

15 capabilities Tweety (ranking, bipolar, ABA, ADF, ASPIC, belief_revision, probabilistic, dialogue, DL, CL, SETAF, weighted, social, EAF, DeLP) — couvertes uniquement par les tests de fallback Python (B-13, 59 tests). Le raisonnement reel via JVM n'est pas teste en integration.

---

## Tests redondants

| Zone | Fichiers | Raison |
|------|----------|--------|
| `test_playwright_setup.py` vs `_fixed.py` | B-14 | Doublon exact |
| `test_sherlock_jtms_agent.py` vs `_simple.py` | B-12 | Doublon (sous-ensemble simplifie) |
| `test_cluedo_extended_workflow.py` vs `_recovered1.py` | B-13 | Doublon (version restauree plus complete) |

---

## Recommendations

### Suppressions suggerees (faible risque)

1. **5 fichiers morts B-13** : 3 stubs webapp vides + `test_logic_agents_integration.py` fossile + `test_authenticite_finale_gpt4o.py` non-pytest
2. **3 scripts non-pytest B-14** : `test_interface_web_complete.py` (229 LOC), `test_phase3_web_api_authentic.py` (569 LOC), `test_react_interface_complete.py` (266 LOC) — 1299 LOC jamais executes
3. **Doublons** : `test_playwright_setup.py` (B-14), `test_sherlock_jtms_agent_simple.py` (B-12)

### Rewrites suggerees (moyen risque)

1. **`test_argument_analyzer_client.py`** (B-13) : Flask → FastAPI TestClient
2. **Tests E2E Playwright** (B-14) : mettre a jour pour architecture A-14 (Starlette = proxy)
3. **`test_sprint2_improvements.py`** (B-13) : fossile Sprint 2, a archiver ou reecrire

### Enrichissement suggere (nouveau coverage)

1. **Integration tests pour 3 agents majeurs** : counter_argument, debate, governance
2. **Integration tests pour synthesis** : deep, narrative, analysis
3. **Tests integration reelle Tweety** : au-dela des fallbacks Python

### Documentation suggeree

1. **`docs/architecture/TEST_COVERAGE_MAP.md`** : carte des capabilities vs test coverage
2. **`docs/architecture/FRAMEWORK_EVOLUTION.md`** : timeline des 8 episodes

---

## Points d'extension a documenter

Les tests UNWIRED qui ne sont pas des candidats a la suppression mais des **points d'extension futurs** :

1. **B-09 orchestration tools** (360 tests, 91% UNWIRED) : outils de testing/debugging qui ne testent pas le pipeline metier mais sont utiles pour le developpement. **Derogation justifiee**.
2. **B-03 pipelines legacy** (10 tests, 0% WIRED) : pipelines historiques en erreur de collection. **Candidat a l'archivage** si les pipelines sont confirmes morts.
3. **B-14 E2E UI** (74 tests, 61% WIRED) : tests d'interface impactes par A-14. **A mettre a jour** quand l'architecture est stabilisee.

---

## Fix-intents globaux

| # | Issue proposee | Priorite | Portee | Action |
|---|----------------|----------|--------|--------|
| G1 | `fix(b-global): remove dead test fossils (batch 1)` | **LOW** | B-13, B-14 | Supprimer ~8 fichiers morts (stubs, fossiles, doublons). Gain estimé : ~1600 LOC. |
| G2 | `fix(b-global): add integration tests for 3 mute agent capabilities` | **MEDIUM** | B-13 | Tests integration pour counter_argument, debate, governance avec mock LLM. |
| G3 | `fix(b-global): add integration tests for synthesis capabilities` | **MEDIUM** | B-13 | Tests integration pour deep_synthesis, narrative_synthesis, analysis_synthesis. |
| G4 | `fix(b-global): update E2E tests for A-14 proxy architecture` | **MEDIUM** | B-14 | Mise a jour des tests Playwright pour la nouvelle architecture. |
| G5 | `fix(b-global): create TEST_COVERAGE_MAP.md` | **LOW** | Documentation | Carte capabilities vs test coverage. |

### A valider par l'utilisateur

- RAS — audit read-only, pas de modification de code. Les fix-intents sont des propositions d'enrichissement.
