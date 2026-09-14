# `plugin_framework/core/services/` — guichet d'orchestration minimal

## Rôle et frontière

« Guichet de service unique » minimaliste du sous-système `plugin_framework` : route des `OrchestrationRequest` vers les instances de plugins d'un registre. **Seul** le mode `direct_plugin_call` est implémenté (`orchestration_service.py:30-36`) ; tout autre mode reçoit une réponse d'erreur explicite.

N'est **pas** (trois homonymes à ne pas confondre) :

- l'orchestration métier — `argumentation_analysis/agents/core/orchestration_service.py:41` est un autre `OrchestrationService` (singleton), importé par `api/main.py:4-5` ;
- `argumentation_analysis/orchestration/service_manager.py:147` (`OrchestrationServiceManager`) ;
- le chargeur de plugins — `core/plugin_loader.py` (dont les limites sont documentées ci-dessous).

Contenu : `orchestration_service.py` seul (66 lignes), **sans `__init__.py`** (namespace package implicite).

## Composants publics

`OrchestrationService` (`orchestration_service.py:8`) :

- `__init__(plugin_registry: Dict[str, Any])` (:14) — dict {nom → instance} **fourni par l'appelant** (les mécanismes de découverte sont retirés, #2099 ; l'intégration le construit directement depuis les manifestes des fixtures) ;
- `handle_request(request)` (:24) — routage par `request.mode` ;
- `_handle_direct_plugin_call` (:38) — split de `target` sur `"."` (:45), lookup registre (:50), `getattr` (:57), invocation `function(**request.payload)` (:60), toute exception attrapée → `OrchestrationResponse(status="error")` (:65).

## Points d'entrée valides

- `benchmarking/benchmark_service.py:7,81` — fonctionnel (voir [`benchmarking/`](../../benchmarking/README.md)) ;
- `plugin_framework/main.py:11,44,52` — **fossile, ne peut pas s'exécuter** (voir Limites) ; depuis #2099 son import du loader retiré échoue bruyamment ;
- hors `plugin_framework/` : aucun. Le runner `run_benchmark.py` a été retiré (#2099).

## Amont / aval

- Amont : `core/contracts.py` (`OrchestrationRequest` :5, `OrchestrationResponse` :29).
- Aval : `benchmarking/benchmark_service.py`, `main.py` (mort), `tests/unit/argumentation_analysis/test_plugin_framework.py` et `tests/integration/triage/test_workflow_execution.py`.

## Statut d'intégration

**spécialisé** — utilisé uniquement au sein du circuit fermé plugin_framework (registre fourni par l'appelant → ce guichet → BenchmarkService). La production consomme les plugins réels **par import direct, sans passer par ce guichet** : `agents/tools/analysis/fallacy_family_analyzer.py:20,24` et `orchestration/fact_checking_orchestrator.py:28,31` importent `taxonomy_explorer` et `external_verification` directement.

Les deux chargeurs qui ne pouvaient pas peupler le registre avec les plugins réels (préfixe `src.` mort pour l'un, manifestes JSON invisibles pour l'autre) ont été **retirés** avec leur mécanisme (#2099) — voir le README parent.

## Artefacts et lecteurs

Aucun — objet purement en mémoire (dict registre), n'écrit rien.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_plugin_framework.py::TestOrchestrationService tests/integration/triage/test_workflow_execution.py -v
```

- `TestOrchestrationService` (`test_plugin_framework.py:469`, 10 tests) — routing, erreurs registre/capacité, cibles malformées, exceptions plugin ;
- intégration (`test_workflow_execution.py`, registre construit directement) — chaîne réelle avec plugins factices.

## Frères et parent

- Parent `core/` : **pas de README**.
- Frère : [`core/plugins/README.md`](../plugins/README.md) — décrit le mécanisme manifest JSON, incompatible avec les `plugin.yaml` réels (drift).

## Limites connues

- `plugin_framework/main.py` est désynchronisé d'au moins deux générations d'API et crasherait immédiatement : `PluginLoader(plugin_dirs=)` + `discover_plugins()`/`load_plugins()`/`loader.plugins` (API inexistantes), `OrchestrationService(plugin_loader=loader)` (paramètre réel `plugin_registry` :14), `execute_request` (méthode réelle `handle_request` :24), `OrchestrationRequest(plugin_name=, inputs=)` (champs réels `mode/target/payload`), `response.request_id`/`.outputs` (champs réels `status/result/error_message`) ;
- pas de `__init__.py` dans `core/services/` ;
- mode `workflow_execution` déclaré au contrat (`contracts.py:11`) mais jamais implémenté — réponse d'erreur systématique ;
- un `target` contenant plusieurs points casse le split (:45) — comportement couvert comme erreur attendue par les tests (:627-634).
