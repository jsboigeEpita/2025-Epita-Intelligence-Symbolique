# `core/interfaces/` — contrats abstraits de la composabilité Lego

## Rôle et frontière

Contrats abstraits (ABC) pour la composabilité : les adapters (`argumentation_analysis/adapters/`) les **implémentent**, les pipelines/plugins les consomment en typage. Sans `__init__.py` (namespace package implicite).

N'est **pas** les services eux-mêmes (`core/llm_service.py`), ni les adapters, ni les plugins SK.

## Composants publics

| Module | Contrat | Méthodes abstraites |
|---|---|---|
| `fallacy_detector.py:4` | `AbstractFallacyDetector` | `detect(text) -> dict` (:5) |
| `analysis_service.py:20` | `AbstractAnalysisService` | `analyze_text` (async, :30), `is_available` (:47), `get_status_details` (:52) |

## Points d'entrée valides — asymétrie totale entre les deux contrats

**`fallacy_detector` : 5 importeurs production + 2 implémentations** :

- `plugins/analysis_tools/plugin.py:11` (typage du paramètre `fallacy_detector` du plugin) et `plugins/analysis_tools/logic/contextual_fallacy_analyzer.py:38` ;
- `pipelines/advanced_rhetoric.py:16` ;
- `adapters/french_fallacy_adapter.py:28` — **implémentation** `FrenchFallacyAdapter(AbstractFallacyDetector)` ;
- `adapters/contextual_fallacy_detector_adapter.py:1` — 2e implémentation.

L'aval de ces implémentations est réel : `AnalysisToolsPlugin` est instancié dans `pipelines/unified_text_analysis.py` et `orchestration/hierarchical/operational/adapters/rhetorical_tools_adapter.py`.

**`analysis_service` : zéro importeur, zéro implémenteur** — les seules mentions sont des docstrings et une doc de skill. La docstring du module **promettait** des « futures integrations via le CapabilityRegistry » jamais advenues (né de #35 « Phase 0+1 Lego foundations ») : depuis le 2026-09-14 (#2105) elle **dit la vérité mesurée** (contrat non adopté, conservé comme point d'extension), et `adapters/__init__.py:8` ne le cite plus comme interface implémentée. La surface hors dépôt qui le cite encore (`.claude/skills/integrate-component/SKILL.md`) est nommée pour le coordinateur.

## Amont / aval

- Amont : rien (ABC purs).
- Aval (via `fallacy_detector`) : `adapters/`, `plugins/analysis_tools/`, `pipelines/advanced_rhetoric.py`.

## Statut d'intégration

- `fallacy_detector.py` : **actif** — 5 importeurs production, 2 implémentations vivantes, tests qui assertent `isinstance(adapter, AbstractFallacyDetector)`.
- `analysis_service.py` : **résiduel, désormais marqué** — contrat orphelin, jamais consommé ; sa docstring le déclare explicitement depuis le 2026-09-14 (#2105) au lieu de promettre une intégration future.

## Artefacts et lecteurs

Aucun (ABC purs).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/adapters/test_french_fallacy_adapter.py tests/unit/argumentation_analysis/adapters/test_contextual_fallacy_detector_adapter.py -v
```

`test_contextual_fallacy_detector_adapter.py:13` importe le contrat ; le test :32 asserte l'`isinstance` directement sur `AbstractFallacyDetector`.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `interfaces/`. Frère avec README : `communication/`.

## Limites connues

- `AbstractFallacyDetector.detect` documenté « returns a dictionary containing the detected fallacies » sans schéma défini — chaque implémentation fixe le sien (l'adapter français documente sa conversion) ;
- `analysis_service.py:30` méthode async dans un ABC jamais implémenté ;
- déplacer `fallacy_detector.py` casserait 5 imports production — le contrat ne vit que par ses implémentations côté `adapters/`.
