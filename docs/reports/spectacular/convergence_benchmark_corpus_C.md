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

## 5. Still open

- **Corpus D** completes the 4-corpus set.
- **Fallacy→report plumbing**: corpus C surfaced 0 named fallacies in the report
  despite upstream fallacy detection — investigate why (likely the same
  source-of-truth mismatch class as #642).
- **Surface-axis lift (Track GG #644)**: citation-rich prose by construction.
- **BR-trace rendering (#642, Track FF)** and the **PL formula bottleneck**
  (Tweety constant pre-declaration) remain.
