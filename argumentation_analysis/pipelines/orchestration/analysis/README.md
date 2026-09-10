# `pipelines/orchestration/analysis/` — assistants d'un pipeline hiérarchique disparu

## Rôle et frontière

Trois modules de **fonctions libres** assistant un pipeline d'orchestration hiérarchique qui n'existe plus : fabrication de résultats de tâches opérationnelles, heuristique de synthèse, recommandations cosmétiques, traçage JSON.

N'est **pas** ce que le README parent annonce (`../README.md:16` — « briques de traitement atomiques… normaliser le texte, extraire les arguments ») : aucun processeur d'extraction/normalisation n'a jamais été écrit ici (les docstrings de `processors.py:21-36` et `post_processors.py:19-35` annoncent 5 processeurs chacun — `ExtractProcessor`, `ResultFormattingProcessor`… — **aucun n'existe**, grep 0 match). À distinguer de `pipelines/analysis_pipeline.py` et de [`orchestration/`](../../../orchestration/README.md) racine.

## Composants publics

| Fonction | Ligne | Ce qu'elle fait réellement |
|---|---|---|
| `post_process_orchestration_results` | `post_processors.py:63` | injecte `results["recommendations"]` (seuils `overall_score > 0.7`, :68-86) + `communication_log` (:88-89) |
| `execute_operational_tasks` | `processors.py:59` | fabrique **jusqu'à 5 tâches factices** `"Résultat de la tâche opérationnelle {i+1}"`, `execution_time: 0.5` codé dur (:70-78) |
| `synthesize_hierarchical_results` | `processors.py:93` | moyenne de 3 scores heuristiques (:104-113) |
| `trace_orchestration` | `traces.py:23` | append une entrée horodatée dans `pipeline.orchestration_trace` (:27-33) |
| `get_communication_log` | `traces.py:36` | `middleware.get_message_history(limit=50)` avec repli `[]` (:40-45) |
| `save_orchestration_trace` | `traces.py:48` | écrit le JSON de trace (:53-73) |

## Points d'entrée valides

- `__init__.py` parent :31-36 (re-export) ;
- `execution/engine.py:73-74`, appels réels :126 (`post_process_orchestration_results`) et :139 (`save_orchestration_trace`) — **mais engine.py lui-même n'a aucun appelant production** (voir [`../execution/`](../execution/README.md)) ;
- hors du paquet : **zéro importeur production** (grep `pipelines.orchestration.analysis` : tests uniquement).

Attention : `execution/strategies.py:179,190` appellent `pipeline._execute_operational_tasks` / `._synthesize_hierarchical_results` — **méthodes du pipeline, pas ces fonctions libres**, et ces méthodes ne sont définies dans aucun fichier du dépôt (elles n'existent que sur les mocks des tests).

## Amont / aval

- Amont : stdlib + `argumentation_analysis.paths.RESULTS_DIR` (`traces.py:18`).
- Aval : `execution/engine.py` seul — lui-même orphelin.

## Statut d'intégration

- `post_process_orchestration_results`, `save_orchestration_trace` : **compatibilité** — appelées par engine.py, dont la chaîne ne vit qu'en test.
- `execute_operational_tasks`, `synthesize_hierarchical_results`, `trace_orchestration`, `get_communication_log` : **résiduel** — aucun appelant nulle part (les stratégies utilisent les méthodes-fantômes du pipeline) ; survivent via le re-export `__init__.py` et leurs tests.

Le paquet parent tout entier est sans importeur production hors de lui-même ; toutes les signatures typent `"UnifiedOrchestrationPipeline"`, **classe définie nulle part dans le dépôt** (`engine.py:76` la déclare obsolète).

## Artefacts et lecteurs

`save_orchestration_trace` écrit `results/orchestration_trace_{analysis_id}.json` (`traces.py:53`) — sous `results/`, gitignoré. Aucun autre effet de bord.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/test_unified_pipelines.py -k "TestPostProcessResults or TestExecuteOperationalTasks or TestSynthesizeHierarchical or TestSaveTrace" -v
```

(`TestPostProcessResults` :1298, `TestExecuteOperationalTasks` :1353, `TestSynthesizeHierarchical` :1376, `TestSaveTrace` :1455 — dans un fichier gardé par `test_import_guard_2076.py:17-18`, réparation #2076/#2077 d'une chaîne d'imports morts.)

## Frères et parent

Parent : [`../README.md`](../README.md) — décrit des processeurs qui n'ont jamais existé ici. Frères : [`../config/`](../config/README.md), [`../core/`](../core/README.md), [`../execution/`](../execution/README.md) (documentés dans ce même lot).

## Limites connues

- docstrings annonçant 10 processeurs inexistants (2 fichiers) ;
- `execute_operational_tasks` = simulation présentée comme exécution (résultats factices) ;
- paramètre `pipeline` jamais utilisé dans les 2 fonctions de `processors.py` — contrat fantôme ;
- `post_processors.py:89` appelle `pipeline._get_communication_log()` — méthode définie nulle part (la fonction libre `traces.py:36` est distincte) ;
- exemples de docstring de `engine.py:42-43` et `strategies.py:48-52` importent des classes jamais écrites ;
- sous-répertoire sans `__init__.py` (namespace implicite).
