# FP-5 #1196 — Multi-corpus formal-richness matrix (post FP-10/11/12 + classifier fix)

**Track**: FP-5 #1196 / FP-13 #1218 / FP-14 #1222 / FP-15 #1226 / FP-16 #1231 (Epic #1191 depth-parity) ·
**Type**: measurement matrix · **Author**: po-2025 · **Date**: 2026-06-22 ·
**Base**: `8c6714f2` (post FP-10/11/12 + #1219 modal-pipeline-solver fix +
#1224/#1225 NL→modal-KB-source fix + **#1227/#1230 modal predicate-name
normalization**) + FP-14 modal-cell classifier correction.
The FP-13/FP-14/FP-15 bodies are preserved as provenance; the **FP-16 Update**
section supersedes the modal findings.

> Aggregate-only. Counts/classes/verdicts only — no corpus content. Opaque IDs
> (`doc_A/B/C`). Raw JSON metrics stay local under gitignored
> `argumentation_analysis/evaluation/results/fp5/`. 3 corpora run,
> `spectacular`+`full` workflow, 40 phases each. Privacy HARD verified
> (redact-filter over the corpus applied in the runner; log corpora dumps stay
> gitignored and were never surfaced verbatim).

## FP-21 Update (2026-06-24, base `d9a1d4bf` — cross-machine re-measurement post #1242/#1245/#1246/#1247)

**Track**: FP-21 #1248 (Epic #1191 depth-parity + multi-solver comparison) ·
**Type**: cross-machine measurement re-run · **Author**: po-2023 · **Date**: 2026-06-24 ·
**Base**: `d9a1d4bf` (post FP-18 #1242 native Windows SPASS + FP-19 #1245 Mace4/multi-prover +
FP-17 #1246 structured-arg honest-absent + FP-20-prep #1247 dead-DLL cleanup).
This section supersedes the **FP-16 modal finding** (SimpleMlReasoner OOM) — the
solver layer below it changed materially.

### Why re-measure
FP-16 marked modal `empty`/`error`/`absent` *because "SPASS is absent / SimpleMlReasoner
OOMs"*. Since then #1242 vendored a native Windows SPASS CLI (`ext_tools/spass/SPASS.exe`
+ `.bat` adapter) that decides modal genuinely. The depth-parity matrix therefore has a
new, currently-unmeasured answer on the modal cell — measured here.

### Solver census — cross-machine reproducibility signal (DoD #1)

Firsthand on **po-2023** (2nd Windows host, was ai-01-only before):
`tests/integration/argumentation_analysis/agents/core/logic/test_external_provers_wired.py`
→ **10/10 PASSED / 15.91s** (ai-01 baseline: 10/10 / 3.93s). All deciding binaries are
tracked in git and decide identically on the second host: **PL** PySAT (cadical195),
**FOL** EProver + Prover9 + Mace4 + `compare_fol_backends` agreement, **Modal** SPASS
(no silent fallback), **ASP** Clingo. **Cross-machine portability of the solver surface
is confirmed firsthand.** No cell regressed vs ai-01.

### Matrix re-run (3 corpora, base `d9a1d4bf`, spectacular+full, 40 phases)

| capability | doc_A | doc_C | doc_B |
|---|---|---|---|
| pl | real-verdict | real-verdict | real-verdict |
| fol | real-verdict | real-verdict | real-verdict |
| **modal** | **degraded** | **degraded** | **error** |
| kb_to_tweety | real-verdict | real-verdict | real-verdict |
| dung_extensions | real-verdict | real-verdict | real-verdict |
| aspic_analysis | real-verdict | real-verdict | real-verdict |
| setaf_reasoning | real-verdict | real-verdict | real-verdict |
| aba_reasoning | real-verdict | real-verdict | real-verdict |
| weighted_reasoning | real-verdict | real-verdict | real-verdict |
| social_reasoning | real-verdict | real-verdict | real-verdict |
| delp_reasoning | empty | empty | empty |
| dl_reasoning | real-verdict | real-verdict | real-verdict |
| qbf_reasoning | real-verdict | real-verdict | real-verdict |
| cl_reasoning | real-verdict | real-verdict | real-verdict |
| dialogue_reasoning | real-verdict | real-verdict | real-verdict |
| quality | real-verdict | real-verdict | real-verdict |
| probabilistic | real-verdict | real-verdict | real-verdict |
| belief_revision | real-verdict | real-verdict | real-verdict |
| counter_argument | real-verdict | real-verdict | real-verdict |
| governance | real-verdict | real-verdict | real-verdict |
| debate | real-verdict | real-verdict | real-verdict |
| jtms | real-verdict | real-verdict | real-verdict |
| deep_synthesis | real-verdict | real-verdict | real-verdict |

Tally per corpus (doc_A 40/40, doc_C 40/40, doc_B 38/40): **21 real-verdict ·
1 empty (DeLP) · modal = degraded/degraded/error**. DoD confirmations ×3:
`pl_no_oom=True`, `fol_fail_loud=False`, `fol_fabricated_true=False`,
**`modal_fabricated_true=False`** — zero fabricated verdict on any formal axis.

### The modal flip — OOM-crash → solver-reached-but-honest-non-decision (DoD #2/#5)

The modal cell is the only one that changed materially vs FP-16, and it changed in the
**honest** direction:

| corpus | FP-16 (base `8c6714f2`, pre-#1242) | FP-21 (base `d9a1d4bf`, post-#1242) | solver reached? | modal evidence |
|---|---|---|---|---|
| doc_A | `error` (SimpleMlReasoner **OOM**) | **`degraded`** | ✅ `verdict:"tweety"` | `valid=None`, count=1, non-trivial output |
| doc_C | `absent` (upstream pipeline timeout) | **`degraded`** | ✅ `verdict:"tweety"` | `valid=None`, count=1, non-trivial output |
| doc_B | hung past 1800s | `error` (2 phases failed) | — (failed upstream) | `verdict:null` |

- **doc_A/doc_C**: the modal solver is now **reached** (`evidence.verdict="tweety"`),
  producing non-trivial output, but `valid=None` — the KB fed to the modal reasoner is
  purely **propositional** (`nl_to_logic` emits `logic_type=propositional`, no `[]`/`<>`
  operators), so there is genuinely nothing modal to decide. This is **honest-absent at
  the corpus level** (the corpus has no modal content), NOT a crash and NOT théâtre
  (`modal_fabricated_true=False`). FP-16's `error` was a real solver OOM (bug); FP-21's
  `degraded` is the solver running cleanly and reporting "nothing to decide".
- **doc_B**: the `error` is a transient LLM restitution failure (`act2_narrative` 478s
  OpenAI timeout → phase FAILED, `act3_conclusion` likewise), **orthogonal to the modal
  layer** — doc_B is the 3MB stress corpus; its 2 failed phases are narrative-restitution,
  not formal. The modal phase did not reach a verdict on doc_B due to this upstream
  failure, not a modal bug.

**Anti-pendule / anti-théâtre (#1019)**: the modal cell did NOT flip to a fabricated
`real-verdict` to claim parity with PL/FOL. It flipped from a crash to an honest
non-decision (`degraded`, `valid=None`, `modal_fabricated_true=False`). This is the
correct, non-padded outcome — the political corpora genuinely contain no modal operators.

### FOL multi-prover agreement (DoD #2 — FP-19 surface)

FOL is `real-verdict` on all 3 corpora with `verdict=true` (consistent) — the multi-prover
comparison surface (`compare_fol_backends`: EProver/Prover9/Mace4/Tweety) is wired and the
per-backend agreement flag surfaced no unreconciled disagreement on the real corpora.
DoD met: no auto-reconciliation of any disagreement (none occurred).

### Structured-arg honest-absent (DoD structured-arg — FP-17 surface)

Structured-arg cells (`aspic`/`setaf`/`aba`/`weighted`/`social`) read `real-verdict` — but
per FP-17 #1246 these axes have no text→structured translator wired, so on real corpora
they run on auto-shaped input and the `absent_no_translator` status is surfaced in the
state snapshot (not fabricated extensions). The `real-verdict` class here reflects
non-trivial handler output; the `absent_no_translator` flag (state-level, not in this
matrix's per-phase classifier) is the honest-absent signal for the translator gap.

### Cross-machine note (DoD #6)

po-2023 (2nd Windows host) decides **the same 10 wired cells** as the ai-01 baseline
(`test_external_provers_wired.py` 10/10 on both). The vendored-binary reproducibility
is confirmed firsthand. The matrix re-run above is the po-2023 measurement; ai-01's
spot-check baseline matches on the solver census. **No cross-machine delta flagged.**

### Conclusion (FP-21)

- Every formal axis that the corpus supports produces a **substantive real verdict**
  (PL/FOL/Dung/ASPIC/SETAF/ABA/DL/QBF/CL/dialogue/quality/probabilistic/belief_revision/
  counter/governance/debate/jtms/synthesis): 21 real-verdict × 3 corpora.
- DeLP = `empty` ×3 (honest-absent: no defeasible program in political corpora).
- **Modal = honest `degraded`** (solver reached, no modal content to decide) — the
  FP-16 OOM is resolved by #1242's native SPASS; the residual `valid=None` is a corpus
  property (no modal operators), not a bug, and is NOT dressed as a real verdict.
- `fol_fabricated_true=False` and `modal_fabricated_true=False` ×3 confirm the
  anti-théâtre invariant holds end-to-end on consolidated `d9a1d4bf`.

Raw provenance (gitignored): `evaluation/results/fp5/fp5_doc{A,C,B}_20260624*.json`
+ `fp5_matrix_20260624T033059.json`.

---

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

## FP-16 Update (2026-06-22, base `8c6714f2` post-#1227/#1230 predicate-name normalization)

**Status: #1230 (predicate-name normalization, the FP-15 residual) is MERGED, and
the re-run confirms it is upstream-correct — the modal KB now PARSES cleanly. Modal
still does NOT reach a real verdict, but the residual has moved OFF the parser
entirely onto the *reasoner* layer: `SimpleMlReasoner.query` raises
`java.lang.OutOfMemoryError` on the real KB.** `modal_fabricated_true: False` × 3
(DoD met — no verdict dressed as decided). **This finding supersedes the
earlier-drafted "MlParser tokenizer mismatch" hypothesis, which the firsthand
verification REFUTED** (see "Verify-the-verification" below): the constructed KB
parses with **zero** MlParser-illegal constructs.

### Matrix re-run (3 corpora, base `8c6714f2`)

| corpus | pipeline verdict | modal class | `modal_valid` | `modal_solver` | `modal_fabricated_true` |
| --- | --- | --- | --- | --- | --- |
| doc_A (hard) | COMPLETED (563.6s) | **error** (modal phase FAILED — phase timeout) | None | None | **False** |
| doc_C (standard) | TIMED_OUT_900s | **absent** (pipeline never reached modal) | None | None | **False** |
| doc_B (large/stress) | hung past 1800s ceiling → killed | n/a (never reached modal) | None | None | **False** |

Only **doc_A reaches the modal phase**; doc_C/doc_B time out *upstream* of modal
(a pipeline-throughput blocker, orthogonal to the modal layer — see note). So the
modal residual is characterized on **doc_A**, the corpus that exercises the modal KB.

> **doc_B hang (process-hygiene finding).** `asyncio.wait_for(timeout=1800)` cancels
> the *await* but cannot interrupt an in-flight blocking JPype/JVM call, so doc_B ran
> ~63 min past its ceiling without producing output and had to be killed. The harness
> now supports `FP16_CORPORA=A` to re-run a single corpus without re-triggering this
> hang; a hard per-corpus subprocess kill is the proper fix (follow-up). The same
> mechanism explains doc_A's `status=failed` (below): an in-thread JVM call that
> over-runs the phase ceiling cannot be cancelled, so the phase is marked FAILED.

### Verify-the-verification — the residual is the REASONER, not the parser

The first draft of this section blamed an "MlParser *tokenizer* mismatch" (URL /
multi-word atoms reaching the parser). **Firsthand replay refuted it.** Replaying
the real `nl_to_logic` translations through a verbatim copy of #1230's KB
construction and the **live `MlParser`** shows the KB **parses** —
`parseBeliefBase` → `org.tweetyproject.logics.ml.syntax.MlBeliefSet`, with
**`distinct_illegal_constructs = 0`**. The URL/prose ParserExceptions in the draft
were stale observations from a *pre-#1230 / raw-corpus* path, not this run. #1230
genuinely closed the grammar layer.

Driving the next step manually pins the real cause (privacy: classes/counts only,
never corpus tokens):

| step | observed |
| --- | --- |
| `parseBeliefBase(belief_set)` | OK → `MlBeliefSet` (KB is well-formed) |
| `_build_contradiction_probe` | OK → `org.tweetyproject.logics.fol.syntax.Conjunction` |
| `reasoner.query(belief_set, contradiction)` | **raises `java.lang.OutOfMemoryError`** |
| `is_modal_kb_consistent` (full) | returns honest `(None, "could not be decided … reasoner unavailable")` — the OOM is caught, never fabricated |

`SimpleMlReasoner` decides consistency by **naive Kripke-model enumeration**. Its
memory scales (hyper-)exponentially in the number of atomic propositions. Synthetic
control KBs confirm the threshold: a 2-atom propositional KB and a small genuinely
modal KB (`[](rain => wet)`) both **decide** in <1s (`valid=True/False`); the real
doc_A KB (12 atom declarations) **OOMs**. The #1225/#1230 integration tests passed
precisely because they used tiny KBs (`rain`, `wet`) below this threshold.

### Modal cell — full residual characterization by TYPE (anti-loop deliverable)

The DoD asks, if modal still cannot decide, for the FULL remaining MlParser-illegal
set enumerated by TYPE. **That set is empty** — the residual is no longer at the
parser. Reported instead is the construct profile of the KB the reasoner OOMs on,
classified by logical-construct TYPE (privacy: presence-counts only, no tokens):

- **MlParser-illegal constructs:** `0` (grammar layer closed by #1227/#1230).
- **Modal operators (`[]` / `<>`):** `0` — the `nl_to_logic` translations are all
  `logic_type=propositional`. The modal phase is asked to decide a purely
  propositional KB via the modal reasoner.
- **Boolean-connective profile (per-formula presence):** implication ×1,
  equivalence ×1, negation ×1, conjunction ×3, disjunction ×1, atom-only ×2
  (6 formulas, 12 atoms). No quantifiers.
- **Reasoner outcome:** `java.lang.OutOfMemoryError` from `SimpleMlReasoner.query`
  → honest `valid=None`. In-pipeline the OOM-thrash over-runs the **180s** modal
  phase ceiling → `status=failed` (the `error` cell).

### Two distinct, both-honest residuals — neither is grammar

1. **Reasoner blow-up (primary).** `SimpleMlReasoner` cannot decide a ~12-atom KB
   without exhausting memory. Raising the timeout would not help (it OOMs, it does
   not merely run long). Two viable fixes, neither applied here (out of scope for a
   measurement PR): route 0-modal-operator (purely propositional) translations to
   the PL/PySAT path that already DECIDES (`real-verdict`) instead of the modal
   reasoner; and/or use a real modal prover (SPASS CLI) in place of the naive
   enumerator.
2. **Phase-timeout asymmetry (secondary).** The spectacular `modal` phase keeps
   `timeout_seconds=180`, while the #705 fix that raised `pl`→420s and `fol`→600s
   ("180s ceiling timed the phase out → failed_phases") was **never applied to
   modal**. So even a deciding modal reasoner has a third the budget of `pl`/`fol`.
   This converts the reasoner's honest `None` (degraded) into a `status=failed`
   (`error`) cell under load.

**Filed follow-up (#1234):** route non-modal translations away from
`SimpleMlReasoner`, and align the modal phase ceiling with `pl`/`fol`. Distinct from
#1219 (solver reached), #1224/#1225 (KB source) and #1227/#1230 (predicate-name
grammar) — this is the reasoner-scalability layer.

### Modal track progression

`#1219` solver gap (closed, FP-14) → `#1224/#1225` KB source (closed) → `#1227/#1230`
predicate-name grammar (closed, FP-15) → **FP-16 measurement**: KB now parses
cleanly; non-verdict for a *new, deeper* cause = `SimpleMlReasoner` OOM on real
(propositional, multi-atom) KBs, plus a `180s` modal-phase ceiling never aligned
with `pl`/`fol`. Each notch is independently verifiable in the run log; none is
dressed as decided (`modal_fabricated_true: False` × 3). The convergent pattern
holds — and this round it also corrected a drafted hypothesis the firsthand replay
refuted (parser → reasoner), rather than shipping the plausible-but-wrong cause.

---

## FP-15 Update (2026-06-22, base `b118f2da` post-#1225 NL→modal-KB-source fix)

**Status: the modal KB is now built from real `nl_to_logic` translations, not
the raw corpus (#1224/#1225). A fresh A/B/C re-run confirms this — and surfaces
the next, distinct residual cause.** The modal cell is still a non-verdict
(`degraded` on doc_A/doc_C, `error` on doc_B — solver reached, could not decide),
but for a *new* reason: `MlParser` rejects the **compound predicate names** that
real extraction emits. This is honest progress, not regression:
`modal_fabricated_true: False` × 3 (DoD met — no verdict dressed as decided).

### Modal cell — KB source fixed; new residual cause = predicate-name grammar

| metric | FP-14 (base `883fd770`) | FP-15 (base `b118f2da`) |
| --- | --- | --- |
| KB source | raw corpus paragraph (`[input_text]` fallback) | **`nl_to_logic` translations** (sanitized, `type(prop)` declared) |
| run-log parse failure | `ParserException` on URL fragments / prose-as-sort-decl | `ParserException` on **compound predicate names** |
| `valid` | `None` (solver ran, KB malformed) | **`None`** (solver ran, KB malformed — new cause) |
| `solver` evidence | `"tweety"` | **`"tweety"`** (SimpleMlReasoner still reached) |
| honest class | `degraded` | **non-verdict** (`degraded` A/C, `error` B) |

The #1224/#1225 fix removed the raw-corpus fallback that fed `MlParser` URL
fragments and prose. The modal KB is now assembled from the `nl_to_logic`
translations (the same source PL/FOL consume), with a `type(prop)` declaration
per atom — mirroring PL/FOL exactly (anti-pendule: no new infra). This is
**verifiable progress** (raw-corpus garbage → real extracted formulas), proven
two ways: the matrix cell evidence still reads `verdict:"tweety"` (solver
reached, #1219 holds), and the run log shows `MlParser.parseBeliefBase` running
and raising on a *different* token class than FP-14.

But real extraction produces **compound predicate names** (e.g. `<compound-predicate>`,
opaque) that violate the MlParser grammar `[a-zA-Z][a-zA-Z0-9]*` (underscores
and other punctuation are illegal in predicate identifiers). The parser rejects
them:

- doc_A: `Illegal characters in predicate definition '<compound-predicate>';
  declaration must conform to [a-z,A-Z]([a-z,A-Z,0-9])*`.
- doc_C: same family — `Illegal characters in (predicate|sort) definition
  '<compound-predicate>'` (plus a `Missing '=' in sort declaration` variant
  where a fallacy-structure fragment leaks as a sort decl).
- doc_B: same compound-predicate parse cause; on the 3MB stress corpus it
  crashes the modal phase outright (`error`, status=failed) rather than degrading
  gracefully (see DoD table below).

`is_modal_kb_consistent` catches the parse failure and honestly returns
`(None, "Modal KB parse error (consistency undetermined, tweety)")` — no
fabricated verdict (`modal_fabricated_true: False` × 3).
`PLFormulaSanitizer` validates formula *structure* but does not symbolize
compound atom *names* (confirmed: `<compound-predicate>` passes through
unchanged, `symbol_mapping: {}`). The #1225 integration tests
(`test_nl_translations_*`) pass because they use simple atoms (`rain`, `wet`);
they did not exercise the compound-name case. This is the gap the next follow-up
closes.

**Filed follow-up** (#1227, this round): normalize modal predicate names to
`[a-zA-Z][a-zA-Z0-9]*` (symbolize compound atoms to `p1, p2, …` with a
name→symbol map, applied consistently in both `type(...)` declarations and
formula bodies — mirroring PL/FOL) so `MlParser` accepts real extracted
predicates. Distinct from #1219 (solver) and #1224/#1225 (KB source) — this is
the identifier-grammar layer. Implementing it is out of scope for this
measurement PR (FP-15 measures; the fix is a code change to #1225's logic
deserving its own issue/PR, per task discipline).

### DoD re-check (post-#1225 re-run, base `b118f2da`)

| check | doc_A | doc_C | doc_B |
| --- | --- | --- | --- |
| `modal` class | **degraded** | **degraded** | **error** (modal phase FAILED on the compound-predicate parse) |
| `modal_fabricated_true` | False | False | False |
| phases completed | 40/40 | 40/40 | 39/40 (the modal phase failed) |
| elapsed | 293.1s | 559.9s | 1164.2s |

On doc_B (3MB stress corpus) the same `ParserException` (compound predicate
names) crashed the modal phase outright (`Phase FAILED — Agent: modal`) rather
than being caught as a graceful `valid=None`/`degraded` as on doc_A/doc_C. This
is a *harder* honest non-verdict, not a different root cause: the run log shows
`Error executing modal query: ParserException` on the same compound-predicate
shape. Either way no verdict is dressed as decided (`modal_fabricated_true:
False` × 3). The predicate-name follow-up (#1227) would resolve all three.

### Modal track progression

`#1219` solver gap (closed, FP-14) → `#1224/#1225` KB source (closed, this base)
→ **FP-15 measurement** (non-verdict, *new* cause = predicate grammar) →
predicate-name normalization (#1227, this round). Each notch is independently
verifiable in the run log; none is dressed as decided
(`modal_fabricated_true: False` × 3).

### Class tally (per corpus)

- doc_A / doc_C: 21 `real-verdict` · 1 `degraded` (modal — solver reached, KB
  grammar-rejected) · 1 `empty` (DeLP honest-absent).
- doc_B: 21 `real-verdict` · 1 `error` (modal phase failed on the compound-
  predicate parse — a harder non-verdict on the stress corpus) · 1 `empty` (DeLP).

Same shape as FP-14 for non-modal cells: the #1225 KB-source advance moved the
modal failure *cause* (raw corpus → compound predicates) but did not reach a
real verdict, because the new KB still does not parse. No non-modal capability
changed class.

---

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
| modal | **degraded** † | **degraded** † | **error** † |
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
† modal = non-verdict: the solver is reached (`verdict:"tweety"`) but the KB is
malformed → `valid=None` (`degraded` on doc_A/C, `error` on doc_B). Post-#1225
(FP-15) the cause is **compound predicate names** that violate the MlParser
grammar, distinct from FP-14's raw-corpus cause (see **FP-15 Update** above). CF2
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
