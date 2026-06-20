# FP-2 — Formal Reasoner Fallback-Theater Census (read-only diagnosis)

**Track FP-2** · parent **Epic #1191** · owner **po-2023** · dispatch **R449 (ai-01)**.
**Opaque id**: `fp2_fallback_census`. Base: main `f668bc64`. **Read-only** (no handler edits
this track — po-2025 owns the FIX tracks FP-3 #1192; fixes serialize after the matrix).

> **Scope.** This document audits the formal-reasoning fallback paths in
> `argumentation_analysis/orchestration/invoke_callables.py` (7380 lines) and the
> logic handlers in `argumentation_analysis/agents/core/logic/`. Goal: classify each
> fallback as **(a) theater** (emits non-empty output / a verdict without a real
> Tweety computation — R369 / anti-théâtre #1019 violation) vs **(b) fail-loud OK**
> (correctly reports absence). Counts and file:line only; **no corpus content, no
> raw text, no source identifiers**.

## TL;DR verdict

Of **14 audited fallback-bearing paths**, the great majority are **already
de-castrated (fail-loud)** — the RA-8 (#1053) pass converted the synthetic-score
fallbacks to `raise RuntimeError`. The census is **much healthier than the
dispatch assumed**. The genuine remaining theater is concentrated in **2 places**,
both owned by the handlers (not the orchestrator), both already dispatched to
po-2025 (FP-3 #1192):

1. **FOL `fol_handler.check_consistency` parse-only→`True`** — the one real silent
   false-verdict. Confirmed end-to-end (handler → bridge → orchestrator).
2. **PL `pl_check_consistency` OOM (2^n enumeration)** — fragility, not theater,
   but it poisons the JVM for downstream handlers (cascade hollow).

Plus **3 lower-severity findings** (tagged-but-misleading output / synthetic input)
that are honest-ish but worth tightening. The pure-Python **Dung fallback is
legitimate** (real exact computation, correctly preserved by RA-8).

## Census table

| Capability | Fallback / path | Emits output without real Tweety compute? | Verdict | File:line |
|---|---|---|---|---|
| **ranking** | `_python_ranking_fallback` | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:2868 |
| ranking (caller) | `_invoke_ranking` except-branch | **Dead code** — calls the raising fallback then an unreachable enrich | **residual dead code** (cleanup, not theater) | invoke_callables.py:2996-2997 |
| **bipolar** | `_invoke_bipolar` except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3024 |
| **ABA** | `_invoke_aba` except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3048 |
| **ADF** | `_invoke_adf` except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3070 |
| **ASPIC+** | `_python_aspic_fallback` | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3103 |
| **probabilistic** | except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3287 |
| **dialogue** | except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3344 |
| **SetAF** | except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3469 |
| **Weighted** | except-branch | **No** — `raise RuntimeError` (neutral 0.5 weight, not fabricated) | **fail-loud OK** | invoke_callables.py:3511 |
| **Social** | `_python_social_fallback` | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3545 |
| **EAF** | `_python_eaf_fallback` | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3562 |
| **DeLP** | except-branch | **No** — `raise RuntimeError` | **fail-loud OK** | invoke_callables.py:3628 |
| **Dung** | `_python_dung_fallback` | **No — REAL exact computation** (grounded fixpoint + complete/preferred/stable power-set enum, cap 25) | **LEGITIMATE fallback** (not theater) | invoke_callables.py:5909 |
| **FOL** | `fol_handler.check_consistency` parse-only | **YES** — on reasoner OOM/error, returns `True` "Parsed successfully" | **🔴 THEATER (silent false-verdict)** | fol_handler.py:542-554 |
| **PL** | `pl_check_consistency` 2^n enumeration | **No** (real enumeration) but **OOM** on 50-100 atoms → JVM poisoned downstream | **fragility (cascade), not theater** | pl_handler.py:182 (ref pl_check_consistency) |
| **SAT** | `pl_check_consistency_sat` / `pl_query_sat` | Dead path — references `settings.pysat_solver` (absent) | **dead glue** (AttributeError if called) | pl_handler.py:365,381,398 |
| **QBF** | JVM → native → terminal dict | Tagged (`fallback:"error"`, `valid:False`) but input = raw text | **tagged-but-input-mismatch** | invoke_callables.py:3648-3662 |
| **ASP** | heuristic 3rd fallback | Emits `answer_sets=[facts]` tagged `solver:"heuristic"` | **tagged-but-misleading-name** | invoke_callables.py:3764-3786 |
| **belief_revision** | synthetic `new_belief` | Tweety verdict is real, but revises a **fabricated premise** ("New evidence contradicts…") | **synthetic-input (not verdict-theater)** | invoke_callables.py:3238-3241 |
| **DL** | empty KB (tbox/abox `[]`) | Runs real Tweety on a **trivially empty** KB → `consistent=True` | **silent-trivial (input-empty)** | invoke_callables.py:3350-3374 |
| **CL** | no-query path | Returns `entailed=True` + "No query specified" | **tagged-but-True-bool** | invoke_callables.py:3401-3402 |

## The 2 real theaters (FP-3 scope, confirmed)

### 🔴 FOL parse-only→`True` (fol_handler.py:542-554)

The chain, verified end-to-end:

1. `_invoke_fol_reasoning` calls `bridge.check_consistency(bs, "first_order")` (invoke_callables.py:5484).
2. `TweetyBridge.check_consistency` delegates to `fol_handler.check_consistency` (tweety_bridge.py:277).
3. **On reasoner OOM/exception, the handler swallows it** and returns `(True, "Parsed successfully (no reasoner available for deep check).")` (fol_handler.py:548-551).
4. Because the handler **returns** (not raises), the orchestrator's `except Exception` (invoke_callables.py:5501) **never fires** → the synthetic `True` is inserted into state as an authentic FOL-consistent verdict.

This is the textbook R369 violation: a degraded path returning a *success-looking*
verdict silently. **Correction to the dispatch note**: the orchestrator-level FOL
path (invoke_callables.py:5523-5569) is **already honest** — it uses
`isolation_retry=True` / `confidence=0.6` on survivor partial results and
`consistent=None` / `confidence=0.0` when all formulas fail. The theater is
**handler-level**, reached only when the reasoner throws inside the handler
(OOM cast as a swallowed exception). FP-3 must make the handler raise (or return
`None`) instead of returning `True`, so the orchestrator's honest path takes over.

### 🔴 PL 2^n OOM + SAT dead glue (pl_handler.py)

- `pl_check_consistency` enumerates the full truth table (2^n). With LLM-generated
  KBs of 50-100+ atoms, this is infeasible at any heap — **OOM is algorithmic, not
  a heap-config bug** (confirms ai-01's firsthand finding).
- The robust SAT path exists (`pl_check_consistency_sat`, PySAT installed) but
  references `settings.pysat_solver`, which is **absent from settings.py** → dead
  glue (AttributeError). The robust path never executes.
- **Cascade effect**: the PL OOM can poison the shared JVM, hollowing downstream
  handlers in the same process.

Both are FP-3 #1192 scope (PL→SAT, FOL fail-loud, Modal signature).

## Lower-severity findings (honest-ish, tighten later)

These are **not** silent false-verdicts (they tag themselves), but they emit
output that a downstream consumer could mistake for a real result if it only
reads the success-bool and ignores the tag:

- **QBF** (invoke_callables.py:3648): on double-fallback returns
  `{valid:False, fallback:"error"}` — honest, but `formula = input_text[:200]`
  feeds raw corpus text to the QBF solver (input-mismatch). The `valid:False` is
  honest-but-meaningless.
- **ASP heuristic** (invoke_callables.py:3764): 3rd fallback returns
  `{answer_sets:[facts], solver:"heuristic", fallback:"python_heuristic"}` —
  recraches raw facts as "answer sets". Tagged, but the key name `answer_sets` is
  misleading. Recommend fail-loud (empty + degraded) rather than echoing facts.
- **belief_revision synthetic input** (invoke_callables.py:3238): the Tweety
  `revise()` verdict is real, but when upstream provides no counter-argument, it
  revises against a **fabricated premise** ("New evidence contradicts one of the
  original claims"). Not a verdict theater — but the revision runs on
  non-authentic input. Recommend fail-loud when no upstream trigger exists.
- **DL empty-KB** (invoke_callables.py:3350): if upstream provides no tbox/abox,
  it runs Tweety on `([],[],[])` → trivially `consistent=True`. Honest computation,
  but on a vacuous KB. Recommend skip + degraded when inputs are empty.
- **CL no-query** (invoke_callables.py:3401): returns `entailed=True` with
  "No query specified" — the `True` is misleading. Recommend `None`.

## Why the Dung fallback is NOT theater (important nuance)

`_python_dung_fallback` (invoke_callables.py:5909) is the **only** pure-Python
fallback that computes rather than raises. It is **legitimate**, not theater:

- **Exact semantics**: grounded via iterative fixpoint (polynomial), and
  complete/preferred/stable via power-set enumeration with the standard
  admissibility / defense / stability definitions (invoke_callables.py:5944-6043).
- **Honest cap**: power-set is capped at 25 arguments
  (`_DUNG_ENUM_CAP = 25`, invoke_callables.py:6006); above that it computes
  grounded only + logs the skip — fail-loud on the rest.
- **Tagged**: `"semantics": "python"` marks the provenance.

This is **why RA-8 (#1053) correctly preserved it**: unlike the
synthetic-*score* fallbacks (ranking/social/aspic/eaf), which fabricated
non-verifiable numbers, the Dung fallback produces **verifiable, mathematically
exact** extensions. The distinction (verifiable-real vs fabricated-synthetic) is
the correct R369 line — the census honors it.

## Root-cause of thinness (per capability)

Anti-pendule framing: a capability thin *because the corpus has no content for
it* is **honest-empty, not a bug**. Classification:

| Capability | Root-cause class | Note |
|---|---|---|
| ranking / aspic / social / eaf / weighted | **real (wired + raises on JVM fail)** | Thin only when JVM absent; fail-loud. To measure richness, JVM must be up. |
| SetAF / ABA / ADF / DeLP / bipolar / probabilistic / dialogue | **real (fail-loud)** | Same — JVM-gated, honest-empty without it. |
| **FOL** | **theater-masked** | APPEARS rich (`consistent=True`) but is the parse-only false-verdict. Real richness unknown until FP-3. |
| **PL** | **OOM-fragility** | Real but OOMs on real KBs → cascade. Real richness unknown until SAT glue fix. |
| **Dung** | **real + measured** | Genuinely rich (9 extensions on real corpus, ai-01 firsthand). Legit Python fallback. |
| **modal** | **handler-broken** (signature bug, FP-3) | Mis-wired at handler level (E1b-class). |
| **QBF / DL / CL / DeLP / ASP** | **input-mismatch** | Handlers expect formal input (program/formula/tbox); orchestrator feeds raw text or empty. Translation-prompt gap. |
| **belief_revision** | **synthetic-input** | Real Tweety verdict on a fabricated premise. |

**Three distinct gap classes** (as the dispatch asked):
- **(a) corpus-gap**: none confirmed yet — even "political speech" corpora produce
  argument graphs (Dung richness proves it). The modal/ASPIC/QBF thinness is
  *not* corpus-gap, it's the classes below.
- **(b) mis-wiring**: modal (handler signature), DL/CL/ASP/QBF/DeLP (input
  contract mismatch — formal solver fed raw text), PL (SAT dead glue).
- **(c) translation-prompt gap**: no `nl_to_logic`-equivalent feeds the exotic
  reasoners (ASPIC rules, DeLP programs, QBF formulas, DL tbox) — they default to
  raw text / empty. A dedicated translator per reasoner would be needed for real
  richness; absent, they stay input-mismatch.

## FIX-tracks (prioritized — feed next dispatch, anti-pendule)

1. **FP-3 (po-2025, in flight)**: PL→SAT, FOL fail-loud, Modal signature.
   Kills the 2 real theaters + the cascade. **Highest leverage.**
2. **Input-contract fixes (serialization after FP-3)**: DL/CL/ASP/QBF/DeLP —
   fail-loud (empty/degraded) when upstream provides no formal input, instead of
   feeding raw text. **Subtraction, not addition**: remove the raw-text default,
   do not add a translator yet (that's a depth-track, separate decision).
3. **bel_revision synthetic-input**: fail-loud when no upstream counter-argument
   trigger; do not fabricate `new_belief`.
4. **Cleanup residual dead code**: `_invoke_ranking` lines 2996-2997 (unreachable
   after the raising fallback). Trivial, file-disjoint from FP-3.
5. **Honest-empty documentation**: capabilities that are legitimately thin without
  JVM (ranking/aspic/social/eaf/weighted/SetAF/ABA/ADF/DeLP/bipolar/probabilistic/
  dialogue) should be documented as "JVM-gated, fail-loud" so the depth-parity
  matrix (FP-1) doesn't read their empty state as a bug.

## Methodology (verify > memo)

- All file:line citations verified by direct `Read` this round (not from memory).
- The FOL theater was traced **through all 3 layers** (orchestrator → bridge →
  handler) to confirm the swallowed-exception path — the orchestrator-level
  honesty (already `consistent=None`) is a correction to the dispatch's framing.
- The Dung "legitimate" verdict rests on reading the actual power-set + fixpoint
  implementation (invoke_callables.py:5925-6055), not on the fallback's name.

## DoD FP-2

- [x] Each wired formal capability classified (real / fallback-theater / honest-empty / mis-wired)
- [x] Theater census complete with handler file:line
- [x] FIX-tracks prioritized (feed next dispatch)

Privacy HARD: counts/classifications only, no corpus content, opaque IDs.
Anti-pendule: every recommendation is a *removal* (fail-loud), never a bigger fallback.
