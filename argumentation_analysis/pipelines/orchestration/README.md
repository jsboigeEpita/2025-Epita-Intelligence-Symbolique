# `pipelines/orchestration/` — vocabulaire et stratégies résiduelles

## Rôle et frontière

Ce sous-paquet conserve le vocabulaire de configuration et les stratégies async
du chemin historique de `pipelines/`. Il ne contient plus de moteur d'exécution :
la chaîne orpheline `analysis/` + `execution/engine.py` a été retirée dans #2113.

Ce n'est pas le moteur vivant du dépôt :

- `argumentation_analysis/orchestration/unified_pipeline.py` exécute les phases
  avec le `WorkflowExecutor` de `orchestration/workflow_dsl.py` ;
- `argumentation_analysis/pipelines/unified_pipeline.py` refuse explicitement
  l'ancien chemin (`ORCHESTRATION_PIPELINE_AVAILABLE = False`) ;
- aucun code de production hors du paquet n'importe cette surface résiduelle.

## Structure mesurée

| Sous-répertoire | Contenu conservé | Statut |
|---|---|---|
| [`config/`](config/README.md) | `OrchestrationMode`, `AnalysisType`, `ExtendedOrchestrationConfig` | vocabulaire consommé par les stratégies et leurs tests |
| [`execution/`](execution/README.md) | `strategies.py` : sélection + quatre exécuteurs async + sélection spécialisée | résiduel, sans moteur ni appelant production |
| ~~`analysis/`~~ | retiré (#2113) : tâches factices, post-traitement et traces de l'engine orphelin | — |
| ~~`core/`~~ | retiré (#2113) : wrapper de délégation, 0 importeur, 0 test | — |
| ~~`orchestrators/specialized/`~~ | retiré (#2111) : wrappers sans instanciation | — |

Le `__init__.py` ne réexporte plus l'ancien alias `Engine` ni les helpers
d'analyse. Il conserve uniquement la configuration et les alias historiques
`Middleware` / `ServiceManager`.

## Sélection de stratégie

`select_orchestration_strategy` calcule puis valide les quatre noms acceptés par
`DISPATCHABLE_STRATEGIES` : `hierarchical_full`, `specialized_direct`,
`fallback`, `hybrid`. Les autres modes calculables (`strategic_only`,
`tactical_coordination`, `operational_direct`, `service_manager`, `real`,
`conversation`) lèvent `ValueError` plutôt que de retomber silencieusement sur
l'hybride (#2109, #2205).

## Historique des corrections

#2110 a retiré les descriptions de classes et processeurs qui n'ont jamais
existé. #2111 a retiré les wrappers spécialisés sans consommateur. #2113 a
retiré la coquille `operational/`, le wrapper `core/`, le flag
`use_new_orchestrator`, puis la chaîne morte `analysis/` + engine + tests et
réexports associés.

## Frères et parent

- à ne pas confondre avec [`orchestration/`](../../../orchestration/README.md),
  le système vivant (`unified_pipeline.py`, `workflow_dsl.py`, registre de
  capabilities) ;
- parent : [`pipelines/`](../README.md).

## Limites connues

- le paramètre `pipeline` des stratégies reste un contrat implicite dont les
  méthodes (`_trace_orchestration`, `_execute_operational_tasks`,
  `_synthesize_hierarchical_results`) n'existent que sur les mocks de tests ;
- le type forward-ref `UnifiedOrchestrationPipeline` n'est pas importé ;
- `execution/` et `config/` sont des packages de namespace implicites.
