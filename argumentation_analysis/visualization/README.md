# `visualization/` — rapports HTML

## Rôle et frontière

Génération de sorties visuelles à partir d'un état d'analyse : rapport HTML auto-contenu (Jinja2). **Aucune logique d'analyse** — entrée = dict d'état, sortie = HTML. Le trio matplotlib (radar de qualité, graphe d'attaques Dung, dashboard de pipeline) a été **retiré** (#2116 : 0 importeur production, 0 test).

N'est **pas** : `utils/visualization_generator.py` (reporting perf, consommé par `utils/reporting_utils.py:24`), ni [`cli/output_formatter.py:67`](../cli/README.md) `render_spectacular_result` (formateur **terminal** Rich, celui que `run_orchestration.py:276-280` appelle), ni le HTML maison de `scripts/validation/main.py:506`.

## Composants publics

- `render_html_report` (`html_report.py:489`) — rapport HTML auto-contenu, template Jinja2 inline (:22-472, 10 sections, cytoscape + D3 via CDN) ; CLI autonome `python -m argumentation_analysis.visualization.html_report state.json out.html` (:654-686) ;
- ré-export : `__init__.py` (`__all__` = `["render_html_report"]`).

## Points d'entrée valides

**Zéro importeur production** (grep plein dépôt). Consommateurs :

- tests : `tests/unit/argumentation_analysis/visualization/test_html_report.py` (19 imports, :28-294 ; skip si la golden fixture `tests/golden/fixtures/spectacular/doc_a_golden.json` manque :17-19) ;
- doc de soutenance : `docs/soutenance/FAQ.md:198` cite `html_report.py` comme option de démo ;
- CLI `__main__` (:654-686) pour usage manuel.

## Amont / aval

- Amont : schéma d'état spectacular (`state_snapshot`, clés lues :506-517), golden fixtures.
- Aval : rien dans le dépôt ne consomme les sorties — fichiers PNG/HTML à destination humaine (soutenance, debug).

## Statut d'intégration

| Composant | Statut | Preuve |
|---|---|---|
| `html_report.py` | **spécialisé** | 19 tests snapshot, doc FAQ, CLI autonome |
| `quality_viz.py`, `dung_viz.py`, `pipeline_viz.py` | **retiré (#2116)** | 0 importeur, 0 test — la clé de vertu erronée `faible_redundance` part avec |

## Artefacts et lecteurs

PNG bytes en mémoire par défaut ; fichier écrit uniquement si `output_path` passé. Lecteurs : humains (soutenance, revue de runs).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/visualization/test_html_report.py -v
```

(19 tests snapshot sur la golden fixture spectacular.)

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `visualization/`. Frères : [`cli/`](../cli/README.md) (rendu terminal), [`reporting/`](../reporting/) (exports, sans README).

## Limites connues

- `html_report.py:547-550` : itération `dung_frameworks.values()` first-wins — déjà documenté `docs/reports/1648-flattening-inventory.md:425,517` ;
- template inline de 450 lignes dans le fichier Python (:22-472) — pas extractible/testable séparément.
