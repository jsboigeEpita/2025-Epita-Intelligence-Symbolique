# FB-38 — Adversarial cross-verify (po-2023, independent of po-2025's measurement)

**Track**: FB-38 #1127 · **Role**: adversarial cross-verify (reserved per coordinator R417 + #1127) · **Target**: po-2025's PR #1128 (`feat/1127-fb38-quality-agentic`, commit `84d28a73`)
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-16

> Privacy: opaque IDs only. This report references code paths, test probes, and
> detector mechanics — no `raw_text`, no source/speaker identifiers.

---

## TL;DR — verdict

**FB-38 HOLDS. The EDGES verdict is honestly earned. No inflation.**

The load-bearing property that makes po-2025's `pertinence +0.516` separation
trustworthy — *the agentic detectors faithfully propagate the step3 LLM verdict
without floor-up* — is **independently verified** by 24 adversarial probes
(`test_fb38_adversarial_verify.py`, this PR). The measurement instrument (the 5
new detectors + the head-to-head script) is sound and non-inflationary; the
measured bidirectional split (2/7 separates, 2/7 stricter, 3/7 neutral) is a
genuine split, not dominance — so EDGES (not DECIDES) is correctly earned. I do
**not** amend po-2025's §5 axis verdict.

---

## Why this cross-verify exists

po-2025 both **produced** the FB-38 measurement (PR #1128) and **reported** the
axis verdict. Per #1127 + R417, the verdict must be adversarially cross-verified
before it weighs on Epic #947 closure (po-2025 cannot verify its own number —
conflict of interest). This is the same role po-2023 played for FB-29 (#1114).

The measurement I cannot reproduce: the live +0.516 number comes from
gitignored per-corpus runs (`evaluation/results/capstone_c1/fb38_*.json`) that
need API spend — po-2025's runs lane. **But the measurement *instrument* is
verifiable**, and that is what makes the number trustworthy: if the detectors
could inflate, the separation could be an artefact of detector code, not the
LLM locating genuine structure. So I stress-test the no-inflation property.

---

## Method — call-order stubs that DECOUPLE step3 from the verdict

po-2025's own 30 tests use **prompt-content-keyed stubs** that COUPLE step3's
score to step2's verdict (digression→0.0, toutes_pertinentes→1.0) — a coherent
chain. That tests positive/negative matching. It does **not** isolate the
inflation vector: it cannot answer "if step3 returns a low score while steps 1-2
report a strong argument, does the detector floor it up?".

These probes use **call-order stubs** (closure with a counter, fresh per detector
invocation) that always emit "strong/real" step1+step2 structure (so no
early-return gate fires) but hand step3 a **controlled** score (0.0 / 0.2 / 0.5
/ 1.0) regardless of the verdict. The detector must return EXACTLY that
controlled score. A floor-up surfaces as a returned score higher than controlled.

This mirrors the FB-29 cross-verify technique (`test_fb29_adversarial_verify.py`).

---

## Results — 24 probes, all PASS

### 1. No-upward-inflation (11 probes) ✅ — the load-bearing claim
For all 5 new detectors, a controlled LOW step3 score (0.0, 0.2, 0.5) propagates
**faithfully** even when steps 1-2 say "real/strong":

| Detector | 0.0 propagates | 0.2 propagates | 0.5 propagates |
|----------|:---:|:---:|:---:|
| pertinence (the +0.516 separator) | ✅ | ✅ | ✅ |
| clarte | ✅ | ✅ | — |
| structure_logique | ✅ | ✅ | — |
| exhaustivite | ✅ | ✅ | — |
| redondance_faible | ✅ | ✅ | — |

**No floor-up found.** The detector code is `score = _snap_to_scale(step3.get("score"))`
used directly — there is no code path that lifts a low step3 score based on the
step1/step2 verdict. Therefore po-2025's separation numbers reflect the LLM's
honest read of located structure, not a tuning artefact.

### 2. Bidirectional fidelity (3 probes) ✅
A controlled HIGH step3 score (1.0) also propagates faithfully (pertinence,
structure, redondance). The detector is a **pure pass-through** of the step3
verdict — not a one-directional correction. This rules out a "ceiling" that
would mask the measurement in the other direction.

### 3. Exhibit non-vacant (6 probes) ✅ — anti-theatre #1019
Every detector embeds the `exhibit` (located structure a 0-shot cannot emit) in
its returned comment, and the exhibit is non-empty. The content-separation
evidence is **real**, not a bare score. The step2 verdict token also surfaces in
the comment (proves the verify-step output is retained, not discarded).

### 4. Fail-loud on corruption (4 probes) ✅ — bounds the measurement
- Non-numeric score (string `"high"`) → `AgenticDetectorError` (fail-loud). ✅
- `bool` score (`True`, an int subclass) → rejected → raises (verified the
  explicit bool guard in `_snap_to_scale`). ✅
- Numeric off-scale (`0.7`) → **snaps to nearest** (0.7→0.5), does NOT raise.
  This is a deliberate tolerance band, **not** an inflation vector — see below.

---

## The one finding — `_snap_to_scale` snaps numeric off-scale values

My first probe run surfaced this (1 initial fail, since corrected). `_snap_to_scale`
snaps a numeric value to the nearest of `{0.0, 0.2, 0.5, 1.0}` rather than failing
loud on a mid-scale value (`0.7`→`0.5`, `0.4`→`0.5`, `0.1`→`0.2`).

**Is this inflation? No** — for two reasons:

1. **Symmetric.** The head-to-head script applies the SAME `_snap_to_scale` to
   the 0-shot baseline side (`run_fb29_agentic_headtohead.py`: `scores[v] = _snap_to_scale(float(val))`).
   Snapping cannot bias the pipe-vs-base differential — both sides snap identically.
2. **Narrow band.** The LLM is asked for strict `{0.0, 0.2, 0.5, 1.0}` and mostly
   complies; snapping only catches minor imprecision (±0.1 around each scale
   point) and rounds both up and down (0.4→0.5 up, 0.6→0.5 down).

The fail-loud guarantee holds where it matters: non-numeric / bool corruption
cannot quietly inject a fabricated score. I record this as a **verified
property** (the probe asserts 0.7→0.5), not a defect. No change to po-2025's code
recommended.

---

## Also verified (source read, not probed)

- **All 5 detectors are genuinely 3-step** (decompose → verify/locate → score)
  with `prev_step` threading between steps — the chain is real, not three
  parallel independent calls.
- **2 source-virtues (`presence_sources`, `fiabilite_sources`) deliberately kept
  lexical.** The module docstring states why: the corpus plausibly lacks external
  citations, so agenticizing them would fabricate sources the text does not
  contain = degraded theatre (#1019). This is an honest subtraction, not an
  oversight. It also means the 7/9 "agentic" headline is honest — the remaining
  2/9 are correctly un-agentizable for this corpus.
- **Head-to-head fairness**: same model (`gpt-5-mini`, single client+model for
  both agentic and baseline paths), same scale `[0.0, 0.2, 0.5, 1.0]`, same rubric
  (`BASELINE_EVAL_PROMPT` byte-identical to FB-28). Separation reflects
  methodology (multi-step locate→verify→score vs single-shot), not model capacity.

---

## Verdict on the axis (EDGES) — concurs with po-2025

The no-inflation property HOLDS, and the methodology is fair (same-model,
symmetric snapping, genuine multi-step chains with non-vacuous exhibits).
Therefore the measured **bidirectional split** (2/7 separates, 2/7 stricter,
3/7 neutral) is honest. A split is not dominance — DECIDES requires clean
one-directional separation, which the data does not show. **EDGES is correctly
earned.** I concur with po-2025's §5 verdict and add no amendment.

### Honest limitations (same shape as FB-29 cross-verify)
1. **Live numbers not reproduced** — the +0.516 / −0.289 figures come from
   gitignored runs needing API spend (po-2025's lane). I verified the *instrument*,
   not the *run*.
2. **No ground truth** — without a gold-standard quality score per arg, the
   bidirectional split cannot be resolved into "agentic is more correct" (po-2025
   hedges this too). My probes confirm the detectors don't *force* a direction;
   they don't establish which direction is *true*.
3. **Discrimination delegated to the LLM verdict chain** — there is no
   detector-level strawman guard beyond the planted pseudo-structure negative
   controls (which po-2025 unit-tests). A genuinely adversarial input that fools
   the step2 verify-call would propagate. This is inherent to LLM-grounded
   detection and is documented, not a defect.

---

## DoD — what this cross-verify delivers

- [x] Independent no-inflation verification of the 5 new detectors (24 probes).
- [x] Anti-theatre check (exhibits non-vacant) + fail-loud bounds.
- [x] Methodology fairness check (same-model/scale/rubric, symmetric snapping).
- [x] Axis-verdict concurrence (EDGES holds) with honest limitations — no §5 amendment.
- [x] Standing-guard probe file committed (`test_fb38_adversarial_verify.py`) —
      merges as a companion to #1128 (test-only, file-disjoint from po-2025's
      detector code; targets the same branch so it runs against the real code).

**Net for Epic #947**: the quality-axis EDGES verdict is independently
corroborated and may bear on the closure decision. The formal axis (DECIDES)
+ quality axis (EDGES, now cross-verified) stand as po-2025 measured them.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
