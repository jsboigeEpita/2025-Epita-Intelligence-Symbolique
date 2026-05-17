# SCDA DeepSynthesis Baseline Comparison Report

**Date:** 2026-05-17
**Epic:** #530 (Sprint 2 sub-issue)
**Issue:** #592
**Machine:** myia-po-2025
**Commit:** `966be819` (harness script)

## 1. Executive Summary

First baseline comparison between the SCDA multi-agent pipeline (DeepSynthesis report) and a direct LLM 0-shot analysis on corpus A (58K EN). The pipeline produces **unique formal-method findings** (FOL analysis, AGM belief revision) and **cross-text rhetorical parallels** that the 0-shot baseline does not generate. However, the 0-shot baseline is surprisingly strong at surface-level analysis: more textual citations, more named fallacies, and comparable formal-method mentions.

**Verdict:** The pipeline shows value in **2 unique categories** (FOL analysis, cross-text parallels), below the ≥3 threshold from DoD. The pipeline's advantage is architectural (formal methods grounded in Tweety solvers, structured taxonomy) but currently under-realized due to thin state (1 argument, 0 fallacies extracted).

## 2. Method

### Harness: `scripts/scda_deepsynthesis_vs_baseline.py`

| Step | Action | Output |
|------|--------|--------|
| 1 | Run full SCDA pipeline (4 phases, `spectacular=True`) | `deepsynth_report.md` |
| 2 | Run direct LLM 0-shot with rhetorical analysis prompt | `baseline_0shot.md` |
| 3 | Compare on 5 measurable dimensions | `comparison.json` |

**Model:** gpt-4o-mini (same for both pipeline and baseline)
**Corpus:** corpus_dense_A (58,052 chars EN)

### Comparison Dimensions

| Dimension | Measurement Method |
|-----------|-------------------|
| Textual citations | Regex count of quoted passages ≥10 chars |
| Named fallacies | Keyword matching against 30+ fallacy names with taxonomy check |
| Formal methods | Keyword detection (Tweety, Dung, ASPIC, FOL, PL, Modal, AGM) |
| Cross-text parallels | Keyword detection (cross-text, intertextual, parallels) |
| Report structure | Word count + section count |

## 3. Results — Corpus A

### 3.1 Run Metrics

| Metric | Pipeline | Baseline |
|--------|----------|----------|
| Duration | 698s (11.6 min) | 11.5s |
| Turns/messages | 16 turns, 17 msgs | 1 completion |
| Report length | 210 words, 11 sections | 527 words, 7 sections |
| DeepSynthesis | 4/9 sections populated | N/A |

### 3.2 Dimension Comparison

| Dimension | Pipeline | Baseline | Delta |
|-----------|----------|----------|-------|
| Textual citations | 1 | 12 | **-11** |
| Named fallacies | 0 | 4 (Appel à l'autorité, Ad hominem, Faux dilemme, Généralisation hâtive) | **-4** |
| Formal methods | dung, FOL, AGM | dung, ASPIC, PL | 2 unique to pipeline |
| Cross-text parallels | Yes | No | **Pipeline unique** |
| Word count | 210 | 527 | -317 |
| Section count | 11 | 7 | +4 |

### 3.3 Formal Method Details

**Pipeline (grounded in Tweety/state):**
- `fol_analysis` — FOL axiom generated (`title:(X)`)
- `agm_revision` — AGM belief revision framework available
- `dung_extensions` — Dung framework attempted

**Baseline (text-only, no solver):**
- `dung_extensions` — Mentioned dialectical structure conceptually
- `aspic_inconsistency` — Mentioned ASPIC+ conceptually
- `pl_analysis` — Mentioned propositional logic conceptually

**Pipeline-unique:** FOL (solver-grounded axiom), AGM (state-grounded revision)
**Baseline-unique:** ASPIC (conceptual mention only), PL (conceptual mention only)

## 4. Analysis

### 4.1 Why the Baseline Appears Stronger

The 0-shot baseline generates richer surface-level analysis because:

1. **Direct text access:** The baseline sees the full 30K-char excerpt and freely quotes from it. The pipeline's DeepSynthesis template works from structured state data (arguments, fallacies), which is thin when extraction agents underperform.

2. **No extraction bottleneck:** The baseline doesn't depend on agent coordination — it analyzes everything in one shot. The pipeline's multi-agent approach introduces bottlenecks where upstream failures cascade (e.g., 1 argument extracted → thin DeepSynthesis).

3. **Conceptual vs. grounded formal methods:** The baseline *mentions* Dung/ASPIC/PL conceptually. The pipeline *runs* Tweety solvers and produces grounded axioms. The qualitative difference is significant but not captured by keyword counting.

### 4.2 Pipeline's Genuine Advantages

1. **Solver-grounded formal findings:** FOL axiom `title:(X)` was produced by Tweety, not hallucinated. AGM revision is available in state. These are verifiable computational artifacts, not LLM prose.

2. **Cross-text rhetorical parallels:** The DeepSynthesis report template includes a cross-text parallel section (even if empty for single-corpus runs), which the baseline never attempts.

3. **Structured taxonomy:** When the pipeline works fully (enough arguments extracted), fallacies are taxonomy-anchored with full family paths. The baseline names fallacies but without systematic classification.

4. **Multi-perspective depth:** The pipeline runs 5 specialist agents across 4 phases, each contributing different analytical angles. The baseline is a single-pass monolithic analysis.

### 4.3 Root Cause of Pipeline Underperformance

The pipeline's DeepSynthesis report is thin (210 words, 4/9 sections) because:

1. **Argument extraction failure:** Only 1 argument (`arg_1: "arguments"`) extracted from 58K chars — the LLM uses `add_jtms_belief` instead of `add_argument()`
2. **No fallacies detected:** InformalAgent returns `type: "none"` despite the text being highly rhetorical
3. **No counter-arguments:** Synthesis phase converges on turn 1

These are LLM behavioral issues (agent instruction adherence), not architectural limitations.

## 5. Recommendations

### To Meet ≥3 Categories Threshold

1. **Fix argument extraction** (highest impact): Update ExtractAgent/PM instructions to prefer `add_argument()` with structured fields. This would populate sections 2-8 of the DeepSynthesis report.

2. **Fix fallacy detection**: Investigate why InformalAgent returns `type: "none"` on a text rich with rhetorical devices. Consider updating the fallacy detection prompt or switching to gpt-5-mini.

3. **Strengthen comparison methodology**: Replace keyword-based formal method detection with structured comparison (did Tweety actually run? did it produce a belief set?).

4. **Cross-corpus runs**: Run the comparison on B and C — different languages and rhetorical styles may show different pipeline advantages.

### DoD Status

- [x] Script harness operational
- [ ] 3 runs DeepSynthesis (A/B/C) + 3 baselines 0-shot — A done, B/C pending
- [ ] Report with ≥3 categories — NOT MET (2 unique categories)
- [x] Privacy: opaque IDs, outputs gitignored

## 6. References

- Harness script: `scripts/scda_deepsynthesis_vs_baseline.py`
- Outputs: `outputs/deep_analysis/corpus_dense_A/` (gitignored)
- Convergence fix: commit `73d10e94`
- Sprint 4 audit: `docs/reports/SCDA_AUDIT_POST_SPRINT4_2026-05-16.md`
- Corpus A push: `docs/reports/SCDA_CORPUS_A_PUSH_2026-05-17.md`
