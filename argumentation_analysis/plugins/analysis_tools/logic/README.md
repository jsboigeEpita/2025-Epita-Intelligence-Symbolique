# `plugins/analysis_tools/logic/` — moteurs d'analyse rhétorique et de sophismes

## Rôle et frontière

6 modules (4 595 lignes) — les moteurs d'analyse du plugin SK `analysis_tools` (la façade vit dans le parent `plugin.py`). C'est le code métier d'analyse « Enhanced » (sophismes complexes/contextuels, sévérité, rhétorique), pas des wrappers.

## Composants publics

- `complex_fallacy_analyzer.py` (1 608 l.) — `EnhancedComplexFallacyAnalyzer` (:57) ;
- `contextual_fallacy_analyzer.py` (975 l.) — `EnhancedContextualFallacyAnalyzer` (:82) ;
- `fallacy_severity_evaluator.py` (446 l.) — `EnhancedFallacySeverityEvaluator` (:36) ;
- `rhetorical_result_analyzer.py` (817 l.) — `RecommendationGenerator` (:36), `EnhancedRhetoricalResultAnalyzer` (:173) ;
- `rhetorical_result_visualizer.py` (568 l.) — `EnhancedRhetoricalResultVisualizer` (:43) ;
- `nlp_model_manager.py` (157 l.) — `NLPModelManager` (:47) + singleton `nlp_model_manager` (:157).

`__init__.py` (24 l.) exporte 6 noms — **tous vérifiés réels, zéro fantôme**.

## Points d'entrée valides

Façade `analysis_tools/plugin.py:16-21` (importe les 6), elle-même consommée par : `orchestration/advanced_analyzer.py:10`, `orchestration/hierarchical/operational/adapters/rhetorical_tools_adapter.py:25`, `pipelines/advanced_rhetoric.py:12`, `pipelines/unified_text_analysis.py:85`. Import direct : `services/web_api/services/fallacy_service.py:16,19` ; `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py:66`.

Chaîne pipeline : `run_orchestration.py --mode pipeline` → `unified_text_analysis.py:85` (AnalysisToolsPlugin). Chaîne web : `fallacy_service.py` → `services/mcp_server/main.py:33`.

## Amont / aval

- Amont : `core/interfaces/fallacy_detector.py` (`AbstractFallacyDetector`, plugin.py:12), modèles NLP via `nlp_model_manager` (spacy).
- Aval : façade AnalysisToolsPlugin, `FallacyService` web, showcase pédagogique.

## Statut d'intégration

**actif** — 4 chaînes production mesurées (pipeline unifié, hiérarchique, web fallacy_service, showcase), façade exportant les 6 modules.

## Artefacts et lecteurs

Doc technique : `docs/technical/complex_fallacy_analyzer.md:8` (humains).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/plugins/analysis_tools/logic/ -v
```

4 fichiers, **180 `def test_`** (55 contextual + 37 severity + 12 nlp_manager + 76 rhetorical_analyzer). ⚠ Une seconde suite, partielle et non collectée, vit dans [`../tests/`](../tests/README.md) — voir sa fiche.

## Frères et parent

Parent : `plugins/analysis_tools/` (sans README — parents bloqués #2088). Frère documenté : [`../../semantic_kernel/`](../../semantic_kernel/README.md). Amont logique : [`../../../core/`](../../../core/README.md) (`AbstractFallacyDetector`).

## Limites connues

- `nlp_model_manager` est un singleton module-level (:157) — état global partagé entre tous les consommateurs du processus ;
- la couverture mesurée sur runs réels de la façade est faible (0 % ligne sur le plugin jtms voisin selon `docs/reports/coverage_audit_2026_03_07.md` — pas mesuré ici pour logic/) : les 180 tests unitaires n'attestent pas l'exécution en run réel.
