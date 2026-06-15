# FB-28 — Quality Axis Content-Dominance Test (0-shot baseline vs pipeline 9-virtue radar)

**Issue**: #1102 (Epic #947). **Dispatch**: R402b (ai-01, mandate user « pousse encore »).
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique.
**Base**: main `a04f627b`. **Date**: 2026-06-15.

> Privacy: aggregate-only, opaque IDs (`doc_A/B/C`, `arg_N`). No raw_text, no
> speaker names, no corpus titles. Raw per-arg results are gitignored under
> `argumentation_analysis/evaluation/results/capstone_c1/fb28_*`.

## 1. Question

Epic #947 is at its terminal verdict **EDGES** (FB-26 #1099). The **quality axis
is the only non-DECIDES axis** (§5.1/§5.3): the pipeline's 9-virtue radar
demonstrates *existence-dominance* (the 0-shot baseline emits no radar) but
had not been tested for *content-dominance*. **Mandate**: test rigorously whether
the pipeline's quality evaluation **separates** from a 0-shot baseline on the
**content** — if yes, quality → DECIDES; if not, it stays EDGES, honestly.

## 2. Method — apples-to-apples head-to-head

The pipeline radar evaluates the **extracted arguments** (deterministic radar,
FB-25). To isolate *content-dominance* from *extraction-variance*, the **same
extracted arguments** (from the replayable FB-25 artifacts) are fed to a **0-shot
LLM baseline**, asked to evaluate each argument on the **same 9 virtues** with
the **same scale** `{0.0, 0.2, 0.5, 1.0}`. The differential is then pure
*evaluation-capability* on identical units.

| Side | Source | Determinism |
|------|--------|-------------|
| Pipeline | `ArgumentQualityEvaluator` (rule + LLM-assessment), native radar (FB-25 #1095) | deterministic (spread 0.000000) |
| Baseline | 0-shot LLM (`gpt-5-mini` via OpenRouter), structured JSON eval on same rubric | stochastic (LLM) |

Both sides judge the same `arg_1..arg_N` (N≤8 per corpus, same FB-25 window).
Anti-théâtre (#1019): the pipeline radar was **NOT tuned** to score higher —
the radar code is byte-identical to main. The deliverable is the honest
differential, whichever direction it goes.

## 3. Differential — overall (pipeline vs baseline)

| Corpus | n args | Pipeline overall mean | Baseline overall mean | Δ (pipe−base) | pipe > base |
|--------|--------|-----------------------|-----------------------|---------------|-------------|
| doc_A | 8 | **1.70** | 2.33 | **−0.63** | 1 / 8 |
| doc_B | 3 | **1.67** | 3.97 | **−2.30** | 0 / 3 |
| doc_C | 8 | **1.63** | 3.05 | **−1.43** | 0 / 8 |
| **Aggregate (19 args)** | 19 | **~1.66** | **~3.04** | **−1.39** | **1 / 19** |

**The differential is negative on all three corpora.** The 0-shot baseline
scores systematically **higher** than the pipeline on the same arguments
(18/19 args: baseline ≥ pipeline). The pipeline radar is **more restrictive**
than the LLM baseline — it is not *generous*, it is *strict*.

## 4. Differential — per virtue (aggregate across A/B/C)

`Δ` = pipeline_mean − baseline_mean (positive = pipeline stricter-better; negative = baseline scored higher).

| Virtue | Pipe (typical) | Base (typical) | Δ | Read |
|--------|----------------|----------------|---|------|
| clarte | 0.20–0.44 | 0.63–1.00 | −0.19 to −0.74 | Baseline generously credits readability; pipeline Flesch-based, stricter |
| pertinence | 0.20–0.24 | 0.39–0.83 | −0.19 to −0.63 | Baseline credits connectors LLM-perceived; pipeline lexical-only |
| presence_sources | 0.0 | 0.0–0.50 | −0.50 (B) / 0 (A,C) | Tie at 0 on source-light text; baseline sees 1 source in B |
| refutation_constructive | 0.0 | 0.0 | 0.0 | **Tie** — neither detects constructive refutation |
| structure_logique | 0.0 | 0.18–0.30 | −0.18 to −0.30 | Baseline credits perceived logic; pipeline lexical-only |
| analogie_pertinente | 0.0 | 0.0 | 0.0 | **Tie** — neither detects analogy |
| fiabilite_sources | 0.0 | 0.0–0.13 | −0.13 (B) / ~0 (A,C) | Tie at 0 — source-light text |
| exhaustivite | 0.06–0.19 | 0.15–0.24 | −0.03 to −0.18 | Baseline marginally higher |
| redondance_faible | 1.0 | 0.90–1.00 | **+0.10** | **Pipeline ≥ baseline** — deterministic non-redundancy detection |

**Where the pipeline separates from the baseline (Δ ≥ 0)**:
- `redondance_faibre`: pipeline **≥** baseline (deterministic sentence-count +
  repetition heuristic vs LLM judgment) — the one virtue where the pipeline's
  deterministic detection is as-good-or-better.
- `presence_sources`, `refutation_constructive`, `analogie_pertinente`,
  `fiabilite_sources`: **tie at ~0.0** on source-light, dense text — neither
  side detects these virtues (honest joint-blindspot, not a pipeline failure).

**Where the baseline scores higher (Δ < 0)**:
- `clarte`, `pertinence`, `structure_logique`, `exhaustivite`: the LLM baseline
  is consistently more generous, crediting perceived readability/logic that the
  pipeline's lexical heuristics do not surface.

## 5. Verdict fork (DoD) — **EDGES, confirmed rigorously (not DECIDES)**

DECIDES would require the pipeline to demonstrate **content-dominance**: its
evaluation must *separate* from the baseline's — either richer, more anchored,
or detecting virtues the baseline cannot. **The measurement shows the opposite
on 18/19 arguments**: the pipeline is *more restrictive* than, not *richer than*,
the 0-shot baseline.

- The pipeline's only content-edge is `redondance_faible` (deterministic
  non-redundancy), and a set of joint-zero virtues where neither side fires on
  source-light text. That is **not content-dominance**.
- The pipeline's real edge is **existence-dominance + determinism**: it emits a
  **reproducible** (spread 0.000000), **structured** 9-virtue radar the baseline
  cannot emit natively, and it is **stricter** (less generous) than a stochastic
  LLM judgment. Those are real properties — but they are *process* properties
  (deterministic, structured, conservative), not *content-separation* properties.

**Per the #1019 anti-auto-promotion mandate, this is EDGES, not DECIDES.**
Promoting quality to DECIDES would require either (a) the radar to detect
virtues the baseline structurally cannot (it does not — the joint-zero virtues
are a joint blindspot, not a pipeline win), or (b) the radar to be measurably
more *accurate* than the LLM against a ground-truth rubric (not measured here,
and the LLM's higher scores are not evidence of LLM correctness — just
generosity). **EDGES reasoned > DECIDES maximal weakly-claimed.**

## 6. Consequence for the Epic #947 terminal verdict

The Epic verdict (§5, FB-26 #1099) stands at **EDGES (min-rule)**:
formal-logic block DECIDES (Tweety-verified artifacts structurally impossible
for 0-shot), quality axis EDGES (existence + determinism + strictness, not
content-separation). **FB-28 confirms EDGES on the quality axis is the
correct, honestly-measured call — it is not a cap-on-excuse; the measurement
shows the pipeline does not separate from the baseline on content.**

No §5 amendment is proposed (the fork resolves to EDGES, the current verdict).

## 7. Honest hedges (traceable, not clean-story)

- **N is small** (19 args total, 3 for corpus_B due to truncation). The
  direction (baseline ≥ pipeline) is consistent across all 3 corpora and 18/19
  args, but a larger N could sharpen the per-virtue deltas.
- **Same-model comparison**: both pipeline-assessment and baseline use
  `gpt-5-mini`. The pipeline's *deterministic* part (rule + Flesch) is what
  differs from the baseline's *stochastic* judgment. A multi-model baseline
  would strengthen the content-dominance claim either way.
- **No ground truth**: without a human-graded rubric, we cannot say the
  pipeline's stricter scores are *more correct* than the baseline's generous
  ones — only that they do not *separate* (which is what DECIDES requires).
- **Variance**: baseline is stochastic; 1 run/corpus captured (radar side is
  deterministic, spread 0.000000). The idle-fallback re-measure (post FB-27
  merge) can capture baseline variance if needed.

## 8. Reproducibility

- Harness: `scripts/run_fb28_quality_headtohead.py` (file-disjoint from FB-27).
- Pipeline side: replayed from `evaluation/results/capstone_c1/fb25_quality_args_{A,B,C}.json` (FB-25 artifacts, deterministic).
- Baseline side: `evaluation/results/capstone_c1/fb28_headtohead_{A,B,C}.json` (gitignored).
- Assembled differential: `evaluation/results/capstone_c1/fb28_summary.json` (gitignored).
- Budget: OpenRouter $163.39 → $161.29 (FB-28 spend ~$2.10 for 19 baseline evals + 1 retry on C). Verified real via credits API before spend (FB-21).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
