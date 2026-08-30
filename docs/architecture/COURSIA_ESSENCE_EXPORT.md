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
| Tag recommandé par ce manifeste (2026-07-14) | ~~`coursia-essence-20260714`~~ — **jamais créé**, voir §3 |
| **Tag réellement poussé** | **`coursia-essence-20260830`** → `73d95d7b` (recréé — voir §3) |
| Carries | `#1443` (sanitization modal/FOL) + `#1444` (doc BNF) + `#1446` (Constat 5 conversational) + `#1447` (harness) |

> **Pourquoi rafraîchir.** Le pin `a8025f60` **précède** le fix `#1441`/`#1443` (« sanitize modal sort decls + FOL T/F bool constants »). Or `#1443` porte **directement dans la surface vendorée** — les deux handlers modal/FOL ci-dessous (§2). Rafraîchir le pin propage le fix en aval : un corpus qui faisait crasher le solveur modal sur le token `'p && q'` (sort declaration illégale) ou le parseur FOL sur `T`/`F` (Top/Bottom = `+`/`-`, pas `T`/`F`) est désormais neutralisé en amont du parseur.

---

## 2. Surface vendorée — mesurée, pas supposée

> **Autorité.** Le ledger `NOTICE-EPITA` (CoursIA) est la source de vérité du set exact.
> Cette section n'est plus une liste d'intention : elle est **rejouée** par
> `scripts/coursia/check_vendored_drift.py`, qui lit leur ledger et compare octet à octet.
> Ce qui suit est la sortie du 2026-08-30 (`--rev HEAD`). Pour la re-mesurer :
>
> ```bash
> python scripts/coursia/check_vendored_drift.py --self-check   # prouve l'instrument
> python scripts/coursia/check_vendored_drift.py                # table complete
> ```

### 2.1 Ce que le ledger tabule réellement — 15 fichiers

Leur repertoire porte 22 `.py` ; **15** sont tabulés dans `NOTICE-EPITA`, les 7 autres sont
de la glue CoursIA (`__init__`, `_config`, `_paths`, `_runner`, `_jvm_compat`,
`_jvm_setup_compat`, `_reporting_noop`) — hors périmètre malgré leur préfixe `_`.

| État | N | Fichiers |
|------|---|----------|
| `identical` | 7 | `_af_handler`, `_belief_revision_handler`, `_dialogue_handler`, `_probabilistic_handler`, `_ranking_handler`, `_informal_definitions`, `_taxonomy_sophism_detector` |
| `drifted` | 6 | `_adf_handler` (1 commit), `_fol_handler` (1), `_pl_handler` (1), `_tweety_initializer` (2), `_modal_handler` (3), `_tweety_bridge` (3) |
| `partial` | 2 | `_shared_state` (11 commits **et** 370 lignes absentes dès le pin), `_state_manager_plugin` (1 commit, 55 lignes absentes) |

### 2.2 Correction — la liste `logic/` annoncée était une supposition

La version précédente de cette section annonçait **14 fichiers** sous `logic/` comme
« l'essence Tweety/JPype ». La lecture firsthand de leur repertoire en donne **11**
(9 handlers + `tweety_bridge` + `tweety_initializer`). L'écart n'est pas un arrondi :

- **Annoncés mais jamais vendorisés** : `tweety_bridge_sk.py`, `modal_logic_agent.py`,
  `modal_kb_identifier_normalizer.py`, `fol_logic_agent.py`,
  `first_order_logic_agent_adapter.py`, `propositional_logic_agent.py`, `belief_set.py`,
  `logic_factory.py`, `pl_formula_sanitizer.py`. Tous existent chez nous ; aucun chez eux.
- **Vendorisés mais absents de la liste** : `adf_handler.py`, `af_handler.py`,
  `ranking_handler.py`, `belief_revision_handler.py`, `probabilistic_handler.py`,
  `dialogue_handler.py` — soit 6 des 9 handlers réellement portés.

C'était l'inventaire de *notre* essence, présenté comme *leur* surface.

⚠ **Conséquence sur le motif `#1443` (§2.3).** Le refresh est justifié par deux fichiers
porteurs des sanitizers. `fol_handler.py` est bien vendorisé (et dérivé d'1 commit) ;
`modal_kb_identifier_normalizer.py` **ne l'est pas**. Tirer le tag ne leur livrera donc pas
la moitié modale du fix — il faudrait d'abord qu'ils vendorisént ce fichier.

### 2.3 Cœur du refresh — fichiers touchés par `#1443` (HOT)

| Fichier upstream (nous) | Vendorisé ? | Fix `#1443` apporté |
|-------------------------|-------------|---------------------|
| `argumentation_analysis/agents/core/logic/fol_handler.py` | **oui**, dérivé 1 commit | `_sanitize_fol_bool_constants` — `Top`/`Bottom` = `+`/`-` (pas `T`/`F`, per BNF Tweety FOL) |
| `argumentation_analysis/agents/core/logic/modal_kb_identifier_normalizer.py` | **non** | `strip_illégal_sort_declarations` — retire le keyword `sort` (illégal en modal, sorts = `NAME={const}`) |

### 2.4 Les deux copies partielles — ce qui n'a jamais traversé

`_shared_state.py` et `_state_manager_plugin.py` ne sont pas des copies verbatim intégrales.
Leur propre colonne de taille l'enregistre (`1121 lignes` pour un amont de 1483) ; c'est leur
clause « Verbatim integrity: byte-for-byte identical » qui surestime. La distinction compte,
parce qu'un fichier `partial` ne se répare pas par un re-pull : la surface absente le restera.

Absent de `_shared_state.py` dès le pin `a8025f60` — alors même que ce commit **est** celui
qui a introduit cette machinerie (`#1334` phase 3/3, `#1345`) :

`DesignationRecord`, `record_désignation`, `_désignation_fingerprint`,
`backfill_last_désignation_for`, `_désignation_delta_summary` (trace de désignation CONV-C),
`record_cap_breach` (audit anti-runaway `#708`), `set_source_metadata`,
`add_structured_arg_status`.

Absent de `_state_manager_plugin.py` : le `@kernel_function record_désignation`.

C'est cohérent avec leur EPIC, qui exclut explicitement l'orchestration de l'import « essence » —
donc plausiblement un périmètre assumé, pas un accident. Mais cela déplace la conclusion de
`#1949` : la dérive n'est pas seulement « 11 commits de retard sur `shared_state` », c'est
**11 commits de retard sur une base qui n'a jamais porté la trace de désignation**.

### 2.5 Autres fichiers d'essence (hors `logic/`)

| Fichier | État mesuré |
|---------|-------------|
| `argumentation_analysis/core/shared_state.py` | `partial` — voir §2.4 |
| `argumentation_analysis/core/state_manager_plugin.py` | `partial` — voir §2.4 |
| `argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py` | `identical` (au saut de ligne final près) |
| `argumentation_analysis/agents/core/informal/informal_definitions.py` | `identical` |

---

## 3. Tag — état réel au 2026-08-30

> ⚠ **Le tag recommandé ci-dessous n'a jamais été créé.** #1451 a été fermée sur ce document, qui
> *proposait* un tag ; la procédure « une fois validé » n'a jamais été exécutée. Conséquence
> mesurable : la commande de re-pull documentée ne pouvait pas s'exécuter, et le pin CoursIA est
> resté figé sur `a8025f60` (2026-07-02) pendant huit semaines. Voir #1949.
>
> **Tag effectivement poussé le 2026-08-30** : `coursia-essence-20260830` → **`73d95d7b`**.
> Il a été **recréé** le jour même : sa première cible (`59f9cbd9`) ne portait pas encore
> `docs/coursia_contrib/quality_contract_note_argumentprofile.md`, que son propre message cite —
> soit exactement la faute reprochée à #1451 (un artefact dont la commande documentée ne
> s'exécute pas). Vérifié avant suppression : rien ne l'avait consommé.
>
> Dérive mesurée depuis leur pin `a8025f60` : **383 commits** au total, dont **21** touchant les
> **15 fichiers réellement tabulés** au ledger et **11** touchant `core/shared_state.py` seul.
>
> ⚠ Le message du tag annonce **32** pour la surface vendorée. Ce n'est pas faux mais c'est un
> compte **par répertoire** (`core/shared_state.py` + `agents/core/logic/` +
> `agents/core/informal/`), et il nomme lui-même ce périmètre. Ces répertoires contiennent des
> fichiers que CoursIA ne vendorise pas — le compte par fichier tabulé est **21**. Le tag n'a pas
> été rejoué pour autant : ses commandes s'exécutent et il énonce son propre périmètre. Le
> prochain tag doit utiliser 21, mesuré par `scripts/coursia/check_vendored_drift.py` (§2).
>
> Il porte deux changements qui concernent directement la copie vendorée :
> - **#1942 / #1946** — un seul contrat d'unité pour `overall` (somme des vertus en [0, 1] sur les
>   vertus évaluées ; les lecteurs divisent par `len(scores)`).
> - **#1951** — `get_weak_arguments`, le **5ᵉ lecteur**, était resté sur la lecture absolue dans le
>   fichier même de la déclaration, 580 lignes plus bas. Il lit désormais la fraction et **lève** sur
>   un seuil note-sur-10 au lieu de renvoyer silencieusement tous les arguments.
>
> ⚠ **À lire avant de re-pull `_shared_state.py`** : leur notebook `ArgumentProfile` appelle
> `get_weak_arguments(threshold=5.0)` avec un corrigé écrit. Cet appel lève désormais, **par
> conception**. La migration ne coûte rien pédagogiquement — vérifié numériquement, tous les verdicts
> affichés sont préservés. Cellules migrées :
> [`quality_contract_note_argumentprofile.md`](../coursia_contrib/quality_contract_note_argumentprofile.md).
> Garder l'échelle /10 côté enseignement reste un choix légitime : dans ce cas **ne pas** re-pull ce
> fichier, et le consigner dans `NOTICE-EPITA`.

### 3.1 Proposition d'origine (2026-07-14, historique)

```
tag:    coursia-essence-20260714    <-- JAMAIS CRÉÉ
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
| Source de vérité du set exact = `NOTICE-EPITA` (CoursIA) | ✓ — revue croisée **faite** : le §2 est désormais lu depuis leur ledger par `scripts/coursia/check_vendored_drift.py` |

> ⚠ **Limite qui reste ouverte, et qu'il faut nommer.** L'instrument existe ; **rien ne le lance
> automatiquement.** Notre CI n'a pas de checkout `D:\CoursIA`, donc le vérificateur ne peut pas
> tourner en intégration continue — il a un `--fail-on` prêt pour le jour où un runner y aura accès,
> mais aujourd'hui personne ne l'appelle. La prochaine dérive sera donc constatée quand quelqu'un
> regardera, exactement comme celle-ci. La différence avec l'état d'avant #1949 n'est pas que la
> dérive est surveillée : c'est que **regarder coûte désormais une commande au lieu d'une enquête**,
> et que le résultat est reproductible par un tiers au lieu d'être un jugement.
>
> Ne pas lire ce tableau comme « la dérive est sous contrôle ».

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
| [`formal_solvers_decide.ipynb`](../coursia_contrib/formal_solvers_decide.ipynb) | solveurs formels (PL SAT/UNSAT · FOL consistance EProver+Tweety · modal □/◇ Tweety+SPASS · Dung) | ✓ livré, exécuté firsthand | code local `argumentation_analysis.agents.core.logic` (refresh essence à venir) |

**DoD CI-2 respecté** (par notebook) : tourne firsthand (cellules exécutées, sorties présentes), textes **synthétiques domaine-public uniquement** (aucun corpus chiffré, aucun `raw_text`).

- **governance** — la méthode de vote décide du gagnant (pluralité élit le perdant de Condorcet ; Borda/Condorcet élisent le gagnant de Condorcet), le paradoxe de Condorcet (cycle sans gagnant), la manipulabilité de la Borda (backfire du vote stratégique). Scénario : un club de robotique choisit un menu.
- **counter-argument** — un modèle pondéré à 5 critères (pertinence / force logique / persuasion / originalité / clarté) départage trois contre-arguments de qualité contrastée (A étude statistique > C reductio > B ad hominem) **de façon déterministe, sans LLM**. Chaque critère capte une dimension distincte ; l'évaluateur émet des recommandations ciblées sur les critères faibles. Scénario : réfuter « le télétravail réduit la productivité ».
- **formal_solvers_decide** (CI-3 #1466) — des **vrais solveurs formels** rendent un verdict tranché sur la même carte d'arguments (club d'échecs) : **PL** (cadical195/PySAT) SAT vs UNSAT + entailment ; **FOL** (EProver + Tweety SimpleFolReasoner, cross-check concordant) consistante vs inconsistante (`∀X(Registers(X)⇒Pays(X))` + Bob inscrit impayé → inconsistance prouvée) ; **modal** (Tweety SimpleMlReasoner + SPASS, cross-check) `[](Rain⇒Wet)` consistante vs `Rain ∧ ¬Rain` inconsistante ; **bonus Dung** extension préférée en pur Python. Anti-théâtre : aucun verdict codé en dur ; solveur absent → honnête-dégradé signalé.

> **Note d'import.** Chaque notebook localise la racine du dépôt en remontant depuis son CWD et importe son module essence. Lors du refresh du pin essence, les imports pointeront vers l'`argumentation_lib/` vendoré — surfaces API identiques (`Agent`/`GOVERNANCE_METHODS`/`approval_voting`… pour governance ; `Argument`/`CounterArgument`/`CounterArgumentEvaluator.evaluate` pour contre-argument).
