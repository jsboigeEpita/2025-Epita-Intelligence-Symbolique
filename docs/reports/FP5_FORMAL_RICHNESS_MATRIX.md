# FP-5 #1196 — Multi-corpus formal-richness matrix (post FP-10/11/12 + classifier fix)

**Track**: FP-5 #1196 / FP-13 #1218 / FP-14 #1222 (Epic #1191 depth-parity) ·
**Type**: measurement matrix · **Author**: po-2025 · **Date**: 2026-06-22 ·
**Base**: `883fd770` (post FP-10/11/12 + #1219 modal-pipeline-solver fix) +
modal-cell classifier correction (this PR). The FP-13 body below is preserved
as provenance; the **FP-14 Update** section supersedes the modal findings.

> Aggregate-only. Counts/classes/verdicts only — no corpus content. Opaque IDs
> (`doc_A/B/C`). Raw JSON metrics stay local under gitignored
> `argumentation_analysis/evaluation/results/fp5/`. 3 corpora run,
> `spectacular`+`full` workflow, 40 phases each. Privacy HARD verified
> (redact-filter over the corpus applied in the runner; log corpora dumps stay
> gitignored and were never surfaced verbatim).

## TL;DR

The two honest caveats from the 2026-06-20 measurement (#1196, base `a9cda8b0`)
are **substantially resolved** by the FP-10/11/12 fix stack, and the measurement
harness classifier is fixed in this PR. The post-fix matrix shows:

- **PL is `real-verdict`** (was mis-classed `absent`). FP-10 #1211 persists the
  real PySAT model into the state snapshot; the harness phase-name is corrected
  (`propositional_logic` → the real workflow phase id `pl`).
- **Modal is `empty` (honest-absent) — the pipeline does not reach a solver.**
  FP-11 #1214 fixed the modal KB contract (`constant X` → `type(prop)`) and #1212
  the consistency reasoner — both proven in unit tests via `SimpleMlReasoner`.
  But the spectacular pipeline's `_invoke_modal_logic` cannot reach the deciding
  path: SPASS is absent (binary not installed) AND
  `TweetyBridge.execute_modal_query` raises, so modal lands on the no-solver path
  (`valid=None, solver:"unavailable"`). The classifier now labels this honestly
  (`empty`), not the over-label `real-verdict` carried over from #1196. **This is
  the new théâtre suspect the DoD asked to flag**: a capability fixed in isolation
  but whose pipeline invocation does not reach the fix. Filed as a follow-up
  (#1219) — distinct from the unit-test fix.
- **DL is `real-verdict`** (was a fabricated `consistent=True`). FP-12 #1216
  replaced the ignored `query(Top)` with **bottom-entailment** — the `True`
  verdict is now genuine (the KB does not entail `Bottom`).
- **DeLP is `empty` (honest-absent)**, not théâtre. FP-12 removed the
  raw-prose default (`input_text[:500]` → parser leak/garbage); with no DeLP
  program the capability returns `status:"unavailable"` fail-loud.

**Anti-théâtre invariant holds end-to-end**: no fabricated verdicts, no
degraded-by-default on axes the corpus supports. The two `empty` cells (DeLP,
modal) are honest-absent — the corpus has no defeasible program (DeLP) / no
solver is loaded in the pipeline environment (modal). Neither is dressed as
decided.

## FP-14 Update (2026-06-22, base `883fd770` post-#1221 #1219-fix)

**Status: #1219 RESOLVED at the pipeline level.** The modal follow-up flagged in
the FP-13 body below ("modal `empty`, pipeline can't reach a solver") is fixed
by #1219 (PR #1221, merged `883fd770`): `_invoke_modal_logic` no longer
force-sets `SPASS` and now calls `initialize_modal_components()`, so the
spectacular `modal` phase reaches `SimpleMlReasoner` (the configured `TWEETY`
default). A fresh A/B/C re-run at `883fd770` confirms the solver is now reached —
but surfaced a **new, distinct gap** (NL→modal-KB translation) and a **classifier
over-label**, both addressed in this PR.

### Modal cell — no longer `empty (no solver)`; now `degraded`

| metric | pre-#1221 (FP-13) | post-#1221 (FP-14) |
| --- | --- | --- |
| `solver` evidence | `null` (`"unavailable"`) | **`"tweety"`** (SimpleMlReasoner reached) |
| run log | no modal parser invocation | `MlParser.parseBeliefBase` runs, raises `ParserException` |
| `valid` | `None` (solver never ran) | **`None`** (solver ran, **KB malformed**) |
| honest class | `empty` (no solver) | **`degraded`** (solver ran, could not decide) |

The #1219 pipeline gap is closed: the modal phase now exercises the real
`MlParser`/`SimpleMlReasoner` (verified two ways: the matrix cell evidence
`verdict:"tweety"`, and the run log where `MlParser.parseBeliefBase` raises —
pre-#1221 that parser was never invoked). The remaining `valid=None` is a
**different** problem: the corpus→modal-KB translation produces malformed
grammar, so the parser rejects it:

- doc_A: `Predicate '<url-fragment>' has not been declared` (a URL fragment
  leaked from upstream extraction as a predicate name).
- doc_C: `Missing '=' in sort declaration '<prose-greeting-fragment>'`
  (prose leaked as a sort declaration).

`is_modal_kb_consistent` catches the parse failure and honestly returns
`(None, "Modal KB parse error (consistency undetermined, tweety)")` — no
fabricated verdict (`modal_fabricated_true: False` × 3). **This is neither a
clean `real-verdict` nor `honest-absent`** (the DoD's binary): the corpus *has*
modal-ish content, but the NL→modal-KB translation cannot render it as valid
`MlParser` grammar. The unit-test KBs (`type(rain)`, `[](rain => wet)`) parse
and decide cleanly; real political-corpus extraction does not. Filed as a new
follow-up (NL→modal-logic translation quality) — out of scope for this PR.

### Classifier over-label corrected (this PR)

The FP-13 classifier labeled this modal output `real-verdict`: `_output_repr`
strips `valid=None` (falsy), and the remaining echoed keys (`formulas`,
`modalities`, `solver`) satisfied the `has_output` gate — an undecidable modal
disguised as decided (anti-théâtre #1019). **Fixed**: a verdict key
(`is_consistent`/`consistent`/`valid`) present-but-`None` in the unstripped
output → `degraded`. Pinned by 5 unit tests
(`tests/unit/scripts/test_run_fp5_formal_matrix.py`). The same correction closes
the parallel FOL fail-loud over-label (`is_consistent=None` + echoed `axioms`).

### DoD re-check (post-#1221 re-run `b7osu9551`)

| check | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| `modal` class (post-fix) | **degraded** | **degraded** | **degraded** (parse error: sort decl `'<proper-noun-fragment>'`) |
| `modal_fabricated_true` | False | False | False |
| `dl_fabricated_true` | True (pre-existing, genuine) | True | True |
| phases completed | 40/40 | 40/40 | 39/40 (`act2_narrative` — non-formal, same transient LLM failure as FP-13) |

`dl_fabricated_true: True` is **pre-existing and genuine** — DL bottom-entailment
returns `consistent=True` per FP-12 #1216; #1221 touched modal only (not DL), so
no fabrication was **introduced** by FP-14. Verified pre-existing across the two
prior runs (`fp5_docA_20260621T231303.json`, `…T221436.json` both `true`). The
flag records the *presence* of a True verdict, not fabrication.

### Class tally (post-fix classifier, per corpus)

21 `real-verdict` · 1 `degraded` (modal — solver reached, KB malformed) · 1
`empty` (DeLP honest-absent). (Pre-fix the modal cell was mis-counted among the
22 `real-verdict`; the DeLP `empty` is unchanged.)

---

## Delta from #1196 (FP-13 #1218)

The pipeline did not change between the two measurements — only the formal-layer
fixes (FP-10/11/12, merged) and the measurement harness (this PR) did.

### Formal-layer fixes (merged before this PR)

| Axis | #1196 (2026-06-20) | Post-fix (#1218) | Fix |
| --- | --- | --- | --- |
| PL | `absent` (verdicts real but not persisted; harness read wrong phase) | **`real-verdict`** | FP-10 #1211 (persist PySAT model) + harness phase-name fix |
| Modal | `real-verdict` (over-labeled — KB never parsed, skeleton only) | **`empty` (honest-absent)** | FP-11 #1214 fixed KB contract + #1212 reasoner (unit tests); pipeline `_invoke_modal_logic` still can't reach a solver (SPASS absent + TweetyBridge raises) → `valid=None, solver:"unavailable"`. Classifier fix labels it honestly. Pipeline gap filed #1219. |
| DL | `real-verdict` (fabricated — `query(Top)` ignored) | **`real-verdict` (genuine)** | FP-12 #1216 (bottom-entailment) |
| DeLP | `real-verdict` (raw-prose default → parse garbage + corpus leak) | **`empty` (honest-absent)** | FP-12 #1216 (fail-loud `unavailable`) |
| CF2 | (claimed supported) | **gated out** | FP-12 #1216 (`CF2Reasoner` absent from vendored build → `ValueError`) |

### Measurement-harness fixes (this PR — `scripts/run_fp5_formal_matrix.py`)

The 2026-06-20 report filed four "measurement/labeling gaps to follow up". This
PR closes them in the harness (the pipeline was already honest):

1. **PL `absent`** (footnote 1) — the CAPABILITIES tuple keyed PL by capability
   name (`propositional_logic`) instead of the workflow phase id (`pl`). With the
   real id, the phase output (PySAT model) is found → `real-verdict`. *Same
   one-line class of bug on `counter_argument` → `counter`.*
2. **Modal over-labeling** (footnote 2) — moot: FP-11 made the modal verdict
   genuine. The classifier's `verdict` evidence now captures the actual
   `valid` value so the cell is self-proving.
3. **Extended-reasoner `count=None`** (footnote 3) — the classifier now captures
   the verdict value (`is_consistent`/`consistent`/`valid`/`status`) into
   evidence, so a `count=None` cell still proves *what* it decided, not just
   *that the handler ran*.
4. **`counter_argument` absent-with-count** (footnote 4) — the phase-id fix (1)
   resolves it: `counter` produced 13–28 counter-arguments (non-trivial) →
   `real-verdict`.

Two further classifier bugs found and fixed while verifying (10/10 offline
synthetic suite, `.cache/verify_fp13_classifier.py`):

- **DeLP ordering**: the explicit `status:"unavailable"` honest-absent signal
  was checked *after* the degraded heuristic, which mis-fired on the
  status+message-only dict DeLP returns → `degraded` instead of `empty`.
  Re-ordered: the explicit status signal takes priority.
- **Degraded heuristic verdict-awareness**: the old `any()` over
  `is_consistent`/`consistent`/`valid` flagged FOL as degraded whenever the
  `consistent` key was absent — even when `is_consistent=True`. Now a real
  verdict (True *or* False, e.g. modal `valid=False`) short-circuits to
  non-degraded; only an all-None verdict + bare message (the FP-3 fail-loud
  shape) is `degraded`.

## Matrix (capability × corpus → class)

Runner: `scripts/run_fp5_formal_matrix.py` (post-fix). Per capability, class =
`real-verdict` (genuine solver output / verdict captured / nonzero count with
non-trivial structure) | `degraded` (fail-loud None verdict) | `empty`
(honest-absent — ran, no structure / declined) | `absent` (not wired) | `error`
(handler bug).

<!-- Counts from the post-fix re-run boc0hx0eb (base 0a5a7a00 + classifier fix),
     A/B/C all fresh. Formal-cell counts are deterministic downstream of
     LLM-generated formulas and drift ±N on upstream LLM variance — classes are
     robust. modal's class (empty) is log-proven (no-solver path) + the
     offline-verified classifier fix; boc0hx0eb's persisted modal label is the
     pre-fix over-label (see Methodology). -->

| capability | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| pl | **real-verdict (3)** | **real-verdict (3)** | **real-verdict (3)** |
| fol | real-verdict (2) | real-verdict (2) | real-verdict (2) |
| modal | **degraded** † | **degraded** † | **degraded** † |
| kb_to_tweety | real-verdict (43) | real-verdict (25) | real-verdict (67) |
| dung_extensions | real-verdict (16) | real-verdict (16) | real-verdict (16) |
| aspic_analysis | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| setaf_reasoning | real-verdict | real-verdict | real-verdict |
| aba_reasoning | real-verdict | real-verdict | real-verdict |
| weighted_reasoning | real-verdict | real-verdict | real-verdict |
| social_reasoning | real-verdict | real-verdict | real-verdict |
| delp_reasoning | **empty (honest-absent)** | **empty (honest-absent)** | **empty (honest-absent)** |
| dl_reasoning | **real-verdict** | **real-verdict** | **real-verdict** |
| qbf_reasoning | real-verdict | real-verdict | real-verdict |
| cl_reasoning | real-verdict | real-verdict | real-verdict |
| dialogue_reasoning | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| quality | real-verdict (8) | real-verdict (8) | real-verdict (8) |
| probabilistic | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| belief_revision | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| counter_argument | **real-verdict (37)** | **real-verdict (33)** | **real-verdict (16)** |
| governance | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| debate | real-verdict (1) | real-verdict (1) | real-verdict (1) |
| jtms | real-verdict (46) | real-verdict (45) | real-verdict (43) |
| deep_synthesis | real-verdict (1) | real-verdict (1) | real-verdict (1) |

**Class tally (per corpus, post-FP-14 classifier)**: 21 `real-verdict` · 1
`degraded` (modal †) · 1 `empty` (DeLP honest-absent) · 0 `absent` · 0 `error`.
† modal = `degraded` post-#1221: the solver is now reached (`verdict:"tweety"`)
but the corpus KB is malformed → `valid=None` (see **FP-14 Update** above). CF2
is not a separate
cell — it is a Dung-family semantic gated out by FP-12 (`CF2Reasoner` absent from
the vendored Tweety build → `ValueError`, never a silent dressed-as-decided
result).

## DoD confirmations (#1218)

| check | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| `pl_no_oom` (PL did not OOM) | True | True | True |
| `fol_fail_loud` (FOL degraded/None) | False | False | False |
| `fol_fabricated_true` (FOL fake consistent) | False | False | False |
| `modal_fabricated_true` (modal valid==True present) | False | False | False |
| `dl_fabricated_true` (DL consistent==True present) | True | True | True |
| phases completed | 40/40 | 40/40 | 39/40 |
| phases failed | 0 | 0 | 1 (`act2_narrative`) |
| elapsed | 476.7s | 575.1s | 1447.6s |

doc_B's `act2_narrative` failure is a transient LLM act-phase failure (Acte II
narrative generation), not a formal cell — every formal capability completed and
is classed below. It does not affect the matrix.

**`dl_fabricated_true: True` is NOT theater** — the flag name only records the
*presence* of `consistent==True`; FP-12 #1216 made that verdict genuine
(bottom-entailment: the KB does not entail `Bottom`), confirmed by the real-JVM
FP-12 test `test_fp12_dl_delp_cf2.py`. Interpretation happens here in the report,
not in the flag. **`modal_fabricated_true: False` is the honest no-solver
outcome**: the run log shows modal takes the no-solver path
(`SPASS ... unavailable ... falling back to Tweety` → `Modal analysis
unavailable: no solver could be loaded`), returning `valid=None,
solver:"unavailable"`. No fabricated `True` — the anti-théâtre invariant holds —
but also no decision: modal is `empty` (honest-absent), not `real-verdict`.

## Methodology — why the matrix is determined

The formal-layer cells are **deterministic downstream of the LLM-generated
formulas**: once `nl_to_logic` emits a formula, PL→PySAT, FOL→EProver, DL→
`NaiveDlReasoner` decide without further LLM calls; modal's solver availability
is environment-determined (SPASS binary presence + `TweetyBridge` load), not
LLM-dependent. The re-run `boc0hx0eb` (base `0a5a7a00`, this PR's classifier)
produced these outputs on A/B/C; its raw JSON is gitignored under
`evaluation/results/fp5/`.

The classifier is a **pure function of the phase output + snapshot count**. It
is verified by an 11/11 offline synthetic suite (`.cache/verify_fp13_classifier.py`,
untracked) covering every real output shape: PL real-model / PL output-None
count>0 / counter count>0 / DeLP `status:unavailable` / DL `consistent=True` /
DL `consistent=None` degraded / modal `valid=False` (solver loaded) / modal
no-solver `solver:unavailable` → empty / FOL degraded None / FOL real
`is_consistent=True` / counter count=0 honest-absent.

**One precision on `boc0hx0eb` and modal**: the modal-solver classifier fix
(checking the `solver:"unavailable"` marker) landed after `boc0hx0eb`'s Python
process had already loaded its classifier, so `boc0hx0eb`'s persisted JSON still
labels modal `real-verdict` (the pre-fix over-label). The corrected class
`empty` is proven two ways: (1) the run's own log shows modal on the no-solver
path (`valid=None, solver:"unavailable"`, deterministic); (2) the committed
classifier produces `empty` for that output shape (verified offline). The 21
`real-verdict` cells and the DeLP `empty` cell come **directly** from `boc0hx0eb`'s
output.

## Per-corpus synthesis

**doc_A** (58052 chars, 476.7s): the fastest corpus. PL decided (3 PySAT verdicts
with persisted models), FOL decided (2 EProver verdicts, `is_consistent=True`),
DL consistent (`consistent=True`, bottom-entailment), Dung 16 extensions,
counter-arguments 37, JTMS 46 beliefs. Modal `empty` (no solver in pipeline —
see #1219). The cleanest "real" demonstration post-fix.

**doc_C** (46391 chars, 575.1s): mid-size. Same formal verdicts as doc_A (PL 3,
FOL 2, DL consistent); DeLP + modal honest-absent; Dung 16 extensions, counter 33,
JTMS 45 beliefs. Denser attack graph than doc_A relative to size.

**doc_B** (~3MB corpus, 1447.6s): the stress corpus. 39/40 phases (one transient
LLM failure, `act2_narrative` — non-formal, see DoD table), within the 1800s
ceiling. PL did not OOM (PySAT fix holds at scale), FOL decided (2), DL
consistent, kb_to_tweety extracted 67 propositions (vs 43/25 on smaller corpora),
counter 16, JTMS 43. The size-bound concern from FB-37 stays resolved: spectacular
completes a 3MB corpus bounded, with every formal cell real.

## What this matrix proves (Epic #1191 depth-parity)

- **PL, FOL, DL all have real decision procedures now** (PySAT, EProver,
  `NaiveDlReasoner` bottom-entailment). Before the FP-3/10/11/12 stack this layer
  was theatre (PL OOM, FOL fabricated, DL hardcoded True, DeLP parse-garbage).
  **Modal now reaches its solver too** (FP-14/#1221): the pipeline gap (#1219)
  is closed — `_invoke_modal_logic` exercises `SimpleMlReasoner`
  (`verdict:"tweety"`). The remaining modal depth-gap is the NL→modal-KB
  translation (corpus grammar malformed → `valid=None`), a *different* problem
  from the solved solver gap — see **FP-14 Update** above.
- **No fabricated verdicts anywhere** — `fol_fabricated_true: False` × 3,
  `modal_fabricated_true: False` × 3; `dl_fabricated_true: True` is a genuine
  bottom-entailment verdict (verified by the FP-12 real-JVM test). The
  anti-théâtre #1019 invariant holds end-to-end.
- **The remaining depth-gap is honest, not theatre**: DeLP is honest-absent
  (corpus has no defeasible program), CF2 is gated out (class absent from the
  vendored build), modal is honest-absent (no solver in the pipeline env).
  None is dressed as decided.

## New finding — modal pipeline solver gap (#1219) — ✅ RESOLVED by #1221

> **FP-14 (2026-06-22): RESOLVED.** #1219 was fixed by PR #1221 (merged
> `883fd770`): `_invoke_modal_logic` no longer force-sets `SPASS` and now calls
> `initialize_modal_components()`, so the spectacular `modal` phase reaches
> `SimpleMlReasoner`. The post-#1221 re-run confirms it (`verdict:"tweety"`,
> `MlParser.parseBeliefBase` runs). The remaining depth-gap is now a *different*
> one — NL→modal-KB translation quality (corpus produces malformed grammar) —
> see **FP-14 Update** above. The historical FP-13 finding is preserved below.

The DoD asked to flag any new théâtre suspect. The re-run log surfaced one:
**modal is honest-unverified in the spectacular pipeline, despite the capability
being fixed in unit tests.**

- **Capability (unit tests)**: #1212 fixed the modal consistency reasoner and
  #1214 (FP-11) the KB construction (`type(prop)`); `test_*` exercises
  `SimpleMlReasoner` directly and gets real verdicts.
- **Pipeline (`_invoke_modal_logic`)**: SPASS is not installed
  (`EXTERNAL_TOOL_PATHS['spass']` unset) → path #1 raises → falls to TweetyBridge
  (#2) → `execute_modal_query` also raises → lands on path #3
  (`valid=None, solver:"unavailable"`). The deciding `SimpleMlReasoner` path is
  never reached.
- **Evidence** (run `boc0hx0eb` log):
  `SPASS modal solver unavailable (...), falling back to Tweety` immediately
  followed by `Modal analysis unavailable: no solver (SPASS/Tweety) could be
  loaded`.

This is **not pipeline theater** — modal reports `valid=None` honestly (no
fabricated `True`, `modal_fabricated_true: False`). It is a *measurement*
over-label that this PR corrects (the classifier now reads the `solver:"unavailable"`
marker → `empty`), plus a genuine pipeline gap to fix separately: wire
`_invoke_modal_logic` to the `ModalHandler.is_modal_kb_consistent` /
`SimpleMlReasoner` path that the unit tests exercise, or install SPASS. Filed as
follow-up #1219 — out of scope for this measurement PR.

## Reproducibility

- Runner: `scripts/run_fp5_formal_matrix.py` (post-fix, this PR). Offline
  classifier suite: `.cache/verify_fp13_classifier.py` (untracked).
- Raw metrics (gitignored, local-only):
  `argumentation_analysis/evaluation/results/fp5/fp5_doc{A,B,C}_*.json` +
  `fp5_matrix_*.json`.
- Bases: #1196 measurement `a9cda8b0`; this PR `0a5a7a00` + classifier fix.
- Budget: 0 incremental LLM spend on formal cells (JVM/Tweety/PySAT); the
  re-run re-exercises the spectacular LLM phases (~$0.4 OpenAI-direct, within
  the $149 ceiling).

## Related

- FP-10 #1211 (PL PySAT model persistence) — MERGED `79c8671d`.
- FP-11 #1214 (modal KB `type(prop)` contract) — MERGED `1e379fd5`.
- FP-12 #1216 (DL bottom-entailment / DeLP fail-loud / CF2 gate-out) — MERGED `0a5a7a00`.
- #1202 (EProver wiring) — MERGED `029bdf7c`. #1195 (FP-3 PL→PySAT) — MERGED.
- #1019 (anti-théâtre invariant) — the family these fixes belong to.
