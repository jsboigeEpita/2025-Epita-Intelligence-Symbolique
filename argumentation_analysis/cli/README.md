# `cli/` — formateur de sortie terminal (Rich)

## Rôle et frontière

Le rendu **terminal** des résultats d'analyse : `output_formatter.py` (avec `__init__.py`), formateur Rich avec numérotation de sections pour cross-references.

N'est **pas** le CLI d'orchestration (`run_orchestration.py` est le runner ; ce module n'est que sa couche de rendu), ni le rendu HTML (voir [`visualization/`](../visualization/README.md)), ni le rapport maison de `scripts/validation/main.py:506`.

## Composants publics

- `render_spectacular_result(result, console=None)` (`output_formatter.py:67`) — rendu Rich complet du résultat spectacular ;
- `render_state_snapshot(state, console=None)` (`output_formatter.py:319`) — rendu d'un state snapshot de pipeline ;
- `SECTIONS` (:35-46) — numérotation des 10 sections (Extraction :36 … Narrative :45), `_section_ref` :51 génère les cross-references « see Section N » ;
- helpers : `_truncate` :59, `_count_non_empty` :63.

## Points d'entrée valides

Trois importeurs production :

- [`run_orchestration.py:276`](../run_orchestration.py) et `:686` — le rendu principal du CLI d'orchestration ;
- [`reporting/multi_format_exporter.py:321`](../reporting/multi_format_exporter.py) — export multi-format.

## Amont / aval

- Amont : dicts de résultats / state snapshots produits par le pipeline unifié et l'orchestrateur ; Rich (optionnel, garde `HAS_RICH` :30-32).
- Aval : console terminal uniquement — aucun fichier écrit par ce module.

## Statut d'intégration

**actif** — rendu consommé par le CLI d'orchestration (`run_orchestration.py`), l'exporteur multi-format, et les demos.

## Artefacts et lecteurs

Aucun — sortie console.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/test_rich_output_formatter.py -v
```

(suite dédiée : `tests/unit/argumentation_analysis/test_rich_output_formatter.py` — seul fichier de tests consommant le module, grep plein dépôt).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `cli/`. Frères : [`visualization/`](../visualization/README.md) (rendu PNG/HTML), [`reporting/`](../reporting/) (exports multi-format, sans README).

## Limites connues

- `SECTIONS` déclare `(5, "ATMS")` (:40) mais **aucune donnée `atms` n'est consommée** dans le module (grep vide) — la section est numérotée pour les cross-references sans branch de rendu propre : un résultat ATMS ne s'affiche pas ;
- le header docstring (:16) liste les sections promises — y compris ATMS — périmé par rapport au rendu réel.
