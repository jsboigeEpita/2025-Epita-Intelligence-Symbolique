# `plugin_framework/benchmarking/` — mesure du framework de plugins

## Rôle et frontière

Couche de mesure du sous-système `plugin_framework` : exécute une suite de requêtes contre une capacité de plugin **via** `OrchestrationService`, chronomètre chaque exécution, collecte des métriques personnalisées (ex. tokens) et agrège le tout en `BenchmarkSuiteResult`.

N'est **pas** :

- un mesureur de latence générique — l'homonyme `argumentation_analysis/services/benchmark_service.py:5` définit une classe `BenchmarkService` **distincte** (API `measure_latency`, dict `metrics`), testée par `tests/unit/argumentation_analysis/services/test_benchmark_service.py:4`. Deux classes `BenchmarkService` coexistent dans le dépôt avec des APIs incompatibles ;
- un découvreur de plugins — la découverte (et ses limites) vit dans `core/plugin_loader.py`, documenté dans le README de [`core/services/`](../core/services/README.md).

## Composants publics

Tout le contenu utile est `benchmark_service.py` (143 lignes ; `__init__.py` vide) :

- `BenchmarkService` (`benchmark_service.py:13`) ;
- `__init__(orchestration_service)` (:20) — reçoit le guichet [`core/services/orchestration_service.py`](../core/services/README.md) ;
- `record_metric(metric_type, value)` (:30) — métriques tamponnées, associées à la prochaine suite ;
- `run_suite(plugin_name, capability_name, requests)` (:48) — boucle : `OrchestrationRequest(mode="direct_plugin_call", target="plugin.capacité")`, chrono `perf_counter` autour de `handle_request`, statistiques avg/min/max **sur les réussites seules**, somme des métriques numériques, retour `BenchmarkSuiteResult`.

## Points d'entrée valides

- `plugin_framework/run_benchmark.py:15,62,88` — runner standalone, fonctionnel ;
- `plugin_framework/core/decorators.py:3-4` — le décorateur `track_tokens` (:8) appelle `record_metric`, mais **aucun plugin réel n'est décoré** par `track_tokens` (les seuls usages sont dans `tests/unit/argumentation_analysis/test_plugin_framework.py:674+`).

Hors de `plugin_framework/` : **aucun importeur** (api/, orchestration/, interface_web = 0 match).

## Amont / aval

- Amont : `core/contracts.py` (`BenchmarkResult` :91, `BenchmarkSuiteResult` :115, `OrchestrationRequest` :5) et `core/services/orchestration_service.py:7`.
- Aval : `run_benchmark.py`, `core/decorators.py`, les deux fichiers de tests cités ci-dessous.

## Statut d'intégration

**spécialisé** — instrument câblé uniquement à l'intérieur de son sous-système (runner dédié + décorateur lui-même sans consommateur), jamais invoqué par les chemins production (`orchestration/registry_setup.py`, api, workflows) ; en revanche testé unitairement et en intégration réelle.

## Artefacts et lecteurs

Tout en mémoire — sortie console `pprint` (`run_benchmark.py:111`), aucun rapport persisté. **Effet de bord** : `run_benchmark.py:34-44` écrit un plugin factice `hello_world/` **dans l'arborescence source** puis le supprime en fin d'exécution (:113-115) — un résidu est garanti si une exception survient entre les deux.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_plugin_framework.py::TestBenchmarkService tests/unit/argumentation_analysis/test_plugin_framework.py::TestTrackTokensDecorator tests/integration/triage/test_workflow_execution.py -v
```

- `TestBenchmarkService` (`test_plugin_framework.py:818`, 12 tests) — agrégation, métriques, stats sur réussites ;
- `TestTrackTokensDecorator` (:674, 7 tests) — décorateur seul (aucun plugin réel décoré) ;
- `tests/integration/triage/test_workflow_execution.py` (:43, classe :52) — chaîne réelle PluginLoader → OrchestrationService → BenchmarkService (3 tests :99, :165, :214).

## Frères et parent

- Parent `plugin_framework/` : **pas de README**.
- Seuls cousins dotés dans l'arbre : [`agents/README.md`](../agents/README.md) et [`core/plugins/README.md`](../core/plugins/README.md).

## Limites connues

- Deux classes `BenchmarkService` homonymes dans le dépôt (celle-ci :13 vs `services/benchmark_service.py:5`, APIs incompatibles) ;
- écriture runtime dans l'arborescence source par `run_benchmark.py` (voir Artefacts) ;
- association métrique↔exécution **par index** (`benchmark_service.py:92-94`, `if i < len(values)`) — fragile si le code décoré enregistre un nombre de `record_metric` différent du nombre d'exécutions.
