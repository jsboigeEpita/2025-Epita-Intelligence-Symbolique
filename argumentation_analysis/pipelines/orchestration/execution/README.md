# `pipelines/orchestration/execution/` — stratégies résiduelles

## Rôle et frontière

Le répertoire conserve uniquement `strategies.py` : six fonctions async libres,
sans classe ni moteur :

- `select_orchestration_strategy` ;
- `execute_hierarchical_full_orchestration` ;
- `execute_specialized_orchestration` ;
- `execute_fallback_orchestration` ;
- `execute_hybrid_orchestration` ;
- `select_specialized_orchestrator`.

L'ancien `engine.py` a été retiré dans #2113 avec ses helpers `analysis/`, ses
réexports et son test de dispatch. Il n'avait aucun appelant production et le
chemin amont est refusé explicitement par `pipelines/unified_pipeline.py`.

## Dépendances

Les stratégies consomment [`config/`](../config/README.md) pour les enums et
`ExtendedOrchestrationConfig`. Elles ne produisent aucun artefact sur disque.
Leur paramètre `pipeline` reste un contrat implicite fourni uniquement par les
mocks de tests : plusieurs méthodes appelées ne sont définies dans aucun code de
production.

## Dispatch accepté

`DISPATCHABLE_STRATEGIES` contient exactement :

- `hierarchical_full` ;
- `specialized_direct` ;
- `fallback` ;
- `hybrid`.

Le sélecteur refuse par `ValueError` les noms hors de cet ensemble (#2109,
#2205), sans repli silencieux vers l'hybride.

## Tests

```bash
pytest tests/unit/argumentation_analysis/pipelines/orchestration/execution/test_execution_strategies.py -v
```

Ces tests valident la sélection et les quatre exécuteurs sur des pipelines
mockés. Ils ne prouvent pas l'existence d'un chemin production.

## Frères et parent

Parent : [`../README.md`](../README.md). Frère :
[`../config/`](../config/README.md). Les anciens répertoires `analysis/`,
`core/` et `orchestrators/specialized/` ont été retirés (#2113, #2111).
