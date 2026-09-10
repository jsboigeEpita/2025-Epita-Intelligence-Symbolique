# `pipelines/orchestration/core/` — wrapper de délégation résiduel

## Rôle et frontière

Un seul fichier (`service_manager.py`) : un **wrapper de délégation de 2 fonctions** vers le vrai gestionnaire de services, l'homonyme racine [`orchestration/service_manager.py`](../../../orchestration/README.md) (`OrchestrationServiceManager` :147, `initialize()` :282, `analyze_text()` :479).

N'est **pas** le « core » contenant « les structures de données de base, comme les `PipelineData` » (`../README.md:15`) — `PipelineData` est introuvable dans tout le dépôt (grep 0 match). Ne pas confondre avec `plugin_framework/core/services/` (autre wrapper de guichet, documenté dans la vague feuilles #2088) non plus.

## Composants publics

- `initialize_service_manager` (`service_manager.py:34`) — construit le dict de config (:54-65), instancie + `initialize()` (:67-80), `None` si échec ;
- `execute_service_manager_orchestration` (:83) — délègue à `analyze_text` (:114-118), peuple `results["service_manager_results"]` (:120) ou le marque `unavailable` (:125-128).

Import défensif de l'homonyme racine en try/except avec `OrchestrationServiceManager = None` (:21-29).

## Points d'entrée valides

**Aucun.** Grep `pipelines.orchestration.core` sur tout le dépôt : 0 match. Le `__init__.py` parent importe `ServiceManager` **directement depuis** `argumentation_analysis.orchestration.service_manager` (:21-25), pas depuis `core/`. Zéro test également.

## Amont / aval

- Amont : `config/base_config` (:14-16), `paths.RESULTS_DIR/DATA_DIR` (:17), l'homonyme racine (:21-29).
- Aval : personne.

## Statut d'intégration

**résiduel intégral** — zéro importeur, zéro appelant, zéro test. Précédent direct documenté : `orchestration/core/communication.py` a été **supprimé dans #1574** pour exactement ce motif (« zero production callers… dead code pinned green by its own tests », `test_unified_pipelines.py:14-16`) ; ce module est dans la même situation, en pire (pas même de tests l'épinglant vert). Sort à trancher par le coordinateur — aucune suppression faite ici.

## Artefacts et lecteurs

Aucun direct — délègue au service manager racine.

## Tests représentatifs

Aucun test n'existe pour ce module (grep exhaustif).

## Frères et parent

Parent : [`../README.md`](../README.md) — décrit un `PipelineData` inexistant. Frères : [`../analysis/`](../analysis/README.md), [`../config/`](../config/README.md), [`../execution/`](../execution/README.md).

## Limites connues

- bug latent :132 — `results["service_manager_results"]["error"] = str(e)` : si l'exception lève **avant** l'assignation :120, la clé n'existe pas → `KeyError` dans le handler qui masque l'erreur d'origine ;
- dette assumée jamais résolue : « This import might be circular depending on the final structure, needs review » (:19-20) ;
- commentaire mort :122-123 — `self._trace_orchestration(...)` dans une fonction de module où `self` n'existe pas ;
- jamais touché par un commit fonctionnel depuis sa création (3 derniers touchers = 2 black + 1 cleanup).
