# Convergence Benchmark — Corpus C (DeepSynthesis vs 0-shot, hardened rubric)

**Date:** 2026-05-20 · **Harness:** `scripts/scda_deepsynthesis_vs_baseline.py` (#592, Track EE #641)
**Pipeline build:** main `8cc25ac8` (Track EE substance rubric + corpus B report)
**Model (both sides):** `gpt-5-mini` · **Corpus:** `corpus_dense_C` (~46K chars, opaque ID)
**Raw outputs:** `outputs/deep_analysis/corpus_dense_C/` (gitignored — aggregate only here)

> Privacy: all identifiers are opaque (`arg_N`, `fallacy_*`). No source text, no
> nominative content, no LLM-paraphrased premises/conclusions are reproduced.

---

## 1. Headline

Third corpus in the Track EE confirmatory set. The **substance threshold holds
again** (pipeline 2/2, baseline 0/2), making it 3-for-3 across A/B/C. But corpus
C is the pipeline's **weakest surface showing** and surfaces a real quality gap
worth fixing.

| Dimension | Type | Pipeline | 0-shot | Winner |
|---|---|---|---|---|
| Textual citations | surface | 37 | **60** | 0-shot |
| Named fallacies | surface | **0** | **6** | 0-shot |
| Formal methods (named) | surface | 3 | **5** | 0-shot |
| Cross-text parallels | surface (fixed) | false | false | — |
| **Convergence verdicts** | **substance** | **2 (max 4 methods)** | **0** | **pipeline** |
| **Computed artifacts** | **substance** | **grounded-ext members + 6-edge attack list** | **none** | **pipeline** |

Verdict: `meets ≥3 overall: False` (2 categories, both substance) ·
**`meets_substance_threshold: True`** (2/2 substance).

## 2. The substance story is now robust (3-for-3)

Across A, B, and C the unfakeable axis is unanimous:

| Corpus | Convergence (pipeline / baseline) | Computed artifacts (pipeline / baseline) | Substance verdict |
|---|---|---|---|
| A | 5 / 0 | 2 / 0 | pipeline 2/2 |
| B | 5 / 0 | 2 / 0 | pipeline 2/2 |
| C | 2 / 0 | 2 / 0 | pipeline 2/2 |

The baseline scores **zero** on convergence and computed artifacts on every
corpus. A 0-shot cannot run independent solvers and tally their agreement, nor
emit a grounded-extension membership set and an explicit attack edge list. This
is the spectacular differentiator, and it is now demonstrated three times.

## 3. Honest weaknesses on corpus C (the boulot)

- **The pipeline named ZERO fallacies in the report.** The 0-shot named 6. This
  is not a rubric artifact — the DeepSynthesis report's fallacy section was
  empty for corpus C. A concrete pipeline gap: fallacies detected upstream are
  not surfacing into the report the jury reads (the recurring
  components-vs-deliverables failure). Worth a dedicated fix.
- **Fewer convergence verdicts (2 vs 5 on A/B).** Still beats the baseline's 0,
  and one argument is still flagged by 4 independent methods — but the
  convergence layer found less to converge on here. Partly downstream of the
  empty fallacy section: a fallacy signal is one of the five convergence inputs,
  so zero named fallacies starves the convergence count.
- **Baseline name-drops more formal methods than the pipeline computes (5 vs
  3).** `aspic_inconsistency` and `modal_analysis` appear in the baseline's prose
  as bare keywords; its computed-artifacts set is **empty**. The pipeline's
  `pipeline_unique` formal-method set is empty this run — but its computed
  artifacts are not, which is the distinction that actually matters.

## 4. Consequence

The substance threshold is the stable signal: **3 corpora, pipeline 2/2 every
time, baseline 0/2 every time.** The overall ≥3 bar remains noise (PASS on B,
FAIL on A and C, entirely on surface variance). And corpus C makes the open
boulot concrete: the empty fallacy section directly suppresses both the surface
fallacy count *and* the convergence depth. Fixing the fallacy→report plumbing
(plus Track GG's prose layer) is the path to winning surface and substance
together rather than depending on a coin flip.

## 5. Post-fix re-run (Track FF #642 + GG #644 + HH #648)

Re-ran the same corpus C harness on main `c7350a9f` after the three fixes
landed. The fallacy section is no longer empty, and — as predicted — the
convergence layer recovered once it stopped being starved of fallacy signals.

| Metric | Pre-fix (`8cc25ac8`) | Post-fix (`c7350a9f`) | Δ |
|---|---|---|---|
| Named fallacies (report Section 3) | **0** | **populated** (e.g. genetic-fallacy, cherry-picking diagnoses) | empty → non-empty |
| Convergence verdicts | 2 | **4** | +2 (doubled) |
| Convergence method signals | 6 | **10** | +4 |
| Textual citations (pipeline) | 37 | **49** | +12 |
| Attack-edge list | 6 | **15** | +9 |
| Section count | 18 | 34 | +16 |
| **Overall ≥3 threshold** | **FAIL** | **PASS** | flipped |
| **Substance threshold** | PASS | **PASS** | held |

Root cause was **not** a report-reader mismatch. The deterministic parent-harness
fallacy fallback was already wired and *did* detect fallacies, but its
registration guarded on `hasattr(state, "add_identified_fallacy")` — always
False on `UnifiedAnalysisState` (which exposes `add_fallacy`, not the singular).
So every detected fallacy was silently dropped (#648). The fix registers via
`add_fallacy`.

The knock-on prediction held exactly: with fallacies now in state, the
convergence layer's rhetoric signal feeds `compute_argument_convergence`, and the
top verdict (arg_1) is now flagged by **4 independent methods** — rhetoric/fallacy
+ quality + JTMS + Dung — rendered as Track GG citation-rich prose in the report
the jury reads. Corpus C went from the *weakest* showing (FAIL overall) to a full
PASS on **both** surface and substance.

> Single-run caveat: LLM detection depth varies run-to-run; the structural
> change (0 → non-empty fallacies, 2 → 4 convergence, FAIL → PASS) is the durable
> signal, not the exact counts.

## 6. Still open

- **Corpus D** completes the 4-corpus set.
- ~~**Fallacy→report plumbing**~~ — **RESOLVED** (#648, Track HH; see §5).
- ~~**Surface-axis lift (Track GG #644)**~~ — **DONE** (CC convergence prose now
  rendered in the report; citation-rich by construction).
- ~~**BR-trace rendering (#642, Track FF)**~~ — **RESOLVED** (dual-source belief
  retractions: JTMS chain + AGM contractions).
- **PL formula bottleneck** (Tweety constant pre-declaration) remains — formal
  findings still bottleneck at a small formula count.
- **Fallacy detection depth**: the harness now *registers* fallacies, but named
  count (1 this run) still trails the 0-shot's prose enumeration (7) — a
  detection-recall question, no longer a plumbing one.
