# `argumentation_analysis/core/utils/` — un assembleur d'utilitaires transverses à trois régimes : feuilles réellement consommées, façade par star-import, et fossiles test-only

22 modules feuilles plus un `__init__.py` : **23 fichiers `.py`, 4483 lignes** à la racine du paquet, **4641 lignes** en comptant la suite colocée `tests/` (2 fichiers : `__init__.py` 1 ligne, `test_error_recovery_manager.py` 157 lignes). Mesure des importeurs **résolue par `ast`** (`argumentation_analysis.core.utils.<module>`, dédupliquée) : **85 sites d'import de production**, dont **50 pour `crypto_utils` seul** (44 d'entre eux dans `scripts/`). **12 modules** ont un import de production direct, **2** ne sont atteints qu'en transitif via la façade `file_utils.py`, **8** n'ont aucun consommateur de production. Ce que le paquet fait que ses feuilles ne font pas : `__init__.py` importe 19 modules d'un coup (coût d'import lourd et effets de bord), et `file_utils.py` ré-exporte quatre feuilles par star-import en une façade unique que deux pipelines consomment.

## Rôle et frontière

Le paquet se présente comme une couche d'utilitaires transverses, mais **aucune convention unique ne le traverse** — trois régimes cohabitent, et c'est le fait structurant :

1. **Feuilles réelles**, modules de fonctions pures ou quasi (crypto, logging, réseau, CLI, reporting, chargement/sauvegarde de fichiers) : `crypto_utils.py:33`, `logging_utils.py:12`, `network_utils.py:247`, `cli_utils.py:35`, `reporting_utils.py:360`, `file_loaders.py:23`.
2. **Façade d'agrégation** — `file_utils.py` ne définit **aucune** fonction (`ast` sur le corps du module : 0 `def`), il empile quatre star-imports (`file_utils.py:42-45` : `file_loaders`, `file_savers`, `markdown_utils`, `path_operations`). Aucune de ces feuilles ne déclare `__all__`, donc **tout nom public fuit dans l'espace de noms de la façade**, y compris le paquet PyPI `markdown` importé par `markdown_utils.py:10` — fait mesuré de première main : `tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py:335` patche `argumentation_analysis.core.utils.file_utils.markdown.markdown`.
3. **Fossiles et stub** — `error_management.py` (150 l.) est auto-déclaré « simplifiée pour les tests » (`:7`, `:59`) et réussit toute récupération par simulation en dur (`time.sleep(0.001); return True`, `:85-86`, `:103-104`, `:119-120`). Le paquet héberge aussi un **doublon fonctionnel interne** (`run_shell_command` défini deux fois, voir Limites) et un module dont le littéral docstring précède ses imports.

La frontière avec le **paquet frère `argumentation_analysis/utils/`** (37 entrées à la racine) n'est **pas étanche** : trois noms de modules existent des deux côtés (`path_operations`, `reporting_utils`, `system_utils`), et deux implémentations sont vérifiées dupliquées (`ensure_directory_exists`, `generate_performance_visualizations` — voir Frères et parent). Un comptage par `grep` du nom nu confond donc les deux paquets ; **tous les chiffres de ce README sont résolus par import**, pas par nom de fichier.

## Composants publics

`__init__.py` pèse **990 octets** : 19 instructions `from . import` (`:3-21`) et 19 entrées `__all__` (`:23-43`). **Trois modules sur 22 ne sont pas exportés** — `code_manipulation_utils`, `error_management`, `llm_completion_guard` — importables seulement par chemin explicite.

| Nom | Fichier (lignes) | Statut mesuré (ancres vérifiées) |
|---|---|---|
| `cli_utils` | `cli_utils.py` (290) | vivant ; **5 parseurs actifs** (`:35`, `:87`, `:116`, `:157`, `:246`) + 1 commenté (`:82-86`) ; `DEPRECATED_ORATOR_ALIAS` `:16` |
| `code_manipulation_utils` | `code_manipulation_utils.py` (100) | vivant, mono-consommateur ; non exporté |
| `crypto_utils` | `crypto_utils.py` (418) | **vivant, pivot de flotte** ; `FIXED_SALT:30`, `derive_encryption_key:33`, `load_encryption_key:68` |
| `error_management` | `error_management.py` (150) | **stub test-only** ; `StateManager:8`, `ErrorRecoveryManager:60` ; non exporté |
| `file_loaders` | `file_loaders.py` (213) | vivant (2 directs + 4 noms via façade) ; `load_json_file:23`, `load_csv_file:150`, `load_document_content:186` |
| `file_savers` | `file_savers.py` (147) | **aucun consommateur réel** ; `save_json_file:24` ; seul « appel » = commentaires |
| `file_utils` | `file_utils.py` (51) | **façade vivante**, 0 `def` ; star-imports `:42-45` |
| `file_validation_utils` | `file_validation_utils.py` (125) | test-only ; `check_json_file_valid:51` |
| `filesystem_utils` | `filesystem_utils.py` (185) | **import mort** ; `ensure_directory_exists:14`, `check_files_existence:73`, `get_all_files_in_directory:127` |
| `json_utils` | `json_utils.py` (195) | test-only ; doublon de `file_loaders`/`file_savers` ; `load_json_from_file:22`, `save_json_to_file:61` |
| `llm_completion_guard` | `llm_completion_guard.py` (38) | vivant, récent ; `ReasoningStarvedError:22`, `assert_not_reasoning_starved:26` ; non exporté |
| `logging_utils` | `logging_utils.py` (101) | vivant ; `setup_logging:12` |
| `markdown_utils` | `markdown_utils.py` (182) | transitif via façade ; `save_markdown_to_html:26`, `convert_markdown_file_to_html:152` (0 appelant) |
| `network_utils` | `network_utils.py` (334) | vivant partiel ; `network_breaker:34`, `retry_on_network_error:40`, `download_file:80`, `get_resilient_async_client:247` |
| `parsing_utils` | `parsing_utils.py` (97) | test-only ; `parse_colon_separated_string_to_regex_dict:14` |
| `path_operations` | `path_operations.py` (312) | transitif via façade ; `sanitize_filename:38` |
| `reporting_utils` | `reporting_utils.py` (535) | vivant partiel ; 7 générateurs, `save_json_report:19`, `save_text_report:64`, `generate_markdown_report_for_corpus:360`, `generate_overall_summary_markdown:461` |
| `shell_utils` | `shell_utils.py` (127) | vivant via 1 chaîne ; `run_shell_command:14` |
| `string_utils` | `string_utils.py` (49) | test-only ; `get_significant_substrings:12` |
| `system_utils` | `system_utils.py` (245) | **aucun consommateur de production** ; `run_shell_command:30` — doublon de `shell_utils` |
| `text_utils` | `text_utils.py` (314) | test-only ; `normalize_text:18`, `find_segment_with_markers:186`, `populate_text_segment:255` |
| `visualization_utils` | `visualization_utils.py` (232) | vivant, mono-consommateur, **0 test** ; `generate_performance_visualizations:15` |

## Points d'entrée valides

**Aucun exécutable propre au paquet.** Trois voies réelles, une quatrième dépréciée :

1. **Import direct** — `from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key` (`argumentation_analysis/core/io_manager.py:13`). C'est la voie dominante.
2. **Façade** — `from argumentation_analysis.core.utils.file_utils import load_json_file, sanitize_filename, load_document_content` (`argumentation_analysis/pipelines/embedding_pipeline.py:59-62`). Six noms réels atteignent la production par ce chemin (voir Amont / aval).
3. **Suite canonique** (`pytest.ini:2` `testpaths = tests`) :
   ```
   pytest tests/unit/argumentation_analysis/utils/core_utils/ -v
   ```
   20 fichiers, **374 fonctions `test_`** (comptées par `ast`). Plus le fichier isolé `tests/unit/argumentation_analysis/core/utils/test_llm_completion_guard_1929.py` (6 tests).
4. **Shim déprécié** — `argumentation_analysis/utils/core_utils/` (star-import + `DeprecationWarning`). **0 importeur** (grep plein dépôt : les seules occurrences sont l'avertissement du shim lui-même, des commentaires et des chaînes de chemins de test).

## Amont / aval

Mesure résolue par `ast` sur tout le dépôt, hors `libs/` (vendored), en distinguant **production** (`argumentation_analysis/`, `scripts/`, `project_core/`, `examples/`) et **`tests/`**. 85 sites de production au total.

**Amont (dépendances externes chargées à l'import du paquet)** : `cryptography`, `httpx` (`network_utils.py`), `markdown` (`markdown_utils.py:10`), `unidecode` (`path_operations.py`), `matplotlib.pyplot` + `pandas` (`visualization_utils.py`). Comme `__init__.py:3-21` importe les 19 modules, **importer `core.utils` — même pour un seul utilitaire — tire matplotlib et pandas**.

**Aval, du plus consommé au nul** :

| Module | Sites prod | Zones | Ancres |
|---|---|---|---|
| `crypto_utils` | **50** | aa 3, examples 1, project_core 2, scripts 44 | `core/io_manager.py:13`, `core/source_management.py:36`, `scripts/security/verify_encrypted_dataset_completeness.py:26` |
| `logging_utils` | **10** | aa 6, scripts 4 | `pipelines/analysis_pipeline.py:37`, `agents/core/logic/tweety_initializer.py:22` |
| `cli_utils` | **6** | aa 3, scripts 3 | `utils/run_verify_extracts.py:38`, `scripts/orchestration/run_extract_repair.py:38` |
| `shell_utils` | **5** | project_core 4, scripts 1 | `project_core/core_from_scripts/environment_manager.py:14`, `.../validation_engine.py:6`, `.../strategies/base_strategy.py:4`, `project_core/managers/repository_manager.py:8`, `scripts/setup/fix_dependencies.py:24` |
| `file_utils` (façade) | **3** | aa 2, scripts 1 | `pipelines/embedding_pipeline.py:59`, `pipelines/reporting_pipeline.py:74`, `scripts/reporting/compare_rhetorical_agents_simple.py:32` |
| `file_loaders` | 2 (+4 noms via façade) | aa 1, scripts 1 | `agents/core/informal/informal_definitions.py:44` (`load_csv_file`), `scripts/data_preparation/generate_taxonomy_subsets.py:11` |
| `network_utils` | 2 | aa 2 | `core/llm_service.py:23` (`get_resilient_async_client`, appelé `:285`), `services/fetch_service.py:19-21` (`retry_on_network_error`, `network_breaker`) |
| `reporting_utils` | 2 | aa 1, scripts 1 | `pipelines/reporting_pipeline.py:80-82`, `scripts/reporting/compare_rhetorical_agents_simple.py:41` |
| `llm_completion_guard` | 2 | aa 2 | `agents/core/logic/watson_logic_assistant.py:22`, `services/ai_shield/layers/llm_validator.py:14` (**consommateur inter-paquets**) |
| `code_manipulation_utils` | 1 | project_core 1 | `project_core/core_from_scripts/refactoring_manager.py:7`, appelé `:25` et `:31` |
| `filesystem_utils` | 1 | project_core 1 | `project_core/core_from_scripts/organization_manager.py:5` — **import jamais référencé** (grep dans ce fichier = cette seule ligne) |
| `visualization_utils` | 1 | scripts 1 | `scripts/reporting/compare_rhetorical_agents_simple.py:38`, appelé `:220` |

**Modules sans aucun consommateur de production — c'est un fait, pas un oubli** (chacun n'a qu'un importeur de `tests/`, ou un import mort) :

| Module | Importeur unique |
|---|---|
| `error_management` | `tests/.../test_error_management.py:6` (+ la suite colocée `core/utils/tests/test_error_recovery_manager.py`) |
| `file_savers` | `tests/.../test_file_savers.py:8` — les seuls « appels » de production sont **commentés** (`pipelines/analysis_pipeline.py:283-284`) |
| `file_validation_utils` | `tests/.../test_file_validation_utils.py:8` |
| `json_utils` | `tests/.../test_json_utils.py:8` |
| `markdown_utils` | `tests/.../test_markdown_utils.py:7` (mais `save_markdown_to_html` est atteint via la façade, cf. ci-dessous) |
| `parsing_utils` | `tests/.../test_parsing_utils.py:7` — l'unique autre mention du dépôt est un message d'erreur (`scripts/utils/analyze_directory_usage.py:106`) |
| `path_operations` | `tests/.../test_path_operations.py:7` (mais `sanitize_filename` est atteint via la façade) |
| `string_utils` | `tests/.../test_string_utils.py:6` |
| `system_utils` | `tests/.../test_system_utils.py:16` |
| `text_utils` | `tests/.../test_text_utils.py:3` |

**Chemin transitif par la façade** — noms réellement consommés en production via `file_utils`, remontant à leur feuille :

| Nom | Feuille | Site de production |
|---|---|---|
| `load_json_file` | `file_loaders.py:23` | `embedding_pipeline.py:59`, `reporting_pipeline.py:74`, `compare_rhetorical_agents_simple.py:32` |
| `load_text_file` | `file_loaders.py` | `reporting_pipeline.py:74` |
| `load_csv_file` | `file_loaders.py:150` | `reporting_pipeline.py:74` |
| `load_document_content` | `file_loaders.py:186` | `embedding_pipeline.py:59` |
| `sanitize_filename` | `path_operations.py:38` | `embedding_pipeline.py:59` |
| `save_markdown_to_html` | `markdown_utils.py:26` | `reporting_pipeline.py:74` |

`file_savers` fuite intégralement dans la façade (`save_json_file`, `save_text_file`, `save_temp_extracts_json`) sans qu'aucun de ces noms soit consommé hors tests.

## Statut d'intégration

Verdict mesuré, en trois régimes nets — **22 modules se partitionnent exactement** :

- **Vivants (12)** — ≥1 import de production direct : `crypto_utils` (pivot de flotte, 50 sites, consommé par `core/` lui-même), `logging_utils`, `cli_utils`, `shell_utils`, `file_utils` (façade), `file_loaders`, `network_utils`, `reporting_utils`, `llm_completion_guard`, `code_manipulation_utils`, `visualization_utils`, plus `filesystem_utils` (import mort : le module *apparaît* importé en production sans l'être — le classer vivant serait une lecture fausse).
- **Transitifs seulement (2)** — atteints uniquement par la façade : `path_operations` (`sanitize_filename`), `markdown_utils` (`save_markdown_to_html`).
- **Inertes (8)** — 0 consommateur de production, direct ou transitif : `error_management` (stub), `file_savers`, `file_validation_utils`, `json_utils`, `parsing_utils`, `string_utils`, `system_utils`, `text_utils`.

Autrement dit : **14 modules sur 22 sont réellement atteignables en production**, dont **1 par un import mort** et **2 seulement via une façade de compatibilité**. Les modules inertes sont néanmoins couverts par la suite canonique (374 tests) — ils sont *testés* sans être *appelés*, ce qui est le mode de panne propre à ce paquet : **le vert des tests ne mesure pas l'intégration**.

## Artefacts et lecteurs

Oui, le paquet écrit et lit des fichiers — mais **presque uniquement par sa moitié non consommée** :

- **Écritures** : `reporting_utils.save_json_report:19` / `save_text_report:64`, `file_savers.save_json_file:24`, `file_savers.save_text_file`, `file_savers.save_temp_extracts_json`, `path_operations.archive_file`, `filesystem_utils.create_gitkeep_in_directory`. **Aucune de ces fonctions n'a d'appelant de production** : `save_json_file` n'apparaît que dans un bloc commenté (`analysis_pipeline.py:283-284`), et le `save_json_report` appelé ailleurs (`project_core/core_from_scripts/test_config_definition.py:566`) est celui, homonyme et indépendant, de `project_core/core_from_scripts/common_utils.py:247`.
- **Lectures effectives** : `file_loaders` (`load_json_file`, `load_text_file`, `load_csv_file`, `load_document_content`) — vivant, y compris via la façade.
- **Déclaré sans lecteur** : `reporting_utils` expose **7 générateurs**, seuls **2** sont importés par le pipeline (`reporting_pipeline.py:80-82`).
- **Effet de bord à l'import** : la façade attache un `StreamHandler` au logger du module (`file_utils.py:26-35`) et émet un `logger.info` **à chaque import** (`:49-51`).
- **Aucun artefact de données ou de journal n'est produit par le paquet lui-même.**

## Tests représentatifs

- **Suite canonique** : `tests/unit/argumentation_analysis/utils/core_utils/` — **20 fichiers, 374 fonctions `test_`** (comptées par `ast`). Plus gros contributeurs : `test_file_utils.py` (39), `test_path_operations.py` (32), `test_error_management.py` (31).
- **Fichier isolé** : `tests/unit/argumentation_analysis/core/utils/test_llm_completion_guard_1929.py` — 6 tests, hors du dossier principal.
- **Ce que les tests mesurent** : majoritairement le **contrat des feuilles** en isolation (mock, `tmp_path`), pas le chemin réel d'intégration. Le cas d'école est `test_file_utils.py:335` : il patche `file_utils.markdown.markdown`, c'est-à-dire le **nom du paquet PyPI qui a fui** dans la façade — le test épingle un détail d'implémentation de la fuite, pas la façade comme contrat.
- **Trou de couverture** : `grep -rl "visualization_utils" tests/` = **0 résultat**. Le module n'est couvert par aucun test ; le seul fichier proche (`tests/unit/argumentation_analysis/utils/test_visualization_generator.py`) teste l'implémentation **du paquet frère**, pas celle-ci.
- **Suite colocée non collectée** : `core/utils/tests/test_error_recovery_manager.py` — 5 fonctions `test_`, **0 `assert`** pour **22 `print`** : vert garanti. `pytest.ini:2` (`testpaths = tests`) fait qu'un `pytest` nu ne la collecte pas. Sa jumelle collectée (`tests/.../test_error_management.py`) porte, elle, de vraies assertions.
- **20 fichiers de test pour 22 modules** : manquent `visualization_utils` (0 partout) et `llm_completion_guard` (testé ailleurs, dans le dossier `core/utils/`).

## Frères et parent

- **Parent** : [`argumentation_analysis/core/`](../README.md) — et ce fichier est le **premier README du paquet lui-même** (aucun `.md` à la racine de `core/utils/` avant lui).
- **Sous-dossier documenté** : `core/utils/tests/README.md` (suite colocée).
- **Shim** : `argumentation_analysis/utils/core_utils/` — `__init__.py` de 11 lignes, star-import de `core/utils/` + `DeprecationWarning`. **0 importeur** : la migration vers le chemin canonique est achevée, le shim est resté derrière.
- **Frère homonyme et collisions vérifiées** : `argumentation_analysis/utils/` — 39 entrées hors `__pycache__` (35 `.py` à la racine, `README.md`, et 3 sous-dossiers : `core_utils/` le shim, `dev_tools/`, `extract_repair/`). Trois noms de modules sont **identiques des deux côtés** (`path_operations.py`, `reporting_utils.py`, `system_utils.py`), et deux implémentations sont **dupliquées mot pour mot dans leur rôle** :
  - `ensure_directory_exists` — `core/utils/filesystem_utils.py:14` vs `argumentation_analysis/utils/system_utils.py:18` ;
  - `generate_performance_visualizations` — `core/utils/visualization_utils.py:15` vs `argumentation_analysis/utils/visualization_generator.py:169` (cette dernière, elle, **est testée**).
  Conséquence pratique : un `grep` du nom nu **surestime** la consommation de ce paquet — c'est la cause mesurée de l'écart entre un comptage nominal et les 2 sites réels de `reporting_utils`.
- **Autres frères** : `argumentation_analysis/agents/utils/` (documenté), `project_core/utils/` (réduit à `shell.py` + `__init__.py` — les commentaires `project_core.utils.file_loaders` disséminés dans le dépôt pointent donc vers un chemin disparu).

## Limites connues

Relevées et **non corrigées** :

**Suivi** : les items **1, 2, 3, 5, 7, 8, 9, 10, 11, 12** sont portés par **#2146**. L'item **6**
(alias sur surface indexée) n'est **pas** une anomalie non gardée : le scanner le détecte
déjà — voir la mesure dans l'item lui-même. Le shim `utils/core_utils/` relève de **#2126**.

1. **Doublon fonctionnel intra-paquet** — `run_shell_command` est défini **deux fois** : `shell_utils.py:14` (le consommé) et `system_utils.py:30` (l'orphelin). `__init__.py` exporte les deux.
2. **Doublon JSON inter-modules** — `json_utils.load_json_from_file:22` / `save_json_to_file:61` font le travail de `file_loaders.load_json_file:23` / `file_savers.save_json_file:24` ; les premiers n'ont aucun consommateur, les seconds sont vivants.
3. **Import mort présenté comme consommation** — `project_core/core_from_scripts/organization_manager.py:5` importe `filesystem_utils` sans jamais l'utiliser. Un comptage par grep classerait ce module « consommé en production ».
4. **Surfaces déclarées sans consommateur** — `network_utils.download_file:80` (le seul `download_file` appelé ailleurs est l'homonyme indépendant de `core/jvm_setup.py`), `markdown_utils.convert_markdown_file_to_html:152`, les 3 fonctions de `file_validation_utils`, `text_utils.find_segment_with_markers:186` / `populate_text_segment:255` : 0 appelant hors tests.
5. **`cli_utils` : parseurs fossiles** — 5 parseurs actifs (`:35`, `:87`, `:116`, `:157`, `:246`) plus 1 commenté (`:82-86`). **2 sur 5** n'ont aucun appelant de production (`:35`, `:157` : test-only) ; les 3 autres sont appelés par `scripts/orchestration/run_extract_repair.py:48`, `scripts/orchestration/run_verify_extracts.py:46`, `scripts/reporting/generate_rhetorical_analysis_summaries.py:201`.
6. **Alias CLI déprécié sur une surface indexée** — `cli_utils.py:16` conserve, comme littéral d'un flag CLI de compatibilité déprécié (#2009), **le nom d'une source de dataset**. Le commentaire `:11-15` assume le choix (compatibilité de parsing, avertissement `DeprecationWarning`) et exporte la constante pour que les tests l'épinglent sans respeller le nom ailleurs ; le littéral n'en reste pas moins sur une surface indexée par GitHub. Le littéral **n'est pas reproduit ici**.
   **Mesure** : `scan_indexed_surfaces.py --text-file cli_utils.py` **le détecte** (`LEAK line 16, hits=1`) — le terme est un leader déjà présent dans les motifs partagés (`evaluation/leak_patterns.py`, `LEADER_PATTERNS`), donc toute **nouvelle** occurrence serait bloquée par le gate commit (#2014). Le cas est donc **gardé, pas toléré** : ce qui reste ouvert est la ligne préexistante elle-même, pas l'absence de garde. À ne pas confondre avec les noms **absents** des motifs (#2119).
7. **Façade à fuite de noms** — `file_utils.py:42-45` : quatre star-imports sans `__all__` côté feuilles. Tout nom public des quatre feuilles entre dans l'espace de noms `file_utils`, y compris `markdown` (paquet PyPI) et les constantes `PATH_TYPE_*` de `path_operations`. Fait mesuré : `test_file_utils.py:335` patche `file_utils.markdown.markdown`.
8. **Effets de bord et coût d'import** — importer `core.utils` (ou n'importe quelle feuille via `__init__`) tire `matplotlib.pyplot`, `pandas`, `httpx`, `cryptography`, `unidecode` ; `file_utils.py:26-35` ajoute un handler de logging et `:49-51` journalise à chaque import.
9. **Stub silencieusement vert** — `error_management.py` réussit toute récupération (`:85-86`, `:103-104`, `:119-120`) ; sa suite colocée n'asserte rien (0 `assert`, 22 `print`) et n'est pas collectée.
10. **Docstring morte** — `text_utils.py` place ses `import` et `logger = ...` (`:1-4`) **avant** le littéral docstring (`:5-11`) : ce bloc n'est donc pas `__doc__` du module, contrairement à tous ses voisins.
11. **Documentation contredisant le code** — `core/utils/tests/README.md:46` annonce « 27 fichiers .py » pour le paquet parent ; mesuré : **23 `.py`** à la racine (22 modules + `__init__.py`), +2 dans `tests/`. L'écart n'est expliqué par aucun fichier du dépôt.
12. **Modules non exportés** — `code_manipulation_utils`, `error_management`, `llm_completion_guard` ne figurent ni dans les `from . import` (`__init__.py:3-21`) ni dans `__all__` (`:23-43`) : atteignables seulement par chemin explicite, ce qui les rend invisibles à un inventaire dérivé de `dir(core.utils)`.

---

*Provenance : 2026-09-11, branche `docs/readme/2088-parents`. Méthode : comptage et résolution d'imports par `ast` (`utf-8-sig`, dédoublonnage par `(fichier, ligne)`, zones production/`tests/` séparées, `libs/` vendored exclu), ancres `fichier.py:ligne` vérifiées une par une par lecture ou `grep -n` ; lignes et tailles en octets mesurées sur le disque. Les chiffres issus d'un `grep` de nom nu ont été écartés au profit des importeurs résolus, le dépôt hébergeant des modules homonymes dans le paquet frère `argumentation_analysis/utils/`. Aucun fichier du dépôt modifié hors ce README.*
