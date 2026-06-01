# Audit C-02: Section I-B "Frameworks d'Argumentation" (9 sujets)

**Issue**: #780 (C-02) | **Epic**: #744 | **Date audit**: 2026-05-31 | **Enriched**: 2026-06-01 (po-2023)

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
| --- | --- | --- |
| 1.2.1 Dung (abstraite) | 🟢 Treated (code + projet étudiant) | A-02 #746 🟢 INTÉGRÉ (fermée) |
| 1.2.2 Bipolaire | 🟢 Code exists, no subject doc | — |
| 1.2.3 Pondérée | 🟢 Code exists, no subject doc | — |
| 1.2.4 ABA | 🟢 Code exists, no subject doc | — |
| 1.2.5 VAF | 🟠 Angle mort utile — aucun code ni JAR | — |
| 1.2.6 ASPIC+ | 🟢 Code exists, no subject doc | — |
| 1.2.7 Dialogique | 🟢 Treated (subject + code) | A-03 #747 🟢 INTÉGRÉ (fermée) |
| 1.2.8 ADF | 🟢 Code exists, no subject doc | — |
| 1.2.9 Probabiliste | 🟢 Code exists, no subject doc | — |

## Résultats — Sujets traités (cross-réf Epic A)

### 1.2.1 Dung (Argumentation Abstraite) — 🟢 TREATED → Epic A #746 (A-02)

- **Projet étudiant**: `abs_arg_dung/` (2790 LOC, 14 fichiers, auteur "Wassim")
- **SUIVI**: Entrée ligne 26, intégré partiellement (Score 60%)
- **Audit A-02**: PR #803 mergée — verdict 🟢 partiel (60% préservation fonctionnelle)
- **Core**: `af_handler.py` (11 sémantiques via Tweety) + `dung_native.py` (5 sémantiques pure-Python)
- **Wiring**: Handler + Agent + Plugin + Workflow + Registry = ✅ Full
- **Assessment**: Plus riche que l'original étudiant. Archivable après migration API (fix-intent F1).

### 1.2.7 Dialogique — 🟢 TREATED → Epic A #747 (A-03)

- **Projet étudiant**: `1_2_7_argumentation_dialogique/`
- **Sujet doc**: `docs/projets/sujets/1.2.7_Argumentation_Dialogique.md`
- **SUIVI**: Entrée ligne 36, intégré (Score 90%)
- **Audit A-03**: PR #807 mergée — verdict 🟢 INTÉGRÉ
- **Core**: `DebateAgent(BaseAgent)` + 8 personnalités + Walton-Krabbe protocols
- **Wiring**: Handler + Agent + Plugin + Workflow + Registry = ✅ Full
- **Assessment**: Aucun gap pipeline. 198 tests. 3 workflows.

## Résultats — Sujets NON-traités mais avec code existant

### 1.2.2 Bipolaire (Attaque + Support) — 🟢 Code exists, no subject doc

- **Handler**: `bipolar_handler.py` (92 LOC) — `BipolarHandler` (necessity + evidential frameworks) + `eaf_handler.py` (135 LOC, Extended/Epistemic AF)
- **Plugin**: `TweetyLogicPlugin.analyze_bipolar_framework()` + `analyze_epistemic_framework()`
- **Invoker**: `_invoke_bipolar` in `invoke_callables.py:2541`
- **Registry**: `"bipolar_handler"` → `["bipolar_argumentation"]`
- **State writer**: `_write_bipolar_to_state` in `state_writers.py:521`
- **Workflow**: Node "bipolar" (L3c step from counter-argument)
- **JAR**: `org.tweetyproject.arg.bipolar-1.28-with-dependencies.jar`
- **Agent**: None dédié (handler-only)
- **Subject doc**: None
- **Assessment**: Fully wired. No angle mort technique.

### 1.2.3 Pondérée (Weighted + Social + Ranking) — 🟢 Code exists, no subject doc

- **Handler weighted**: `weighted_handler.py` (140 LOC) — `WeightedHandler`, 6 sémantiques avec threshold
- **Handler social**: `social_handler.py` (126 LOC) — `SocialHandler`, ISS reasoner with voting
- **Handler ranking**: `ranking_handler.py` (120 LOC) — 12 reasoners (categorizer, burden, discussion, counting, tuples, strategy, propagation, saf, counter_transitivity, probabilistic_ranking, iterated_graded_defense, serialisable)
- **Plugin**: `analyze_weighted_framework()` + `analyze_social_framework()` + `rank_arguments()`
- **Invoker**: `_invoke_weighted` + `_invoke_social` + `_invoke_ranking`
- **Registry**: `"weighted_handler"` → `["weighted_argumentation"]`, `"social_handler"` → `["social_argumentation"]`, `"ranking_semantics_handler"` → `["ranking_semantics"]`
- **State writer**: `_write_weighted_to_state` + `_write_social_to_state`
- **Workflow**: Nodes "ranking" (L3b), "weighted", "social" in full chain
- **JAR**: `arg.weighted-1.28` + `arg.social-1.28` + `arg.rankings-1.28`
- **Agent**: None dédié
- **Subject doc**: None
- **Assessment**: Triple implémentation — **supérieur au sujet original** qui ne mentionnait que semi-anneaux. Les 12 reasoners de ranking couvrent un spectre très large. No angle mort.

### 1.2.4 ABA (Assumption-Based Argumentation) — 🟢 Code exists, no subject doc

- **Handler**: `aba_handler.py` (165 LOC) — `ABAHandler`, 6 sémantiques (preferred, stable, complete, well_founded, ideal, flat)
- **Plugin**: `TweetyLogicPlugin.analyze_aba()`
- **Invoker**: `_invoke_aba` in `invoke_callables.py:2571`
- **Registry**: `"aba_handler"` → `["aba_reasoning"]`
- **State writer**: `_write_aba_to_state` in `state_writers.py:535`
- **Workflow**: Node "aba" in full chain (aspic → aba → adf → bipolar)
- **JAR**: `org.tweetyproject.arg.aba-1.28-with-dependencies.jar`
- **Agent**: None dédié
- **Subject doc**: None
- **Assessment**: Fully wired. Fait partie du workflow DAG complet. No angle mort.

### 1.2.6 ASPIC+ (Argumentation Structurée) — 🟢 Code exists, no subject doc

- **Handler**: `aspic_handler.py` (127 LOC) — `ASPICHandler`, SimpleAspicReasoner + DirectionalAspicReasoner
- **Plugin dédié**: `argumentation_analysis/plugins/aspic_plugin.py` — `ASPICPlugin` (fichier dédié!)
- **Agent**: Enregistré dans `agents/factory.py` — `capability="aspic_plus_reasoning"`
- **Invoker**: `_invoke_aspic` + `_python_aspic_fallback`
- **Registry**: `"aspic_handler"` → `["aspic_plus_reasoning"]`
- **State writer**: `_write_aspic_to_state` in `state_writers.py:466`
- **Workflow**: Node "aspic_analysis", prerequisite dans le DAG complet, multiple steps L1-L3
- **JAR**: `org.tweetyproject.arg.aspic-1.28-with-dependencies.jar`
- **Bonus**: `delp_handler.py` (164 LOC, DeLP — Defeasible Logic Programming)
- **Subject doc**: None
- **Assessment**: L'implémentation la plus riche de la section — a son propre plugin dédié, agent dédié, et est un nœud central du workflow DAG. **No angle mort.**

### 1.2.8 ADF (Abstract Dialectical Frameworks) — 🟢 Code exists, no subject doc

- **Handler**: `adf_handler.py` (161 LOC) — `ADFHandler`, 7 sémantiques + file parser
- **Plugin**: `TweetyLogicPlugin.analyze_adf()`
- **Invoker**: `_invoke_adf` in `invoke_callables.py:2597`
- **Registry**: `"adf_handler"` → `["adf_reasoning"]`
- **State writer**: `_write_adf_to_state` in `state_writers.py:551`
- **Workflow**: Node "adf" in full chain (aspic → aba → adf → bipolar)
- **JAR**: `org.tweetyproject.arg.adf-1.28-with-dependencies.jar`
- **Agent**: None dédié
- **Subject doc**: None
- **Assessment**: Fully wired. No angle mort.

### 1.2.9 Probabiliste — 🟢 Code exists, no subject doc

- **Handler**: `probabilistic_handler.py` (145 LOC) — `ProbabilisticHandler`, énumération exacte des sous-graphes (<15 args) + approximation fallback
- **Plugin**: `TweetyLogicPlugin.analyze_probabilistic()`
- **Invoker**: `_invoke_probabilistic` in `invoke_callables.py:2859`
- **Registry**: `"probabilistic_handler"` → `["probabilistic_argumentation"]`
- **State writer**: `_write_probabilistic_to_state` in `state_writers.py:508`
- **Workflow**: Node "probabilistic", L3d step, full chain
- **JAR**: `org.tweetyproject.arg.prob-1.28-with-dependencies.jar`
- **Agent**: None dédié
- **Subject doc**: None
- **Assessment**: Fully wired. La limite à 15 arguments est un design intentionnel (2^n énumération). No angle mort.

## Résultats — Sujet NON-traité, SANS code (vrai angle mort)

### 1.2.5 VAF (Argumentation Basée sur les Valeurs) — 🟠 Angle mort utile

- **Handler**: **AUCUN** — pas de `vaf_handler.py`
- **Agent**: **AUCUN**
- **Plugin**: **AUCUN** — pas de kernel function VAF
- **Workflow**: **AUCUN** — pas de node VAF
- **Registry**: **AUCUN** — pas de capability `vaf_reasoning` ou `value_based_argumentation`
- **JAR**: **AUCUN** — pas de `org.tweetyproject.arg.vaf*` (TweetyProject ne fournit pas ce module)
- **Subject doc**: None
- **SUIVI**: None

**ATTENTION**: `setaf_handler.py` est *set-based AF* (attaques collectives), PAS *value-based*.

**Analyse de la valeur potentielle**:

VAF (Bench-Capon, 2003) étend Dung avec :

1. Chaque argument est associé à une **valeur** (ex: justice, liberté, sécurité)
2. Les audiences ont des **préférences** sur les valeurs
3. Une attaque réussit seulement si la valeur de l'attaquant est **préférée** ou égale à celle de la cible

**Use case pipeline**: Le pipeline actuel analyse des discours politiques/argumentatifs. VAF apporterait :

- **Préférences de valeurs** : classifier les arguments par valeurs éthiques/politiques et résoudre les conflits via des préférences d'audience
- **Analyse multi-perspective** : un même framework peut produire des extensions différentes selon l'audience (conservateur vs progressiste)
- **Pont avec les sophismes** : un argument dont la valeur n'est pas préférée dans l'audience cible peut être qualifié de "persuasivement faible" — enrichit la détection de fallacies

**Faisabilité technique**: TweetyProject n'a pas de module `arg.vaf` natif. Implémentation options :

1. **Custom handler** — VAF est un Dung framework + value assignment + preference ordering. Le `af_handler.py` existant peut être étendu.
2. **Intégration logique de préférence** — le `modal_handler.py` (logique des préférences) ou le `cl_handler.py` (conditionnelle) peuvent fournir les préférences
3. **Temps estimé**: ~200-300 LOC handler + plugin + tests

**Classification**: 🟠 **Angle mort utile** — valeur ajoutée claire pour l'analyse de discours politiques, implémentation faisable via extension de `af_handler.py`.

## Wiring Matrix (enriched R293)

| Framework | Handler | Agent | Kernel Function | Workflow Pipeline | Registry | Wiring |
| --- | --- | --- | --- | --- | --- | --- |
| 1.2.1 Dung | `af_handler.py` + `dung_native.py` | ✅ Dung agent | ✅ `analyze_dung_framework` | ✅ dung_extensions node | ✅ `abstract_argumentation` | ✅ Full |
| 1.2.2 Bipolaire | `bipolar_handler.py` + `eaf_handler.py` | — | ✅ `analyze_bipolar_framework` | ✅ bipolar node (L3c) | ✅ `bipolar_argumentation` | ✅ Full |
| 1.2.3 Pondérée | `weighted_handler.py` + `social_handler.py` + `ranking_handler.py` | — | ✅ 3 functions | ✅ ranking+weighted+social | ✅ 3 caps | ✅ Full |
| 1.2.4 ABA | `aba_handler.py` | — | ✅ `analyze_aba` | ✅ aba node | ✅ `aba_reasoning` | ✅ Full |
| 1.2.5 VAF | **NONE** | **NONE** | **NONE** | **NONE** | **NONE** | ⚫ Missing |
| 1.2.6 ASPIC+ | `aspic_handler.py` | ✅ ASPIC agent | ✅ dedicated `aspic_plugin.py` | ✅ aspic_analysis node | ✅ `aspic_plus_reasoning` | ✅ Full |
| 1.2.7 Dialogique | `dialogue_handler.py` | ✅ Debate agents | ✅ `execute_dialogue` | ✅ dialogue node | ✅ `adversarial_debate` | ✅ Full |
| 1.2.8 ADF | `adf_handler.py` | — | ✅ `analyze_adf` | ✅ adf node | ✅ `adf_reasoning` | ✅ Full |
| 1.2.9 Probabiliste | `probabilistic_handler.py` | — | ✅ `analyze_probabilistic` | ✅ probabilistic node (L3d) | ✅ `probabilistic_argumentation` | ✅ Full |

## Synthèse C-02

**9/9 sujets couverts par l'analyse.** Résultat inattendu : **8/9 ont du code existant** dans le core, dont 7 sans sujet documenté mais avec handler + plugin + workflow + registry complets.

**2/9 Treated** (Dung A-02, Dialogique A-03 — cross-réf Epic A, intégration vérifiée).
**6/9 Code exists** (Bipolaire, Pondérée, ABA, ASPIC+, ADF, Probabiliste — tous fully wired, no angle mort technique).
**1/9 Angle mort utile** (VAF — aucun code ni JAR Tweety, mais valeur ajoutée claire pour l'analyse de discours politiques).

**Gap documentation**: Seul 1.2.7 (Dialogique) a un fichier sujet. Les 7 autres frameworks implémentés ne sont pas documentés comme sujets pédagogiques — même pattern que C-01 (code avant documentation).

**Découverte bonus**: Le core a aussi des handlers pour des frameworks hors-catalogue I-B : `eaf_handler.py` (Extended/Epistemic AF), `setaf_handler.py` (SETAF — attacks from sets), `delp_handler.py` (DeLP — Defeasible Logic Programming), `belief_revision_handler.py`. Ceux-ci sont implémentés mais pas dans le catalogue pédagogique original.

## Enhancement proposals

| # | Issue | Priorité | Justification |
| --- | --- | --- | --- |
| E1 | `enhancement(c-02): add VAF handler extending af_handler with value preferences` | **MEDIUM** | Seul framework I-B sans implémentation. Valeur ajoutée : analyse multi-perspective par valeurs d'audience. ~200-300 LOC. Nécessite custom handler (pas de JAR Tweety). |

## Fichiers sources

- `argumentation_analysis/agents/core/logic/` — handlers pour tous les frameworks (af, bipolar, weighted, social, ranking, aba, aspic, adf, probabilistic, eaf, setaf, delp)
- `argumentation_analysis/plugins/tweety_logic_plugin.py` — exposition SK (kernel functions pour 9+ frameworks)
- `argumentation_analysis/plugins/aspic_plugin.py` — plugin dédié ASPIC+
- `argumentation_analysis/plugins/ranking_plugin.py` — plugin dédié ranking
- `argumentation_analysis/orchestration/invoke_callables.py` — invoke callables pour tous les frameworks
- `argumentation_analysis/orchestration/state_writers.py` — state writers pour tous les frameworks
- `argumentation_analysis/orchestration/workflows.py` — DAG complet avec nodes interconnectés
- `argumentation_analysis/orchestration/registry_setup.py` — capability registration
- `libs/tweety/` — JARs Tweety `arg.{dung,bipolar,weighted,social,rankings,aba,aspic,adf,prob,extended,setaf,delp}-1.28`
