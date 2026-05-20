# Convergence Benchmark — Corpus A (DeepSynthesis vs 0-shot)

**Date:** 2026-05-20 · **Harness:** `scripts/scda_deepsynthesis_vs_baseline.py` (#592)
**Pipeline build:** main `5e8eba0f` (Track DD convergence wiring, #637/#639 merged)
**Model (both sides):** `gpt-5-mini` · **Corpus:** `corpus_dense_A` (~58K chars, opaque ID)
**Raw outputs:** `outputs/deep_analysis/corpus_dense_A/` (gitignored — aggregate only here)

> Privacy: all identifiers are opaque (`arg_N`, `fallacy_*`). No source text, no
> nominative content, no LLM-paraphrased premises/conclusions are reproduced.

---

## 1. Headline — honest verdict

With a **fair baseline** (see §2), the pipeline wins **2 of 4** scored advantage
categories, **below the ≥3 threshold** the harness uses for "spectacular".

| Scored category | Pipeline | 0-shot | Pipeline wins? |
|---|---|---|---|
| More textual citations | 85 | 55 | ✅ |
| More named fallacies | 6 | 6 | ➖ tie |
| Formal methods unique to pipeline | 4 named | 5 named | ❌ |
| Cross-text parallels unique | "present" | absent | ✅ (but false-positive, §3) |

**Verdict by the script's own bar: FAIL (2/4).** This is the real signal behind
the user's directive — *"tant que les analyses ne sont pas spectaculaires, il y a
du boulot."* There is boulot.

## 2. The first run was a hollow win — fixed

The initial run reported a 4/4 PASS, but the **baseline produced 0 words**:
`gpt-5-mini` is a reasoning model and the `max_tokens=4096` budget (a) is rejected
by the gpt-5 API in favor of `max_completion_tokens`, and (b) was entirely consumed
by hidden reasoning tokens, returning empty visible content. A win against an empty
opponent is not a win. Fixed in this PR: `max_completion_tokens=16384` + graceful
fallback for older models. The numbers in §1 are from the **fair** re-run (baseline
= 3015 words, 8 sections).

## 3. Why the surface metrics under-sell the pipeline

The harness scores **vocabulary presence**, not **computational substance**:

- **Formal methods are name-dropped, not computed, by the 0-shot.** The baseline
  writes *"Cadre ASPIC+/Dung : les arguments sont attaquables par rebuttal /
  undermining / undercutting"* and closes with *"il faudrait formaliser quelques
  arguments en logique propositionnelle ou ASPIC+ pour montrer où les attaques
  s'appliquent."* It **describes** the frameworks; it never builds one. Yet
  `detect_formal_method_findings` matches the bare keywords (`dung`, `framework`,
  `attaque`, `aspic`…) and credits the baseline with **5 formal methods** — one
  more than the pipeline.
- **Cross-text parallels is a section-header false-positive.** The pipeline's S8
  literally says *"No cross-text parallels in this run (single-corpus analysis)"*,
  but the heading "Cross-Text Rhetorical Parallels" trips the `cross-text` marker.
  The pipeline is credited for an **empty** section.
- **Named-fallacy tie hides an anchoring gap.** Both name 6 families, but the
  metric never checks whether a fallacy is **tied to a specific argument**. The
  pipeline's are (see §4); the 0-shot's float free.

## 4. What the pipeline actually does that a 0-shot structurally cannot

These are **computed artifacts**, present in the pipeline report and absent (only
described) in the baseline — and **none are in the scoring rubric**:

- **Computed Dung framework**: 32 arguments, 26 attacks, a concrete **27-member
  grounded extension** (explicit membership list), and an explicit attack relation
  (`fallacy_Post hoc → arg_1`, `fallacy_Straw man → arg_2`, …). The 0-shot never
  emits a membership set or an edge list.
- **Convergent verdicts (Track DD, the genuine differentiator):** 5 arguments
  flagged by **≥2 independent methods**, with the strongest, `arg_1`, flagged by
  **5 distinct analyses** — rhetorical fallacy detection + quality scoring (0.2/10)
  + counter-argumentation + JTMS truth-maintenance + Dung rejection. A single LLM
  pass cannot run five independent solvers and report their *actual* agreement.
  This cross-method convergence is the spectacular insight — and the benchmark
  does not measure it at all.

## 5. Pipeline quality gaps found during this run (real bugs)

- **Belief Revision Trace renders empty.** The orchestrator log shows *"Belief
  revision: 4 beliefs contracted (4 → 0)"*, but report S6 prints *"No belief
  retractions in this run."* The convergence layer reads JTMS-invalid beliefs from
  a different source than S6, so `arg_1`'s "JTMS retracté" signal and the empty S6
  contradict each other. Rendering/source-of-truth mismatch.
- **PL/Modal findings are thin.** The PL finding contains only extraction-metadata
  atoms, not computed formulas — the long-standing Tweety constant-declaration
  bottleneck. Modal finding is empty.

## 6. Recommended next work (the boulot)

1. **Score substance, not vocabulary** (harness): add a **convergence-depth**
   metric (count of args flagged by ≥2 independent methods; max convergence) and a
   **computed-artifact** metric (presence of an explicit grounded-extension
   membership set, an attack edge list, numeric inconsistency measures, a JTMS
   retraction count). These are unfakeable by a 0-shot.
2. **Fix the cross-text false-positive**: detect populated content, not the heading.
3. **Fix the Belief Revision Trace rendering** so S6 reflects the contractions the
   orchestrator actually computed (and reconcile with the convergence JTMS signal).
4. **Address the PL formula bottleneck** (constant pre-declaration in the signature)
   so Finding shows real formulas instead of extraction metadata.

Once (1) lands, re-run on corpora A/B/C: the expectation is that the pipeline's
margin widens decisively on the *substance* metrics even where it ties or trails on
the surface ones — which is the honest definition of "spectacular" for this system.
