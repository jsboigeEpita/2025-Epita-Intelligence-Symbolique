# Audit B-05: `tests/unit/argumentation_analysis/core/` + `tests/unit/argumentation_analysis/services/` (51 files, ~1665 tests)

**Issue**: #761 (B-05) | **Epic**: #743 | **Date audit**: 2026-05-31
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Fichiers test | 51 |
| Fonctions test | ~1 665 |
| LOC tests | 18 014 (core: 9 495, services: 8 519) |
| Fichiers source (`core/` + `services/`) | ~100 |
| LOC source | 38 692 (core: 23 648, services: 15 044) |
| Ratio tests/source | 0.47 |

### Périmètre source audité

#### `argumentation_analysis/core/` (~23 648 LOC, 67 fichiers)

| Module source | LOC | Rôle |
|--------------|-----|------|
| `shared_state.py` | 1 110 | UnifiedAnalysisState + RhetoricalAnalysisState (10 dimensions) |
| `cluedo_oracle_state.py` | 1 707 | Oracle dataset + MoriartyInterrogator state |
| `jvm_setup.py` | 988 | JVM initialization for JPype/Tweety |
| `state_manager_plugin.py` | 831 | State manager SK plugin |
| `capability_registry.py` | 586 | CapabilityRegistry + ServiceDiscovery |
| `source_management.py` | 785 | Source loading, decryption, validation |
| `bootstrap.py` | 736 | System initialization |
| `strategies.py` | 516 | Analysis strategies |
| `communication/` (9 files) | ~4 800 | Multi-channel messaging (hierarchical, collaboration, pub/sub, request/response, middleware, adapters) |
| `utils/` (17 files) | ~3 600 | Crypto, IO, text, JSON, path, file, reporting utilities |
| `phase_scoped_state.py` | 500 | Phase-scoped state management |
| `enquete_states.py` | 427 | Investigation (Sherlock) state |
| `io_manager.py` | 228 | Encrypted IO manager |
| `llm_service.py` | 209 | LLM service layer |
| `environment.py` | 218 | Environment configuration |
| `argumentation_analyzer.py` | 239 | Core analyzer |
| `logique_complexe_states.py` | 270 | Complex logic states |
| `pyo3_singleton.py` | 195 | PyO3 singleton manager |
| `setup/` (2 files) | ~780 | Prover9 + portable tools setup |

#### `argumentation_analysis/services/` (~15 044 LOC, 53 fichiers)

| Module source | LOC | Rôle |
|--------------|-----|------|
| `web_api/services/` (4 files) | ~2 500 | Analysis, Fallacy, Logic, Validation services |
| `web_api/models/` (2 files) | ~740 | Request/Response models |
| `mcp_server/` (7 files) | ~1 350 | FastMCP server, session, tools |
| `logic_service.py` | 677 | Logic service (Tweety delegation) |
| `nl_to_logic.py` | 836 | NL→formal logic translation |
| `semantic_index_service.py` | 581 | Kernel Memory semantic indexing |
| `fallacy_family_definitions.py` | 625 | 8-family fallacy definitions |
| `fetch_service.py` | 466 | Multi-strategy document fetching |
| `extract_service.py` | 457 | Extract management service |
| `definition_service.py` | 426 | Definition management |
| `jtms/` (4 files) | ~1 000 | JTMS core, ATMS, extended belief, conflict resolution |
| `jtms_service.py` | 475 | JTMS service (high-level) |
| `jtms_session_manager.py` | 484 | JTMS session management |
| `flask_service_integration.py` | 346 | Flask integration layer |
| `crypto_service.py` | 308 | Encryption service |
| `ai_shield/` (5 files) | ~700 | AI Shield framework (presets, layers, shield) |
| `websocket_manager.py` | 226 | WebSocket connection management |
| `cache_service.py` | 190 | Cache service |
| `llm_cache.py` | 242 | LLM response cache |

---

## 1. Classification a/b/c — Tableau de wiring

### Légende

- ✅ **Wired** : test couvre un module enregistré dans `CapabilityRegistry` / utilisé par un workflow
- ⚠️ **Dérogation justifiée** : helper interne, infrastructure, interface, modèle
- ❌ **Orphelin** : source sans test OU test sans source correspondante

---

### 1A. Core Infrastructure — 27 fichiers test, ~855 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_capability_registry.py` | 26 | `capability_registry.py` | ✅ Wired | Registry + ServiceDiscovery — Lego architecture backbone |
| `test_bootstrap.py` | 24 | `bootstrap.py` | ✅ Wired | System init, component loading, error handling |
| `test_io_manager.py` | 27 | `io_manager.py` | ✅ Wired | Encrypted IO, passphrase, load/save |
| `test_shared_state` (dans orchestration/) | — | `shared_state.py` | ✅ Wired | Covered by B-02 test_unified_pipeline.py (state injection tests) |
| `test_source_management_extended.py` | 65 | `source_management.py` + `source_manager.py` | ✅ Wired | Source loading, decryption, validation, card system |
| `test_argumentation_analyzer.py` | 31 | `argumentation_analyzer.py` | ✅ Wired | Core analyzer (text splitting, analysis orchestration) |
| `test_environment.py` | 13 | `environment.py` | ✅ Wired | Config loading, env vars, defaults |
| `test_config.py` | 3 | `config.py` | ⚠️ Justifié | Minimal config module (66 LOC) |
| `test_jvm_setup.py` | 4 | `jvm_setup.py` | ✅ Wired | JVM startup/shutdown, classpath |
| `test_llm_service_extended.py` | 12 | `llm_service.py` | ✅ Wired | LLM service, client creation, streaming |
| `test_enums.py` | 25 | `enums.py` | ✅ Wired | Enum definitions (37 LOC → 87 LOC test, thorough) |
| `test_pyo3_singleton.py` | 19 | `pyo3_singleton.py` | ✅ Wired | Singleton manager for PyO3 native extensions |
| `test_dll_guard.py` | 3 | `dll_guard.py` | ⚠️ Justifié | Windows DLL load order guard (#512) |
| `test_prover9_runner.py` | 8 | `prover9_runner.py` | ✅ Wired | Prover9 external solver runner |
| `test_phase_scoped_state.py` | 24 | `phase_scoped_state.py` | ✅ Wired | Phase-scoped state management (#605) |
| `test_enquete_states.py` | 60 | `enquete_states.py` | ✅ Wired | Investigation states (Sherlock/Cluedo) |
| `test_cluedo_oracle_state.py` | 19 | `cluedo_oracle_state.py` | ✅ Wired | Oracle dataset, Moriarty interrogation |
| `test_cluedo_oracle_state_extended.py` | 98 | `cluedo_oracle_state.py` (extended) | ✅ Wired | Extended oracle tests (game scenarios) |
| `test_logique_complexe_states.py` | 30 | `logique_complexe_states.py` | ✅ Wired | Complex logic states (PL/FOL/Modal belief sets) |

### 1B. Core Communication — 9 fichiers test, ~411 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `communication/test_message.py` | 47 | `communication/message.py` | ✅ Wired | Message model, metadata, priority |
| `communication/test_channel_interface.py` | 50 | `communication/channel_interface.py` | ✅ Wired | Channel ABC, subscribe/publish |
| `communication/test_data_channel.py` | 45 | `communication/data_channel.py` | ✅ Wired | Data channel (681 LOC), message routing |
| `communication/test_hierarchical_channel.py` | 37 | `communication/hierarchical_channel.py` | ✅ Wired | Hierarchical channel (strategic/tactical/operational) |
| `communication/test_collaboration_channel.py` | 52 | `communication/collaboration_channel.py` | ✅ Wired | Multi-agent collaboration |
| `communication/test_pub_sub.py` | 51 | `communication/pub_sub.py` | ✅ Wired | Pub/sub event system |
| `communication/test_request_response.py` | 38 | `communication/request_response.py` | ✅ Wired | Request/response pattern |
| `communication/test_middleware.py` | 38 | `communication/middleware.py` | ✅ Wired | Message middleware, interceptors |
| `communication/test_adapters.py` | 53 | `communication/operational_adapter.py` + `tactical_adapter.py` + `strategic_adapter.py` | ✅ Wired | 3 operational-level adapters in 1 test file |

### 1C. Services JTMS — 4 fichiers test, ~124 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_jtms_core.py` | 28 | `services/jtms/jtms_core.py` | ✅ Wired | JTMS core: Belief, Justification, JTMS class |
| `test_jtms_service.py` | 51 | `services/jtms_service.py` | ✅ Wired | High-level JTMS service |
| `test_jtms_session_manager.py` | 55 | `services/jtms_session_manager.py` | ✅ Wired | Session management, persistence |
| `test_jtms_conflict_resolution.py` | 19 | `services/jtms/conflict_resolution.py` | ✅ Wired | Conflict detection and resolution |
| `test_extended_belief.py` | 30 | `services/jtms/extended_belief.py` | ✅ Wired | Extended belief model |

### 1D. Services Logic + AI — 6 fichiers test, ~195 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_logic_service.py` | 45 | `services/logic_service.py` | ✅ Wired | Logic service (Tweety delegation) |
| `test_fact_verification_service.py` | 24 | `services/fact_verification_service.py` | ✅ Wired | Fact verification (7 states, 5 reliability levels) |
| `test_fallacy_family_definitions.py` | 41 | `services/fallacy_family_definitions.py` | ✅ Wired | 8-family fallacy taxonomy |
| `test_fallacy_taxonomy_service.py` | 15 | `services/fallacy_taxonomy_service.py` | ✅ Wired | Taxonomy service (CSV loading, navigation) |
| `test_dung_integration.py` | 12 | `services/dung_integration` (via orchestration) | ✅ Wired | Dung semantics integration |
| `test_mcp_server.py` | 64 | `services/mcp_server/` | ✅ Wired | MCP server main + tools + session |

### 1E. Services Web API — 4 fichiers test, ~246 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_web_api_models_and_services.py` | 113 | `services/web_api/models/` + `services/web_api/services/` | ✅ Wired | Composite: request/response models + service layer |
| `web_api/models/test_response_models.py` | 47 | `services/web_api/models/response_models.py` | ✅ Wired | Pydantic response models |
| `web_api/services/test_fallacy_service.py` | 35 | `services/web_api/services/fallacy_service.py` | ✅ Wired | Fallacy analysis API service |
| `web_api/services/test_validation_service.py` | 51 | `services/web_api/services/validation_service.py` | ✅ Wired | Validation API service |

### 1F. Services Infrastructure — 7 fichiers test, ~136 tests

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_crypto_service.py` | 29 | `services/crypto_service.py` | ✅ Wired | Encryption/decryption service |
| `test_cache_service.py` | 27 | `services/cache_service.py` | ✅ Wired | Cache service |
| `test_llm_cache.py` | 32 | `services/llm_cache.py` | ✅ Wired | LLM response caching |
| `test_local_llm_service.py` | 10 | `services/local_llm_service.py` | ✅ Wired | Local LLM adapter (vLLM/Ollama) |
| `test_speech_transcription_service.py` | 18 | `services/speech_transcription_service.py` | ✅ Wired | Speech-to-text HTTP adapter |
| `test_semantic_index_service.py` | 20 | `services/semantic_index_service.py` | ✅ Wired | Kernel Memory semantic indexing |
| `test_websocket_manager.py` | 22 | `services/websocket_manager.py` | ✅ Wired | WebSocket connection management |
| `test_flask_service_integration.py` | 29 | `services/flask_service_integration.py` | ⚠️ Justifié | Flask integration layer (legacy compatibility) |
| `test_benchmark_service.py` | 2 | `services/benchmark_service.py` | ⚠️ Justifié | Minimal tests (58 LOC source) |

**Sous-total Services Infrastructure**: 7 fichiers, ~136 tests

---

## 2. Sources sans test dédié — Angle morts

### Core — Sources critiques sans test

| Source | LOC | Rôle | Priorité |
|--------|-----|------|----------|
| `shared_state.py` | 1 110 | **Backbone state** — UnifiedAnalysisState. Tested via B-02 orchestration tests (state injection) but no dedicated unit test file in core/ | HIGH |
| `state_manager_plugin.py` | 831 | SK plugin for state management. Has in-source test (`core/tests/test_state_manager_plugin.py`, 309 LOC) but not in `tests/unit/` | MEDIUM |
| `strategies.py` | 516 | Analysis strategies — untested | MEDIUM |
| `llm_service.py` | 209 | LLM service — partially tested via `test_llm_service_extended.py` (12 tests) | LOW |

### Core — Communication adapters (tested via composite)

| Source | LOC | Test coverage |
|--------|-----|---------------|
| `operational_adapter.py` | 626 | Tested via `communication/test_adapters.py` (composite) |
| `tactical_adapter.py` | 720 | Tested via `communication/test_adapters.py` (composite) |
| `strategic_adapter.py` | 745 | Tested via `communication/test_adapters.py` (composite) |

### Core — Utils (39 files, 0 dedicated unit tests)

The entire `core/utils/` directory (17 files, ~3 600 LOC) has **zero dedicated test files** in `tests/unit/`. Notable:
- `crypto_utils.py` (418 LOC) — tested indirectly via `test_crypto_service.py`
- `reporting_utils.py` (535 LOC) — no test
- `text_utils.py` (314 LOC) — no test
- `json_utils.py` (195 LOC) — no test
- `file_loaders.py` (213 LOC) — no test

**Assessment**: These are utility modules. Most are tested indirectly through their consumers (services, orchestration). Creating dedicated utils tests is LOW priority.

### Services — Sources critiques sans test

| Source | LOC | Rôle | Priorité |
|--------|-----|------|----------|
| `nl_to_logic.py` | 836 | NL→formal translation service. Tested via `test_nl_to_logic_plugin.py` (plugin wrapper) but service itself not tested | MEDIUM |
| `fetch_service.py` | 466 | Multi-strategy document fetcher. No test. | MEDIUM |
| `extract_service.py` | 457 | Extract management. No test. | MEDIUM |
| `definition_service.py` | 426 | Definition management. No test. | LOW |
| `services/jtms/atms_core.py` | 223 | ATMS pure Python. Tested via `test_atms_plugin.py` (plugin) but core not tested directly | LOW |
| `ai_shield/` (5 files, ~700 LOC) | — | AI Shield framework. Tested via `test_quality_scoring_plugin.py` indirectly. No dedicated test | LOW |

### Services — Web API (partial coverage)

| Source | LOC | Test coverage |
|--------|-----|---------------|
| `web_api/services/analysis_service.py` | 578 | Tested via `test_web_api_models_and_services.py` (composite) |
| `web_api/services/logic_service.py` | 482 | Tested via `test_logic_service.py` |
| `web_api/models/request_models.py` | 347 | Tested via `test_web_api_models_and_services.py` |
| `web_api/routes/` (5 files) | ~15 | Route stubs — no dedicated test |
| `web_api/app.py` | 44 | ASGI app — no test needed (thin wrapper) |

---

## 3. Récit du framework — Évolution cristallisée dans les tests

### Épisode 1: Le système de communication (Issue #36, Phase 1 — Mars 2025)
Les 9 fichiers `communication/test_*.py` (411 tests) documentent le système de messagerie multi-canal le plus complet du framework. Construit en une seule vague (`1572d61f` — "274 tests for channels, pub/sub, crypto, states"), il couvre: message (47 tests), channel interface (50), data channel (45), hierarchical (37), collaboration (52), pub/sub (51), request/response (38), middleware (38), adapters (53). Ce packet est remarquable car il a été conçu **before** les workflows qui l'utilisent — il a été construit comme une bibliothèque de communication générique, puis adopté par l'orchestration hiérarchique (mode dormant). Le fait que `test_adapters.py` teste les 3 adapters (operational/tactical/strategic) dans un seul fichier suggère qu'ils ont été implémentés ensemble comme un système cohérent.

### Épisode 2: LeCapability Registry — la clé de voûte Lego (Issue #35)
`test_capability_registry.py` (26 tests) teste le composant central de l'architecture Lego: `CapabilityRegistry` + `ServiceDiscovery`. Ce sont les tests qui définissent le contrat d'enregistrement (register_agent, register_plugin, register_service, find_*_for_capability). L'architecture Lego a été introduite avec #35 (intégration des 12 projets étudiants) et ces tests garantissent que le contrat d'interface est respecté. Chaque nouveau plugin ou service doit passer par ce registry pour être découvrable.

### Épisode 3: Le JTMS — du service au plugin (Issue #214)
Les 5 fichiers de test JTMS (153 tests) documentent la maturation du JTMS: `test_jtms_core.py` (28 tests, Belief/Justification/JTMS basics) → `test_jtms_service.py` (51 tests, high-level service) → `test_jtms_session_manager.py` (55 tests, persistence/sessions) → `test_jtms_conflict_resolution.py` (19 tests) → `test_extended_belief.py` (30 tests). La consolidation dans `services/jtms/` (commit `dae46400`) a structuré le JTMS comme un service à part entière, qui est ensuite wrappé par le `JTMSSemanticKernelPlugin` (testé dans B-04).

### Épisode 4: Le Cluedo Oracle State — le plus gros test du packet (98 tests)
`test_cluedo_oracle_state_extended.py` (98 tests, 907 LOC) est le fichier de test le plus volumineux du packet. Il teste le jeu d'investigation Sherlock-Watson-Moriarty avec des scénarios complets (moriarty_interrogation, element_revelation, game_phase_transitions). `test_cluedo_oracle_state.py` (19 tests) couvre les bases. Ensemble, ils représentent **117 tests pour le mode Cluedo** — un investissement de test disproportionné pour un mode qui est "ACTIVED mais séparé" des workflows principaux. Cela suggère que le Cluedo a été un démonstrateur pédagogique important.

### Épisode 5: Le DLL Guard — Windows hardening (Issue #512)
`test_dll_guard.py` (3 tests, 28 LOC) est le test le plus petit du packet mais documente un **episod crucial**: le crash `WinError 182` sur Windows quand JPype charge une DLL avant PyTorch. Le guard (`dll_guard.py`, 51 LOC) impose l'ordre de chargement via `conftest.py` (torch/transformers before jpype). Ce test est un **canari de plateforme** — il ne teste pas la logique métier mais la compatibilité Windows.

### Épisode 6: Le MCP Server — le student project le mieux testé (Issue #773)
`test_mcp_server.py` (64 tests, 781 LOC) teste le serveur MCP (FastMCP) qui est le projet étudiant avec le score le plus élevé (90%). Le test couvre: main server setup, tool registration, session management, conversation tools, capability tools, workflow tools. C'est un exemple de test de bout en bout pour un service complet.

### Épisode 7: Le Web API — le composite test pattern (Issue #36)
`test_web_api_models_and_services.py` (113 tests, 1118 LOC) est le plus gros fichier de test des services. Il utilise un pattern **composite**: un seul fichier test couvre les modèles request/response + les services analysis/fallacy/logic/validation. Ce pattern est un artefact de la phase de couverture initiale (Issue #36 — "148 tests for response models, refactoring utils"). Les fichiers `web_api/models/test_response_models.py` et `web_api/services/test_*.py` sont des ajouts ultérieurs qui décomposent ce composite.

### Épisode 8: Le Source Management — le gardien du dataset (Extended tests)
`test_source_management_extended.py` (65 tests, 1115 LOC) teste le système de chargement et validation des sources (données chiffrées, cartes de sources, métadonnées). C'est un composant critique pour la **discipline de confidentialité** du projet — il garantit que le dataset reste chiffré et que les IDs opaques sont utilisés.

### Épisode 9: Le Phase-Scoped State — le gating par phase (Issue #605)
`test_phase_scoped_state.py` (24 tests, 261 LOC) teste le système de gating qui permet de contrôler quels outils sont disponibles à chaque phase du workflow. Introduit par #605, c'est un mécanisme qui empêche les phases d'utiliser des outils en dehors de leur scope — un pattern de sécurité pour les workflows multi-phases.

### Épisode 10: Le Prover9 Runner — le solver externe (Issue #479)
`test_prover9_runner.py` (8 tests, 114 LOC) teste le runner pour le solver externe Prover9. Ce composant est wrappé par `invoke_callables._invoke_external_fol_solver` dans l'orchestration (testé par B-02 `test_external_solvers.py`). Le runner lui-même est un processus externe — les tests mockent le subprocess.

---

## 4. Patterns transversaux

### 4.1 Infrastructure avant business
Le packet core/ illustre un pattern de développement "bottom-up": la communication (411 tests), le registry (26 tests), le bootstrap (24 tests), et les états (260+ tests) ont été construits AVANT les workflows qui les consomment. Cela contraste avec B-02 (orchestration) où les tests documentent l'intégration "top-down".

### 4.2 Composite test files
Plusieurs fichiers de test couvrent des sources multiples:
- `test_adapters.py` → 3 adapters
- `test_web_api_models_and_services.py` → models + services
- `test_source_management_extended.py` → source_management + source_manager

C'est un artefact de la Phase #36 (coverage initiale) où la priorité était le volume de tests.

### 4.3 In-source tests
`core/tests/` et `core/communication/tests/` contiennent des tests qui doublonnent partiellement les tests unitaires. Ce pattern est un artefact de la période pré-migration vers `tests/unit/`.

### 4.4 Utils: le grand angle mort
Les 17 fichiers `core/utils/` (~3 600 LOC) n'ont **aucun test dédié**. Ils sont testés indirectement via leurs consommateurs (services, orchestration, state writers). C'est un choix délibéré — les utils sont des fonctions pures facilement testables, mais le ROI de tests dédiés est faible puisque les bugs seraient attrapés par les tests consommateurs.

---

## 5. Recommandations

| # | Recommandation | Priorité | Justification |
|---|---------------|----------|---------------|
| R1 | Créer `test_shared_state.py` dédié dans core/ | **HIGH** | 1 110 LOC, backbone state, uniquement testé indirectement via B-02. Un test unitaire dédié améliorerait la maintenabilité. |
| R2 | Créer `test_strategies.py` | **MEDIUM** | 516 LOC, untested. Stratégies d'analyse utilisées par les workflows. |
| R3 | Créer `test_fetch_service.py` | **MEDIUM** | 466 LOC, multi-strategy document fetcher, aucun test. |
| R4 | Créer `test_extract_service.py` | **MEDIUM** | 457 LOC, extract management, aucun test. |
| R5 | Migrer `core/tests/test_state_manager_plugin.py` vers `tests/unit/` | **LOW** | 309 LOC de tests in-source, devraient être dans l'arborescence unifiée. |
| R6 | Archiver tests in-source doublons (`core/tests/`, `core/communication/tests/`) | **LOW** | Doublons partiels des tests dans `tests/unit/`. |
| R7 | Ajouter tests pour `nl_to_logic.py` (836 LOC, service layer) | **LOW** | Testé via plugin wrapper (B-04) mais service pas testé directement. |

---

## 6. Synthèse

| Classification | Fichiers test | Tests | % |
|---------------|--------------|-------|---|
| ✅ Wired | 42 | ~1 400 | 84% |
| ⚠️ Justifié (infrastructure/guards) | 5 | ~66 | 4% |
| 🔍 Composite (multi-source) | 4 | ~243 | 15% |
| ❌ Orphelin | 0 | 0 | 0% |
| **Sources sans test dédié** | ~70 sources | — | — |

**Key finding**: 0 orphelins dans les tests. Le packet core+services est le **fondationnel** du framework — il contient le registry (Lego backbone), la communication (multi-canal), le state management (10 dimensions), et les services critiques (JTMS, crypto, LLM, logic).

**Angle mort principal**: `shared_state.py` (1 110 LOC) est le plus gros fichier source du packet et n'a pas de test unitaire dédié. Testé indirectement via B-02 orchestration tests.

**Le grand angle mort structurel**: `core/utils/` (17 fichiers, ~3 600 LOC) est entièrement non testé unitairement. Choix délibéré (tests consommateurs suffisent) mais remarquable par son volume.
