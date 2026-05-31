# B-10: Audit — `tests/unit/project_core/` + `tests/unit/scripts/`

**Track**: B-10 #766 (Epic B #743)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 14 fichiers, 142 tests collectés

---

## Méthodologie

Même classification a/b/c que B-01 à B-09. Le wiring se vérifie par :
- **CapabilityRegistry** : grep dans `registry_setup.py`
- **Pipeline imports** : grep `from project_core` dans `argumentation_analysis/`
- **Script consumers** : grep dans `scripts/`

`project_core/` est une infrastructure utilitaire racine distincte de `argumentation_analysis/` (voir CLAUDE.md : "KEPT — infrastructure utilities, NOT business logic"). Les scripts dans `scripts/` sont des utilitaires autonomes.

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 2 | 8 | 14% |
| **(b) Non-wiré** | 4 | ~32 | 23% |
| **(c) Justifié** | 8 | ~102 | 63% |

---

## Tableau de classification

### (a) DEAD — Fichier vide ou phantom module

| # | Fichier | Composant testé | Pourquoi DEAD |
|---|---------|-----------------|---------------|
| 1 | `project_core/utils/test_file_utils.py` | Fichier vide (1 ligne) | **Aucun test**. Le fichier existe mais ne contient aucune fonction de test. |
| 2 | `scripts/test_configuration_cli.py` | `unified_production_analyzer` (phantom) | **Entièrement SKIP** (7 tests). Le module testé n'existe pas : `"project_core.rhetorical_analysis_from_scripts.unified_production_analyzer is a PHANTOM MODULE"`. Issue #112 référencée. |

### (b) UNWIRED — Scripts benchmark et diagnostics

| # | Fichier | Composant testé | Importé par | Tests | Pourquoi UNWIRED |
|---|---------|-----------------|-------------|-------|-------------------|
| 1 | `scripts/test_track_pp_fallacy_family_width.py` | `scda_deepsynthesis_vs_baseline` (Track PP #665) | Script autonome | 15 | Benchmark fallacy family counting. Script-only. |
| 2 | `scripts/test_benchmark_substance_metrics.py` | Benchmark #592 substance metrics (#641) | Script autonome | 11 | Benchmark convergence depth metrics. Script-only. |
| 3 | `scripts/test_jpype_dependency_validator.py` | Diagnostic JPype dans DependencyValidator | Aucun | 5 | Test diagnostique pour un bug JPype. Pas un test de composant pipeline. |
| 4 | `scripts/test_maintenance_manager.py` | `maintenance_manager.main` | Script CLI | 1 | CLI maintenance. Script-only. |

### (c) JUSTIFIÉ — Infrastructure critique et privacy

#### project_core/managers/ (6 fichiers, ~33 tests) — Infrastructure de setup

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `managers/test_environment_manager.py` | `EnvironmentManager` | Gestion de l'environnement conda/Python. Importé par `argumentation_analysis/core/environment.py` et 17+ scripts. | 8 |
| 2 | `managers/test_project_setup.py` | `ProjectSetup` | Setup projet (dev/test env). Importé par scripts de setup. | 6 |
| 3 | `managers/test_validation_engine.py` | `ValidationEngine` | Validation de configuration projet. | 5 |
| 4 | `managers/test_organization_manager.py` | `OrganizationManager` | Organisation fichiers projet. | 3 |
| 5 | `managers/test_repository_manager.py` | `RepositoryManager` | Gestion dépôt git. | 3 |
| 6 | `managers/test_refactoring_manager.py` | `RefactoringManager` | Refactoring assisté. | 3 |

#### project_core/utils/ (1 fichier, 1 test)

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `utils/test_shell.py` | `project_core.utils.shell.run_sync` | Exécution commandes shell synchrones. | 1 |

#### scripts/ (3 fichiers, ~71 tests) — Infrastructure critique

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `scripts/analysis/test_generate_spectacular_bundle_privacy.py` | `_scrub_state_for_export`, `_global_entity_scrub` | **Privacy regression tests** — protège les 4 vecteurs de leak (LLM paraphrase, entity regex, FOL formulae, intégration E2E). **Invariant privacy critique** (CLAUDE.md). | 46 |
| 2 | `scripts/test_run_live_reverify.py` | `run_live_reverify` aggregator | Sprint 13.A — orchestrateur de re-verification live (3 modes: live/mock/aggregate). Infrastructure de validation du pipeline. | 21 |
| 3 | `scripts/test_auto_env.py` | `ensure_env()` | **Coupe-circuit environnement** — vérifie que conda env est actif avant exécution. Protection contre les runs hors-env. | 4 |

---

## Récit du framework — 3 épisodes

### Épisode 1 : Le socle project_core (~2025-Q1)

Le répertoire `project_core/` cristallise l'**infrastructure de setup** du projet. Créé avant ou en parallèle de `argumentation_analysis/`, il fournit les utilitaires racine : `EnvironmentManager` (conda/Python), `ProjectSetup` (initialisation), `ValidationEngine` (configuration), `OrganizationManager` (fichiers), `RepositoryManager` (git), `RefactoringManager` (refactoring assisté). Ces managers sont consommés par les scripts de setup et validation, et marginalement par `argumentation_analysis/` (4 imports dans webapp, dev_tools, environment).

**Trace** : Les tests mockent systématiquement `MagicMock(spec=Path)` et patchent les stratégies — signe que le framework a été conçu pour tourner offline et en isolation dès l'origine.

### Épisode 2 : Les benchmarks de substance (~2026-Q1-Q2)

Les tests `test_track_pp_fallacy_family_width.py` (15 tests) et `test_benchmark_substance_metrics.py` (11 tests) témoignent d'une **évolution de la méthodologie de benchmark**. Le problème identifié dans #592 et #641 : les benchmarks scorenaient le *vocabulaire* (le mot "Dung" apparaît-il ?) plutôt que la *computation* (un framework Dung a-t-il été construit ?). Les nouveaux tests valident des métriques "unfakeable" : convergence depth et computed artifacts.

**Trace** : `test_benchmark_substance_metrics.py` importe `scripts.scda_deepsynthesis_vs_baseline` — un script de comparaison qui mesure la substance réelle des analyses. `test_track_pp_fallacy_family_width.py` teste le compteur de familles de sophismes étendu (Track PP #665).

### Épisode 3 : La discipline privacy cristallisée dans les tests (~2026-Q2)

Le fichier `test_generate_spectacular_bundle_privacy.py` (46 tests — **le plus gros fichier du packet**) cristallise la **discipline privacy** en 4 vecteurs de leak découverts dans les Rounds 176/179/180 :
1. **Vecteur 1** : Champs de paraphrase LLM (prémisses, conclusion, justification)
2. **Vecteur 2** : Patterns regex d'entités (word-boundary + substring pour snake_case)
3. **Vecteur 3** : Formules FOL + clés dict dans `nl_to_logic_translations`
4. **Vecteur 4** : Intégration E2E complète du scrub

Ces 46 tests sont des **tests de régression** qui protègent les fixes des Rounds 176/179/180 — si un scrub est retiré ou contourné, les tests échouent.

**Trace** : Le commentaire `"Entity names in test fixtures are intentionally present to verify scrubbing"` documente le pattern : les noms d'entités SONT dans les fixtures pour vérifier qu'ils sont bien supprimés par le scrub pipeline.

---

## Actions recommandées

### Priorité HAUTE — Phantom module + fichier vide

| Action | Fichier | Impact |
|--------|---------|--------|
| Supprimer ou archiver | `test_configuration_cli.py` | 7 tests SKIP (phantom module inexistant) |
| Supprimer ou archiver | `project_core/utils/test_file_utils.py` | Fichier vide (0 tests) |

`test_configuration_cli.py` référence Issue #112 et un module qui n'a jamais existé. `test_file_utils.py` est un fichier stub sans contenu.

### Priorité BASSE — Benchmarks scripts-only

Les 4 fichiers UNWIRED (32 tests) sont des benchmarks et diagnostics autonomes. Pas d'action recommandée — ils sont légitimes.

---

## Fix-intents ouverts

| Issue | Priorité | Fichier | Action |
|-------|----------|---------|--------|
| fix(b-10): remove phantom module test_configuration_cli.py (7 SKIP) | HAUTE | `test_configuration_cli.py` | Supprimer 7 tests SKIP + phantom module reference |
| fix(b-10): remove empty test_file_utils.py | HAUTE | `project_core/utils/test_file_utils.py` | Supprimer fichier stub vide |

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track B-10 #766 — Epic B #743*
