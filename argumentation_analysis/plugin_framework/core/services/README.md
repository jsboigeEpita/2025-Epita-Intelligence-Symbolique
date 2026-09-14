# `plugin_framework/core/services/` — guichet d'orchestration minimal

## Rôle et frontière

« Guichet de service unique » minimaliste du sous-système `plugin_framework` : route des `OrchestrationRequest` vers les instances de plugins d'un registre. **Seul** le mode `direct_plugin_call` est implémenté (`orchestration_service.py:32`) ; tout autre mode reçoit une réponse d'erreur explicite.

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
- hors `plugin_framework/` : aucun. Le runner `run_benchmark.py` a été retiré (#2099), le fossile `main.py` aussi (#2102 §1).

## Amont / aval

- Amont : `core/contracts.py` (`OrchestrationRequest` :5, `OrchestrationResponse` :29).
- Aval : `benchmarking/benchmark_service.py`, `tests/unit/argumentation_analysis/test_plugin_framework.py` et `tests/integration/triage/test_workflow_execution.py`.

## Statut d'intégration

**spécialisé** — utilisé uniquement au sein du circuit fermé plugin_framework (registre fourni par l'appelant → ce guichet → BenchmarkService). La production consomme les plugins réels **par import direct, sans passer par ce guichet** : `agents/tools/analysis/fallacy_family_analyzer.py:20,24` et `orchestration/fact_checking_orchestrator.py:28,31` importent `taxonomy_explorer` et `external_verification` directement.

Les deux chargeurs qui ne pouvaient pas peupler le registre avec les plugins réels (préfixe `src.` mort pour l'un, manifestes JSON invisibles pour l'autre) ont été **retirés** avec leur mécanisme (#2099) — voir le README parent.

## Artefacts et lecteurs

Aucun — objet purement en mémoire (dict registre), n'écrit rien.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_plugin_framework.py::TestOrchestrationService tests/integration/triage/test_workflow_execution.py -v
```

- `TestOrchestrationService` (`test_plugin_framework.py:465`, 9 tests) — routing, erreurs registre/capacité, cibles malformées, exceptions plugin ;
- intégration (`test_workflow_execution.py`, registre construit directement) — chaîne réelle avec plugins factices.

## Frères et parent

- Parent `core/` : **pas de README**.
- Frère : [`core/plugins/README.md`](../plugins/README.md) — décrit le mécanisme manifest JSON, incompatible avec les `plugin.yaml` réels (drift).

## Limites connues

- pas de `__init__.py` dans `core/services/` ;
- un `target` contenant plusieurs points casse le split (:41) — comportement couvert comme erreur attendue par les tests (:524).

Historique résolu : le fossile `main.py` (≥2 générations d'API en retard, 9 appels
inertes) a été retiré (#2102 §1) ; le mode fantôme `workflow_execution` (déclaré au
contrat, jamais implémenté, réponse d'erreur systématique) a été retiré du Literal
(#2102 §5) — sa construction est rejetée par la validation Pydantic, le guichet ne
porte plus de branche morte.
