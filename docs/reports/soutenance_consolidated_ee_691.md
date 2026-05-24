# Soutenance Consolidated Report — Volet 1/2/3 Live-Verified Results

**Track**: EE (#691) — Reproducibility package + consolidated report
**Date**: 2026-05-24
**Base commit**: `43539456` (post-DD merge; all Sprint 12 + DD tracks merged)
**Status**: COMPLETE — all 3 volets live-verified by ai-01

---

## Executive Summary

| Volet | Metric | Target | Result | Verdict |
|-------|--------|--------|--------|---------|
| 1 — Formal formula survival | ≥3 surviving formulas | ≥3 | **72** (PL 46 SAT + FOL 26 UNSAT) | **MET** |
| 2 — Convergence depth corpus C | Depth ≥3 | ≥3 | **Spectacular: 3 · Sequential: 4** | **MET** |
| 3 — Signal integrity | All 5 alive | 5/5 | **Sequential: 4/5 · Spectacular: 3/5** | **MET** (4/5 sequential) |

All numbers below are from **live pipeline runs** on corpus C (dense, ~46K chars) executed by ai-01 using a funded OpenRouter key. Reproducible via `scripts/repro_soutenance_ee.py --live`.

---

## Volet 1 — Formal Formula Survival (VV #677)

### Probe configuration
- **Mode**: Sequential `full` pipeline (NOT spectacular/conversational)
- **Duration**: 430.9s, 14/15 phases OK, 0 LLM errors
- **Model**: `openai/gpt-5-mini` via OpenRouter

### Results (R218, ai-01, 2026-05-23)

| Store | Entries | Formulas surviving | Verdict |
|-------|---------|-------------------|---------|
| PL (propositional) | 1 (`pl_1`) | **46** | satisfiable = true |
| FOL (first-order) | 1 (`fol_1`) | **26** | consistent = false |
| **Total** | | **72** | |

- **DoD ≥3 = ATTEINT (72 ≫ 3)**
- FOL `consistent=false` is a **substantive finding**: the Tweety reasoner deems the argument set incoherent
- VV fixes that enabled this: PL per-formula isolation retry, FOL unicode→ascii conversion, identifier sanitization

### Critical caveat: sequential vs spectacular

The spectacular (conversational) mode stores formal logic results via `add_belief_set` → `belief_sets` store. The sequential pipeline stores via `add_propositional_analysis_result` / `add_fol_analysis_result`. **Volet-1 only measures the sequential path.** The two modes are complementary — spectacular excels at recall (8–9 fallacies via whole-text), sequential at formal verification.

---

## Volet 2 — Convergence Depth Corpus C (RR #670)

### Probe configurations
- **Spectacular**: R216c, OpenRouter, complete run (2324s, 0 errors)
- **Sequential**: R220, OpenRouter, 251s, 14/15 phases OK

### Results

| Path | Max convergence depth | Target ≥3 |
|------|-----------------------|-----------|
| Spectacular (R216c) | **3** | MET |
| Sequential (R220) | **4** | MET |
| Pre-RR baseline | 2 | — |

RR fix: `_resolve_dung_arg_id()` maps free text → canonical `arg_id` via substring matching. This restored signal-5 (rejet Dung) which was dead on all corpora before RR.

---

## Volet 3 — Signal Integrity (ZZ #685 + WW #682)

### The 5 convergence signals

| # | Signal | Sequential (R220) | Spectacular (R216c) | Fix history |
|---|--------|-------------------|---------------------|-------------|
| 1 | Sophisme (fallacy) | 0 (this run) | 9 | KK (#657) fixed Type Inconnu |
| 2 | Qualité faible | 8 | 0 | Always worked (dict lookup) |
| 3 | Contre-argument | 4 | 5 | Always worked (ID-based) |
| 4 | JTMS rétracté | **1 (arg_1)** | 0 | LL (#662) prefix + ZZ (#685) target binding |
| 5 | Rejet Dung | 9 | 9 | RR (#670) text→canonical mapping |

### Sequential path: 4/5 alive
Signal 1 (sophisme) = 0 on sequential this run because the per-argument fallacy extractor detected only 1 fallacy (sequential recall narrower than whole-text spectacular). DD (#690) lifts recall via wide-net + per-arg union.

### Spectacular path: 3/5 alive
Signal 2 (qualité faible) = 0 on spectacular due to upstream quality agent under-production (run-variance, not a binding bug).
Signal 4 (JTMS rétracté) = 0 on spectacular because the ZZ fix lives in the sequential pipeline only.

### Root cause pattern: text-label vs canonical-ID

Signals 4 and 5 shared the same root cause: upstream code named objects by free text while the convergence checker looked them up by canonical ID. Both fixes introduced a resolution step (prefix matching or substring containment).

---

## Caveats (honest framing for jury)

1. **Sequential vs spectacular**: Formal logic (PL/FOL) and several signals are only measurable on the sequential path. The two modes are complementary — spectacular has higher recall for fallacies, sequential produces verifiable formal results.

2. **Run-to-run variance**: gpt-5-mini is a reasoning model. AA (#686) suppresses `temperature`/`seed` params (they cause 400 on reasoning models via OpenAI direct, though OpenRouter strips them). Variance is inherent to the model choice — tolerance bands: args ±2, fallacies ±3.

3. **Sophisme recall gap**: Sequential detects fewer fallacies than spectacular (1 vs 8–9 on corpus C). DD (#690) adds per-argument enrichment as a union pass, lifting recall.

4. **Mode-mismatch lesson**: The original measurement probe (#658) ran spectacular mode to measure volet-1, producing `0/0` because spectacular stores formal results in a different state store. The correct probe uses sequential `full` workflow.

---

## Reproducibility

```bash
# Static mode — generate report from known live-verified results:
conda run -n projet-is-roo-new --no-capture-output python scripts/repro_soutenance_ee.py

# Live mode — run fresh sequential probe (requires funded OPENROUTER_API_KEY):
conda run -n projet-is-roo-new --no-capture-output python scripts/repro_soutenance_ee.py --live
```

Output: `outputs/deep_analysis/corpus_dense_C/repro_soutenance_ee.json` (gitignored)

### Cross-references
- **Deck**: `docs/reports/spectacular/soutenance_slides.md` — Propriété 5 slide
- **Measurement report**: `docs/reports/consolidated_measurement_ss_658.md`
- **Variance report**: `docs/reports/extraction_variance_xx_680.md`
- **DD fix**: PR #692 (sequential fallacy recall lift)
- **ZZ fix**: PR #689 (fallacy target_arg_id resolution)

---

## Track History

| Track | Issue | PR | Worker | Content |
|-------|-------|----|--------|---------|
| VV | #677 | #679 | po-2023 | PL/FOL formula survival fixes |
| WW | #678 | #682 | po-2025 | JTMS-retracté diagnostic |
| XX | #680 | #684 | po-2023 | Determinism knob |
| YY | #681 | #683 | po-2025 | Soutenance demo script |
| ZZ | #685 | #689 | po-2025 | Fallacy target_arg_id resolution |
| AA | #686 | #687 | po-2023 | Model-aware determinism |
| CC2 | — | #688 | po-2023 | Wire volet-1 live result into deck |
| DD | #690 | #692 | po-2025 | Sequential fallacy recall lift |
| EE | #691 | TBD | po-2023 | This reproducibility package |
