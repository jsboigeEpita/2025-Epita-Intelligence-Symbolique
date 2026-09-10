# `pipelines/orchestration/execution/` — moteur d'orchestration non câblé

## Rôle et frontière

- `engine.py` contient **une seule fonction** : `analyze_text_orchestrated` (:81-145) — sélectionne une stratégie, dispatche, post-traite, sauvegarde la trace.
- `strategies.py` contient 6 fonctions async libres : `select_orchestration_strategy` (:83), `execute_hierarchical_full_orchestration` (:147), `execute_specialized_orchestration` (:200), `execute_fallback_orchestration` (:253), `execute_hybrid_orchestration` (:279), `select_specialized_orchestrator` (:317).

N'est **pas** le moteur d'exécution réel du dépôt : le pipeline unifié moderne (`argumentation_analysis/orchestration/unified_pipeline.py`) exécute ses phases via le `WorkflowExecutor` de `workflow_dsl.py` — zéro référence à ce sous-paquet. L'affirmation inverse de `docs/architecture/architecture_map.md:20` est périmée. Les docstrings décrivent des classes (`ExecutionEngine` engine.py:4-57, `SequentialStrategy`/`ParallelStrategy` strategies.py:20-38) **qui n'existent dans aucun fichier**.

## Composants publics

Voir Rôle — deux fichiers, 7 fonctions au total. La sélection AUTO_SELECT applique des heuristiques : INVESTIGATIVE/LOGICAL → `specialized_direct` (:124-129), texte > 1000 caractères → `hierarchical_full` (:130-132), COMPREHENSIVE + service_manager initialisé → `service_manager` (:133-139), défaut `hybrid`.

## Points d'entrée valides

**Aucun appelant production.** `analyze_text_orchestrated` n'est jamais appelé (grep exhaustif) ; ré-exporté comme `Engine` dans le `__init__.py` parent (:28), jamais consommé. `pipelines/unified_pipeline.py:82` hardcode `ORCHESTRATION_PIPELINE_AVAILABLE = False` avec un commentaire assumé (« le mode "orchestration" explicite reste refusé fail-loud ») et :308 lève `RuntimeError("Chemin d'orchestration non câblé.")`. Seul import externe : la garde `tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py:18` (réparation #2076 d'une chaîne d'imports morte).

## Amont / aval

- Amont : [`config/`](../config/README.md) (enums + `ExtendedOrchestrationConfig`, dont `save_orchestration_trace: bool = True`), [`analysis/`](../analysis/README.md) (post-traitement + traces).
- Aval : `save_orchestration_trace` écrit `results/orchestration_trace_{analysis_id}.json` (gitignoré), conditionné par `pipeline.config.save_orchestration_trace` (engine.py:138) — **seul artefact possible**.

## Statut d'intégration

**résiduel (non câblé)** — zéro consommateur, flag désactivé en dur, chemin refusé fail-loud. Les tests maintiennent la logique au vert, mais exclusivement sur mocks (`_make_pipeline` construit l'objet pipeline dont les méthodes appelées n'existent dans aucun fichier du dépôt).

## Artefacts et lecteurs

Voir Aval — un JSON de trace optionnel sous `results/` (gitignoré).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/orchestration/execution/test_execution_strategies.py tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py -v
```

32 tests, 6 classes (`TestSelectOrchestrationStrategy` :95, `TestSelectSpecializedOrchestrator` :286, `TestExecuteHierarchicalFull` :388, `TestExecuteSpecializedOrchestration` :464, `TestExecuteFallbackOrchestration` :580, `TestExecuteHybridOrchestration` :630) — 100 % mocks.

## Frères et parent

Parent : [`../README.md`](../README.md) — périmé sur 2 points (docstrings laissant croire aux classes vivantes ; `analysis_orchestrator.py`:19 inexistant). Frères : [`../analysis/`](../analysis/README.md), [`../config/`](../config/README.md), [`../core/`](../core/README.md), [`../orchestrators/specialized/`](../orchestrators/specialized/README.md).

## Limites connues

- **Dispatch silencieux** : `select_orchestration_strategy` peut retourner `strategic_only`/`tactical_coordination`/`operational_direct` (:105-107) et `service_manager` (:139), mais le dispatcheur engine.py:115-124 ne connaît que `hierarchical_full`/`specialized_direct`/`fallback`/else→hybrid — ces 4 valeurs tombent **silencieusement** dans `execute_hybrid_orchestration` ;
- type hint forward-ref `"UnifiedOrchestrationPipeline"` jamais importé (engine.py:82, strategies.py:84…) — inoffensif à l'exécution, casse `get_type_hints` ;
- docstrings fossiles décrivant des classes inexistantes (les exemples engine.py:42-43 importent des classes jamais écrites) ;
- paramètre `pipeline` = contrat implicite jamais implémenté (méthodes `_trace_orchestration`, `_execute_operational_tasks`… définies nulle part).
