# `pipelines/orchestration/execution/` — moteur d'orchestration non câblé

## Rôle et frontière

- `engine.py` contient **une seule fonction** : `analyze_text_orchestrated` (:59-121) — sélectionne une stratégie, dispatche, post-traite, sauvegarde la trace.
- `strategies.py` contient 6 fonctions async libres : `select_orchestration_strategy` (:50), `execute_hierarchical_full_orchestration` (:150), `execute_specialized_orchestration` (:203), `execute_fallback_orchestration` (:256), `execute_hybrid_orchestration` (:282), `select_specialized_orchestrator` (:320).

N'est **pas** le moteur d'exécution réel du dépôt : le pipeline unifié moderne (`argumentation_analysis/orchestration/unified_pipeline.py`) exécute ses phases via le `WorkflowExecutor` de `workflow_dsl.py` — zéro référence à ce sous-paquet. L'affirmation inverse de `docs/architecture/architecture_map.md:20` est **corrigée** (#2110). Les docstrings décrivaient des classes (`ExecutionEngine`, `SequentialStrategy`/`ParallelStrategy`) **qui n'existent dans aucun fichier** — elles sont retirées (#2110).

## Composants publics

Voir Rôle — deux fichiers, 7 fonctions au total. La sélection AUTO_SELECT applique des heuristiques : INVESTIGATIVE/LOGICAL → `specialized_direct` (:120-125), texte > 1000 caractères → `hierarchical_full` (:126-128), COMPREHENSIVE + service_manager initialisé → `service_manager` (:129-135), défaut `hybrid`.

## Points d'entrée valides

**Aucun appelant production.** `analyze_text_orchestrated` n'est jamais appelé (grep exhaustif) ; ré-exporté comme `Engine` dans le `__init__.py` parent (:28), jamais consommé. `pipelines/unified_pipeline.py:82` hardcode `ORCHESTRATION_PIPELINE_AVAILABLE = False` avec un commentaire assumé (« le mode "orchestration" explicite reste refusé fail-loud ») et :308 lève `RuntimeError("Chemin d'orchestration non câblé.")`. Seul import externe : la garde `tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py:18` (réparation #2076 d'une chaîne d'imports morte).

## Amont / aval

- Amont : [`config/`](../config/README.md) (enums + `ExtendedOrchestrationConfig`, dont `save_orchestration_trace: bool = True`), [`analysis/`](../analysis/README.md) (post-traitement + traces).
- Aval : `save_orchestration_trace` écrit `results/orchestration_trace_{analysis_id}.json` (gitignoré), conditionné par `pipeline.config.save_orchestration_trace` (engine.py:114) — **seul artefact possible**.

## Statut d'intégration

**résiduel (non câblé)** — zéro consommateur, flag désactivé en dur, chemin refusé fail-loud. Les tests maintiennent la logique au vert, mais exclusivement sur mocks (`_make_pipeline` construit l'objet pipeline dont les méthodes appelées n'existent dans aucun fichier du dépôt).

## Artefacts et lecteurs

Voir Aval — un JSON de trace optionnel sous `results/` (gitignoré).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/orchestration/execution/test_execution_strategies.py tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py -v
```

**42 tests exécutés (36 + 6 gardes de cohérence #2109)** : `test_execution_strategies.py`, 6 classes (`TestSelectOrchestrationStrategy` :96, `TestSelectSpecializedOrchestrator` :368, `TestExecuteHierarchicalFull` :470, `TestExecuteSpecializedOrchestration` :546, `TestExecuteFallbackOrchestration` :662, `TestExecuteHybridOrchestration` :712) — 100 % mocks — plus `test_strategy_dispatch_coherence_2109.py` (table `STRATEGY_EXECUTORS` ↔ `DISPATCHABLE_STRATEGIES`).

## Frères et parent

Parent : [`../README.md`](../README.md) — **corrigé (#2110)** : plus d'`analysis_orchestrator.py` annoncé, plus de docstrings laissant croire aux classes vivantes. Frères : [`../analysis/`](../analysis/README.md), [`../config/`](../config/README.md), [`../core/`](../core/README.md). L'ancien frère `orchestrators/specialized/` a été retiré (#2111).

## Limites connues

- **Dispatch fail-loud (#2109, #2205)** — le moteur dispatche par **table explicite** `STRATEGY_EXECUTORS` (engine.py:45) et refuse toute stratégie absente de la table par `ValueError` (engine.py:95) ; `strategies.py` porte la garde symétrique : `DISPATCHABLE_STRATEGIES` = les 4 noms dispatchables (strategies.py:45), refus à strategies.py:140-144, et un mode d'orchestration absent de `mode_strategy_map` lève lui aussi (:104-110, #2205). **Aucune valeur ne retombe sur l'hybride** : `strategic_only`/`tactical_coordination`/`operational_direct`/`service_manager` (calculables par le sélecteur AUTO_SELECT, :121-135) comme `real`/`conversation` (mappés :101-102) lèvent tous. La cohérence table↔garde est testée (`test_strategy_dispatch_coherence_2109.py`, 6 tests). L'ancienne description d'un « dispatch silencieux » vers l'hybride décrivait le comportement pré-#2109 — elle est retirée ;
- type hint forward-ref `"UnifiedOrchestrationPipeline"` jamais importé (engine.py:60, strategies.py:51…) — inoffensif à l'exécution, casse `get_type_hints` ;
- paramètre `pipeline` = contrat implicite jamais implémenté (méthodes `_trace_orchestration`, `_execute_operational_tasks`… définies nulle part).
