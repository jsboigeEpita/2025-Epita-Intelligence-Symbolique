# B-03: Audit — `tests/unit/argumentation_analysis/pipelines/`

**Track**: B-03 #758 (Epic B #743)
**Date**: 2026-05-31
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 5 fichiers de test, ~10 tests collectés (1 fichier en erreur de collection)

---

## Méthodologie

Même classification a/b/c que B-01 et B-02 :

| Catégorie | Sigle | Définition |
|-----------|-------|------------|
| **(a) Mort** | DEAD | Composant n'existe plus ou jamais été wiré |
| **(b) Non-wiré** | UNWIRED | Composant existe mais pas dans les workflows CapabilityRegistry |
| **(c) Justifié** | WIRED | Composant actif dans au moins un workflow |

**Note contextuelle** : Le répertoire `argumentation_analysis/pipelines/` contient les **anciens pipelines** pré-CapabilityRegistry. Le nouveau système (`orchestration/unified_pipeline.py` + `CapabilityRegistry` + `WorkflowDSL`) les a remplacés fonctionnellement. Cependant, `argumentation_analyzer.py` (façade principale) importe encore `UnifiedTextAnalysisPipeline` depuis `pipelines/unified_text_analysis.py` — c'est le dernier pont vivant entre les deux systèmes.

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) DEAD** | 1 | 0 (collection error) | 20% |
| **(b) UNWIRED** | 4 | ~10 | 80% |
| **(c) WIRED** | 0 | 0 | 0% |

---

## Tableau de classification

### (a) DEAD — Collection error / composant obsolète

| # | Fichier | Composant testé | Pourquoi DEAD |
|---|---------|-----------------|---------------|
| 1 | `test_unified_pipelines.py` | `unified_pipeline.py` + `unified_text_analysis.py` + `orchestration/config/enums.py` + `orchestration/config/base_config.py` + `orchestration/core/communication.py` + `orchestration/analysis/post_processors.py` + `orchestration/analysis/processors.py` + `orchestration/analysis/traces.py` | **Erreur de collection** (DLL crash torch/jpype sur Windows). Teste `argumentation_analysis.pipelines.unified_pipeline` (l'ancien routeur, pas le nouveau `orchestration/unified_pipeline.py`). Commentaire dans le fichier : "unified_text_analysis.py has a broken import (get_fallacy_detector) which cascades to all orchestration subpackages". **8 modules testés, 0 wirés dans CapabilityRegistry.** |

### (b) UNWIRED — Anciens pipelines pré-CapabilityRegistry

| # | Fichier | Composant testé | Importé par | Pourquoi UNWIRED |
|---|---------|-----------------|-------------|-------------------|
| 1 | `test_analysis_pipeline.py` | `analysis_pipeline.run_text_analysis_pipeline()` | Aucun (sauf scripts validation) | Pipeline standard pré-Lego. Importe `initialize_analysis_services` (ancienne API). Pas dans CapabilityRegistry. |
| 2 | `test_advanced_rhetoric.py` | `advanced_rhetoric.run_advanced_rhetoric_pipeline()` | Aucun | Pipeline d'analyse rhétorique avancée. Importe `AnalysisToolsPlugin` (ancien plugin pré-SK). Pas dans CapabilityRegistry. |
| 3 | `test_embedding_pipeline.py` | `embedding_pipeline.run_embedding_generation_pipeline()` | Aucun | Pipeline de génération d'embeddings (chunks → vecteurs). Pas dans CapabilityRegistry. |
| 4 | `test_reporting_pipeline.py` | `reporting_pipeline.run_comprehensive_report_pipeline()` | `scripts/reporting/generate_comprehensive_report.py` | Pipeline de rapport (pandas + matplotlib + seaborn). Pas dans CapabilityRegistry. Seul script vivant hors tests. |

---

## Récit du framework — Épisodes visibles dans ce packet

### Épisode 1 : Les pipelines monolithiques (pré-2025-Q3)

Le répertoire `argumentation_analysis/pipelines/` cristallise l'architecture **monolithique** initiale. Chaque pipeline (`analysis_pipeline`, `embedding_pipeline`, `reporting_pipeline`, `advanced_rhetoric`) était un script autonome avec son propre orchestrateur, ses propres services (`initialize_analysis_services`, `get_fallacy_detector`), et son propre format de sortie. Le `unified_pipeline.py` était un routeur qui sélectionnait entre "original", "orchestration" et "auto" — un précurseur du CapabilityRegistry qui n'avait pas encore la notion de **capabilities**.

**Trace** : Les tests dans `test_analysis_pipeline.py` mockent `initialize_analysis_services` et `perform_text_analysis` — deux fonctions de l'ancien service layer qui n'existent plus dans le nouveau système. Le test `test_unified_pipelines.py` mocke `sys.modules` pour contourner un import cassé (`get_fallacy_detector`), signe que le code était déjà fragile.

### Épisode 2 : Le pont unified_text_analysis (transition)

`unified_text_analysis.py` est le **pont de transition** entre l'ancien système et le nouveau. Il importe à la fois `orchestration.unified_pipeline` (nouveau) et `orchestration.real_llm_orchestrator` (ancien, déprécié par Sprint 13). Il définit `UnifiedTextAnalysisPipeline` et `UnifiedAnalysisConfig` — deux classes qui encapsulent l'ancien workflow monolithique derrière une interface unifiée.

**Trace** : `argumentation_analyzer.py` (la façade principale du système) importe encore `UnifiedTextAnalysisPipeline` — c'est le dernier consommateur direct de l'ancien pipeline. Les scripts dans `scripts/validation/` (4 fichiers) importent aussi ces pipelines — ce sont des scripts de validation hérités, pas du code production.

### Épisode 3 : La cohabitation legacy/new (2025-Q4 → 2026)

Les pipelines legacy cohabitent avec le nouveau système CapabilityRegistry. Le CapabilityRegistry (`registry_setup.py`) n'enregistre **aucun** des pipelines dans `argumentation_analysis/pipelines/`. Le nouveau système a ses propres entry points : `run_unified_analysis()` dans `orchestration/unified_pipeline.py`, les workflows `build_*_workflow()`, et les invoke callables. Les anciens pipelines restent pour :
1. **Rétro-compatibilité** : `argumentation_analyzer.py` → `UnifiedTextAnalysisPipeline`
2. **Scripts utilitaires** : `generate_comprehensive_report.py` (reporting), scripts de validation
3. **Documentation vivante** : les docstrings détaillées de chaque pipeline documentent l'architecture pré-Lego

**Trace** : Le test `test_reporting_pipeline.py` mocke `pandas.DataFrame`, `matplotlib.pyplot`, et `seaborn.barplot` — un pipeline de visualisation complet qui n'a jamais été intégré dans le CapabilityRegistry mais reste fonctionnel via le script `generate_comprehensive_report.py`.

---

## Actions recommandées

### Priorité HAUTE — Collection error

| Action | Fichier | Impact |
|--------|---------|--------|
| Réparer ou archiver | `test_unified_pipelines.py` | 0 tests collectés (DLL crash) + import cassé `get_fallacy_detector` |

Ce fichier teste 8 modules à travers un workaround `sys.modules` — il est structurellement fragile. Options :
- **Option A** : Réécrire pour tester le nouveau `orchestration/unified_pipeline.py` (CapabilityRegistry)
- **Option B** : Archiver avec `@pytest.mark.skip("legacy pipeline")` tant que `unified_text_analysis.py` n'est pas nettoyé

### Priorité MOYENNE — Pipelines legacy

Les 4 pipelines testés (`analysis_pipeline`, `advanced_rhetoric`, `embedding_pipeline`, `reporting_pipeline`) ne sont pas wirés dans le CapabilityRegistry. Pourtant :
- `reporting_pipeline` est utilisé par `scripts/reporting/generate_comprehensive_report.py`
- `unified_text_analysis` est importé par `argumentation_analyzer.py` (façade principale)

**Recommandation** : Évaluer la migration de ces pipelines vers des invoke callables dans le CapabilityRegistry (phase post-Epic B). Le `reporting_pipeline` est le meilleur candidat — il produit un artefact concret (rapport visuel) qui mériterait une capability `comprehensive_report`.

### Priorité BASSE — Pont unified_text_analysis

`argumentation_analyzer.py` → `UnifiedTextAnalysisPipeline` est le dernier pont vivant. La migration vers `CapabilityRegistry` + `run_unified_analysis()` éliminerait cette dépendance. Sprint 13 a déjà migré les scripts de validation — `argumentation_analyzer.py` est le consommateur restant.

---

## Annexe : Matrice wiring

| Pipeline testé | CapabilityRegistry | WorkflowDSL | Importé par (hors tests) |
|----------------|--------------------|-------------|--------------------------|
| `analysis_pipeline` | ❌ Non enregistré | ❌ Non utilisé | Aucun |
| `advanced_rhetoric` | ❌ Non enregistré | ❌ Non utilisé | Aucun |
| `embedding_pipeline` | ❌ Non enregistré | ❌ Non utilisé | Aucun |
| `reporting_pipeline` | ❌ Non enregistré | ❌ Non utilisé | `scripts/reporting/generate_comprehensive_report.py` |
| `unified_pipeline` (ancien routeur) | ❌ Non enregistré | ❌ Non utilisé | `argumentation_analyzer.py` (via `unified_text_analysis`) |
| `unified_text_analysis` | ❌ Non enregistré | ❌ Non utilisé | `argumentation_analyzer.py` |

**Contraste** : Le nouveau `orchestration/unified_pipeline.py` (CapabilityRegistry) est importé par 20+ fichiers — c'est le système actif. Les pipelines dans `argumentation_analysis/pipelines/` sont le système legacy.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-03 #758 — Epic B #743*
