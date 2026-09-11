# `agents/core/oracle/` — hiérarchie Oracle « gardien de données » + Cluedo (un seul chemin vivant)

## Rôle et frontière

10 fichiers, 4 361 lignes. Le module fournit une **hiérarchie d'agents gardiens de données** (`OracleBaseAgent` → `MoriartyInterrogatorAgent`) surmontant une pile de contrôle d'accès (ACL par agent × type de requête), un dataset Cluedo synthétique et un gestionnaire d'accès caché. Sa frontière est nette : il **ne participe pas** aux axes d'analyse d'argument (extraction, sophismes, qualité, logique). C'est une famille d'agents de **jeu d'enquête pédagogique** branchée en option sur le système, pas un composant de l'analyse rhétorique.

Point d'honnêteté sur le qualificatif du titre : `CLAUDE.md` (racine) déclare le mode Cluedo « ACTIVE » avec des « dedicated scripts ». Le second terme est vérifié ; le premier l'est **partiellement** — voir « Statut d'intégration ».

## Composants publics

**Agents**
- `oracle_base_agent.py` (723 l.) — `OracleTools` :37 (8 `@kernel_function` : `validate_query_permission` :66, `execute_authorized_query` :98, `get_available_query_types` :154, `reveal_information_controlled` :188, `query_oracle_dataset` :219, `execute_oracle_query` :277, `check_agent_permission` :332, `validate_agent_permissions` :371) ; `OracleBaseAgent` :383 (`BaseAgent`), point d'entrée `process_oracle_request` :531, `get_oracle_statistics` :601, `reset_oracle_state` :639 ;
- `moriarty_interrogator_agent.py` (648 l.) — `MoriartyTools` :35 (4 `@kernel_function` : `validate_cluedo_suggestion` :61, `reveal_card_if_owned` :119, `provide_game_clue` :167, `simulate_other_player_response` :202) ; `MoriartyInterrogatorAgent` :278, `validate_suggestion_cluedo` :393, `invoke` :559, `invoke_single` :587.

**Données et accès**
- `cluedo_dataset.py` (633 l.) — `CluedoSuggestion` :17, `RevelationRecord` :41, `CluedoDataset` :79 (`validate_cluedo_suggestion` :280, `reveal_card` :234, `process_query` :452) ;
- `dataset_access_manager.py` (631 l.) — `QueryCache` :31, `DatasetAccessManager` :185 (`execute_query` :229, `execute_oracle_query` :456, `check_permission` :534), `CluedoDatasetManager` :593 ;
- `permissions.py` (450 l.) — `QueryType` :32 (12 membres), `RevealPolicy` :61, `PermissionRule` :75, `ValidationResult` :137, `OracleResponse` :155, `AccessLog` :197, `PermissionManager` :208, `validate_cluedo_method_access` :354, `get_default_cluedo_permissions` :379.

**Extensions et contrats**
- `phase_d_extensions.py` (687 l.) — `PhaseDExtensions` :59, `extend_oracle_state_phase_d` :590 (monkey-patch) ;
- `interfaces.py` (140 l.) — `OracleAgentInterface` :17, `DatasetManagerInterface` :60, `StandardOracleResponse` :101, `OracleResponseStatus` :128 ;
- `error_handling.py` (127 l.) — `OracleErrorHandler` :41, `oracle_error_handler` :95 ;
- `hypothesis_tracker.py` (219 l.) — `HypothesisTracker` :38 (ATMS, docstring :1 « for Sherlock Modern (#359) »).

`__init__.py` (103 l.) réexporte **26 noms** (`__all__` :45-76, comptage AST). Vérifiés un par un : les 26 existent réellement — zéro fantôme, zéro doublon.

## Points d'entrée valides

1. **CLI (chemin principal)** — `argumentation_analysis/run_orchestration.py --mode cluedo` : le littéral est déclaré `run_orchestration.py:370` (`choices` du `--mode`, aide :377 « investigation Sherlock-Watson-Oracle, #914 ») et la branche est en :814. Elle importe `run_cluedo_oracle_game` (`:817-819`) et l'appelle `:841-844` avec `kernel=` et `initial_question=`. Signature réelle : `orchestration/cluedo_extended_orchestrator.py:986` (`kernel, initial_question, max_turns=15, max_cycles=5, oracle_strategy="balanced", settings=None`).
2. **Runner autonome** — `orchestration/cluedo_runner.py:19` (`run_cluedo_oracle_game(kernel, settings, …)`, `__main__` :91) : construit `CluedoExtendedOrchestrator` :30, `setup_workflow()` :38, `execute_workflow()` :39. L'appel :59-61 omet `settings` — **ce n'est pas un défaut** : `settings=None` est le défaut (`cluedo_extended_orchestrator.py:992`) et la fonction retombe alors sur les settings globaux (`:1008-1011`), il n'y a rien à corriger ici.
3. **Script dédié revendiqué par `CLAUDE.md`** — `scripts/sherlock_watson/run_cluedo_oracle_enhanced.py:46` (importe `cluedo_runner.run_cluedo_oracle_game`), argparse local. **Hors CI**.
4. **Consommateur indirect** — `scripts/sherlock_watson/run_einstein_oracle_demo.py:170-186` importe `core.cluedo_oracle_state.CluedoOracleState` pour fabriquer un état « factice » ; il **ne** charge **pas** `MoriartyInterrogatorAgent`.

**Chemins NON armés** (mesurés, pas supposés) : `grep` sur `oracle`/`cluedo` dans `orchestration/registry_setup.py`, `orchestration/workflows.py` et `agents/factory.py` → **0 hit**. Le module n'a **aucune entrée `CapabilityRegistry`**, **aucune phase `capability=`**, n'est pas dans les workflows `light/standard/full`, et n'est pas atteignable depuis `UnifiedPipeline`.

## Amont / aval

- **Amont** : `agents/core/abc/agent_bases.py` (`BaseAgent`), `utils/performance_monitoring.py` (`monitor_performance`), Semantic Kernel.
- **Aval** : le module alimente `core/cluedo_oracle_state.py` (état partagé du jeu) et `orchestration/cluedo_extended_orchestrator.py` (orchestrateur 3 agents) ; résultat consommé par l'affichage CLI `run_orchestration.py:846+` et `scripts/apps/sherlock_watson/run_unified_investigation.py:112`.

## Statut d'intégration

Le **chemin vivant est unique** : `--mode cluedo` → `CluedoExtendedOrchestrator` → instanciation de `MoriartyInterrogatorAgent` (`cluedo_extended_orchestrator.py:91,256`) + `CluedoDatasetManager` (:248) sur un `CluedoOracleState` (:224) qui importe `cluedo_dataset`, `permissions`, `phase_d_extensions`. Partition **fichier par fichier** (critère : `actif-critique` = la pièce est instanciée/imposée sur ce chemin et son absence casse l'exécution ; `actif` = requise mais de portée utilitaire ; les autres statuts sont explicités) :

| Fichier | L. | Statut | Preuve |
|---|---|---|---|
| `moriarty_interrogator_agent.py` | 648 | **actif-critique** | seul agent Oracle instancié par un chemin production — `cluedo_extended_orchestrator.py:91` (import), `:256` (instanciation) |
| `cluedo_dataset.py` | 633 | **actif-critique** | `core/cluedo_oracle_state.py:17`, `cluedo_extended_orchestrator.py:92` |
| `dataset_access_manager.py` | 631 | **actif-critique** | `CluedoDatasetManager` instancié `cluedo_extended_orchestrator.py:248` et `core/cluedo_oracle_state.py:204` |
| `oracle_base_agent.py` | 723 | **actif** | superclasse de `MoriartyInterrogatorAgent` (`moriarty_interrogator_agent.py:28,278`) — requise, mais sa propre surface `@kernel_function` est en partie redondante (voir Limites) |
| `permissions.py` | 450 | **actif** | `core/cluedo_oracle_state.py:18,152` ; `CluedoDatasetManager` construit son `PermissionManager` — `dataset_access_manager.py:600-602` |
| `phase_d_extensions.py` | 687 | **expérimental** | patch installé à l'import (`core/cluedo_oracle_state.py:23,1664` → exécuté à chaque run Cluedo) mais **0 appelant production** des méthodes injectées ; seul test dédié = `tests/_archived/validation_sherlock_watson/test_phase_d_trace_ideale.py:22` (non collecté) |
| `hypothesis_tracker.py` | 219 | **résiduel** | 0 importeur production ; le mode `sherlock_modern` passe par `_invoke_atms` (`orchestration/invoke_callables.py:2563`) → `services/jtms/atms_core.ATMS` (`:2571`), pas par ce module |
| `error_handling.py` | 127 | **résiduel** | 0 importeur production ; `oracle_error_handler` :95 n'est **jamais** appliqué hors tests/scripts |
| `interfaces.py` | 140 | **résiduel** | 0 implémenteur production — `OracleBaseAgent` :383 n'hérite **pas** de `OracleAgentInterface` :17 ; implémenté uniquement par des classes locales de test (`tests/unit/.../test_interfaces.py:33,83`) |
| `__init__.py` | 103 | **compatibilité** | 0 importeur production du paquet ; la seule façade `from ...core.oracle import …` est dans `scripts/maintenance/tools/` (générateurs de doc/refactor) |

**Verdict sur `CLAUDE.md`** : « dedicated scripts » → **vérifié** (`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py:46`, `run_orchestration.py:814`). « ACTIVE » → **vérifié avec réserve** : le mode est bien dispatchable en CLI, mais il n'a **ni entrée registre ni phase workflow**, et la CLI `--mode cluedo` n'est **exécutée par aucun job CI** (voir Tests).

## Artefacts et lecteurs

Traces de partie (`conversation_trace`, `tool_usage_trace`, `metrics` — `core/cluedo_oracle_state.py:31-44`), `oracle_statistics` et solution finale, imprimés par la CLI (`run_orchestration.py:846+`) et affichés par `cluedo_runner.py:63-85`. Lecteurs : l'utilisateur (démo/soutenance), les scripts `scripts/sherlock_watson/`, les workers d'intégration. **Pas** de lecteur dans la chaîne de restitution (`reporting/`).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/oracle/ -v
```

**153 `def test_` sur 10 fichiers** dans `tests/unit/argumentation_analysis/agents/core/oracle/` (comptage `grep -c 'def test_'`, inclut les méthodes indentées) — dont `test_permissions.py` (43) et `test_cluedo_dataset.py` (24). Tests croisés : `tests/unit/argumentation_analysis/core/test_cluedo_oracle_state.py` (19) et `test_cluedo_oracle_state_extended.py` (98), `tests/unit/argumentation_analysis/orchestration/test_cluedo_extended_orchestrator.py` (56), `tests/unit/orchestration/test_specialized_orchestrators.py` (6), `tests/integration/workers/worker_oracle_integration.py` (14, sans `requires_api`).

**Périmètre CI** : le job pytest de `.github/workflows/ci.yml:258` couvre `tests/unit/` **et** `tests/integration/workers/` — donc les 153 + les workers sont collectés. **Hors CI** : `tests/performance/test_oracle_performance.py` (9) et `tests/integration/triage/` (non listés) ; et surtout, **la commande `run_orchestration.py --mode cluedo` elle-même n'est exécutée par aucun job**. La couverture réelle est donc : *construction* de l'orchestrateur en test (kernel mocké), pas *exécution du mode*.

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`, README de juin 2025, non réécrit par le lot A7 ; il ne mentionne ni `oracle/`, ni `quality/`, ni `political/`). Frères documentés : [`../logic/README.md`](../logic/README.md), [`../informal/README.md`](../informal/README.md), [`../debate/README.md`](../debate/README.md), [`../governance/README.md`](../governance/README.md), [`../synthesis/README.md`](../synthesis/README.md). Consommateurs hors du dossier : [`../../../orchestration/cluedo_extended_orchestrator.py`](../../../orchestration/cluedo_extended_orchestrator.py), [`../../../core/cluedo_oracle_state.py`](../../../core/cluedo_oracle_state.py).

## Limites connues

- **Un seul chemin production, hors CI.** Tout le module tient sur `--mode cluedo` + deux scripts. Aucune entrée `CapabilityRegistry`/workflow : le module est invisible pour le système Lego et pour `compare_orchestration_modes.py`.
- **Données Cluedo inline.** `CluedoDataset` code en dur ses éléments par défaut (`cluedo_dataset.py:106-134` : 6 suspects, 6 armes, 9 lieux, noms de convention Cluedo). Ce sont des données **synthétiques/pédagogiques**, sans rapport avec le dataset chiffré canonique — aucune crainte privacy ici.
- **Trois modules sans consommateur** (`interfaces.py`, `error_handling.py`, `hypothesis_tracker.py`). Ils sont testés, donc verts — mais « un vert peut mesurer une forme que rien ne produit ».

### Anomalies (constatées, non corrigées — mandat documentaire)

1. **`CluedoIntegrityError` défini deux fois, avec des bases incompatibles** — `permissions.py:348` (`(Exception)`) vs `error_handling.py:35` (`(OracleError)`). `dataset_access_manager.py:25` importe celui de `permissions`. Conséquence : le `isinstance(error, CluedoIntegrityError)` de `error_handling.py:80` ne peut **jamais** matcher l'exception réellement levée par `validate_cluedo_method_access` (`permissions.py:373`).
2. **`BASE_ORACLE_SYSTEM_PROMPT` déclaré, jamais lu** — `oracle_base_agent.py:400-425` (`ClassVar`) a **0** lecteur dans le dépôt, tandis que `__init__` ré-inline une copie texte identique en :456-479 — déclaré non mobilisé.
3. **`OracleTools` : surface partiellement redondante et sans consommateur aval** — `query_oracle_dataset` :219 et `execute_oracle_query` :277 sont fonctionnellement identiques (la docstring de :281 l'admet) ; `reveal_information_controlled` :188 est un placeholder explicite. Grep des 8 noms hors `oracle_base_agent.py` : seuls des tests et des archives les citent — **0** référence dans un prompt, un plan d'agent, un orchestrateur ou un workflow. Les outils sont donc exposés au LLM, jamais appelés par du code de production.
4. **Divergence interface/implémentation** — `interfaces.py:27` déclare `process_oracle_request` **async** et renvoyant `Dict[str, Any]` ; `OracleBaseAgent.process_oracle_request` (`oracle_base_agent.py:531`) est **sync** et renvoie `OracleResponse`. Idem `DatasetManagerInterface.execute_query` :69 (sync) vs `DatasetAccessManager.execute_query` :229 (**async**). Contrats jamais branchés, donc jamais démentis.
5. **Faute de frappe dans l'API publique** — `RevealationTiming` (au lieu de « Revelation ») : `phase_d_extensions.py:39`, réexporté `__init__.py:39,73`. Renommer casserait la surface publique ; à arbitrer.
6. **Collision de nom** — `oracle/hypothesis_tracker.py:38` définit un `HypothesisTracker` **ATMS**, et `agents/sherlock_jtms_agent.py:24` en définit un **autre** (basé JTMS). Deux classes homonymes dans l'arbre des agents, sémantiques différentes.
7. **Deux abstractions « Oracle » concurrentes** — `scripts/sherlock_watson/run_einstein_oracle_demo.py:51` définit son propre `EinsteinPuzzleOracle`, sans lien avec la hiérarchie `OracleBaseAgent` ; le nom « oracle » ne désigne donc pas une seule chose dans le dépôt.

### Assertion croisée vérifiée

Le README frère [`../../../data/datasets/legacy_fixtures/README.md`](../../../data/datasets/legacy_fixtures/README.md) (commit `e5ffa3ac`) affirme : *« le scénario Cluedo opérationnel actuel vit dans `agents/oracle/` avec ses propres données »*. **Vérifié, avec une nuance** : le scénario opérationnel consomme bien les données **de ce module**, mais elles sont **codées en dur** aux `cluedo_dataset.py:106-134` — il n'y a **aucun fichier de données** dans `oracle/`. Et elles sont structurellement distinctes de la fixture relocalisée (`solution_secrete` = `{suspect, arme, lieu}` ici, `:177-184`, contre `{coupable, arme, lieu, methode}` dans `mystere_laboratoire_ia_cluedo.json`). L'assertion n'est donc pas périmée ; elle est seulement imprécise sur le mot « données » (code, pas ressources).
