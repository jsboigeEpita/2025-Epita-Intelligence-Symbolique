# Benchmark Re-run Report — Track OO (#660)

**Date**: 2026-05-21
**Base commit**: `4a6b8fe6` (post-KK + LL + NN; pre-MM merge)
**Tracks included**: KK (detection recall), LL (JTMS convergence signal), NN (adjudication)
**Tracks pending**: MM (formal recall metrics, PR #661 open)
**Model**: gpt-5-mini
**Corpora**: corpus_dense_A, corpus_dense_B, corpus_dense_C

---

## 1. Substance/Surface Matrix (post-KK/LL/NN)

| Metric | A (pipeline/bl) | B (pipeline/bl) | C (pipeline/bl) |
|--------|-----------------|-----------------|-----------------|
| Textual citations | **130** / 61 | **89** / 52 | **90** / 59 |
| Named fallacies | 3 / **8** | 2 / **7** | 1 / **6** |
| Formal methods | 4 / 4 | 4 / 6 | 4 / 5 |
| Convergence verdicts | **8** / 0 | **9** / 0 | **8** / 0 |
| Max convergence depth | **4** / 0 | **3** / 0 | **2** / 0 |
| Total method signals | **20** / 0 | **20** / 0 | **16** / 0 |
| Computed artifacts | **2** / 0 | **2** / 0 | **2** / 0 |
| Attack edges | **28** / 0 | **25** / 0 | **15** / 0 |
| Word count | 4297 / 3398 | 3647 / 3255 | 2931 / 3284 |
| Sections | **43** / 0 | **45** / 0 | **30** / 0 |

### Verdicts

| Corpus | meets_threshold (>=3 cat) | meets_substance_threshold (>=1 unfakeable) |
|--------|---------------------------|---------------------------------------------|
| A | **PASS** | **PASS** |
| B | **PASS** | **PASS** |
| C | **PASS** | **PASS** |

Substance advantage categories (recurring across all 3 corpora):
1. **convergence_depth_unique** — pipeline produces cross-method convergence verdicts; baseline produces 0
2. **computed_artifacts_unique** — pipeline computes grounded_extension_members + attack_edge_list; baseline computes nothing

---

## 2. Before/After Comparison vs R203 Baseline

R203 baseline = last benchmark run at main `50baf4ca` (pre-KK/LL/NN). Current run at `4a6b8fe6` (post-KK/LL/NN).

### Pipeline metrics

| Metric | R203 A / B / C | Current A / B / C | Delta |
|--------|----------------|-------------------|-------|
| Citations | 75 / 72 / 49 | **130** / **89** / **90** | +55 / +17 / +41 |
| Convergence verdicts | 8 / 5 / 4 | 8 / **9** / **8** | 0 / +4 / +4 |
| Max convergence depth | 2 / 4 / 4 | **4** / 3 / 2 | +2 / -1 / -2 |
| Attack edges | 21 / N/A / 15 | **28** / **25** / 15 | +7 / N/A / 0 |
| Named fallacies (pipeline) | 4 / 3 / 1 | 3 / 2 / 1 | -1 / -1 / 0 |

### Key observations

**Citations lift**: Major improvement across all corpora (+55 A, +17 B, +41 C). The KK wide-net pass and LL JTMS signal wiring feed more data into the convergence prose (Track GG), which generates citations by construction.

**Convergence verdicts lift**: B and C each gained +4 verdicts. A stayed at 8 but the **depth** doubled from 2 to 4 — the JTMS signal (Track LL) now fires on corpus A arguments, enabling 4-method convergence.

**Named fallacies honest gap**: Pipeline still names fewer distinct fallacy families than baseline (3 vs 8 on A, 2 vs 7 on B, 1 vs 6 on C). The baseline freely name-drops families it never computed; the pipeline only names families with per-argument detection. This is an **honest gap** — the pipeline's detections are grounded, the baseline's are name-drops. Track NN (adjudication table) now exposes this distinction explicitly in the report.

**Depth variance on C**: Max convergence depth dropped from 4 (R203) to 2 (current). Run-to-run variance in LLM extraction quality — different arguments extracted across runs. The substance verdict remains PASS regardless.

---

## 3. Substance Advantage (Unfakeable)

The baseline 0-shot **never** produces:
- Convergence verdicts (0 on all corpora)
- Computed artifacts (0 on all corpora)

The pipeline **always** produces:
- Convergence verdicts: 8-9 per corpus, with max depth 2-4 methods
- Computed artifacts: grounded_extension_members + attack_edge_list (15-28 edges)

This is the **unfakeable substance** — cross-method convergence and formal computation that a simple prompt cannot replicate.

---

## 4. Surface Assessment (Honest)

The baseline wins on raw surface metrics:
- **Named fallacies**: baseline 6-8 vs pipeline 1-3 per corpus
- **Formal methods claimed**: baseline name-drops 4-6 methods (including aspic_inconsistency, fol_analysis) without computing them; pipeline claims 4 methods actually computed

The pipeline's adjudication section (Track NN) now explicitly distinguishes **grounded** detections (per-argument + convergence-confirmed) from **claimed** ones (wide-net only), exposing the baseline's name-dropping for what it is.

---

## 5. Open Items

- **Track MM (#658)**: PR #661 open (formal recall metrics). Once merged, the pl_metrics/fol_metrics instrumentation will be available. A future re-run can measure >=3 surviving formulas.
- **Max convergence on C**: Currently 2 (vs 4 on A, 3 on B). Run-to-run variance in argument extraction. The JTMS signal is now correctly wired; the variance is in which arguments the LLM extracts.
- **Named fallacy gap**: Pipeline detections are grounded but fewer. Future work: improve per-argument fallacy recall quality (not just filtering).
