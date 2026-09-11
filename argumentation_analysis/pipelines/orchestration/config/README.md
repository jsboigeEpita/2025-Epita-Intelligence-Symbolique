# `pipelines/orchestration/config/` — vocabulaire et configuration de l'orchestration

## Rôle et frontière

Le vocabulaire et la configuration de l'orchestration hiérarchique : 2 enums (11 modes, 8 types d'analyse) + 1 classe de config étendant `UnifiedAnalysisConfig`.

N'est **pas** un système de « définitions de pipelines = liste ordonnée de processeurs » (`../README.md:17`) — rien ici n'assemble de processeurs. Les enums `OrchestrationMode`/`AnalysisType` n'existent qu'ici dans le dépôt ; à ne pas confondre avec les modes CLI de `run_orchestration.py` ni le vocabulaire de [`orchestration/`](../../../orchestration/README.md) racine.

## Composants publics

- `OrchestrationMode` (`enums.py:7`) — Enum, 11 valeurs (`PIPELINE`:10 → `AUTO_SELECT`:20) ;
- `AnalysisType` (`enums.py:23`) — Enum, 8 valeurs (`COMPREHENSIVE`:26 → `CUSTOM`:33) ;
- `ExtendedOrchestrationConfig(UnifiedAnalysisConfig)` (`base_config.py:9`) — 13 attributs d'orchestration (:81-96), conversion str↔enum (:56-78), défaut `use_new_orchestrator=True` (:34). Mère : `UnifiedAnalysisConfig` (`pipelines/unified_text_analysis.py:91`).

## Points d'entrée valides

Production **intra-paquet uniquement** : `__init__.py:9-10` ; `execution/strategies.py:72-78` (`select_orchestration_strategy` :83 lit les enums) ; `core/service_manager.py:14`. **Zéro importeur production hors du paquet.**

Tests : `tests/unit/argumentation_analysis/pipelines/test_unified_pipelines.py:39-45` (usages :1196-1289) ; les enums sont aussi consommés par la suite collectée `tests/unit/argumentation_analysis/pipelines/orchestration/execution/test_execution_strategies.py:43`.

## Amont / aval

- Amont : `pipelines.unified_text_analysis.UnifiedAnalysisConfig`.
- Aval : `execution/strategies.py`, `core/service_manager.py`, le re-export `__init__` — tout le sous-système orphelin.

## Statut d'intégration

**spécialisé** — vocabulary-bearer du sous-système `pipelines/orchestration`, lui-même sans appelant externe. C'est le point le plus solide du paquet : les cardinalités des enums sont verrouillées par tests (`len(OrchestrationMode) == 11` :1211, `len(AnalysisType) == 8` :1226).

## Artefacts et lecteurs

Aucun — données pures.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/test_unified_pipelines.py -k "TestOrchestrationModeEnum or TestAnalysisTypeEnum or TestExtendedOrchestrationConfig" -v
```

(`TestOrchestrationModeEnum` :1196 / `test_count` :1210 ; `TestAnalysisTypeEnum` :1214 / :1225 ; `TestExtendedOrchestrationConfig` :1234 — `test_inherits` :1243, `test_mode_from_string` :1256, `test_default` :1236.)

## Frères et parent

Parent : [`../README.md`](../README.md). Frères : [`../analysis/`](../analysis/README.md), [`../core/`](../core/README.md), [`../execution/`](../execution/README.md).

## Limites connues

- `use_new_orchestrator` (:34, :96) « Active le nouveau MainOrchestrator » (:51) — `MainOrchestrator` n'est défini dans **aucun** fichier du dépôt et le flag n'est lu nulle part ;
- double représentation désynchronisable : `orchestration_mode` (str héritée) et `orchestration_mode_enum` (:74-78) coexistent sans garde de cohérence après construction ;
- sous-répertoire sans `__init__.py`.
