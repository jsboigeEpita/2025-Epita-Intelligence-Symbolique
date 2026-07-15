# CoursIA Essence Export — Manifest & Pin Refresh

**Epic** : #1448 · **Track** : CI-1 (#1451) · **Lane** : po-2025.
**Date** : 2026-07-14.
**Auteur** : `Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique`.

> **Posture.** CoursIA (dépôt du professeur) vendorise une *essence curée* d'une quinzaine de nos fichiers dans `argumentation_lib/`, épinglée à un commit via son ledger `NOTICE-EPITA`. Ce document rend notre amont **pull-friendly** : il liste la surface vendorée, mappe chaque fichier à son upstream, et propose un **tag nommé** portant les derniers fixes — pour que le professeur re-pull depuis un tag nommé (pas un SHA nu).
>
> **Ce track est 100% amont** (côté notre dépôt). **Aucune** écriture dans `D:\CoursIA`, **aucun** changement de classpath / `jvm_setup.py` (candidat D, gardé séparé — risque crash natif).

---

## 1. État du pin actuel

| Champ | Valeur |
|-------|--------|
| Pin CoursIA (`NOTICE-EPITA`) | `a8025f60` — `feat(conv-c): de-templatised PM prompt…` (#1345) |
| Date du pin | 2026-07-02 |
| Tag recommandé (ce manifeste) | **`coursia-essence-20260714`** |
| Cible du tag | `a450496a` (origin/main courant) |
| Carries | `#1443` (sanitization modal/FOL) + `#1444` (doc BNF) + `#1446` (Constat 5 conversational) + `#1447` (harness) |

> **Pourquoi rafraîchir.** Le pin `a8025f60` **précède** le fix `#1441`/`#1443` (« sanitize modal sort decls + FOL T/F bool constants »). Or `#1443` porte **directement dans la surface vendorée** — les deux handlers modal/FOL ci-dessous (§2). Rafraîchir le pin propage le fix en aval : un corpus qui faisait crasher le solveur modal sur le token `'p && q'` (sort declaration illégale) ou le parseur FOL sur `T`/`F` (Top/Bottom = `+`/`-`, pas `T`/`F`) est désormais neutralisé en amont du parseur.

---

## 2. Surface vendorée — mapping upstream

> **Note d'autorité.** Le ledger `NOTICE-EPITA` (CoursIA) reste la source de vérité pour le **set exact** des fichiers vendorés. Cette liste documente la *catégorie d'essence* et identifie les fichiers **touchés par `#1443`** (le motif du refresh). Une revue croisée avec `NOTICE-EPITA` reste recommandée avant le re-pull.

### 2.1 Cœur du refresh — fichiers touchés par `#1443` (HOT)

Ces deux fichiers sont la **raison d'être** du pin refresh : ils portent les sanitizers qui neutralisent les `ParserException` modal/FOL.

| Fichier upstream (nous) | Rôle | Fix `#1443` apporté |
|-------------------------|------|---------------------|
| `argumentation_analysis/agents/core/logic/fol_handler.py` | Handler FOL (EProver/Tweety) | `_sanitize_fol_bool_constants` — `Top`/`Bottom` = `+`/`-` (pas `T`/`F`, per BNF Tweety FOL) |
| `argumentation_analysis/agents/core/logic/modal_kb_identifier_normalizer.py` | Normaliseur KB modal | `strip_illegal_sort_declarations` — retire le keyword `sort` (illégal en modal, sorts = `NAME={const}`) |

### 2.2 Handlers logiques (essence canonique)

Le cœur logique vendorisé se concentre dans `argumentation_analysis/agents/core/logic/`. Les fichiers suivants constituent l'essence Tweety/JPype :

| Fichier | Axe formel |
|---------|------------|
| `tweety_bridge.py` | Pont Java/JPype ↔ Tweety (FOL parsing, belief sets, reasoners) |
| `tweety_initializer.py` | Initialisation JVM + classes Tweety |
| `tweety_bridge_sk.py` | Variante Semantic Kernel |
| `fol_handler.py` | ⚠ `#1443` (voir §2.1) |
| `modal_handler.py` | Raisonnement modal (S5) |
| `modal_logic_agent.py` | Agent modal |
| `modal_kb_identifier_normalizer.py` | ⚠ `#1443` (voir §2.1) |
| `pl_handler.py` | Logique propositionnelle (PySAT) |
| `fol_logic_agent.py` / `first_order_logic_agent_adapter.py` | Agents FOL |
| `propositional_logic_agent.py` | Agent PL |
| `belief_set.py` | Structures de belief sets |
| `logic_factory.py` | Fabrique d'agents logiques |
| `pl_formula_sanitizer.py` | Sanitization formules PL |

### 2.3 Autres fichiers d'essence (hors `logic/`)

| Fichier | Rôle |
|---------|------|
| `argumentation_analysis/core/shared_state.py` | `UnifiedAnalysisState` — état partagé multi-dimensions |
| `argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py` | Détection 8 familles de sophismes |

---

## 3. Tag recommandé

```
tag:    coursia-essence-20260714
target: a450496a  (origin/main, 2026-07-14)
carries: #1443 (modal/FOL sanitization) — porté directement dans la surface vendorée
         #1444 (doc FOL BNF Top/Bottom + MlParser gotchas)
         #1446 (Constat 5 — degraded ≠ used, conversational path)
         #1447 (harness ATT-3 reproductible)
```

> **Procédure.** Le tag est **proposé dans la PR**, **non poussé sans validation coord**. Une fois validé :
> ```bash
> gh auth switch --user jsboigeEpita
> git tag -a coursia-essence-20260714 a450496a -m "CoursIA essence export — carries #1443 modal/FOL sanitization. See docs/architecture/COURSIA_ESSENCE_EXPORT.md"
> git push origin coursia-essence-20260714
> ```
> Le professeur re-pull alors depuis le tag nommé : `git checkout coursia-essence-20260714 -- argumentation_lib/...`.

---

## 4. Limites & contraintes respectées

| Contrainte | Statut |
|------------|--------|
| Aucune écriture dans `D:\CoursIA` (amont-only) | ✓ — ce track ne touche que notre dépôt |
| Pas de changement classpath / `jvm_setup.py` (candidat D) | ✓ — seul le manifeste + tag + doc stale |
| IDs opaques, pas de corpus | ✓ — aucun contenu de dataset |
| Source de vérité du set exact = `NOTICE-EPITA` (CoursIA) | ☐ revue croisée recommandée au re-pull |

---

## 5. Voir aussi

- [`TWEETY_CAPABILITY_MAP.md`](TWEETY_CAPABILITY_MAP.md) — map modules Tweety ↔ slots Lego (corrigé : 1.28 + 1.29, 2 JARs).
- [`docs/technical/tweety_bridge.md`](../technical/tweety_bridge.md) — §6 : FOL Top/Bottom BNF + gotchas MlParser (`#1444`).
- [`docs/coursia_contrib/governance_voting_methods.ipynb`](../coursia_contrib/governance_voting_methods.ipynb) — notebook pédagogique CI-2 (axe gouvernance, corpus-free).
- Issue `#1451` (track CI-1) · Issue `#1458` (track CI-2) · Epic `#1448` (CoursIA pin refresh).
- Issues `#1441` / `#1443` — sanitization modal-sort + FOL-bool (la surface portée par ce refresh).

---

## 6. Contributions pédagogiques corpus-free (CI-2)

Le track CI-2 (#1458) prépare des **notebooks pédagogiques** illustrant des axes vendorés-mais-non-enseignés, livrés comme **propositions amont** (dans `docs/coursia_contrib/`, jamais poussés sur CoursIA). Le professeur peut les importer dans CoursIA lors d'un re-pull coordonné.

| Notebook | Axe | Statut | Pin d'exécution |
|----------|-----|--------|-----------------|
| [`governance_voting_methods.ipynb`](../coursia_contrib/governance_voting_methods.ipynb) | governance (7 méthodes de vote + théorie du choix social) | ✓ livré, exécuté firsthand | code local `argumentation_analysis.agents.core.governance` (refresh essence à venir) |
| [`counter_argument_quality.ipynb`](../coursia_contrib/counter_argument_quality.ipynb) | contre-argument (évaluateur qualité 5 critères pondérés) | ✓ livré, exécuté firsthand | code local `argumentation_analysis.agents.core.counter_argument` (refresh essence à venir) |

**DoD CI-2 respecté** (par notebook) : tourne firsthand (cellules exécutées, sorties présentes), textes **synthétiques domaine-public uniquement** (aucun corpus chiffré, aucun `raw_text`).

- **governance** — la méthode de vote décide du gagnant (pluralité élit le perdant de Condorcet ; Borda/Condorcet élisent le gagnant de Condorcet), le paradoxe de Condorcet (cycle sans gagnant), la manipulabilité de la Borda (backfire du vote stratégique). Scénario : un club de robotique choisit un menu.
- **counter-argument** — un modèle pondéré à 5 critères (pertinence / force logique / persuasion / originalité / clarté) départage trois contre-arguments de qualité contrastée (A étude statistique > C reductio > B ad hominem) **de façon déterministe, sans LLM**. Chaque critère capte une dimension distincte ; l'évaluateur émet des recommandations ciblées sur les critères faibles. Scénario : réfuter « le télétravail réduit la productivité ».

> **Note d'import.** Chaque notebook localise la racine du dépôt en remontant depuis son CWD et importe son module essence. Lors du refresh du pin essence, les imports pointeront vers l'`argumentation_lib/` vendoré — surfaces API identiques (`Agent`/`GOVERNANCE_METHODS`/`approval_voting`… pour governance ; `Argument`/`CounterArgument`/`CounterArgumentEvaluator.evaluate` pour contre-argument).
