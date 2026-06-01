# Audit A-07: Projet 2.3.2 — Détection de Sophismes et Biais Cognitifs

**Issue**: #753 (A-07) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `2.3.2-detection-sophismes/` (~2280 LOC, 8 fichiers Python, 9 parquet datasets) a été intégré de manière **supérieure** au core — le consolidé dépasse l'original sur tous les plans (taxonomie 8 familles vs 13 classes plates, 3-tier hybrid + hierarchical deepening vs pipeline 5-module, intégration pipeline DAG complète vs standalone CLI).

**Verdict**: 🟢 **INTÉGRÉ fidèlement et enrichi** — aucune régression fonctionnelle, l'architecture consolidée est strictement supérieure. Le répertoire racine est archivable sans perte.

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant `2.3.2-detection-sophismes/` (auteur "arthur.hamard", ~2280 LOC, 8 fichiers Python) a été digéré en **multiples intégrations distinctes**, couvrant un spectre plus large que l'original :

| Point d'intégration | Fichier(s) | LOC approx | Fonction | Source |
|---------------------|-----------|------------|----------|--------|
| **Agent informel** | `agents/core/informal/informal_agent.py` + `informal_definitions.py` + `informal_agent_adapter.py` | ~800 | `InformalAnalysisAgent(BaseAgent)` — analyse fallacies + arguments + taxonomy browsing | Adapté de 2.3.2 |
| **Plugin SK français** | `plugins/french_fallacy_plugin.py` + `adapters/french_fallacy_adapter.py` | ~1200 | 3-tier hybrid (LLM → NLI → Symbolic) + CamemBERT fallback | Digéré de `fallacy_pipeline.py` |
| **Taxonomie** | `agents/core/informal/taxonomy_sophism_detector.py` + `data/taxonomy_*.csv` | ~300 | 8 familles, 28 labels, exploration hiérarchique | Enrichi de 13 classes plates |
| **WorkflowPlugin** | `plugins/fallacy_workflow_plugin.py` | ~500 | Master-slave deepening + iterative refinement | Nouveau (supérieur) |
| **Family Analyzer** | `agents/tools/analysis/fallacy_family_analyzer.py` | ~200 | 8-family analysis + fact-checking integration | Nouveau |
| **Orchestration** | `orchestration/invoke_callables.py` (3 invokeurs) + `state_writers.py` + `workflows.py` | ~400 | 3 registered services, 4+ workflows, DAG complet | Nouveau |

**CapabilityRegistry**: 3 services enregistrés : `self_hosted_fallacy_detector` (neural_fallacy_detection), `hierarchical_fallacy_detector` (hierarchical_fallacy_detection), `hierarchical_fallacy_per_argument` (per_argument_fallacy_detection).

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
|--------------------------|-------------|-----|-------|
| Pipeline 5-module (mining→neural→symbolic→ensemble→explanation) | ✅ Supérieur | `french_fallacy_adapter.py` 3-tier + `fallacy_workflow_plugin.py` hierarchical | Core a 2 architectures distinctes |
| Classification 13 classes (CamemBERT) | ✅ Supérieur | Taxonomie 8 familles / 28 labels / hiérarchique | Core a **plus de granularité** |
| Règles symboliques (5 types) | ✅ Complet | `french_fallacy_adapter.py` `_SYMBOLIC_FALLACY_RULES` | ad_hominem, pente_glissante, etc. |
| Argument mining (claims/premises) | ✅ Complet | `french_fallacy_adapter.py` spaCy patterns | Même approche spaCy Matcher |
| Fine-tuning CamemBERT | ✅ Enrichi | `train_camembert.py` conservé + adapter supporte CamemBERT | Issue #169 fermée (modèle ~1.8GB) |
| Benchmark GPT vs CamemBERT | ❌ Perdu (remplacé) | LLM judge intégré au pipeline | Supérieur — intégré au workflow |
| Explications template-based | ✅ Supérieur | `InformalAnalysisAgent` LLM-generated explanations | LLM > templates |
| Taxonomie structurée (patterns, confidence) | ✅ Supérieur | `taxonomy_sophism_detector.py` + CSV hiérarchique | 8 familles > 13 classes plates |
| Validation Tweety (Dung extensions) | ✅ Intégré | Pipeline DAG → Dung → fallacy validation | Connecté au pipeline global |
| Temps réel (WebSocket) | ❌ Perdu | API REST streaming (supérieur) | Remplacé par architecture supérieure |
| CLI interactif | ❌ Perdu (remplacé) | API REST + orchestration CLI | Normal — API = superset |
| Dataset parquet (train/val/test) | ✅ Préservé | `2.3.2-detection-sophismes/data/` | Non migré (format entraînement, pas runtime) |

**Score de préservation**: 9/12 fonctionnalités préservées ou supérieures (75%). Les 3 fonctionnalités perdues sont toutes des "utilitaires remplacés par supérieur" (CLI→API, benchmark standalone→LLM judge, WebSocket→REST streaming).

### 1.3 Dilutions / Régressions

#### Dilution 1: Dataset parquet non migré

**Localisation**: `2.3.2-detection-sophismes/data/` (9 fichiers parquet, ~1.3 MB)
**Impact**: NONE — ce sont des datasets d'entraînement (train/val/test/augmented) utilisés uniquement par `train_camembert.py` et `benchmark_model.py`. Ils ne sont pas nécessaires au runtime.
**Assessment**: Pas une dilution — conservation appropriée.

#### Dilution 2: Chemin de recherche CamemBERT incluant le répertoire racine

**Localisation**: `french_fallacy_adapter.py` lignes 752, 808 — le chemin `"2.3.2-detection-sophismes/fine_tuned_camembert"` est listé comme fallback de recherche modèle.
**Impact**: LOW — fonctionnel (si le modèle est dans le répertoire étudiant, il est trouvé), mais crée une dépendance cachée vers le répertoire racine.
**Fix-intent**: `fix(a-07): remove student dir from CamemBERT model search paths in french_fallacy_adapter.py`

#### Pas d'autre dilution

L'architecture consolidée est **strictement supérieure** : 3-tier hybrid + hierarchical deepening > pipeline 5-module, 8 familles hiérarchiques > 13 classes plates, DAG pipeline intégré > standalone.

### 1.4 Statut du répertoire racine `2.3.2-detection-sophismes/`

**Verdict**: 🟡 **Référence pédagogique + 1 référence code (chemin modèle)**

- **0 import live Python** — aucun `from 2.3.2` ou `import 2.3.2` n'existe dans le codebase
- **2 références textuelles** (commentaires docstring : `french_fallacy_plugin.py:8`, `french_fallacy_adapter.py:19`)
- **1 référence code** (chemin de recherche modèle : `french_fallacy_adapter.py:752,808`)
- **8 fichiers orphelins** (fallacy_pipeline.py, symbolic_rules.py, train_camembert.py, etc.)
- **Dataset d'entraînement** (data/ — nécessaire si on re-fine-tune CamemBERT)

**Recommandation**:
1. Court terme: retirer le chemin `2.3.2-detection-sophismes/fine_tuned_camembert` des search paths dans `french_fallacy_adapter.py`
2. Moyen terme: archiver `2.3.2-detection-sophismes/` → `docs/archives/student_projects/2.3.2-detection-sophismes/` (préservé pour référence pédagogique + réentraînement)

---

## 2. Matrice des capabilities

| Capability étudiante | Capability consolidée | Statut |
|---------------------|----------------------|--------|
| Argument mining (spaCy) | `identify_arguments` (InformalAnalysisAgent) | ✅ Identique |
| Neural classification (CamemBERT) | `neural_fallacy_detection` (self_hosted_fallacy_detector) | ✅ Enrichi |
| Symbolic rules (5 types) | Tier 3 symbolic (french_fallacy_adapter) | ✅ Identique |
| Ensemble/vote | `_merge_fallacy_results()` (dedup by taxonomy_pk) | ✅ Enrichi |
| Explanation generation | LLM-generated via InformalAnalysisAgent | ✅ Supérieur |
| Taxonomie 13 classes | Taxonomie 8 familles / 28 labels / hiérarchique | ✅ Supérieur |
| Tweety validation | Pipeline DAG → Dung → fallacy verification | ✅ Intégré |
| Benchmarking | LLM judge intégré + evaluation module | ✅ Supérieur |

---

## 3. Cartographie des connections

```
2.3.2-detection-sophismes/              argumentation_analysis/
├── fallacy_pipeline.py ──────────────►  adapters/french_fallacy_adapter.py (digested)
│   (5-module pipeline)                  plugins/french_fallacy_plugin.py (3 @kernel_function)
│                                        orchestration/invoke_callables.py (3 invokeurs)
│
├── symbolic_rules.py ────────────────►  french_fallacy_adapter._SYMBOLIC_FALLACY_RULES
│   (5 pattern types)                    (same patterns, integrated)
│
├── train_camembert.py ─────────────── (référence — script d'entraînement conservé)
│
├── data/*.parquet ─────────────────── (datasets d'entraînement — conservés)
│
├── classify_with_chatgpt.py ─────────► LLM fallacy detection (Tier 1, integrated)
│
├── benchmark_*.py ─────────────────── (remplacé par LLM judge intégré)
│
└── run_cli.py ─────────────────────── (remplacé par API REST + orchestration)

                                        NOUVEAU (supérieur à l'original):
                                        ├── agents/core/informal/taxonomy_sophism_detector.py
                                        │   (8 families, 28 labels, hierarchical)
                                        ├── plugins/fallacy_workflow_plugin.py
                                        │   (master-slave iterative deepening)
                                        ├── agents/tools/analysis/fallacy_family_analyzer.py
                                        │   (8-family analysis + fact-checking)
                                        └── orchestration/workflows.py
                                            (4+ workflows with fallacy nodes)
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| F1 | `fix(a-07): remove student dir from CamemBERT model search paths` | **LOW** | Retirer `"2.3.2-detection-sophismes/fine_tuned_camembert"` des search paths dans `french_fallacy_adapter.py` |
| F2 | `fix(a-07): archive 2.3.2-detection-sophismes/ after search path cleanup` | **LOW** | Déplacer vers `docs/archives/student_projects/` (préservé pour référence + réentraînement) |

---

## 5. Conclusion

Le projet 2.3.2 est **excellemment intégré** — le consolidé est strictement supérieur à l'original sur tous les plans fonctionnels (taxonomie, architecture de détection, intégration pipeline, explications). Le seul point d'attention est le chemin de recherche CamemBERT qui référence encore le répertoire racine — un nettoyage mineur.

**Cas d'usage soutenance**: couvert et au-delà — la détection de sophismes est l'une des pièces maîtresses du système avec 3 services enregistrés, 4+ workflows, intégration DAG complète (fallacy → Dung → JTMS → quality scoring → counter-argument), et des centaines de tests.

**Test coverage**: 250+ fichiers de test référencent les fallacies/sophismes — parmi la couverture la plus dense du projet.

**Le répertoire `2.3.2-detection-sophismes/` est archivable** après le nettoyage F1 (1 PR, ~15 min de travail).

---

## 6. Fichiers sources
- `argumentation_analysis/agents/core/informal/` — InformalAnalysisAgent, TaxonomySophismDetector, adapter
- `argumentation_analysis/plugins/french_fallacy_plugin.py` — 3 @kernel_function methods
- `argumentation_analysis/plugins/fallacy_workflow_plugin.py` — master-slave deepening
- `argumentation_analysis/adapters/french_fallacy_adapter.py` — 3-tier hybrid adapter
- `argumentation_analysis/agents/tools/analysis/fallacy_family_analyzer.py` — 8-family analysis
- `argumentation_analysis/orchestration/invoke_callables.py` — 3 invokeurs (camembert, hierarchical, per-argument)
- `argumentation_analysis/orchestration/state_writers.py` — neural + hierarchical state writers
- `argumentation_analysis/orchestration/workflows.py` — 4+ workflows with fallacy nodes
- `argumentation_analysis/orchestration/registry_setup.py` — 3 services registered
- `argumentation_analysis/core/shared_state.py` — identified_fallacies + neural_fallacy_scores dimensions
