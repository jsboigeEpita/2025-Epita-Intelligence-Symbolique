# `agents/core/oracle/` — hiérarchie Oracle « gardien de données » + Cluedo (un seul chemin vivant)

## Rôle et frontière

9 fichiers, 4 139 lignes (10 fichiers / 4 361 l. avant le retrait de `hypothesis_tracker.py`, #2137 ; interfaces.py 140→162 l., #2358). Le module fournit une **hiérarchie d'agents gardiens de données** (`OracleBaseAgent` → `MoriartyInterrogatorAgent`) surmontant une pile de contrôle d'accès (ACL par agent × type de requête), un dataset Cluedo synthétique et un gestionnaire d'accès caché. Sa frontière est nette : il **ne participe pas** aux axes d'analyse d'argument (extraction, sophismes, qualité, logique). C'est une famille d'agents de **jeu d'enquête pédagogique** branchée en option sur le système, pas un composant de l'analyse rhétorique.

Point d'honnêteté sur le qualificatif du titre : `CLAUDE.md` (racine) déclare le mode Cluedo « ACTIVE » avec des « dedicated scripts ». Le second terme est vérifié ; le premier l'est **partiellement** — voir « Statut d'intégration ».

## Composants publics

**Agents**
- `oracle_base_agent.py` (698 l. ; 697 avant l'héritage #2358, 711 avant la fusion des jumelles #2345, 723 avant le retrait du `ClassVar` `BASE_ORACLE_SYSTEM_PROMPT`, #2137) — `OracleTools`, voie d'exécution unique `_run_oracle_query` (#2340), corps unique des jumelles `_query_and_report` (#2345) et 8 `@kernel_function` : `validate_query_permission`, `execute_authorized_query`, `get_available_query_types`, `reveal_information_controlled`, `query_oracle_dataset`, `execute_oracle_query`, `check_agent_permission`, `validate_agent_permissions` ; `OracleBaseAgent` (`BaseAgent`, **`OracleAgentInterface` #2358**), point d'entrée `process_oracle_request`, `get_oracle_statistics`, `reset_oracle_state` ;
- `moriarty_interrogator_agent.py` (648 l.) — `MoriartyTools` (4 `@kernel_function` : `validate_cluedo_suggestion`, `reveal_card_if_owned`, `provide_game_clue`, `simulate_other_player_response`) ; `MoriartyInterrogatorAgent`, `validate_suggestion_cluedo`, `invoke`, `invoke_single`.

**Données et accès**
- `cluedo_dataset.py` (633 l.) — `CluedoSuggestion`, `RevelationRecord`, `CluedoDataset` (`validate_cluedo_suggestion`, `reveal_card`, `process_query`) ;
- `dataset_access_manager.py` (632 l.) — `QueryCache`, `DatasetAccessManager` (**`DatasetManagerInterface` #2358** ; `execute_query`, `execute_oracle_query`, `check_permission`), `CluedoDatasetManager` ;
- `permissions.py` (450 l.) — `QueryType` (12 membres), `RevealPolicy`, `PermissionRule`, `ValidationResult`, `OracleResponse`, `AccessLog`, `PermissionManager`, `validate_cluedo_method_access`, `get_default_cluedo_permissions`.

**Extensions et contrats**
- `phase_d_extensions.py` (687 l.) — `PhaseDExtensions`, `extend_oracle_state_phase_d` (monkey-patch) ;
- `interfaces.py` (162 l.) — `OracleAgentInterface`, `DatasetManagerInterface`, `StandardOracleResponse`, `OracleResponseStatus` ; les types `QueryType`/`QueryResult`/`OracleResponse` des signatures viennent de `permissions.py` (#2358) ;
- `error_handling.py` (127 l.) — `OracleErrorHandler`, `oracle_error_handler` ;
- `hypothesis_tracker.py` (219 l.) — **retiré (#2137)** : `HypothesisTracker` (ATMS, « for Sherlock Modern (#359) »), 0 importeur production — le mode `sherlock_modern` passe par `services/jtms/atms_core.ATMS`, pas par ce module. Parti avec ses deux fichiers de tests.

`__init__.py` (103 l.) réexporte **26 noms** (`__all__`, comptage AST). Vérifiés un par un : les 26 existent réellement — zéro fantôme, zéro doublon.

## Points d'entrée valides

1. **CLI (chemin principal)** — `argumentation_analysis/run_orchestration.py --mode cluedo` : le littéral est déclaré `run_orchestration.py` (`choices` du `--mode`, aide « investigation Sherlock-Watson-Oracle, #914 ») et une branche dédiée le traite. Elle importe `run_cluedo_oracle_game` et l'appelle avec `kernel=` et `initial_question=`. Signature réelle : `orchestration/cluedo_extended_orchestrator.py` (`kernel, initial_question, max_turns=15, max_cycles=5, oracle_strategy="balanced", settings=None`).
2. **Runner autonome** — `orchestration/cluedo_runner.py` (`run_cluedo_oracle_game(kernel, settings, …)`, `__main__`) : construit `CluedoExtendedOrchestrator`, `setup_workflow()`, `execute_workflow()`. L'appel omet `settings` — **ce n'est pas un défaut** : `settings=None` est le défaut (`cluedo_extended_orchestrator.py`) et la fonction retombe alors sur les settings globaux, il n'y a rien à corriger ici.
3. **Script dédié revendiqué par `CLAUDE.md`** — `scripts/sherlock_watson/run_cluedo_oracle_enhanced.py` (importe `cluedo_runner.run_cluedo_oracle_game`), argparse local. **Hors CI**.
4. **Consommateur indirect** — `scripts/sherlock_watson/run_einstein_oracle_demo.py` importe `core.cluedo_oracle_state.CluedoOracleState` pour fabriquer un état « factice » ; il **ne** charge **pas** `MoriartyInterrogatorAgent`.

**Chemins NON armés** (mesurés, pas supposés) : `grep` sur `oracle`/`cluedo` dans `orchestration/registry_setup.py`, `orchestration/workflows.py` et `agents/factory.py` → **0 hit**. Le module n'a **aucune entrée `CapabilityRegistry`**, **aucune phase `capability=`**, n'est pas dans les workflows `light/standard/full`, et n'est pas atteignable depuis `UnifiedPipeline`.

## Amont / aval

- **Amont** : `agents/core/abc/agent_bases.py` (`BaseAgent`), `utils/performance_monitoring.py` (`monitor_performance`), Semantic Kernel.
- **Aval** : le module alimente `core/cluedo_oracle_state.py` (état partagé du jeu) et `orchestration/cluedo_extended_orchestrator.py` (orchestrateur 3 agents) ; résultat consommé par l'affichage CLI `run_orchestration.py` et `scripts/apps/sherlock_watson/run_unified_investigation.py`.

## Statut d'intégration

Le **chemin vivant est unique** : `--mode cluedo` → `CluedoExtendedOrchestrator` → instanciation de `MoriartyInterrogatorAgent` (`cluedo_extended_orchestrator.py`) + `CluedoDatasetManager` sur un `CluedoOracleState` qui importe `cluedo_dataset`, `permissions`, `phase_d_extensions`. Partition **fichier par fichier** (critère : `actif-critique` = la pièce est instanciée/imposée sur ce chemin et son absence casse l'exécution ; `actif` = requise mais de portée utilitaire ; les autres statuts sont explicités) :

| Fichier | L. | Statut | Preuve |
|---|---|---|---|
| `moriarty_interrogator_agent.py` | 648 | **actif-critique** | seul agent Oracle instancié par un chemin production — `cluedo_extended_orchestrator.py` (import et instanciation) |
| `cluedo_dataset.py` | 633 | **actif-critique** | `core/cluedo_oracle_state.py`, `cluedo_extended_orchestrator.py` |
| `dataset_access_manager.py` | 632 | **actif-critique** | `CluedoDatasetManager` instancié `cluedo_extended_orchestrator.py` et `core/cluedo_oracle_state.py` |
| `oracle_base_agent.py` | 698 | **actif** | superclasse de `MoriartyInterrogatorAgent` (`moriarty_interrogator_agent.py`) — requise, mais sa propre surface `@kernel_function` est en partie redondante (voir Limites) |
| `permissions.py` | 450 | **actif** | `core/cluedo_oracle_state.py` ; `CluedoDatasetManager` construit son `PermissionManager` — `dataset_access_manager.py` |
| `phase_d_extensions.py` | 687 | **expérimental** | patch installé à l'import (`core/cluedo_oracle_state.py` → exécuté à chaque run Cluedo) mais **0 appelant production** des méthodes injectées ; seul test dédié = `tests/_archived/validation_sherlock_watson/test_phase_d_trace_ideale.py` (non collecté) |
| ~~`hypothesis_tracker.py`~~ | 219 | **retiré (#2137)** | 0 importeur production ; le mode `sherlock_modern` passe par `_invoke_atms` (`orchestration/invoke_callables.py`) → `services/jtms/atms_core.ATMS`, pas par ce module |
| `error_handling.py` | 127 | **résiduel** | 0 importeur production ; `oracle_error_handler` n'est **jamais** appliqué hors tests/scripts |
| `interfaces.py` | 162 | **actif** | **contrat armé (#2358)** : `OracleBaseAgent` et `DatasetAccessManager` en héritent ; garde de conformité signatures + async-ité (`test_interface_contract_2358.py`) — le contrat avait « licencié » le défaut #2340 (déclaration sync pour un `check_permission` async) |
| `__init__.py` | 103 | **compatibilité** | 0 importeur production du paquet ; la seule façade `from ...core.oracle import …` est dans `scripts/maintenance/tools/` (générateurs de doc/refactor) |

**Verdict sur `CLAUDE.md`** : « dedicated scripts » → **vérifié** (`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`, `run_orchestration.py`). « ACTIVE » → **vérifié avec réserve** : le mode est bien dispatchable en CLI, mais il n'a **ni entrée registre ni phase workflow**, et la CLI `--mode cluedo` n'est **exécutée par aucun job CI** (voir Tests).

## Artefacts et lecteurs

Traces de partie (`conversation_trace`, `tool_usage_trace`, `metrics` — `core/cluedo_oracle_state.py`), `oracle_statistics` et solution finale, imprimés par la CLI (`run_orchestration.py`) et affichés par `cluedo_runner.py`. Lecteurs : l'utilisateur (démo/soutenance), les scripts `scripts/sherlock_watson/`, les workers d'intégration. **Pas** de lecteur dans la chaîne de restitution (`reporting/`).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/oracle/ -v
```

**148 `def test_` sur 9 fichiers** dans `tests/unit/argumentation_analysis/agents/core/oracle/` (comptage `grep -c 'def test_'`, inclut les méthodes indentées ; **169/12 après les jumelles #2345 et la garde #2358** `test_interface_contract_2358.py`) — dont `test_permissions.py` (43) et `test_cluedo_dataset.py` (24). Le test croisé `tests/unit/argumentation_analysis/test_sherlock_atms_branching.py` (181 l.), seul autre importeur du tracker retiré, est parti avec lui ; `tests/property/test_atms_invariants.py` teste `services/jtms/atms_core` directement et reste. Tests croisés : `tests/unit/argumentation_analysis/core/test_cluedo_oracle_state.py` (19) et `test_cluedo_oracle_state_extended.py` (98), `tests/unit/argumentation_analysis/orchestration/test_cluedo_extended_orchestrator.py` (56), `tests/unit/orchestration/test_specialized_orchestrators.py` (6), `tests/integration/workers/worker_oracle_integration.py` (14, sans `requires_api`).

**Périmètre CI** : le job pytest de `.github/workflows/ci.yml` couvre `tests/unit/` **et** `tests/integration/workers/` — donc les 153 + les workers sont collectés. **Hors CI** : `tests/performance/test_oracle_performance.py` (9) et `tests/integration/triage/` (non listés) ; et surtout, **la commande `run_orchestration.py --mode cluedo` elle-même n'est exécutée par aucun job**. La couverture réelle est donc : *construction* de l'orchestrateur en test (kernel mocké), pas *exécution du mode*.

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`, README de juin 2025, non réécrit par le lot A7 ; il ne mentionne ni `oracle/`, ni `quality/`, ni `political/`). Frères documentés : [`../logic/README.md`](../logic/README.md), [`../informal/README.md`](../informal/README.md), [`../debate/README.md`](../debate/README.md), [`../governance/README.md`](../governance/README.md), [`../synthesis/README.md`](../synthesis/README.md). Consommateurs hors du dossier : [`../../../orchestration/cluedo_extended_orchestrator.py`](../../../orchestration/cluedo_extended_orchestrator.py), [`../../../core/cluedo_oracle_state.py`](../../../core/cluedo_oracle_state.py).

## Limites connues

- **Un seul chemin production, hors CI.** Tout le module tient sur `--mode cluedo` + deux scripts. Aucune entrée `CapabilityRegistry`/workflow : le module est invisible pour le système Lego et pour `compare_orchestration_modes.py`.
- **Données Cluedo inline.** `CluedoDataset` code en dur ses éléments par défaut (`cluedo_dataset.py` : 6 suspects, 6 armes, 9 lieux, noms de convention Cluedo). Ce sont des données **synthétiques/pédagogiques**, sans rapport avec le dataset chiffré canonique — aucune crainte privacy ici.
- **Modules sans consommateur production** — le lot #2137 n'en a retiré qu'un : `hypothesis_tracker.py` (**retiré**, 0 importeur). Les deux autres sont restés, prémisses du relevé 12-09 périmées à la re-mesure : `error_handling.py` est **vivant** depuis #2139 (`permissions.py` importe `CluedoIntegrityError` de lui, levée à l'exécution par `cluedo_dataset`), et `interfaces.py` a **3 importeurs outillés** (`scripts/maintenance/tools/`, dont `update_test_coverage.py` embarque du code de test réel les important, 84 références de noms) — et depuis #2358, **2 exécutants production** : `OracleBaseAgent` et `DatasetAccessManager` en héritent, garde de conformité à l'appui.

### Anomalies (constatées, non corrigées — mandat documentaire)

1. **`CluedoIntegrityError` défini deux fois, avec des bases incompatibles** — **résolu (#2139)** : la classe canonique est celle de `error_handling.py` (`(OracleError)`) ; `permissions.py` l'importe désormais au lieu de redéfinir la sienne (`(Exception)`), et une garde (`test_cluedo_integrity_error_canonical.py`) vérifie identité de classe + interception réelle par le `isinstance` de `error_handling.py`.
2. **`BASE_ORACLE_SYSTEM_PROMPT` déclaré, jamais lu** — **résolu (#2137)** : le `ClassVar` (`oracle_base_agent.py`, 0 lecteur) a été retiré ; la copie inlinée dans `__init__` (le texte réellement servi) reste l'unique source.
3. **`OracleTools` : surface partiellement redondante — marquée (#2137), exécution unifiée (#2340), jumelles fusionnées (#2345)** — `query_oracle_dataset` et `execute_oracle_query` étaient déclarées « fonctionnellement identiques » (ici et dans la docstring de la seconde). **Mesuré faux (#2345)** : la seconde taisait `revealed_information`, donc un LLM passant par ce nom ne voyait jamais ce que l'Oracle venait de révéler. Le partage de `_run_oracle_query` (#2340) unifiait l'`await`, pas la mise en forme. Les deux noms délèguent désormais à un corps unique `_query_and_report` ; garde `tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_query_twins_2345.py` (même réponse sur toute la matrice, née rouge sur la ligne de la révélation). `execute_authorized_query` reste une troisième surface, **distincte par contrat** : elle prend `agent_name` et répond par une chaîne sur un type invalide au lieu de lever. `reveal_information_controlled` est un placeholder explicite. Les **noms** restent exposés au kernel (arbitrage #2137, ci-dessous). Grep des 8 noms hors `oracle_base_agent.py` : seuls des tests et des archives les citent — **0** référence dans un prompt, un plan d'agent, un orchestrateur ou un workflow. **Marquage #2137** : cette mesure est **statique et structurellement aveugle pour des outils LLM-face** — un `@kernel_function` est appelé par le LLM à l'exécution (comme `identify_vulnerabilities`, nommé dans le prompt de `conversational_orchestrator.py`), donc « 0 appelant Python » n'est pas « jamais appelé ». Le retrait au motif du grep vide est explicitement écarté par l'arbitrage #2137 ; ces outils restent exposés au kernel.
4. **Divergence interface/implémentation** — **résolue (#2340, puis #2358)** : `OracleBaseAgent.process_oracle_request` (`oracle_base_agent.py`) est **async**, conforme à la déclaration `interfaces.py`. #2358 a clos le reste : les signatures déclarées portent désormais `QueryType`/`QueryResult`/`OracleResponse` et l'async-ité réelles, les deux classes production héritent des interfaces, et une garde compare chaque membre déclaré à l'implémentation (`test_interface_contract_2358.py`, témoin négatif à l'appui). La déclaration sync d'origine avait « licencié » le défaut #2340 — un contrat sans exécutant endosse les bugs au lieu de les attraper.
5. **Faute de frappe dans l'API publique** — **résolu (#2139)** : la classe s'appelle désormais `RevelationTiming` (`phase_d_extensions.py`, réexport `__init__.py`). La prémisse « renommer casserait la surface publique » a été mesurée fausse : **0** importeur externe du nom dans le dépôt (seuls le module définisseur, le réexport `__init__` et une chaîne dans un script de maintenance mort).
6. **Collision de nom** — **tranchée par #2137** : le `HypothesisTracker` **ATMS** (`oracle/hypothesis_tracker.py`) a été retiré (0 importeur production). Le `HypothesisTracker` **JTMS** (`agents/sherlock_jtms_agent.py`) est le survivant unique — le renommage éventuel du survivant (s'il reste souhaitable) est un grain séparé.
7. **Deux abstractions « Oracle » concurrentes** — `scripts/sherlock_watson/run_einstein_oracle_demo.py` définit son propre `EinsteinPuzzleOracle`, sans lien avec la hiérarchie `OracleBaseAgent` ; le nom « oracle » ne désigne donc pas une seule chose dans le dépôt.
8. **Coroutines jamais attendues sur la façade kernel** — **résolu (#2340)**. Quatre surfaces appelaient une méthode `async def` du manager **sans `await`** : `validate_query_permission` (via `check_permission` — une coroutine étant *truthy*, la fonction répondait « autorisé » **sur tout refus**), `execute_authorized_query` (l'issue #2340 : `response.authorized` levait `AttributeError` sur la coroutine, avalée par le `except` générique, donc la fonction kernel ne pouvait produire aucune requête), `process_oracle_request`, et `MoriartyTools.provide_game_clue` (via `request_clue`). Aucune des quatre n'avait de test : le seul lien des tests avec elles est une appartenance de **nom** à une liste littérale (`tests/integration/workers/worker_cluedo_extended_workflow.py`), assertion qui ne peut pas rougir sur ce défaut. Les quatre sont désormais `async` et attendues, et l'exécution de requête passe par une voie unique `OracleTools._run_oracle_query` — l'`await` n'est plus écrit qu'une fois, donc ne peut plus diverger d'une surface à l'autre (c'est cette divergence qui avait laissé `execute_authorized_query` synchrone alors que ses deux jumelles étaient correctes). Garde : `tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_kernel_functions_awaited_2340.py`. Conséquence hors module : `monitor_performance` (`utils/performance_monitoring.py`) reconnaît désormais les coroutines — sinon son wrapper synchrone aurait mesuré la *création* de la coroutine (~0 ms) au lieu de son exécution.

### Assertion croisée vérifiée

Le README frère [`../../../data/datasets/legacy_fixtures/README.md`](../../../data/datasets/legacy_fixtures/README.md) (commit `e5ffa3ac`) affirme : *« le scénario Cluedo opérationnel actuel vit dans `agents/oracle/` avec ses propres données »*. **Vérifié, avec une nuance** : le scénario opérationnel consomme bien les données **de ce module**, mais elles sont **codées en dur** dans `cluedo_dataset.py` — il n'y a **aucun fichier de données** dans `oracle/`. Et elles sont structurellement distinctes de la fixture relocalisée (`solution_secrete` = `{suspect, arme, lieu}` ici, contre `{coupable, arme, lieu, methode}` dans `mystere_laboratoire_ia_cluedo.json`). L'assertion n'est donc pas périmée ; elle est seulement imprécise sur le mot « données » (code, pas ressources).
