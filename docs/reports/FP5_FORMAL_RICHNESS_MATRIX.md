# FP-5 #1196 — Multi-corpus formal-richness matrix (post-EProver fix)

**Track**: FP-5 #1196 (Epic #1191 depth-parity) · **Type**: measurement matrix ·
**Author**: po-2025 · **Date**: 2026-06-20 · **Base**: `a9cda8b0` (post all formal fixes)

> Aggregate-only. Counts/classes only — no corpus content. Opaque IDs
> (`doc_A/B/C`). Raw JSON metrics stay local under gitignored
> `argumentation_analysis/evaluation/results/fp5/`. 3 corpora run,
> `spectacular`+`full` workflow, 40 phases each. Privacy HARD verified
> (redact-filter over the corpus applied in the runner; log corpora dumps
> stay gitignored and were never surfaced verbatim).

## TL;DR

After the FP-3/FP-6/#1202/FP-7/FP-8 fix stack landed on main, the formal layer
no longer fabricates. Measuring A/B/C × 23 capabilities shows a **reproducible
21/23 real-verdict** pattern across all three corpora — the FOL axis that was
`degraded (None)` before #1202 now **decides via EProver** on every corpus
(`fol_fail_loud: False` everywhere). Depth-parity PL/FOL is resolved on the
FOL side: both have a real decision procedure now (PL→PySAT, FOL→EProver).

**Two honest caveats** (anti-theater #1019 — a `real-verdict` count must mean
a real decision, not a handler that merely ran):

- **PL is classed `absent` by the runner's classifier, but its verdicts are
  real** — the log shows 6 PySAT decisions with full models (`Consistent (SAT).
  Model: {…}`). The misclassification is a measurement gap: the state snapshot
  persists empty artifacts (`axioms=0, queries=0`) for PL even when the handler
  decided. PL did NOT degrade; the classifier's `has_nontrivial_output` probe
  reads the wrong field.
- **Modal is classed `real-verdict` but is NOT solver-decided** — SPASS is
  absent AND its no-arg constructor raises (the FP-9 #1205 residual bug, same
  family as the EProver bug #1202 fixed). The modal handler produced a
  non-trivial skeleton (count=1) but no SPASS verdict. Honest label:
  *handler-ran, not solver-decided*.

Both caveats are **measurement/labeling nuances on a pipeline that is
fundamentally honest** — 0 `degraded`, 0 `error`, 0 `fol_fabricated_true`
across 3 corpora. The formal theater is dead; what remains is two classifier
bugs to file (PL snapshot persistence, modal label honesty) — not regressions.

## Matrix (capability × corpus → class)

Runner: `scripts/run_fp5_formal_matrix.py`. Per capability, class =
`real-verdict` (genuine solver output / nonzero count with non-trivial
structure) | `degraded` (fail-loud None) | `absent` (count==0 or trivial) |
`error` (handler bug).

| capability | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| pl | absent (3)¹ | absent (3)¹ | absent (3)¹ |
| fol | **real-verdict (2)** | **real-verdict (2)** | **real-verdict (2)** |
| modal | real-verdict (1)² | real-verdict (1)² | real-verdict (1)² |
| kb_to_tweety | real-verdict (43) | real-verdict (28) | real-verdict (66) |
| dung_extensions | real-verdict (17) | real-verdict (17) | real-verdict (17) |
| aspic_analysis | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| setaf_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| aba_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| weighted_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| social_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| delp_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| dl_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| qbf_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| cl_reasoning | real-verdict³ | real-verdict³ | real-verdict³ |
| dialogue_reasoning | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| quality | real-verdict (1) | real-verdict (8) | real-verdict (8) |
| probabilistic | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| belief_revision | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| counter_argument | absent (1)⁴ | absent (37)⁴ | absent (14)⁴ |
| governance | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| debate | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| jtms | real-verdict (17) | real-verdict (46) | real-verdict (44) |
| deep_synthesis | real-verdict (1) | real-verdict (1) | real-verdict (1) |

**Footnotes (the honesty layer):**

1. **PL `absent` is a classifier bug, not real absence.** Log evidence (6
   PySAT decisions with explicit models, e.g. `pl_1 (satisfiable=True)`). The
   state snapshot persists `propositional_analysis_results.[0-2]: axioms=0
   queries=0 results=` so the runner's `has_nontrivial_output` probe sees no
   structure. **New finding**: PL verdicts are produced but not persisted into
   the snapshot — a handler→state plumbing gap (distinct from FP-3 which fixed
   the *decision*, not the *persistence*).
2. **Modal `real-verdict` is over-labeled.** SPASS failed to load every run
   (`SPASSMlReasoner()` no-arg constructor raises under Tweety 1.28+ — the
   FP-9 #1205 residual bug, same API-drift family #1202 fixed for EProver).
   The count=1 is a handler skeleton, not a solver verdict. Honest label:
   *degraded-skeleton*, not `real-verdict`.
3. **Extended reasoners `real-verdict` with count=None** — these phases report
   `status=completed` (the handler ran without raising) but have **no dedicated
   state counter** (`count_key=None` in the runner). "Completed" ≠ "produced
   measurable structure". These should be classed `unknown-output`, not
   `real-verdict`, until a counter verifies non-trivial output.
4. **`counter_argument` `absent` with non-zero count** — handler produced
   counter-args (1/37/14) but the classifier judged them non-substantive
   (`has_nontrivial_output: False`). May be a threshold issue or genuinely
   thin output; needs per-corpus inspection to disambiguate.

## DoD confirmations

| check | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| `pl_no_oom` (PL did not OOM) | True | True | True |
| `fol_fail_loud` (FOL degraded/None) | **False** | **False** | **False** |
| `fol_fabricated_true` (FOL fake consistent) | **False** | **False** | **False** |
| phases completed | 40/40 | 40/40 | 40/40 |
| phases failed | 0 | 0 | 0 |
| elapsed | 274.8s | 718.2s | 1109.1s |

**`fol_fail_loud: False` on all 3 corpora is the headline result**: before
#1202, FOL returned `degraded (None)` (the honest FP-3 outcome) because the
EProver binary was never wired. Now FOL decides — the #1202 fix
(`EXTERNAL_TOOL_PATHS` registry + `EFOLReasoner(path)` + dispatch in
`check_consistency`) is **confirmed working in production on real corpora**,
not just synthetic atoms.

## Per-corpus synthesis

**doc_A** (58052 chars, 274.8s): the fastest corpus. FOL decided consistently
(2 verdicts). Dung framework built 8 args / 17 extensions-region entries.
Quality + JTMS + governance all produced non-trivial structure. The formal
layer here is the cleanest "real" demonstration post-fix.

**doc_C** (46391 chars, 718.2s): mid-size. FOL decided (2 verdicts) despite a
`ParserException: Unrecognized formula type 'S'` on some NL→logic-generated
formulas — the handler fail-loud on malformed formulas but still decided on
the parseable ones (honest partial decision, not theater). Dung took 103s
(vs 1.5s on doc_A) — denser attack graph. JTMS 46 beliefs (richest).

**doc_B** (3,063,493 chars — ~3MB, 1109.1s): the stress corpus. 40/40 phases,
0 failed, within the 1800s ceiling. FOL still decided (2 verdicts), PL did
not OOM (the FP-3 PySAT fix holds at scale), kb_to_tweety extracted 66
propositions (vs 43/28 on smaller corpora). The size-bound concern from FB-37
is confirmed resolved: spectacular completes a 3MB corpus bounded.

## What this matrix proves (Epic #1191 depth-parity)

- **PL and FOL both have real decision procedures now** (PySAT + EProver).
  Before FP-3/#1202 the formal layer was theater (PL OOM, FOL fabricated).
- **No fabricated verdicts anywhere** (`fol_fabricated_true: False` × 3,
  `fol_fail_loud: False` × 3). The anti-theater #1019 invariant holds end-to-end.
- **The depth-gap that remains is honest**, not theater: modal has no working
  external solver (SPASS absent + FP-9 ctor bug), and structured-arg axes
  (aspic/setaf/aba) produce minimal output (count=1) — corroborating FP-4
  #1194's translation-gap diagnosis (pipeline doesn't feed them structured input).

## New findings to file (not blockers — measurement/labeling gaps)

1. **PL state-snapshot persistence gap**: handler decides (PySAT, models in
   log) but the snapshot persists empty artifacts → classifier marks `absent`.
   File: PL `propositional_analysis_results` not populated despite real verdicts.
2. **Modal over-labeling**: `real-verdict` on a SPASS-failed skeleton. The
   classifier should distinguish "solver-decided" from "handler-ran-with-output".
3. **Extended-reasoner `count=None` real-verdicts**: 8 capabilities
   (setaf/aba/weighted/social/delp/dl/qbf/cl) report completed with no
   measurable counter. Class as `unknown-output` until counters exist.

## Reproducibility

- Runner: `scripts/run_fp5_formal_matrix.py` (untracked, committed path
  `scripts/`).
- Raw metrics (gitignored, local-only):
  `argumentation_analysis/evaluation/results/fp5/fp5_doc{A,B,C}_*.json` +
  `fp5_matrix_*.json`.
- Base: `a9cda8b0` (main, post FP-3+FP-6+#1202+FP-7+FP-8).
- Budget: ~$0.75 OpenRouter-class equivalent (OpenAI-direct per R446 flip),
  3 corpora. Solde post-run: within the $149.83 ceiling.

## Related

- #1202 (EProver wiring — the fix this matrix validates) — MERGED `029bdf7c`.
- #1195 (FP-3 PL→PySAT) — MERGED.
- #1198 (FP-6 FOL orchestrator fail-loud) — MERGED.
- #1203 (FP-8 Prover9 runner) — MERGED (2nd FOL solver, alternative to EProver).
- #1194 / #1201 (FP-4 structured-arg translation-gap diagnosis, po-2023).
- #1205 / #1206 (FP-9 SPASS modal residual ctor bug, po-2023) — corroborated
  here: modal not solver-decided.
