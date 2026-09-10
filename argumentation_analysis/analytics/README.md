# `analytics/` — analyse quantitative des résultats d'argumentation

## Rôle et frontière

Analyse statistique **a posteriori** des résultats (moyennes, analyse textuelle, efficacité des agents). 3 modules, ~360 lignes, calculs purs en mémoire.

N'est **pas** le moteur d'analyse lui-même : `text_analyzer` est une façade fine qui délègue à `orchestration/analysis_runner_v2` ; `stats_calculator` et `effectiveness_analyzer` consomment des résultats déjà produits.

## Composants publics

- `calculate_average_scores(grouped_results)` (`stats_calculator.py:15`) — moyennes par corpus de toute métrique numérique, préfixées `average_` (:98) ;
- `perform_text_analysis(text, services, analysis_type)` (`text_analyzer.py:24`, async) — délègue à `AnalysisRunnerV2.run_analysis()` (:52, :70) ; `ValueError` si `llm_service` absent (:44-49) ;
- `analyze_agent_effectiveness(corpus_results, corpus_name)` (`effectiveness_analyzer.py:13`) — score heuristique = moy_sophismes × moy_confiance × 10 (:107-110).

## Points d'entrée valides

- `text_analyzer` : [`pipelines/analysis_pipeline.py:42`](../pipelines/analysis_pipeline.py) — chaîne active : analysis_pipeline ← `pipelines/unified_text_analysis.py:77` ← `core/argumentation_analyzer.py:14` et `pipelines/unified_pipeline.py:62` ;
- `stats_calculator` : [`pipelines/reporting_pipeline.py:85`](../pipelines/reporting_pipeline.py) — chaîne scripts : `scripts/reporting/generate_comprehensive_report.py:79` (référencé en commentaire) ;
- `effectiveness_analyzer` : **zéro importeur production** (grep plein dépôt ; seuls les tests `tests/unit/argumentation_analysis/analytics/`).

## Amont / aval

- Amont : dicts de résultats groupés (`utils/data_processing_utils.group_results_by_corpus`), services d'analyse (orchestrateur v2).
- Aval : rapports markdown (chaîne reporting), rien pour effectiveness.

## Statut d'intégration

| Composant | Statut | Preuve |
|---|---|---|
| `text_analyzer` | **actif** (transitif, chaîne pipelines) | analysis_pipeline.py:42 |
| `stats_calculator` | **spécialisé** (chaîne scripts/reporting, aucune route API) | reporting_pipeline.py:85 |
| `effectiveness_analyzer` | **résiduel testé** | grep vide |

## Artefacts et lecteurs

Aucun — dicts en retour, aucun fichier écrit.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/analytics/ -v
```

3 fichiers + README local de tests (`tests/unit/argumentation_analysis/analytics/README.md`).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `analytics/`. Frères : [`pipelines/`](../pipelines/README.md) (consommateur principal), [`utils/`](../utils/README.md).

## Limites connues

- **Duplication divergente** : `analytics/effectiveness_analyzer.analyze_agent_effectiveness` (:13, signature `corpus_results: List[dict]`) vs `pipelines/reporting_pipeline._analyze_agent_effectiveness` (:88, signature DataFrames) — deux implémentations distinctes du même concept ; l'audit `docs/reports/test_audit/B-07_api_eval_analytics_trace.md:82` prétend que reporting_pipeline importe le module analytics — **infirmé à la lecture** ;
- `text_analyzer.py:19` : `from argumentation_analysis.config.settings import AppSettings` — import mort (jamais utilisé dans le fichier) ;
- `__init__.py:23-26` : `__all__` vide, exports commentés « Exemple » (:20-21), `logger.info` au chargement (:31, effet de bord import-time) ;
- docstring `__init__.py:12-14` ignore `effectiveness_analyzer`.
