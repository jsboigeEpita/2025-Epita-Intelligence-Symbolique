# Audit A-02: Projet 1.2.1 — Argumentation Abstraite de Dung

**Issue**: #746 (A-02) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet Dung étudiant (`abs_arg_dung/`, 2 790 LOC) est intégré à **exactement 1 point** — `api/services.py` importe `EnhancedDungAgent` — tandis que le core a développé **deux implémentations indépendantes** (`af_handler.py` 11 sémantiques + `dung_native.py` 5 sémantiques pure-Python) qui ne dépendent pas du projet étudiant.

**Verdict**: 🟢 **INTÉGRÉ partiellement (60%)** — la digestion est fidèle sur le plan computationnel (les 5 sémantiques principales sont couvertes), mais 3 pans non-négligeables sont perdus (correction heuristiques dans le seul chemin API, visualisation, import/export TGF/DOT). Le répertoire racine est archivable après migration mineure.

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant `abs_arg_dung/` (2 790 LOC, 14 fichiers, auteur "Wassim", 2025-06-10) a été digéré en **3 intégrations distinctes**, non coordonnées:

| Point d'intégration | Fichier | LOC | Sémantiques | JVM requise |
|---------------------|---------|-----|-------------|-------------|
| **API directe** | `api/services.py` → `abs_arg_dung.enhanced_agent.EnhancedDungAgent` | 149 | 5 (grounded, preferred, stable, complete, admissible) + 2 retournées vides (ideal, semi-stable) | ✅ Oui (JPype/Tweety) |
| **SK Plugin** | `argumentation_analysis/plugins/tweety_logic_plugin.py` → `agents/core/logic/af_handler.py` | 229 | **11** (preferred, grounded, stable, complete, admissible, conflict_free, semi_stable, stage, cf2, ideal, naive) | ✅ Oui (JPype/Tweety) |
| **Orchestration** | `argumentation_analysis/orchestration/conversational_orchestrator.py` → `agents/core/logic/dung_native.py` | 277 | **5** (grounded, preferred, stable, complete, admissible) | ❌ Non (pure Python) |

**CapabilityRegistry**: La capability `abstract_argumentation` est enregistrée via `TweetyLogicPlugin` (plugin). Le `DungAnalysisService` est enregistré comme service. Le `dung_native.py` est consommé directement par l'orchestrateur conversationnel (pas de registration formelle — c'est un usage interne du pipeline).

### 1.2 Préservation fonctionnelle

| Fonctionnalité abs_arg_dung | Préservée ? | Où | Notes |
|---------------------------|-------------|-----|-------|
| Computation 7 sémantiques | ✅ Partielle | `af_handler.py` (11 > 7) | Core a PLUS de sémantiques que l'original |
| Grounded/Preferred/Stable/Complete/Admissible | ✅ Complet | Les 3 intégrations | Couverture parfaite sur les 5 fondamentales |
| Ideal extension | ⚠️ Partiel | `af_handler.py` oui, `dung_native.py` non, API retourne `[]` | Disponible via SK plugin mais pas via API |
| Semi-stable extension | ⚠️ Partiel | `af_handler.py` oui, `dung_native.py` non, API retourne `[]` | Idem |
| Argument status (credulous/skeptical) | ✅ Complet | API service | Via `EnhancedDungAgent` |
| Correction heuristiques (cycles parfaits, self-attack+) | ⚠️ API uniquement | `EnhancedDungAgent` dans `api/services.py` | **Pas répliqué dans af_handler ou dung_native** |
| Visualization (matplotlib/networkx) | ❌ Perdu | Nulle part | Le `DungAgent.visualize_graph()` n'a pas été migré |
| Import/Export JSON | ✅ Partiel | API retourne JSON | TGF/DOT/CSV formats perdus |
| Import/Export TGF/DOT | ❌ Perdu | Nulle part | `FrameworkIO` de `io_utils.py` non migré |
| CLI interactif | ❌ Perdu (remplacé) | API REST | Normal — API = superset du CLI |
| Génération aléatoire de frameworks | ❌ Perdu | Nulle part | `FrameworkGenerator.generate_random_framework` non utilisé |
| Exemples classiques (triangle, nixon_diamond) | ✅ Partiel | `dung_native.py` a `triangle()`, `nixon_diamond()` | Le reinstatement est aussi présent |
| Benchmark suite | ❌ Perdu | Nulle part | Pas critique pour le fonctionnement |
| Vérification inclusion sémantiques | ❌ Perdu | Nulle part | `get_semantics_relationships()` théorique |
| Démo interactive | ❌ Perdu | Nulle part | Pas critique |

**Score de préservation**: 9/15 fonctionnalités préservées (60%). Les 6 fonctionnalités perdues sont toutes dans les catégories "utilitaire" ou "outil pédagogique" — aucune fonctionnalité computationnelle critique n'est perdue.

### 1.3 Dilutions / Régressions

#### Dilution 1: L'API retourne des extensions vides pour ideal et semi-stable

**Localisation**: `api/services.py` lignes 85-86
```python
"ideal": [],          # Not implemented in this version
"semi_stable": []     # Not implemented in this version
```
**Impact**: LOW — `af_handler.py` supporte ces 2 sémantiques. Le fix est trivial: déléguer à `AFHandler` au lieu de `EnhancedDungAgent`.
**Fix-intent**: `fix(a-02): compute ideal + semi-stable extensions in DungAnalysisService`

#### Dilution 2: Correction heuristiques non répliquées dans le core

**Localisation**: `abs_arg_dung/enhanced_agent.py` lignes 40-110 (`_is_perfect_cycle`, `_compute_cycle_extensions`, `_check_self_attack_case`)
**Impact**: MEDIUM — Les corrections gèrent des edge cases (cycles parfaits où Tweety peut retourner des résultats vides, self-attack+attack). Ces corrections sont actives dans le chemin API mais pas dans les chemins SK plugin (`af_handler`) ou orchestration (`dung_native`).
**Fix-intent**: `fix(a-02): port EnhancedDungAgent corrections to af_handler.py and dung_native.py`

#### Dilution 3: 3 implémentations non-unifiées

**Impact**: LOW — C'est un pattern acceptable (Tweety pour précision, native pour fallback), mais l'API utilise le chemin étudiant au lieu du chemin core unifié (`af_handler.py`). La migration supprimerait la dépendance `abs_arg_dung`.
**Fix-intent**: `fix(a-02): migrate DungAnalysisService from EnhancedDungAgent to AFHandler`

### 1.4 Statut du répertoire racine `abs_arg_dung/`

**Verdict**: 🟡 **Référence pédagogique + 1 import live**

- **1 import live**: `api/services.py` → `abs_arg_dung.enhanced_agent.EnhancedDungAgent`
- **13 fichiers sans connexion**: agent.py, config.py, cli.py, framework_generator.py, io_utils.py, project_info.py, benchmark.py, demo_interactive.py, test_agent.py, test_enhanced.py, advanced_tests.py, validate_project.py
- **Tests cassés**: `test_enhanced.py` référence un fixture `initialize_jvm` qui n'existe pas dans le conftest.py du projet

**Recommandation**:
1. Court terme: migrer `api/services.py` pour utiliser `AFHandler` au lieu de `EnhancedDungAgent` (supprime le dernier import live)
2. Moyen terme: archiver `abs_arg_dung/` → `docs/archives/student_projects/abs_arg_dung/` (préservé pour référence pédagogique)

---

## 2. Matrice des sémantiques Dung

| Sémantique | `DungAgent` (abs_arg_dung) | `af_handler.py` (Tweety) | `dung_native.py` (Python) | API Service |
|------------|:---:|:---:|:---:|:---:|
| Grounded | ✅ | ✅ | ✅ | ✅ |
| Preferred | ✅ | ✅ | ✅ | ✅ |
| Stable | ✅ | ✅ | ✅ | ✅ |
| Complete | ✅ | ✅ | ✅ | ✅ |
| Admissible | ✅ | ✅ | ✅ | ✅ |
| Ideal | ✅ | ✅ | ❌ | ⚠️ vide |
| Semi-stable | ✅ | ✅ | ❌ | ⚠️ vide |
| Stage | ❌ | ✅ | ❌ | ❌ |
| CF2 | ❌ | ✅ | ❌ | ❌ |
| Naive | ❌ | ✅ | ❌ | ❌ |
| Conflict-free | ❌ | ✅ | ❌ (interne) | ❌ |

**Lecture**: Le core (`af_handler.py`) couvre **11 sémantiques** — supérieur au projet étudiant (7). Le chemin API n'exploite que 5 des 11 disponibles.

---

## 3. Cartographie des connections

```
abs_arg_dung/                           argumentation_analysis/
├── enhanced_agent.py ──────────────────► api/services.py (1 import live)
│   (EnhancedDungAgent)                     DungAnalysisService
│                                            │
│                                            ▼
│                                        api/dependencies.py
│                                        (get_dung_analysis_service)
│
├── agent.py ─────────────────────────── (NON importé)
├── config.py ────────────────────────── (NON importé)
├── cli.py ───────────────────────────── (NON importé)
├── framework_generator.py ───────────── (NON importé)
├── io_utils.py ──────────────────────── (NON importé)
├── benchmark.py ─────────────────────── (NON importé)
├── demo_interactive.py ──────────────── (NON importé)
└── tests/*.py ───────────────────────── (NON découverts par pytest)

                                        argumentation_analysis/agents/core/logic/
                                        ├── af_handler.py (AFHandler, 11 sémantiques)
                                        │   └── utilisé par tweety_logic_plugin.py
                                        └── dung_native.py (DungFramework, 5 sémantiques)
                                            └── utilisé par conversational_orchestrator.py

                                        argumentation_analysis/core/
                                        ├── shared_state.py
                                        │   └── dung_frameworks: Dict (stockage)
                                        └── state_manager_plugin.py
                                            └── add_dung_framework() @kernel_function
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| F1 | `fix(a-02): migrate DungAnalysisService from EnhancedDungAgent to AFHandler` | **HIGH** | Supprime le seul import live de `abs_arg_dung/`, unifie les chemins Dung |
| F2 | `fix(a-02): compute ideal + semi-stable in API DungService` | **MEDIUM** | 2 sémantiques déjà supportées par `af_handler.py` mais retournées vides par l'API |
| F3 | `fix(a-02): port EnhancedDungAgent corrections to core` | **MEDIUM** | Edge case handling (cycles parfaits, self-attack) uniquement dans le chemin API |
| F4 | `fix(a-02): archive abs_arg_dung/ after F1 migration` | **LOW** | Déplacer vers `docs/archives/student_projects/` une fois l'import live supprimé |

---

## 5. Conclusion

Le projet Dung est **bien digéré computationnellement** — le core a des implémentations supérieures (11 sémantiques via `af_handler.py`, 5 en pure Python via `dung_native.py`). La seule lacune est architecturale: l'API utilise encore le chemin étudiant (`EnhancedDungAgent`) au lieu du chemin core unifié (`AFHandler`), créant une dépendance inutile vers le répertoire racine.

**Cas d'usage soutenance**: couvert — les 5 sémantiques fondamentales (grounded, preferred, stable, complete, admissible) sont disponibles dans les 3 chemins (API, SK plugin, orchestration). Les sémantiques avancées (ideal, semi-stable, stage, cf2) sont disponibles via le SK plugin uniquement.

**Le répertoire `abs_arg_dung/` est archivable** après la migration F1 (1 PR, ~30 min de travail).
