# `pipelines/orchestration/` — un sous-système d'orchestration non câblé

## Rôle et frontière

Ancien moteur d'orchestration de `pipelines/` : il **choisit une stratégie**
(hiérarchique / spécialisée / fallback / hybride), la dispatche, post-traite le
résultat et écrit une trace. **11 fichiers `.py`**, cinq sous-répertoires.

N'est **pas** le moteur d'orchestration vivant du dépôt — il ne l'a jamais été :

- le pipeline unifié moderne (`argumentation_analysis/orchestration/unified_pipeline.py`)
  exécute ses phases via le **`WorkflowExecutor`** de `orchestration/workflow_dsl.py`
  (:356), instancié `orchestration/unified_pipeline.py:306` — **zéro référence** à ce paquet ;
- le pipeline unifié de `pipelines/` (`argumentation_analysis/pipelines/unified_pipeline.py`)
  **refuse** ce chemin : `ORCHESTRATION_PIPELINE_AVAILABLE = False` (:82) et
  `raise RuntimeError("Chemin d'orchestration non câblé.")` (:308).

**Zéro importeur de production** : hors du paquet et de ses tests, aucune ligne du
dépôt n'importe `pipelines.orchestration`.

## Structure — mesurée sur le code, pas sur l'intention

| Sous-répertoire | Ce qu'il contient réellement | Statut |
|---|---|---|
| [`config/`](config/README.md) | 2 enums (`OrchestrationMode` 11 valeurs, `AnalysisType` 8) + `ExtendedOrchestrationConfig` (`enums.py` 33 l., `base_config.py` 96 l.) | vocabulary-bearer — le point le plus solide |
| [`execution/`](execution/README.md) | `engine.py` (121 l.) : **1 fonction libre** `analyze_text_orchestrated` ; `strategies.py` (337 l.) : **6 fonctions async libres**. **Zéro classe.** | résiduel, non câblé |
| [`analysis/`](analysis/README.md) | 3 modules, **6 fonctions libres** (post-traitement, tâches opérationnelles simulées, traçage) | résiduel / compatibilité |
| [`core/`](core/README.md) | `service_manager.py` (134 l.) : **1 wrapper de délégation de 2 fonctions** | résiduel intégral (0 importeur, 0 test) |
| ~~`orchestrators/specialized/`~~ | **retiré (#2111)** : 2 wrappers de compatibilité, 0 instanciation prod+test | — |

`__init__.py` (:63) ré-exporte ces noms — dont `Engine = analyze_text_orchestrated`
(:28), jamais consommé. Le paquet reste au vert par ses **seuls tests** (mocks, plus
la garde d'import `tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py`) :
la garde le fait *exister*, elle ne prouve pas qu'il *sert*.

## Ce que le sélecteur peut produire, et ce que le dispatch accepte

`select_orchestration_strategy` calcule des **noms** de stratégie, mais le moteur
n'en exécute que quatre (`STRATEGY_EXECUTORS`, `engine.py:45` ;
`DISPATCHABLE_STRATEGIES`, `strategies.py:45`) : `hierarchical_full`,
`specialized_direct`, `fallback`, `hybrid`. Tout autre nom **lève `ValueError`**
(`engine.py:94-99`, `strategies.py:140-146`) — refus volontaire, qui remplace un
repli silencieux sur l'hybride (#2109). Six valeurs sont dans ce cas :
`strategic_only`, `tactical_coordination`, `operational_direct`, `service_manager`,
`real`, `conversation`.

## Correction (#2110)

Les versions antérieures de ce README annonçaient, comme s'ils existaient (les
renvois de ligne sont ceux de la version antérieure) :
des `PipelineData` dans `core/` (:15), une « liste ordonnée de processeurs » dans
`config/` (:17), des processeurs d'extraction/normalisation dans `analysis/` (:16),
des stratégies dans `execution/` (:18) et un `analysis_orchestrator.py` dans
`orchestrators/` (:19). **Aucun n'existe** — `PipelineData` a 0 occurrence dans le
dépôt, et le seul « orchestrateur » de `orchestrators/` est un couple de wrappers.
Le README est réécrit sur le code ; les docstrings qui décrivaient les mêmes
symboles fantômes (`ExecutionEngine`, `SequentialStrategy`…) sont retirées. Même
traitement pour `analysis/processors.py` et `analysis/post_processors.py`, dont
les docstrings annonçaient **10 classes de processeurs** (`ExtractProcessor`,
`ResultFormattingProcessor`…) : aucune n'existe.

## Frères et parent

- **À ne pas confondre** avec [`orchestration/`](../../../orchestration/README.md)
  racine — le cerveau réel du système (`unified_pipeline.py`, `workflow_dsl.py`,
  `router.py`, `capability_registry.py`) ;
- **Parent** : `pipelines/` ; **voisins** : `pipelines/analysis_pipeline.py`,
  `pipelines/unified_pipeline.py`.

## Limites connues

- le contrat `pipeline` est fantôme : `_trace_orchestration`,
  `_execute_operational_tasks`, `_synthesize_hierarchical_results` ne sont
  définies dans aucun fichier du dépôt — seulement sur les mocks des tests ;
- le type `"UnifiedOrchestrationPipeline"` en forward-ref n'est jamais importé
  (`engine.py:60`, `strategies.py:51`) — inoffensif à l'exécution, casse
  `get_type_hints` ;
- sous-répertoires sans `__init__.py` (packages de namespace implicites) ;
- deux surfaces décrivent encore ce sous-système comme vivant ou à repli
  silencieux, et sont suivies séparément : `execution/README.md:45` → #2223 ;
  `orchestration/README.md:20-22` → #2224.
