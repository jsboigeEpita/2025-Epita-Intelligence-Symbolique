# Audit A-09: Projet 2.3.5 — Évaluation Qualité Argumentative

**Issue**: #755 (A-09) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `2.3.5_argument_quality/` (~460 LOC, 5 fichiers, 4 auteurs) a été intégré de manière **fidèle et considérablement enrichie** — le consolidé préserve les 9 détecteurs de vertus argumentatives à l'identique (mêmes seuils, mêmes patterns, mêmes ressources JSON), ajoute la dégradation gracieuse (spaCy/textstat optionnels), l'intégration Semantic Kernel complète (4 kernel functions), le wiring CapabilityRegistry (5 capabilities), le branchement dans 8+ workflows DAG, et l'enrichissement LLM + cross-KB.

**Verdict**: 🟢 **INTÉGRÉ fidèlement et enrichi** — aucune régression fonctionnelle. Le répertoire racine est sanctuarisé (référence pédagogique conservée).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant a été digéré en **un bloc cohérent** sous `argumentation_analysis/agents/core/quality/` :

| Fichier consolidé | Origine étudiante | LOC approx | Rôle |
|-------------------|-------------------|------------|------|
| `quality_evaluator.py` | `src/agent.py` | ~337 | `ArgumentQualityEvaluator` + 9 détecteurs + `evaluer_argument()` + graceful degradation |
| `__init__.py` | Nouveau | ~36 | `register_with_capability_registry()` + re-exports |
| `ressources_argumentatives.json` | `src/ressources_argumentatives.json` | ~45 | Listes linguistiques préservées à l'identique |

**Intégrations pipeline additionnelles** :

| Fichier pipeline | LOC approx | Rôle |
|------------------|------------|------|
| `plugins/quality_scoring_plugin.py` | ~121 | `QualityScoringPlugin` — 4 `@kernel_function` |
| `orchestration/invoke_callables.py` (quality) | ~150 | `_invoke_quality_evaluator` + `_llm_enrich_quality` + `_run_quality_sweep_from_state` |
| `orchestration/state_writers.py` (quality) | ~80 | `_write_quality_to_state` |
| `orchestration/workflows.py` (quality) | ~100 | 8+ workflows avec quality comme phase obligatoire |
| `orchestration/registry_setup.py` (quality) | ~20 | Enregistrement agent quality_evaluator (3 capabilities) |
| `agents/factory.py` (quality) | ~5 | Plugin quality_scoring pour agents "quality" |

**CapabilityRegistry** (double registration) :
1. **Plugin** (`__init__.py`): `quality_scoring` → capabilities `argument_quality_evaluation`, `virtue_scoring`
2. **Agent** (`registry_setup.py`): `quality_evaluator` → capabilities `argument_quality`, `virtue_detection`, `quality_scoring` + invoke `_invoke_quality_evaluator`

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
|--------------------------|-------------|-----|-------|
| 9 détecteurs de vertus (clarté→redondance) | ✅ Identique | `quality_evaluator.py` | Mêmes fonctions, mêmes seuils, mêmes patterns |
| Flesch Reading Ease (clarté) | ✅ Identique | `detect_clarte` | Seuils identiques : ≥60→1.0, ≥30→0.5, <30→0.2 |
| Connecteurs logiques (pertinence) | ✅ Identique | `detect_pertinence` | Comptage identique : ≥3→1.0, ≥1→0.5, 0→0.2 |
| Patterns citation (sources) | ✅ Identique | `detect_presence_sources` | Mêmes regex : `(Author 2024)`, `[1]`, etc. |
| Marqueurs réfutation | ✅ Identique | `detect_refutation_constructive` | Mêmes marqueurs substring |
| Connecteurs structure logique | ✅ Identique | `detect_structure_logique` | Mêmes connecteurs |
| Patterns analogies | ✅ Identique | `detect_analogie_pertinente` | Mêmes patterns : "comme si", "à l'instar de" |
| Sources crédibles | ✅ Identique | `detect_fiabilite_sources` | Mêmes noms : OMS, CNRS, .gouv.fr |
| Sentence count spaCy (exhaustivité) | ✅ Identique + fallback | `detect_exhaustivite` | + fallback `count(".")` si spaCy absent |
| Unique word ratio (redondance) | ✅ Identique + fallback | `detect_redondance_faible` | + fallback split si spaCy absent |
| Ressources JSON (6 listes) | ✅ Identique | `ressources_argumentatives.json` | + `_FALLBACK_RESOURCES` hardcoded |
| Output format (note_finale, note_moyenne, scores_par_vertu, rapport_detaille) | ✅ Identique | `ArgumentQualityEvaluator.evaluate()` | Exactement la même structure |
| 13 exemples arguments (ARGUMENTS_EXAMPLE) | ❌ Non migré | Reste dans `2.3.5/src/agent.py` | Données de test/démo, pas runtime |
| Classification types argumentaires (ArgumentType) | ❌ Non migré | Reste dans `2.3.5/src/arguments.py` | Module séparé, non connecté à l'évaluateur |
| GUI PyQt5 | ❌ Perdu (remplacé) | REST API + Gradio demo | Supérieur — API = superset |
| WebSocket server (stub) | ❌ Perdu (était un stub) | Nulle part | Retournait "Mock result" — non fonctionnel |
| LLM enrichment | ✅ Supérieur (nouveau) | `_llm_enrich_quality` | Analyse LLM approfondie (hypothèses, biais, raisonnement) |
| Cross-KB context (fallacies→quality) | ✅ Supérieur (nouveau) | `evaluate_with_cross_kb_context` | Ajustement scores via sophismes détectés |
| Quality-gated counter generation | ✅ Supérieur (nouveau) | `build_quality_gated_counter_workflow` | Gate : contre-arguments générés si note > 3.0 |
| Fallacy-based penalty | ✅ Supérieur (nouveau) | `_invoke_quality_evaluator` | Pénalité automatique si sophismes détectés |
| Per-argument scoring | ✅ Supérieur (nouveau) | `_invoke_quality_evaluator` | Évaluation individuelle de chaque argument (cap 8) |
| 4 @kernel_function | ✅ Supérieur (nouveau) | `QualityScoringPlugin` | L'étudiant n'avait aucune intégration SK |

**Score de préservation**: 12/16 fonctionnalités préservées ou supérieures (75%). Les 4 perdues sont : exemples arguments (test data), classification types (module séparé), PyQt5 GUI (remplacé), WebSocket stub (non fonctionnel).

### 1.3 Dilutions / Régressions

#### Dilution 1: 13 exemples arguments non migrés

**Localisation**: `2.3.5_argument_quality/src/agent.py` — `ARGUMENTS_EXAMPLE` list (13 arguments prédéfinis)
**Impact**: NONE — ce sont des données de démonstration pour le GUI PyQt5, pas nécessaires au runtime pipeline.
**Assessment**: Pas une dilution — conservation appropriée dans le répertoire sanctuarisé.

#### Dilution 2: Classification types argumentaires (arguments.py) non intégrée

**Localisation**: `2.3.5_argument_quality/src/arguments.py` — `ArgumentType` enum + `ARGUMENT_PATTERNS` dict (7 types : causal, logical, analogical, rhetorical, authority, example, generalization)
**Impact**: LOW — ce module n'était pas connecté à l'évaluateur dans le projet étudiant lui-même. La fonctionnalité de classification d'arguments existe ailleurs dans le core : `counter_argument/parser.py` (parsing argumentaire), `informal/informal_agent.py` (classification fallacies), et le plugin `counter_argument` a sa propre analyse de types.
**Assessment**: Pas une dilution — le module était standalone et sa fonctionnalité est couverte par d'autres agents.

#### Pas d'autre dilution

L'intégration est **fidèle et enrichie** : les 9 détecteurs sont portés à l'identique, la dégradation gracieuse est un ajout pur (pas de modification des seuils ou patterns), et les enrichissements (LLM, cross-KB, workflows) sont tous additifs.

### 1.4 Statut du répertoire racine `2.3.5_argument_quality/`

**Verdict**: 🟢 **Sanctuarisé — référence pédagogique conservée** (mandate R300)

- **0 import live Python** — aucun `from 2.3.5` n'existe dans le codebase
- **Docstrings référencent l'origine** : `quality_evaluator.py:4` et `quality_scoring_plugin.py:8` mentionnent "Integrated from student project 2.3.5"
- **Fichiers non-migrés** : `arguments.py` (classification types), `interface.py` (PyQt5 GUI), `server.py` (WebSocket stub), `agent.py` (incluant les 13 exemples)
- **Ressource partagée** : `ressources_argumentatives.json` est copié dans le consolidé (pas d'import live)

---

## 2. Matrice des capabilities

| Capability | Module consolidé | Statut |
|------------|------------------|--------|
| Évaluation qualité 9 vertus | `quality_evaluator.py` ArgumentQualityEvaluator | ✅ Identique |
| Détection vertus individuelles | `quality_evaluator.py` 9 detector functions | ✅ Identique |
| Scoring SK (4 kernel functions) | `quality_scoring_plugin.py` QualityScoringPlugin | ✅ Supérieur (nouveau) |
| Enrichissement LLM | `invoke_callables.py` `_llm_enrich_quality` | ✅ Supérieur (nouveau) |
| Cross-KB context | `quality_scoring_plugin.py` `evaluate_with_cross_kb_context` | ✅ Supérieur (nouveau) |
| Pipeline per-argument | `invoke_callables.py` `_invoke_quality_evaluator` | ✅ Supérieur (nouveau) |
| Quality-gated counter generation | `workflows.py` `build_quality_gated_counter_workflow` | ✅ Supérieur (nouveau) |
| Quality sweep (conversational) | `invoke_callables.py` `_run_quality_sweep_from_state` | ✅ Supérieur (nouveau) |

---

## 3. Cartographie des connections

```
2.3.5_argument_quality/                 argumentation_analysis/
├── src/agent.py ─────────────────────►  agents/core/quality/quality_evaluator.py
│   (9 detectors + evaluer_argument)     (same detectors + graceful degradation + class wrapper)
│
├── src/ressources_argumentatives.json ► agents/core/quality/ressources_argumentatives.json
│   (6 linguistic resource lists)        (identical copy + hardcoded fallback)
│
├── src/arguments.py ──────────────── (NON migré — module standalone, couvert par d'autres agents)
├── src/interface.py ──────────────── (NON migré — PyQt5 remplacé par REST API + Gradio)
├── src/server.py ─────────────────── (NON migré — WebSocket stub non fonctionnel)
└── README.md ─────────────────────── (sanctuarisé)

                                        NOUVEAU (intégration pipeline):
                                        ├── agents/core/quality/__init__.py
                                        │   (register_with_capability_registry, 2 caps plugin)
                                        ├── plugins/quality_scoring_plugin.py
                                        │   (QualityScoringPlugin: 4 @kernel_function)
                                        ├── agents/factory.py
                                        │   (quality → quality_scoring plugin)
                                        ├── orchestration/invoke_callables.py
                                        │   (_invoke_quality_evaluator + _llm_enrich_quality + _run_quality_sweep_from_state)
                                        ├── orchestration/state_writers.py
                                        │   (_write_quality_to_state → state.add_quality_score)
                                        ├── orchestration/workflows.py
                                        │   (8+ workflows, quality phase mandatory)
                                        ├── orchestration/registry_setup.py
                                        │   (agent quality_evaluator, 3 capabilities)
                                        ├── core/shared_state.py
                                        │   (argument_quality_scores + add_quality_score + get_weak_arguments)
                                        └── cross-pipeline consumers:
                                            ├── workflows/debate_tournament.py (quality gating)
                                            ├── workflows/democratech.py (quality feeding)
                                            ├── workflows/fact_check_pipeline.py (quality→depth)
                                            ├── reporting/cross_reference_graph.py
                                            ├── reporting/multi_format_exporter.py
                                            └── visualization/html_report.py
```

---

## 4. Fix-intents

Aucun fix-intent nécessaire. L'intégration est fidèle, complète, et sans régression.

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| — | Aucune | — | Pas de DEAD, pas de capability muette, pas de dilution fonctionnelle |

---

## 5. Conclusion

Le projet 2.3.5 est **fidèlement intégré** — les 9 détecteurs de vertus argumentatives ont été portés à l'identique (mêmes seuils, mêmes patterns, mêmes ressources linguistiques), enrichis par la dégradation gracieuse (spaCy/textstat optionnels), l'intégration SK (4 kernel functions), le wiring CapabilityRegistry (5 capabilities sur 2 registration paths), et le branchement dans 8+ workflows DAG. La qualité est l'une des phases les plus critiques du pipeline — obligatoire dans la quasi-totalité des workflows, elle alimente directement les contre-arguments (tri par qualité), la gouvernance, le débat, et la synthèse.

**Cas d'usage soutenance**: excellent candidat — le `ArgumentQualityEvaluator` est simple à démontrer (input texte → 9 scores), le `QualityScoringPlugin` montre l'intégration SK (4 kernel functions), le quality-gated counter workflow montre le pipeline DAG avec dépendances, et le LLM enrichment montre la collaboration entre heuristiques et LLM.

**Test coverage**: l'évaluateur qualité est référencé dans de nombreux tests de workflow et d'intégration.

**Le répertoire `2.3.5_argument_quality/` est sanctuarisé** (mandate R300) — conservé comme référence pédagogique, jamais archivé ni déplacé.

---

## 6. Fichiers sources
- `argumentation_analysis/agents/core/quality/` — 3 fichiers (quality_evaluator, __init__, ressources_argumentatives.json)
- `argumentation_analysis/plugins/quality_scoring_plugin.py` — 4 @kernel_function methods
- `argumentation_analysis/orchestration/invoke_callables.py` — _invoke_quality_evaluator + _llm_enrich_quality + _run_quality_sweep_from_state
- `argumentation_analysis/orchestration/state_writers.py` — _write_quality_to_state
- `argumentation_analysis/orchestration/workflows.py` — 8+ workflows avec quality phase
- `argumentation_analysis/orchestration/registry_setup.py` — agent registration (3 capabilities)
- `argumentation_analysis/agents/factory.py` — quality_scoring plugin for quality agents
- `argumentation_analysis/core/shared_state.py` — argument_quality_scores + add_quality_score + get_weak_arguments + get_enrichment_summary
