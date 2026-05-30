# Sprint 13.C — Audit `RealLLMOrchestrator` Restants

**Date**: 2026-05-30
**Auteur**: po-2025 (audit)
**Base**: main `7452551a` (post Sprint 13.A merge + batch 1 po-2023)

## Synthèse

Après le batch 1 de po-2023 (12 fichiers `scripts/validation/`) et le batch 2 en cours (2 callers applicatifs par po-2023), il reste **~24 fichiers** contenant des références à `RealLLMOrchestrator`. La grande majorité (~70%) sont des **tests unitaires/intégration** qui instancient ou mockent la classe archivée — ils sont déjà skipés par des marqueurs `@pytest.mark.skip(reason="RealLLMOrchestrator archived")` et ne bloquent pas la CI. Les **shims** (~15%) sont les fichiers source qui définissent la classe archivée et ses wrappers — ils ne doivent PAS être supprimés (back-compat). Les **callers applicatifs live** restants (~10%) sont déjà couverts par le batch 2 de po-2023. Le batch 3 consistera principalement à nettoyer les tests morts et à mettre à jour les mocks dans les tests qui restent actifs.

**Effort estimé batch 3** : moyen (~3-4h). Risque principal : les tests d'intégration dans `test_unified_system_integration.py` et `test_authentic_components_integration.py` ont des constructions `RealLLMOrchestrator(mode="real")` qui lèveraient `NotImplementedError` si jamais exécutés — **latent broken**.

## Tableau de Classification

| # | Fichier | Catégorie | LOC RLO | Action batch 3 |
|---|---------|-----------|---------|----------------|
| 1 | `argumentation_analysis/orchestration/real_llm_orchestrator.py` | **shim source** | ~70 | **Garder** (back-compat, import explicite encore supporté) |
| 2 | `argumentation_analysis/orchestration/__init__.py` | **shim export** | 3 | **Garder** (commentaire only, auto-import déjà retiré po-2023 Iter 4) |
| 3 | `argumentation_analysis/orchestration/engine/main_orchestrator.py` | **caller applicatif** | ~10 | **Migrer** → remplacer factory `RealLLMOrchestrator(self.kernel)` par `UnifiedPipeline` |
| 4 | `argumentation_analysis/orchestration/service_manager.py` | **caller applicatif** | ~15 | **Migrer** → `self.llm_orchestrator: Optional[RealLLMOrchestrator]` → `UnifiedPipeline` |
| 5 | `argumentation_analysis/orchestration/pipeline_utils.py` | **commentaire/doc** | 4 | **Nettoyer** → retirer mentions "archived RealLLMOrchestrator" dans docstrings |
| 6 | `argumentation_analysis/pipelines/orchestration/orchestrators/specialized/real_llm_orchestrator.py` | **shim wrapper** | ~50 | **Garder** (`RealLLMOrchestratorWrapper` = back-compat wrapper) |
| 7 | `argumentation_analysis/pipelines/orchestration/__init__.py` | **shim export** | 2 | **Garder** (re-export wrapper) |
| 8 | `argumentation_analysis/pipelines/unified_pipeline.py` | **caller applicatif** | 2 | **Migrer** → po-2023 batch 2 |
| 9 | `argumentation_analysis/pipelines/unified_text_analysis.py` | **caller applicatif** | 3 | **Migrer** → po-2023 batch 2 |
| 10 | `project_core/core_from_scripts/unified_report_generator.py` | **commentaire** | 1 | **Nettoyer** → update docstring |
| 11 | `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py` | **caller applicatif** | 1 | **Migrer** → po-2023 batch 2 |
| 12 | `scripts/validation/main.py` | **commentaire legacy** | 1 | **Nettoyer** → déjà traité batch 1, commentaire restant |
| 13 | `tests/integration/test_authentic_components_integration.py` | **test live** | ~8 | **Migrer** → remplacer par UnifiedPipeline, risque latent broken |
| 14 | `tests/integration/test_unified_system_integration.py` | **test live** | ~15 | **Migrer** → gros fichier, ~7 instanciations, latent broken |
| 15 | `tests/integration/workers/worker_fol_pipeline.py` | **test live** | 3 | **Migrer** → constructeur + fallback local mock |
| 16 | `tests/unit/.../test_pipeline_utils.py` | **commentaire doc** | 1 | **Nettoyer** → update docstring |
| 17 | `tests/unit/.../test_real_llm_orchestrator.py` | **test unit shim** | ~40 | **Supprimer** — tout le fichier teste le shim archivé, 100% skippé |
| 18 | `tests/unit/.../test_service_manager.py` | **test unit mock** | 4 | **Nettoyer** → mettre à jour `mock.patch` strings + class name checks |
| 19 | `tests/unit/.../test_unified_pipelines.py` | **test unit mock** | 2 | **Nettoyer** → mettre à jour mock class name |
| 20 | `tests/unit/orchestration/engine/test_main_orchestrator.py` | **test unit mock** | 1 | **Nettoyer** → update mock.patch target |
| 21 | `tests/unit/orchestration/test_specialized_orchestrators.py` | **test unit live** | ~10 | **Supprimer** `TestRealLLMOrchestrator` class (skip), garder reste |
| 22 | `tests/unit/orchestration/test_unified_orchestrations.py` | **test unit live** | ~15 | **Migrer** → 4 test classes utilisent RealLLMOrchestrator, 2 skippées, 2 avec mock local |
| 23 | `tests/_archived/diagnostic/test_import.py` | **archive** | 2 | **Ignorer** (déjà archivé) |
| 24 | `tests/_archived/diagnostic/test_import_bypass_env.py` | **archive** | 1 | **Ignorer** (déjà archivé) |
| 25 | `docs/archives/orchestration_legacy/real_llm_orchestrator.py` | **archive** | 4 | **Ignorer** (archive historique) |

## Plan Batch 3 — Groupes Ordonnés

### Groupe 1 : Suppression tests morts (quick-win, ~30 min)

**Scope** : `test_real_llm_orchestrator.py` (fichier entier, ~720 lignes)
**Action** : Supprimer. 100% des tests sont `@pytest.mark.skip(reason="RealLLMOrchestrator archived")`.
**Risque** : Nul (rien ne tourne).
**Vérif** : `pytest --collect-only` inchangé.

### Groupe 2 : Migration callers applicatifs restants (~1h)

**Scope** : `main_orchestrator.py` (#3), `service_manager.py` (#4)
**Action** : Remplacer `RealLLMOrchestrator(self.kernel)` par instanciation `UnifiedPipeline`. Adapter `service_manager.llm_orchestrator` type annotation.
**Risque** : Moyen — `service_manager.py` est un gros fichier (~1200 lignes) avec plusieurs paths conditionnels. Tester que le path `RealLLMOrchestrator` n'est plus le default.
**Vérif** : `grep "RealLLMOrchestrator" argumentation_analysis/orchestration/` = 0 (sauf shim source + `__init__.py` commentaires).

### Groupe 3 : Nettoyage commentaires/docstrings (~20 min)

**Scope** : `pipeline_utils.py` (#5), `unified_report_generator.py` (#10), `test_pipeline_utils.py` (#16), `scripts/validation/main.py` (#12)
**Action** : Retirer mentions "archived RealLLMOrchestrator" des docstrings, remplacer par "UnifiedPipeline".
**Risque** : Nul (texte only).

### Groupe 4 : Migration tests intégration (~1.5h)

**Scope** : `test_authentic_components_integration.py` (#13), `test_unified_system_integration.py` (#14), `worker_fol_pipeline.py` (#15)
**Action** : Remplacer instanciations `RealLLMOrchestrator(mode="real")` par `UnifiedPipeline`. Ces tests sont probablement **latent broken** (NotImplementedError à l'exécution).
**Risque** : Élevé — les tests d'intégration dépendent de beaucoup de setup (kernel, LLM service, state). Probablement besoin de re-écrire une partie des fixtures.
**Vérif** : `pytest tests/integration/ -x --timeout=120 -k "real_llm or orchestrator"` (peu importe le résultat — le but est de ne plus référencer RLO).

### Groupe 5 : Nettoyage mocks tests unitaires (~30 min)

**Scope** : `test_service_manager.py` (#18), `test_unified_pipelines.py` (#19), `test_main_orchestrator.py` (#20), `test_specialized_orchestrators.py` (#21), `test_unified_orchestrations.py` (#22)
**Action** : Mettre à jour `mock.patch` targets, class name checks (`__class__.__name__ = "RealLLMOrchestrator"` → `"UnifiedPipeline"`), retirer `TestRealLLMOrchestrator` skippé.
**Risque** : Faible — ce sont des mocks, pas du code live.

### Groupe 6 : Conservation shims (ne pas toucher)

**Scope** : `real_llm_orchestrator.py` (#1), `orchestration/__init__.py` (#2), `pipelines/.../real_llm_orchestrator.py` (#6), `pipelines/.../__init__.py` (#7)
**Action** : Aucune. Ces shims assurent la back-compat pour les imports explicites (`from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator`).
**Note** : Si le nettoyage total est souhaité à terme, ces shims peuvent être supprimés après vérification qu'aucun consommateur externe ne les importe.

### Groupe 7 : Archives (ignorer)

**Scope** : `tests/_archived/` (#23, #24), `docs/archives/` (#25)
**Action** : Aucune.

## Risques Identifiés

### R1 : Tests intégration latent broken

`test_unified_system_integration.py` et `test_authentic_components_integration.py` construisent des `RealLLMOrchestrator(mode="real")`. Si ces tests sont exécutés (via `-m integration` ou sans filtre), ils lèveront `NotImplementedError` car `initialize()` est stubé dans le shim.

**Impact** : Pas bloquant CI (tests integration pas dans le run par défaut), mais trompeur pour un développeur qui les lance manuellement.

**Recommandation** : Groupe 4 prioritaire après suppression tests morts.

### R2 : `service_manager.py` couplage profond

`ServiceManager` a un attribut typé `Optional[RealLLMOrchestrator]` et un path conditionnel `if RealLLMOrchestrator:` qui instancie la classe. Remplacer par `UnifiedPipeline` nécessite de comprendre le cycle de vie du service manager.

**Impact** : Si mal migré, le path LLM réel du service manager ne fonctionne plus.

**Recommandation** : Bien tester le path LLM avant/après.

### R3 : `main_orchestrator.py` factory

La méthode `_create_orchestrator_config` construit un dict `"orchestrator": RealLLMOrchestrator(self.kernel)`. Remplacer par `UnifiedPipeline` nécessite de vérifier que les downstream consumers de ce dict attendent la même interface.

**Impact** : Le `MainOrchestrator` est l'entry point du mode hiérarchique (dormant selon CLAUDE.md).

**Recommandation** : Vérifier si le mode hiérarchique est actif avant de migrer. Si dormant, le risque est théorique.

## Quick-Wins Identifiés (pour po-2023 lane batch 2)

Ces callers sont trivialement migrables et déjà dans le scope de po-2023 batch 2 :
- `unified_pipeline.py:304` — une seule instanciation, import déjà présent
- `unified_text_analysis.py:217` — un seul caller, déjà noté par po-2023
- `educational_showcase_system.py:84` — un seul import + instanciation

## Métriques

| Catégorie | Fichiers | LOC RLO estimé |
|-----------|----------|----------------|
| Shim source/export | 4 | ~125 |
| Caller applicatif | 5 | ~31 |
| Test live (intégration) | 3 | ~26 |
| Test unit (mock/skip) | 5 | ~57 |
| Test unit shim (100% skip) | 1 | ~40 |
| Commentaire/docstring | 4 | ~7 |
| Archive | 3 | ~7 |
| **Total** | **25** | **~293** |
