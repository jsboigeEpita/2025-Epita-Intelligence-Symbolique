# Audit C-02: Section I-B "Frameworks d'Argumentation" (9 sujets)

**Issue**: #780 (C-02) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 1.2.1 Dung | 🟢 Treated (subject + code) | #746 (A-02) |
| 1.2.2 Bipolaire | 🟡 Code exists, no subject doc | — |
| 1.2.3 Pondérée | 🟡 Code exists, no subject doc | — |
| 1.2.4 ABA | 🟡 Code exists, no subject doc | — |
| 1.2.5 VAF | 🔴 **Angle mort** — no code, no Tweety, no doc | — |
| 1.2.6 ASPIC+ | 🟡 Code exists, no subject doc | — |
| 1.2.7 Dialogique | 🟢 Treated (subject + code) | #747 (A-03) |
| 1.2.8 ADF | 🟡 Code exists, no subject doc | — |
| 1.2.9 Probabiliste | 🟡 Code exists, no subject doc | — |

## Résultats

### 1.2.1 Dung — 🟢 TREATED → Epic A #746 (A-02)
- **Code**: `dung_native.py` (277 LOC, native Python) + `af_handler.py` (229 LOC, Tweety) + `dung_viz.py`
- **Plugin**: `analyze_dung_framework` (`tweety_logic_plugin.py:102`)
- **State**: `dung_frameworks` (`shared_state.py:404,538`)
- **Student dir**: `abs_arg_dung/`

### 1.2.7 Dialogique — 🟢 TREATED → Epic A #747 (A-03)
- **Code**: `dialogue_handler.py` (153 LOC, Tweety `agents.dialogues`)
- **Plugin**: `execute_dialogue` (`tweety_logic_plugin.py:362`)
- **State**: `dialogue_results` (`shared_state.py:419,699`)
- **Student dir**: `1_2_7_argumentation_dialogique/`

### 1.2.2 Bipolaire — 🟡 CODE EXISTS
- **Handler**: `bipolar_handler.py` (92 LOC) + `eaf_handler.py` (135 LOC)
- **JAR**: `arg.bipolar-1.28`
- **Plugin**: `analyze_bipolar_framework` (`:212`), `analyze_epistemic_framework` (`:558`)
- **State**: `bipolar_results` (`shared_state.py:421,732`)
- **Gap**: Pas de fichier sujet, pas d'entrée SUIVI

### 1.2.3 Pondérée — 🟡 CODE EXISTS
- **Handler**: `weighted_handler.py` (140 LOC) + `ranking_handler.py` (120 LOC) + `social_handler.py` (126 LOC)
- **JAR**: `arg.weighted-1.28`, `arg.rankings-1.28`, `arg.social-1.28`
- **Plugin**: `analyze_weighted_framework` (`:505`), `rank_arguments` (`:187`), `analyze_social_framework` (`:530`)
- **State**: `ranking_results` (`shared_state.py:416,654`)
- **Gap**: Pas de fichier sujet

### 1.2.4 ABA — 🟡 CODE EXISTS
- **Handler**: `aba_handler.py` (165 LOC, `arg.aba-1.28`)
- **Plugin**: `analyze_aba` (`:239`)
- **State**: Pas de dimension dédiée dans `shared_state.py` (résultats pliés dans structures génériques)
- **Gap**: Pas de fichier sujet, pas de dimension état dédiée

### 1.2.5 VAF (Value-based AF) — 🔴 ANGLE MORT
- **Code**: AUCUN. Pas de handler `vaf_handler.py`, `value_based_handler.py` ou similaire
- **Tweety**: PAS de support natif. Recherche dans `tweety-full-1.29` → pas de `ValueBasedArgumentationFramework`/`Vaf`
- **ATTENTION**: `setaf_handler.py` est *set-based AF* (attaques collectives), PAS *value-based*
- **Valeur pipeline**: HAUTE — VAF connecte naturellement l'extraction de valeurs/enjeux existante (`stakes_extractor.py`, vertus qualité) avec les frameworks d'argumentation symboliques. Réduit à Dung filtré par ordre de préférence/audience → implémentable comme moteur natif Python (cf. `dung_native.py`)
- **Recommandation**: 🟠 Angle mort utile — candidat prioritaire pour nouveau sujet Epic A

### 1.2.6 ASPIC+ — 🟡 CODE EXISTS
- **Handler**: `aspic_handler.py` (127 LOC) + `aspic_plugin.py` (plugin dédié) + `delp_handler.py` (164 LOC, DeLP)
- **JAR**: `arg.aspic-1.28`
- **Plugin**: `analyze_aspic` (`:287`), `analyze_delp` (`:580`)
- **Gap**: Pas de fichier sujet

### 1.2.8 ADF — 🟡 CODE EXISTS
- **Handler**: `adf_handler.py` (161 LOC, `arg.adf-1.28`)
- **Plugin**: `analyze_adf` (`:264`)
- **Gap**: Pas de fichier sujet, pas de dimension état dédiée

### 1.2.9 Probabiliste — 🟡 CODE EXISTS
- **Handler**: `probabilistic_handler.py` (145 LOC, `arg.prob-1.28`)
- **Plugin**: `analyze_probabilistic` (`:336`)
- **State**: `probabilistic_results` (`shared_state.py:420,716`)
- **Gap**: Pas de fichier sujet

## Synthèse C-02

- **2/9 🟢 Treated** (Dung, Dialogique — sujets étudiants avec documentation)
- **6/9 🟡 Code exists** (implémentation complète, handlers + plugins + JARs, mais sans sujet pédagogique)
- **1/9 🔴 Angle mort** (VAF — pas de code, pas de support Tweety, haute valeur pipeline)

**Angle mort prioritaire**: 1.2.5 VAF est le seul gap technique du packet. Implémentation recommandée comme moteur natif Python s'appuyant sur `dung_native.py` + l'extraction de valeurs existante.

**Gap documentation**: Les 6 frameworks "code-only" (1.2.2/3/4/6/8/9) méritent des fichiers sujets dans `docs/projets/sujets/` — l'effort est minimal (le code existe déjà), la valeur pédagogique est réelle.

**Gap état mineur**: ABA (1.2.4) et ADF (1.2.8) n'ont pas de dimension `*_results` dédiée dans `shared_state.py`.

## Fichiers sources
- `argumentation_analysis/agents/core/logic/` — tous les handlers
- `argumentation_analysis/plugins/tweety_logic_plugin.py` — exposition SK (lignes 102-601)
- `argumentation_analysis/core/shared_state.py` — dimensions état (lignes 404-421)
- `libs/tweety/` — tous les JARs frameworks (`arg.{dung,bipolar,weighted,aba,aspic,adf,prob,rankings,social}-1.28`)
