# Convergence Benchmark — Corpus B (DeepSynthesis vs 0-shot, hardened rubric)

**Date:** 2026-05-20 · **Harness:** `scripts/scda_deepsynthesis_vs_baseline.py` (#592, Track EE #641)
**Pipeline build:** main `2a4e254e` (Track EE substance rubric merged)
**Model (both sides):** `gpt-5-mini` · **Corpus:** `corpus_dense_B` (~59K chars, opaque ID)
**Raw outputs:** `outputs/deep_analysis/corpus_dense_B/` (gitignored — aggregate only here)

> Privacy: all identifiers are opaque (`arg_N`, `fallacy_*`). No source text, no
> nominative content, no LLM-paraphrased premises/conclusions are reproduced.

---

## 1. Headline

Confirmatory re-run of corpus A's Track EE result (#641) on a second corpus.
The substance advantage **replicates decisively**, and corpus B additionally
clears the ≥3 overall bar that corpus A missed.

| Dimension | Type | Pipeline | 0-shot | Winner |
|---|---|---|---|---|
| Textual citations | surface | **72** | 55 | **pipeline** |
| Named fallacies | surface | 3 | **9** | 0-shot |
| Formal methods (named) | surface | 4 | 4 | tie (pipeline-unique: AGM revision) |
| Cross-text parallels | surface (fixed) | false | false | — (no phantom win) |
| **Convergence verdicts** | **substance** | **5 (max 4 methods)** | **0** | **pipeline** |
| **Computed artifacts** | **substance** | **grounded-ext members + 13-edge attack list** | **none** | **pipeline** |

Verdict: **`meets ≥3 overall: True`** (3 categories: citations + 2 substance) ·
**`meets_substance_threshold: True`** (2/2 substance).

## 2. What replicates from corpus A

The two **unfakeable substance** dimensions behave identically to corpus A:

- **Convergence verdicts: pipeline 5, baseline 0.** Five arguments flagged by
  ≥2 independent methods, the strongest by 4. A single LLM pass cannot run
  independent solvers and report their *actual* agreement.
- **Computed artifacts: pipeline 2, baseline 0.** A concrete grounded-extension
  membership set and a 13-edge attack relation (explicit edge list). The 0-shot
  emits neither.

This is the core claim of "spectacular vs one-shot," now confirmed on **two**
corpora rather than one: the pipeline wins the axis a 0-shot structurally
cannot fake, and the baseline scores **zero** on it both times.

## 3. What differs from corpus A — and why it matters

- **Citations flip in the pipeline's favor here (72 vs 55).** On corpus A the
  0-shot produced *more* citations (106 vs 85); on corpus B the pipeline does.
  This is exactly the variance Track EE warned about: surface metrics are
  baseline-variance-dependent and prove nothing on their own. Corpus B happens
  to clear ≥3 overall *because* the citation coin landed pipeline-side this run
  — not because anything substantive changed between the corpora.
- **The baseline name-drops a formal method it never computes.** The 0-shot is
  credited with `aspic_inconsistency` as a "formal method" (bare-keyword match),
  yet its `computed_artifacts` set is **empty** — it describes ASPIC, builds
  nothing. This is the precise failure mode Track EE's substance metrics were
  built to expose, and they expose it cleanly here: **4 named formal methods, 0
  computed artifacts.**

## 4. Consequence

Two corpora, same verdict on the axis that matters:
**`meets_substance_threshold: True`, baseline 0/2, both times.** The overall
≥3 bar is noisy — it flipped from FAIL on A (2/4) to PASS on B (3/3) purely on
surface variance, while the substance result never moved. The substance
threshold is the stable, decisive measure. The spectacular value of the
pipeline is the cross-method convergence and the computed formal artifacts:
measured, replicated, and unfakeable.

## 5. Still open

- **Corpus C/D re-runs** under the hardened rubric to complete the 4-corpus set.
- **Surface-axis lift (Track GG #644):** wire the CC LLM-prose layer into
  the DeepSynthesis report so the pipeline's prose is citation-rich *by
  construction*, not by baseline variance — winning surface and substance
  together rather than depending on a coin flip.
- **BR-trace rendering bug (#642, Track FF)** and the **PL formula bottleneck**
  (Tweety constant pre-declaration) remain.
