# R5 volet-1b — DERIVED virtuous confirmation (pipeline run)

**Epic #1134 (Restitution)** — Track R5 #1139 volet-1b. Worker `myia-po-2025`,
dispatch coordinateur R426/R427 (ACK budget ~$2, file-disjoint, lane lourde).
Suite naturelle de R5 volet-1 (PR #1145) : faire tourner le pipeline sur les top
candidats et confirmer lesquels sont réellement vertueux.

**Privacy HARD** : IDs opaques uniquement (`src_N_ext_M`, format `src0_ext0`).
Aucun nom de source, aucun prose, aucune valeur de texte. Dataset chiffré
consommé in-memory. Rapport agrégé opaque-only.

---

## Contexte

R5 volet-1 a livré un **générateur de candidats** cheap (0 LLM/0 JVM,
`argumentation_analysis/reporting/restitution/virtuous_identification.py`) qui
narrow le corpus aux extraits « worth confirming ». Spec §5.1 : le flag vertueux
est **DERIVED du pipeline output**, jamais asserté sur preuve lexicale. Volet-1b
est la **confirmation DERIVED** : run pipeline sur les top candidats.

Le caveat central volet-1 (« un texte à `density 0.0` = quasi-certainement un
mismatch langue/registre, PAS de la vertu ; le screen est recall-oriented, pas un
classifieur ») est ici **testé contre le vrai moteur**.

## Méthode

Workflow **custom minimal chirurgical** (passé via `custom_workflow=` à
`run_unified_analysis`) — exactement le signal spec §5.1, ~1/3 du coût de
`spectacular` (pas de debate/governance/jtms/narrative/synthesis overhead) :

```
extract (fact_extraction)
├─ hierarchical_fallacy (hierarchical_fallacy_detection)   → fallacy_count
├─ nl_to_logic (nl_to_logic_translation)
│  ├─ pl (propositional_logic)                              → axe formel
│  └─ fol (fol_reasoning)                                   → axe formel
└─ quality (argument_quality)                               → axe quality
```

Flag **DERIVED** spec §5.1 : `CONFIRMED_VIRTUOUS` iff `fallacy_count==0` AND axe
formel non-trivial (nl_to_logic COMPLETED + (pl|fol) COMPLETED non-empty) AND
quality non-trivial (`argument_quality_scores` populated).

4 candidats (cheapest-first : tri char_count asc), timeout borné 420s chacun,
run séquentiel (évite race JPype + pic budget). Privacy : redact-filter sur
fenêtres 40-chars du prose, stdout redacted, outputs gitignored.

## Résultats

| opaque_id | chars | verdict | t(s) | fallacy_count | formal(nltl/pl/fol) | quality_count | flag |
|---|---:|---|---:|---:|---|---:|---|
| src_3_ext_3 | 4274 | COMPLETED | 298.8 | 12 | completed/completed/completed | 8 | NOT_VIRTUOUS |
| src_2_ext_1 | 4547 | COMPLETED | 295.3 | 11 | completed/completed/completed | 6 | NOT_VIRTUOUS |
| src_0_ext_4 | 4688 | TIMED_OUT_420s | 420.1 | 0 | absent/absent/absent | 0 | INCONCLUSIVE |
| src_3_ext_1 | 5049 | COMPLETED | 334.8 | 10 | completed/completed/completed | 8 | NOT_VIRTUOUS |

**Synthèse : 0 CONFIRMED_VIRTUOUS · 0 PARTIAL · 3 NOT_VIRTUOUS · 1 INCONCLUSIVE (timeout).**

> `src_0_ext_4` a TIMED_OUT avant les phases formelles → `fallacy_count=0` /
> `formal=absent` sont des **artefacts du timeout**, pas une évaluation de vertu.
> Flag script brut disait « formal trivial » (bug `_derive_flag` : timeout ≠
> formal-trivial) ; corrigé en INCONCLUSIVE. Le timeout lui-même est un diagnostic
> utile : la descente `hierarchical_fallacy` dépasse 420s même sur 4.7k chars
> (famille FB-35/36 — coût de descente, non size-bound).

## Conclusion

**0/4 CONFIRMED_VIRTUOUS.** Les candidats density-0.0 du screen cheap volet-1
sont des **faux positifs** : le VRAI pipeline trouve **10-12 fallacies
structurelles** chacun (ad hominem, jeu de pouvoir, attaque personnelle) — une
rhétorique agressive dont les sophismes ne sont **pas lexicaux** (les signaux
« tous / experts / peur » du screen ne les attrapent pas). Le caveat volet-1 est
**confirmé par la preuve** : le screen lexical est recall-oriented, pas un
classifieur.

**Réponse à la question owner** « le dataset en contient, peut-être pas assez » :
les extraits à faible signal lexical du corpus ne sont PAS vertueux — ce sont des
discours agressifs. Le corpus semble **manquer de textes argumentatifs
vertueux** parmi les low-signal. Per spec §5.1, R5 **rapporte ce gap fail-loud**,
ne synthétise JAMAIS un texte vertueux.

**Le moteur tourne sur ces textes** : axe formel non-trivial (pl/fol COMPLETED) +
quality populated (6-8) sur les 3 complétés → la capacité restitution/moteur est
OK ; le gap est la **composition du corpus**, pas la capacité de l'engine.

## Caveats & diagnostics capturés

- **Caveat R3** (`argument_quality_scores` vide, per dispatch coord R426) **n'a
  PAS déclenché** sur ce path — quality était populated (6-8) sur les 3 complétés.
  Le diagnostic empty-quality est donc scoped à un autre path (pas celui-ci).
  Capture honnête : quality disponible ici. Pas de fix (collision R3 évitée).
- **Budget** : pipeline a utilisé le path **OpenAI primaire** (gpt-5-mini, per
  CLAUDE.md), pas OpenRouter (solde OpenRouter inchangé $149.84). Spend estimé
  négligeable (~$0.02, ~24 calls gpt-5-mini), bien dans l'ACK ~$2.
- **Privacy** : leak audit 0/4 sur les outputs formels surfacés. Les sorties
  brutes (state_snapshot, prompts LLM) restent gitignored sous
  `argumentation_analysis/evaluation/results/r5_derived/`. Le rapport committed
  est opaque-only.

## Artefacts

- Runner (throwaway, gitignored) : `.cache/_r5_derived_run.py` + dry-run.
- Rapport détaillé (gitignored, privacy) :
  `argumentation_analysis/evaluation/results/r5_derived/r5_derived_virtuous_report.md`
  + agrégat JSON + raw per-candidate.
- **Ce rapport** (committed, opaque) : `docs/reports/R5_DERIVED_VIRTUOUS_REPORT.md`.

## Leçons

- **Le screen lexical recall-oriented produit des faux positifs structurels** :
  la rhétorique agressive (ad hominem, power-play) n'utilise pas les marqueurs
  lexicaux que le screen cheap détecte. Un générateur de candidats ne suffit pas
  pour identifier la vertu — seule l'évaluation pipeline (DERIVED) tranche.
- **`_derive_flag` bug** : un timeout (phases formelles absentes) ≠ axe formel
  trivial. Distinguer « phase absent (timeout/error) » de « phase
  completed-but-trivial ». Corrigé dans le rapport (INCONCLUSIVE), à encoder
  dans tout futur runner réutilisable.
- **`argument_quality_scores` n'est pas universellement vide** : le caveat R3 est
  path-specific, pas global. Ne pas assumer quality indisponible.
