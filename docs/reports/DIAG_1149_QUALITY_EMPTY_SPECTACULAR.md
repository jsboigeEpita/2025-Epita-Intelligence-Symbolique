# DIAG #1149 — `argument_quality_scores` vide sur spectacular (peuplé sur custom/DERIVED)

**Epic #1134 (Restitution)** — Diagnostic read-only track #1149. Worker
`myia-po-2023`, dispatch coordinateur R430. Lane file-disjoint des actes
(po-2025 possède les 5 fichiers infra pour R4/R6). **Zéro edit des 5 fichiers
infra** dans ce track — audit pur, correctif proposé localisé.

**Privacy HARD** : IDs opaques uniquement (`arg_N`, `corpus_A`). Aucun nom de
source, aucun `raw_text`, aucune prose de corpus. Reproduction déterministe
(0 LLM, 0 JVM, 0 dataset) — le diagnostic porte sur le wiring, pas le contenu.

---

## TL;DR

Deux findings, un **prouvé** et un **non-prouvé (à honnêtement réviser)** :

1. **FINDING A — BUG de schéma writer/reader (PROUVÉ, universel, les DEUX paths).**
   Le state-writer `_write_quality_to_state` stocke les vertus sous la clé
   **`scores`**, mais le lecteur de l'Acte II `build_act2_evidence` lit
   **`scores_par_vertu`**. Conséquence : `arg.virtues` est **TOUJOURS `{}`**,
   même quand `argument_quality_scores` est populé. Le LLM tisse alors
   « vertus : — » au lieu des vraies vertus (clarté/cohérence/pertinence…).
   **Ce bug est présent sur custom ET spectacular** — il n'est pas la cause de
   l'empty, mais il appauvrit silencieusement la restitution qualité partout.

2. **FINDING B — « spectacular = empty » est NON-PROUVÉ par run direct.**
   La seule preuve empirique dont on dispose (DERIVED #1146) montre quality
   **populé (6-8)** sur le path **custom**. L'affirmation « vide sur spectacular »
   est une **inférence** (po-2025 R3 caveat depuis le dispatch coord), pas une
   observation de run spectacular direct. Le mécanisme *prouvé* par lequel
   `argument_quality_scores` devient `{}` est un échec/timeout de phase
   (`workflow_dsl.py:651` ne déclenche le writer QUE si `status==COMPLETED`),
   mais les deps qualité (`textstat` + `fr_core_news_sm`) **sont disponibles**
   dans `projet-is` sur ce cluster → l'évaluateur ne lève pas ici. **Conclusion
   honnête** : l'empty spectacular est soit (a) le Finding A mal étiqueté
   (« vertus vides » lu comme « qualité vide »), soit (b) un échec de phase
   réel qu'aucun run n'a capturé. Un run spectacular direct est nécessaire pour
   trancher — ce diagnostic recommande de NE PAS appliquer un fix basé sur (b)
   tant qu'il n'est pas observé (anti-pendule #1019/#369).

---

## 1. Contexte

Le run DERIVED (R5 volet-1b, PR #1146) a observé `argument_quality_scores`
**populé** (mean ~1.6-1.7, 3-8 args) sur un workflow custom minimal
(`extract → {hierarchical_fallacy, nl_to_logic→{pl,fol}, quality}`). Le plugin
Acte II (R3 #1147) et l'Acte III (R4, en cours) doivent fail-loud « non
concluable sur l'axe qualité ici » **sur spectacular** — ce qui appauvrit la
restitution. L'issue #1149 demande : pourquoi la phase `quality` produit un
`argument_quality_scores` vide sur le path `spectacular` spécifiquement ?

## 2. Méthode (triple grounding)

- **Technique** : Read/Grep du flux `quality` phase → invoke callable → state
  writer → clé `argument_quality_scores` → lecteur act2/renderer/state_adapter.
- **Conversationnel** : dashboard workspace (R425-R430), report DERIVED #1146,
  dispatch R430.
- **Reproduction déterministe** : probe isolant le writer + le reader du pipeline
  live (`.cache/_diag1149_quality_probe.py`, 0 LLM/JVM/dataset). Trois sondes :
  A (writer sur output COMPLETED), B (lecteur act2 sur le state populé), C
  (gate executor `status==COMPLETED`).

## 3. Le flux de données qualité

```
build_*_workflow:  .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        │  (IDENTIQUE spectacular L713 et custom — même wiring)
        ▼
WorkflowExecutor._store_phase_result (workflow_dsl.py:638)
        │  gate (ligne 651): IF result.status == PhaseStatus.COMPLETED:
        │                     THEN state_writers["argument_quality"](output, state, ctx)
        │  (FAILED/TIMED_OUT/SKIPPED → writer JAMAIS appelé)
        ▼
_invoke_quality_evaluator (invoke_callables.py:437)
   reads phase_extract_output["arguments"]  + phase_hierarchical_fallacy_output
   → per_argument_scores{arg_N: {scores_par_vertu, note_finale, llm_assessment}}
        ▼
_write_quality_to_state (state_writers.py:58)
   for arg_id in per_argument_scores:
       scores = result.get("scores_par_vertu", {})
       overall = result.get("note_finale", 0.0)
       if isinstance(overall,(int,float)) and (scores or overall>0):   # ligne 74
           state.add_quality_score(arg_id, scores, float(overall), ...)
        ▼
UnifiedAnalysisState.add_quality_score (shared_state.py:517)
   entry = {"scores": scores, "overall": overall}    # ← stocké sous "scores"
   self.argument_quality_scores[store_id] = entry
        ▼
build_act2_evidence (act2_narrative_plugin.py:207)
   quality = getattr(state, "argument_quality_scores", {})
   quality_axis_available = bool(quality) and isinstance(quality, dict)   # ligne 210
   qs = quality.get(arg_id)
   spv = qs.get("scores_par_vertu")   # ← lit "scores_par_vertu"  (ligne 295)
   ov = qs.get("overall")              # ← lit "overall"            (ligne 300)
```

## 4. Finding A — BUG de schéma (prouvé par reproduction)

### Preuve (Probe A + Probe B)

Probe A alimente le writer avec un output qualité réaliste (format
`per_argument_scores` produit par `_invoke_quality_evaluator`). Le writer
popule correctement :

```
argument_quality_scores = {
  'arg_1': {'scores': {'clarte': 2.0, 'coherence': 1.5, 'pertinence': 2.0},
            'overall': 1.83,
            'llm_assessment': 'weak evidence'}
}
```

Probe B alimente ce state populé à `build_act2_evidence` :

```
quality_axis_available: True
arg0.quality_available: True
arg0.quality_overall: 1.83
arg0.virtues: {}        ← reader lit 'scores_par_vertu' → {} (toujours vide)
```

### Cause racine

Désalignement de clé entre writer et reader :

| Rôle | Fichier:Ligne | Clé écrite/lue |
|------|---------------|----------------|
| writer (`add_quality_score`) | `shared_state.py:536` | **`scores`** |
| reader (`build_act2_evidence`) | `act2_narrative_plugin.py:295` | **`scores_par_vertu`** |

`overall` correspond des deux côtés → `quality_overall` est correct, mais
`virtues` est **toujours `{}`**.

### Impact

- `quality_axis_available = True` (le dict est non-vide), donc l'acte ne
  fail-loud **pas** sur ce bug — mais le battement de mouvement tisse
  « vertus : — » (ligne 460 `", ".join(...virtues.keys()) or "—"`) au lieu des
  vraies vertus. La qualité est **silencieusement appauvrie** partout (custom
  ET spectacular). C'est un bug réel, orthogonal au symptôme « empty ».
- Le state_adapter (`state_adapter.py`) copie `argument_quality_scores` tel
  quel — aucun correctif en aval.

### Correctif localisé proposé (append-only-compatible, track séparé)

Le reader est le côté à corriger (la clé writer `scores` est l'API canonique de
`add_quality_score`, consommée ailleurs via `argument_quality_scores[arg]` dans
shared_state `get_argument_profile` ligne 900). Correction : dans
`act2_narrative_plugin.py:295`, lire la clé réelle :

```python
spv = qs.get("scores") or qs.get("scores_par_vertu")  # canonical + legacy
```

(Bidirectionnel défensif : `scores` canonical, `scores_par_vertu` legacy pour
toute source externe.) **1-liner, append-only, fichier de l'Acte II** — pas un
des 5 fichiers infra verrouillés par po-2025 (mais po-2025 possède
`act2_narrative_plugin.py` via R3/R4 → **sérialiser derrière R4**).

## 5. Finding B — « spectacular = empty » NON-PROUVÉ

### Preuve (Probe C — le mécanisme d'empty)

Le writer n'est appelé **que si** `result.status == PhaseStatus.COMPLETED`
(`workflow_dsl.py:651`). Reproduction du gate executor :

```
status=COMPLETED  -> argument_quality_scores populated: True  (len=1)
status=FAILED     -> argument_quality_scores populated: False (len=0)
status=TIMED_OUT  -> argument_quality_scores populated: False (len=0)
```

→ Mécanisme prouvé : une phase qualité FAILED ou TIMED_OUT laisse
`argument_quality_scores = {}`, ce qui déclenche le fail-loud act2
(`quality_axis_available = False`, ligne 619 « non concluable »).

### MAIS : pourquoi spectacular échouerait-il et pas custom ?

**C'est ici que le diagnostic doit être honnête (anti-pendule #1019/#369).**

1. **Pas de timeout spécifique à quality** sur spectacular
   (`workflows.py:713` — aucun `timeout_seconds`, contrairement à pl/fol/counter).
   → L'empty spectacular n'est pas un timeout de la phase quality elle-même.

2. **Les deps qualité sont disponibles** dans `projet-is` sur ce cluster :
   `textstat OK`, `fr_core_news_sm OK` (vérifié). L'évaluateur
   (`quality_evaluator.py:96,128`) lève `RuntimeError` SEULEMENT si
   textstat/spacy/model manquent — ils ne manquent pas ici.

3. **Aucun run spectacular direct** n'a capturé `argument_quality_scores={}`.
   L'affirmation originelle (po-2025 R3 caveat) est une **inférence depuis le
   dispatch coord R426**, pas une observation. Le seul run enregistré (DERIVED
   #1146) a utilisé le path **custom** où quality était **populé**.

### Conclusion honnête

L'empty spectacular est **non-prouvé**. Trois explications plausibles, par
probabilité décroissante :

| # | Explication | Preuve | Statut |
|---|-------------|--------|--------|
| B1 | Le Finding A (virtues vides) a été **mal étiqueté** « qualité vide » — l'acte paraît « non concluable » non parce que quality est absent mais parce que le tissage sort appauvri | Finding A prouvé | **Probable** |
| B2 | Sur un run spectacular réel, la phase quality échoue/timed-out (race JVM, OOM, exception `_llm_enrich_quality` API) → writer sauté | Mécanisme prouvé (Probe C), déclencheur non observé | **Possible, non prouvé** |
| B3 | `phase_extract_output["arguments"]` est vide sur spectacular (extract échoue avant) → l'évaluateur itère 0 args → `per_argument_scores={}` → writer no-op | Hypothèse, non observée | **Spéculatif** |

**Recommandation** : NE PAS appliquer de fix basé sur B2/B3 tant qu'aucun run
spectacular direct n'a capturé l'empty. Un run spectacular **avec capture de
`phase_quality_output` + `results["quality"].status`** est le seul probe qui
tranche (B1 vs B2/B3). Le Finding A, lui, est à corriger indépendamment
(propre, prouvé, append-only).

## 6. DoD checklist

- [x] **Cause racine prouvée** (phase/callable/clé exacte + repro) : Finding A
      — clé `scores` (writer, `shared_state.py:536`) vs `scores_par_vertu`
      (reader, `act2_narrative_plugin.py:295`). Reproduction déterministe
      Probe A/B/C, 0 LLM/JVM/dataset.
- [x] **Correctif proposé décrit** (localisé, append-only-compatible) : reader
      lit `qs.get("scores") or qs.get("scores_par_vertu")` — 1-liner, fichier
      act2 (sérialiser derrière R4, pas un des 5 fichiers infra).
- [x] **Comparaison documentée** : custom popule (DERIVED #1146) ; spectacular
      empty = **non-prouvé par run direct** (Finding B honnêtement révisé).
- [x] **Aucun edit des 5 fichiers infra** (`shared_state.py`, `invoke_callables.py`,
      `registry_setup.py`, `state_writers.py`, `workflows.py`) — audit pur.

## 7. Leçons

- **« Verify the verification » (FB-39, REUSABLE)** : l'affirmation « spectacular
  = qualité vide » s'est propagée R426→R427→R3 caveat→#1149 sans run direct.
  Comme R408 (paren-over-spacing, faux), c'était une inférence non vérifiée.
  Seul le probe direct tranche. Ne pas appliquer un fix sur une inférence
  non observée.
- **Schéma writer/reader désaligné = bug silencieux** : `quality_axis_available`
  reste `True` (dict non-vide) même quand le contenu est inutilisable → le
  fail-loud ne déclenche pas → dégradation silencieuse (anti-pattern #1019).
  Le gate devrait vérifier le *contenu utilisable* (virtues + overall), pas
  juste `bool(dict)`.

## 8. Artefacts

- Probe de reproduction (throwaway, gitignored) :
  `.cache/_diag1149_quality_probe.py` (Probe A/B/C, exécutable standalone).
- **Ce rapport** (committed, opaque) :
  `docs/reports/DIAG_1149_QUALITY_EMPTY_SPECTACULAR.md`.
