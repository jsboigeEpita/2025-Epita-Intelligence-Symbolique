# `visualization/` — rendu PNG matplotlib et rapports HTML

## Rôle et frontière

Génération de sorties visuelles à partir d'un état d'analyse : radar de qualité, graphe d'attaques Dung, dashboard de pipeline (PNG matplotlib), rapport HTML auto-contenu (Jinja2). **Aucune logique d'analyse** — entrée = dict d'état, sortie = PNG/HTML.

N'est **pas** : `utils/visualization_generator.py` (reporting perf, consommé par `utils/reporting_utils.py:24`), ni [`cli/output_formatter.py:67`](../cli/README.md) `render_spectacular_result` (formateur **terminal** Rich, celui que `run_orchestration.py:276-280` appelle), ni le HTML maison de `scripts/validation/main.py:506`.

## Composants publics

- `render_quality_radar` (`quality_viz.py:41`) — radar des vertus, matplotlib Agg, PNG bytes ou fichier (`output_path`, :99-103) ;
- `render_attack_graph` (`dung_viz.py:15`) — graphe d'attaques networkx, layout adaptatif (:56-61), coloration par extension (:70-77) ;
- `render_pipeline_dashboard` (`pipeline_viz.py:15`) — dashboard 4 panneaux (:73, :112, :144, :175) ;
- `render_html_report` (`html_report.py:489`) — rapport HTML auto-contenu, template Jinja2 inline (:22-472, 10 sections, cytoscape + D3 via CDN) ; CLI autonome `python -m argumentation_analysis.visualization.html_report state.json out.html` (:654-686) ;
- ré-exports : `__init__.py:16-21` (`__all__` = les 4 fonctions).

## Points d'entrée valides

**Zéro importeur production** (grep plein dépôt — y compris `render_html_report`). Consommateurs :

- tests : `tests/unit/argumentation_analysis/visualization/test_html_report.py` (19 imports, :28-294 ; skip si la golden fixture `tests/golden/fixtures/spectacular/doc_a_golden.json` manque :17-19) ;
- doc de soutenance : `docs/soutenance/FAQ.md:198` cite `html_report.py` comme option de démo ;
- CLI `__main__` (:654-686) pour usage manuel.

Conséquence : `quality_viz`, `dung_viz`, `pipeline_viz` n'ont **ni importeur production ni test**.

## Amont / aval

- Amont : schéma d'état spectacular (`state_snapshot`, clés lues :506-517), golden fixtures.
- Aval : rien dans le dépôt ne consomme les sorties — fichiers PNG/HTML à destination humaine (soutenance, debug).

## Statut d'intégration

| Composant | Statut | Preuve |
|---|---|---|
| `html_report.py` | **spécialisé** | 19 tests snapshot, doc FAQ, CLI autonome |
| `quality_viz.py`, `dung_viz.py`, `pipeline_viz.py` | **résiduel** | 0 importeur, 0 test |

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

- **Clé de vertu erronée** : `quality_viz.py:37` attend `faible_redundance` alors que la clé canonique est `redondance_faible` (`agents/core/quality/agentic_virtue_detectors.py:769,874`) — l'axe radar correspondant vaudrait toujours 0.0 (latent, module sans importeur) ;
- 3 modules sur 4 sans importeur production ni test ; imports matplotlib/networkx avec fallback silencieux (retour `None` + warning :62-64, :42-44, :35-37) ;
- `html_report.py:547-550` : itération `dung_frameworks.values()` first-wins — déjà documenté `docs/reports/1648-flattening-inventory.md:425,517` ;
- template inline de 450 lignes dans le fichier Python (:22-472) — pas extractible/testable séparément.
