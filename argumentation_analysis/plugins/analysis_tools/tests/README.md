# `plugins/analysis_tools/tests/` — suite de tests in-package, NON collectée par pytest

## Rôle et frontière

3 fichiers de tests + `__init__.py` (0 octet) : `test_enhanced_complex_fallacy_analyzer.py` (187 l., 10 `def test_`), `test_enhanced_contextual_fallacy_analyzer.py` (318 l., 10), `test_enhanced_fallacy_severity_evaluator.py` (271 l., 11) — **31 `def test_`** ciblant [`../logic/`](../logic/README.md) via imports relatifs `..logic.*` (:23/:17/:24). Arrivés avec la consolidation #34 (commit `df031b345`).

## Composants publics

Aucun (répertoire de tests). Rien ne l'importe.

## Points d'entrée valides

**Aucun — et pytest ne collecte pas ce répertoire par défaut** : `pytest.ini:2` (`testpaths = tests`) borne la collecte au répertoire racine `tests/` (même verdict documenté pour le cas analogue `core/utils/tests/`). Exécution possible uniquement par chemin explicite :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest argumentation_analysis/plugins/analysis_tools/tests/ -v
```

## Amont / aval

- Amont : [`../logic/`](../logic/README.md).
- Aval : personne.

## Statut d'intégration

**résiduel (tests non exécutés)** — la suite canonique équivalente vit dans `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/` (4 fichiers, 180 `def test_`, collectée par défaut). Chevauchement partiel des cibles (severity, contextual, complex) mais fichiers **non identiques**. Sort à trancher par le coordinateur : fusionner ce qui manque à la canonique puis retirer, ou assumer la duplication.

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

Ils en **sont** — mais ne tournent pas dans CI ni en local par défaut (cf. Points d'entrée). Aucun test de ces tests.

## Frères et parent

Parent : `plugins/analysis_tools/` (sans README — parents bloqués #2088). Cible : [`../logic/`](../logic/README.md). Canonique : `tests/unit/argumentation_analysis/plugins/analysis_tools/logic/` (décrite dans la fiche logic).

## Limites connues

- docstrings fossiles citant le chemin pré-consolidation `agents.tools.analysis.enhanced.*` (p.ex. `test_enhanced_fallacy_severity_evaluator.py:6`) ;
- `sys`/`os` importés avec manipulation `sys.path` (:8-9) — style pré-restructuration ;
- 31 tests que rien n'exécute = poids mort qui donne une impression de couverture (famille #1019).
