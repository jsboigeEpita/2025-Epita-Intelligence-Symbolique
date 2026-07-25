# S6 — Labelling trajectory under sequential arrival: pedagogy design

**Scope**: a **pedagogical design** — how to present the Dung labelling-trajectory
concept (`IN / OUT / UNDEC` evolving as arguments arrive one by one) in the
CoursIA notebook `Dung_AF_Semantics.ipynb`, anchored on its **Cell [22]**
labelling-trajectory stub.
**Feeds**: CoursIA wrap issue [`jsboige/CoursIA#4960`](https://github.com/jsboige/CoursIA/issues/4960)
(coord-held, proposal-only).
**Built on** (do not reimplement — anti-pendule):
* substrate **#1** (symbolic, grounded, opaque exemplar) —
  [`s6_a2_labelling_trajectory.md`](s6_a2_labelling_trajectory.md), engine
  [`argumentation_analysis/orchestration/dung_labelling_trajectory.py`](../../argumentation_analysis/orchestration/dung_labelling_trajectory.py)
  (Track S6-A2 #1506, MERGED);
* substrate **M2** (AIF attack-typed trajectory, per-step native≡Tweety) —
  issue #1524 (`aif_labelling_trajectory`, CLOSED), the AIF layer that feeds the
  same Cell [22] wrap.

---

## What this doc is — and is not

| | |
|---|---|
| **Is** | A *design* for the pedagogy: learning objectives, teaching sequence, the artefacts to render, and the discipline to keep. The blueprint the coord's notebook wrap (CoursIA #4960) follows to fill Cell [22]. |
| **Is not** | The substrate itself (see the substrate doc above), nor the AIF realization (#1524), nor notebook authoring (coord-held), nor a re-derivation of Dung semantics (the engine is reused). |

**Anti-pendule**: this is a *teaching design* layered on the two existing
substrates. It adds zero new computation. Where the notebook needs a number, it
cites the computed artefact; where it needs a claim, the claim is
machine-checked below.

---

## The pedagogical move (the one idea to land)

> **Argumentation is a process, not a snapshot.**

A static abstract framework answers *"what is accepted?"*. A discourse, however,
*delivers* its arguments in a rhetorical order. Fixing that order and recomputing
the labelling after each arrival turns the static answer into a **trajectory of
states** — and the question shifts from *"what is accepted?"* to
*"how did acceptance evolve, and what changed it?"*.

This is the bridge the Cell [22] stub is meant to cross: from Dung's static AF
(which the earlier cells teach) to a *discourse-aware* view in which an
argument's status is provisional on what has arrived so far. Everything below
serves that one move.

---

## Learning objectives

After the Cell [22] section, a student can:

1. **Define** a Dung labelling `L: Args → {in, out, undec}` under a semantics
   (grounded first; preferred/stable as stretch).
2. **Explain** why a static labelling *hides* the process of argumentation —
   what it cannot say that a trajectory can.
3. **Predict**, given a new argument or attack arriving, how each existing
   argument's label can change — naming the three dynamics (acceptance,
   refutation, reinstatement).
4. **Read** a trajectory table (step × `{in, out, undec}`) and a per-argument
   transition sequence, and identify *which arguments flipped* at a given step.
5. **(Stretch)** Relate the symbolic trajectory to the AIF attack typology
   (undercut / undermine / rebut, via #1524) and to multi-semantics, and state
   why every step is verified against a second backend (anti-théâtre).

---

## Teaching sequence (mapped to Cell [22] progression)

| Step | Cell intent | What the student does |
|-----:|-------------|------------------------|
| **0** (prereq, assumed from earlier cells) | Static AF, attack relation, one grounded labelling. | Recall: `in` = defended, `out` = attacked by an `in`, `undec` = the rest (cycles). |
| **1** — the hook | "A discourse delivers arguments one by one. Does the thesis *stay* accepted as the discourse unfolds?" | Make a prediction *before* seeing the trajectory. |
| **2** — the worked exemplar | Render the opaque `prop_*` trajectory table (below). | Read the table row by row; confirm/refute their prediction. |
| **3** — the three dynamics | Walk acceptance → refutation → reinstatement. | Name, for each flip, *which arrival caused it*. |
| **4** — per-argument transitions | Render the per-argument label sequences. | See that an argument's label is a *time series*, not a constant. |
| **5** — stretch (AIF + multi-semantics, #1524) | Same trajectory under AIF attack types and under preferred/stable; per-step native≡Tweety. | Observe that the grounded trajectory is the *deterministic spine*; richer semantics branch but do not contradict it. |

The arc is deliberate: **predict → compute → reconcile → generalize**. The
prediction in step 1 is what makes step 2 land — a student who guessed "the
thesis stays accepted" is set up to feel the refutation at step 4.

---

## The worked exemplar (computed, not asserted)

A structurally-realistic synthetic framework with **opaque ids** (privacy HARD —
no source content, no corpus). Reproduce verbatim with
`python scripts/labelling_trajectory.py --exemplar discourse`. This is the actual
machine output the notebook should show:

```
step | arrived                                              | in                                   | out                      | undec
-----+------------------------------------------------------+--------------------------------------+--------------------------+---------------------
  1  | prop_thesis                                          | prop_thesis                          | -                        | -
  2  | prop_thesis, prop_cycle_a                            | prop_cycle_a, prop_thesis            | -                        | -
  3  | prop_thesis, prop_cycle_a, prop_cycle_b              | prop_thesis                          | -                        | prop_cycle_a, prop_cycle_b
  4  | prop_thesis, prop_cycle_a, prop_cycle_b, prop_counter| prop_counter                         | prop_thesis              | prop_cycle_a, prop_cycle_b
  5  | …all five…                                           | prop_counter, prop_cycle_b, prop_defender | prop_cycle_a, prop_thesis | -
```

Per-argument transitions (label from each argument's *arrival* onward):

```
prop_thesis    : in  -> in  -> in  -> out -> out      ← refuted at step 4
prop_cycle_a   : in  -> undec -> undec -> out        ← triple transition (bonus, see below)
prop_cycle_b   : undec -> undec -> in                 ← reinstated at step 5
prop_counter   : in  -> in
prop_defender  : in
```

These are the figures the Cell [22] prose must cite. **Falsifiability**: grounded
semantics on this exemplar is deterministic — if it did not produce the
refutation and reinstatement above, the substrate would be falsified. It is not
asserted; it is reproduced above on every clean checkout.

---

## The three dynamics (the "aha" moments)

1. **Acceptance** — `prop_thesis` is `in` from step 1 (unattacked opening claim).
   *Pedagogy*: the baseline; "accepted" is provisional on what has *not yet*
   arrived.
2. **Refutation** — `prop_thesis` flips `in → out` at **step 4** when
   `prop_counter` lands and is itself accepted. *Pedagogy*: an accepted argument
   can be un-accepted without ever being "wrong" — a stronger argument arrived.
3. **Reinstatement** — `prop_cycle_b` flips `undec → in` at **step 5** when
   `prop_defender` attacks `prop_cycle_a`, thereby *defending* `prop_cycle_b`
   (its only attacker is now itself rejected). *Pedagogy*: defence is indirect —
   defending `b` here means attacking `b`'s attacker. This is the non-obvious
   payoff of the trajectory view.

**Bonus (the substrate doc understates this)**: `prop_cycle_a` undergoes a
**triple transition** `in → undec → undec → out` — accepted alone (step 2,
unattacked), pushed to undecided when the cycle completes (step 3), then
rejected when the defender attacks it directly (step 5). Teaching this
*alongside* `prop_cycle_b`'s reinstatement makes the mechanism vivid: the **same
arrival** (`prop_defender`) simultaneously drives one cycle member `undec → out`
and the other `undec → in`. That coincidence is the cleanest illustration of
"defence = attacking the attacker" the exemplar offers — surface it explicitly.

---

## Pedagogical artefacts (what to render in the notebook)

* **The trajectory table** (above) — the spine. One row per arrival.
* **Per-argument transition sequences** (above) — makes the evolution
  per-argument, not per-step, visible. Useful as a "small multiples" view.
* **A label-flip highlighter** — for each step, which arguments *changed label*
  vs the previous step (e.g. step 4: `prop_thesis in→out`; step 5:
  `prop_cycle_a undec→out`, `prop_cycle_b undec→in`). This is the artefact that
  answers *"what changed it?"* directly. (Compute it by diffing adjacent
  `Labelling.as_map()`s — the engine exposes `label_transitions` already.)
* **(Stretch)** A per-step comparison across grounded / preferred / stable, with
  the native≡Tweety agreement flag per step (from #1524). Shows grounded as the
  deterministic spine; richer semantics add branches but never contradict the
  spine on this exemplar.

---

## Pedagogical discipline

* **Compute, don't assert.** Every label in the notebook is the output of the
  reused reasoner. If a step's labelling cannot be computed, the cell degrades
  honestly (`available=False`) — never a fabricated label (anti-#1019).
* **Opaque ids only.** The exemplar uses `prop_*` / `arg_*` tokens with **no
  source content** and **no corpus access** (privacy HARD). A corpus-derived AF
  is an explicit, privacy-sensitive follow-up, out of scope for the teaching
  exemplar.
* **Don't reimplement semantics.** Grounded comes from
  [`abs_arg_dung.backends.compute_grounded`](../../abs_arg_dung/backends/native.py);
  the AIF trajectory and multi-backend verification come from #1524. The
  notebook *calls* them; it does not re-derive Dung semantics (anti-pendule).
* **Don't conflate with the sibling.** This is the *symbolic* labelling
  trajectory. The belief-state stochastic matrix
  ([`strate6_phaseA_source_verdict.md`](strate6_phaseA_source_verdict.md),
  S6-A1) is its *stochastic* complement over real text — a different substrate,
  a different teaching unit. Keep them separate in the notebook.
* **Backend cross-check is honest-degraded.** The optional native-vs-Tweety
  grounded cross-check (`--cross-check-tweety`) either agrees, or the
  disagreement is reported verbatim — never auto-reconciled. If the JVM is
  unavailable, the trajectory (computed JVM-free) still stands.

---

## Mapping to the Cell [22] stub

Cell [22] is currently a **placeholder** for this section. This design proposes
it become, in order: the hook (step 1), the rendered exemplar table (step 2),
the three-dynamics walkthrough (step 3), and the per-argument transitions (step
4); the stretch (step 5) lands in a follow-on cell that calls #1524's
`aif_labelling_trajectory`. **The actual notebook authoring is coord-held**
(CoursIA wrap #4960, proposal-only); this doc is the design that wrap follows.
po-2023 authors the design in *this* repo; po-2023 ≠ a CoursIA author.

---

## Reproduce & engine

```bash
# The trajectory table + per-argument transitions the notebook should show:
python scripts/labelling_trajectory.py --exemplar discourse

# Optional native-vs-Tweety grounded cross-check (honest-degraded without JVM):
python scripts/labelling_trajectory.py --exemplar discourse --cross-check-tweety

# JSON export (for the notebook to consume):
python scripts/labelling_trajectory.py --json trajectory.json
```

* **Engine (symbolic, grounded)**:
  [`argumentation_analysis/orchestration/dung_labelling_trajectory.py`](../../argumentation_analysis/orchestration/dung_labelling_trajectory.py)
  — `labelling_trajectory`, `label_transitions`, `render_trajectory`,
  `build_discourse_exemplar`.
* **CLI**: [`scripts/labelling_trajectory.py`](../../scripts/labelling_trajectory.py).

---

## Relation to the sibling substrates

* **Substrate #1 (symbolic)** — [`s6_a2_labelling_trajectory.md`](s6_a2_labelling_trajectory.md):
  the trajectory-of-labellings *concept*, made executable on the opaque exemplar
  (Track S6-A2 #1506, MERGED). This is the deterministic spine the pedagogy
  teaches first.
* **Substrate M2 (AIF)** — issue #1524 (`aif_labelling_trajectory`, CLOSED):
  the same trajectory under AIF attack types (undercut / undermine / rebut) and
  under grounded/preferred/stable, each step verified native≡Tweety. This is the
  stretch material (step 5).
* **Substrate #2 (stochastic)** — [`strate6_phaseA_source_verdict.md`](strate6_phaseA_source_verdict.md):
  the belief-state transition matrix over real corpora (S6-A1). A *separate*
  teaching unit — the stochastic complement, not a duplicate of this one.

— Track S6 (pedagogy) · worker myia-po-2023 · Item 2 of dispatch R703 · #1506 / #1524 / CoursIA #4960
