# FB-29 — Adversarial Cross-Verification (anti-self-confirmation)

**Issue**: #1105 (Epic #947). **Dispatch**: R404b (ai-01) → `po-2023 | adversarial-verify FB-29 (anti-self-confirmation) | deep-queue, conditionnel sur PR #1105`.
**Reviewer**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique (independent lane — did NOT write FB-29).
**Target**: PR #1106 (merged `70669eab`) — po-2025's agentic multi-step blindspot-virtue detection.
**Date**: 2026-06-15.

> Privacy: this report references only opaque IDs (`doc_A/B/C`, `arg_N`) and the
> exhibit phrases already published in the merged `FB29_QUALITY_BLINDSPOT_REPORT.md`
> (paraphrased located claims, no speaker names/titles/dates). No `raw_text`.

---

## 1. Mandate

The coordinator (R404b) queued an **independent adversarial cross-verification**
of po-2025's FB-29 claim before letting it bear on the Epic #947 quality verdict.
The specific concern: is the agentic chain's positive differential
(**7/19 args with "demonstrated structure"**, baseline=0.0) **genuine
content-separation**, or **self-confirmation theatre** — a chain tuned to score
higher, a crippled baseline, vacuous "exhibits", or non-load-bearing negative
controls? The DoD itself (#1105) names the trap: *"Higher numbers alone do NOT
count."*

This report is the result of reading the implementation + harness + report and
running independent probes. It does **not** modify po-2025's code (file-disjoint
verify lane); the only artifact added is a new adversarial test file + this report.

---

## 2. What was verified (method)

| Check | How | Result |
|-------|-----|--------|
| **Baseline fairness** | Diffed `BASELINE_EVAL_PROMPT` in `run_fb29_agentic_headtohead.py` vs `run_fb28_quality_headtohead.py` | **Byte-identical** — the differential isolates the agentic upgrade, not a rubric asymmetry. |
| **Author tests load-bearing** | Ran the 13 tests in `test_agentic_virtue_detectors.py` independently (`conda run -n projet-is`) | **13/13 PASS** (1.52s). |
| **No upward inflation** | Wrote 6 NEW adversarial probes (`test_fb29_adversarial_verify.py`) attacking the "chain tuned to score higher" vector | **6/6 PASS** — detector faithfully propagates low/zero scores. |
| **Chain-not-tuned discipline** | Read `agentic_virtue_detectors.py` step3 rubric + the harness corpus_B handling | Strict rubric (strawman→0.0, surface→0.0); rejects where structure absent. |
| **Fail-loud** | Read `_resolve_llm` / `_run_chain_step` / evaluator error path | `AgenticDetectorError` propagates; `None` on failure; never synthetic 0.0. |
| **Exhibits non-vacuous** | Read report §4 exhibits | Specific located claims/domains per arg (not generic "refutation detected"). |
| **Live reproducibility** | Attempted to re-run the head-to-head | **Not possible on this machine** — FB-25 artifacts (`fb25_quality_args_*.json`) are gitignored on po-2025's machine, absent here. See §5. |

---

## 3. Solid properties (genuine anti-theater)

1. **Apples-to-apples baseline.** The 0-shot baseline uses the *exact* FB-28
   prompt (verified by diff) — same 9 virtues, same `{0.0, 0.2, 0.5, 1.0}` scale,
   same rubric. It is not secretly told to score these virtues low. The positive
   differential is therefore attributable to the **multi-step structure**, not a
   crippled baseline. This is the single most important anti-theater property and
   it holds.

2. **The chain is NOT tuned to score higher.** The step3 scoring rubric is strict:
   strawman / non-sequitur → 0.0; surface `comme X` → 0.0. The empirical evidence
   is that the chain **rejects where structure is absent**: corpus_B returns 0/3,
   and 15/19 args score a measured 0.0 (not inflated). A theatre chain would have
   manufactured positives on corpus_B too; it did not.

3. **No upward inflation (independently probed).** My 6 adversarial probes feed
   the detector a *real-refutation* chain (step1 real, step2 `engagement_réel`)
   but a **controlled LOW/ZERO step3 score**. The detector returns exactly that
   low/zero score — it never floors a 0.2 up to 1.0, never overrides a 0.0 verdict
   upward. The detector is a faithful propagator of the LLM's verdict, high *or*
   low. (If FB-29 were theatre, `test_refut_zero_score_propagates_when_steps_say_real`
   would fail — it passes.)

4. **Fail-loud is real.** No-LLM, unparseable-output, and transport-error all
   raise `AgenticDetectorError`; the harness records `None` + `"AGENTIC_FAIL"`
   rather than a synthetic 0.0. No degraded-theatre fallback (#1019).

5. **Exhibits are non-vacuous.** The 7 separating args each cite a specific
   located claim/domain *from that argument* (téléprompteur, calamité économique,
   identité ukrainienne, explication historique; domains guerre/paix, âge d'or) —
   not a generic "refutation detected". A 0-shot call emitted a bare 0.0 on each.
   This is shown structure, the DoD success criterion.

6. **No auto-promotion.** po-2025 explicitly refuses axis-DECIDES (2/9 virtues
   separating ≠ axis-dominance). Anti-#1019 honored.

---

## 4. Honest limitations found (po-2025 flagged most; one is new)

- **Same model both sides.** `gpt-5-mini` judges both the 3-step chain and the
  0-shot baseline. The demonstrated separation is therefore *"vs gpt-5-mini
  0-shot"*, not *"vs any conceivable 0-shot"*. A stronger 1-shot model (e.g.
  gpt-5) might surface the same structure in one call, collapsing the separation.
  (po-2025 §7 hedge 2; the claim "a 0-shot call *cannot* replicate" should be read
  as scoped to this model.)

- **No human ground truth.** The located structures *read* as genuine but are not
  verified against a human-graded rubric — are the 4 "located opposing claims" the
  *correct* opposing claims, or plausible confabulations? Separation is shown;
  correctness-against-ground-truth is the next bar and is unmeasured. (po-2025 §6/§7.)

- **N is small** (19 args; 3 for corpus_B). corpus_B 0/3 could be a genuinely
  source-light sample or insufficient N. (po-2025 §7.)

- **[NEW] Discrimination is fully delegated to the LLM verdict chain; the detector
  has no independent strawman-rejection guard.** The unit-test negative control
  proves the detector *faithfully propagates* an "homme_de_paille" verdict into a
  0.0 — it does **not** prove the detector independently catches strawmen. The
  actual real-vs-strawman classification lives in the LLM's step2/step3 verdicts.
  If a future or flakier LLM returned an *inconsistent* chain (step2 `homme_de_paille`
  but step3 score=1.0), the detector would propagate the 1.0 (false positive) —
  there is no detector-level defense. The current `gpt-5-mini` honors the chain
  (empirically: corpus_B 0/3, 15/19 measured-zero), so this is a **robustness note
  for whoever scales this to more virtues (the idle-fallback lane)**, not a current
  hole. Worth recording: the anti-theater guarantee here is *empirical* (this LLM
  behaves), not *structural* (the detector enforces it).

---

## 5. What I could NOT independently verify

- **The live 7/19 number.** Re-running `run_fb29_agentic_headtohead.py` requires
  the FB-25 extracted-args artifacts (`fb25_quality_args_{A,B,C}.json`), which are
  gitignored and live only on po-2025's machine. I verified the **methodology**
  (fairness, anti-inflation, fail-loud, exhibits) and the **test layer**, but I did
  not reproduce the live LLM run. To fully close the loop, po-2025 (or a run on a
  machine with the artifacts + OpenRouter key) would re-execute and confirm the
  7/19 + per-corpus means. Given the methodology is sound and the budget is ~$0.08,
  this is low-risk to defer, but it is the one claim taken on po-2025's evidence
  rather than independently reproduced.

---

## 6. Verdict

**FB-29's content-separation claim HOLDS under adversarial scrutiny.** It is not
self-confirmation theatre:

- The baseline is fair (identical rubric, not crippled).
- The chain is not tuned to score higher (strict rubric; rejects where structure
  is absent; 6 independent probes confirm no upward inflation).
- The fail-loud is real; the exhibits are non-vacuous; the hedges are honest.

**On the Epic #947 quality axis**: I **concur with po-2025's fork** —
content-separation is **demonstrated on the 2 upgraded virtues** (2/9), the
quality **AXIS stays EDGES** (partial content-separation, not axis-DECIDES). **No
§5 amendment warranted.** This is a *better-substantiated* EDGES (measured partial
separation vs FB-28's reasoned-only), exactly as po-2025 stated — no more, no less.

**Caveat from R405**: FB-29's number was measured under the *castrated* pipeline.
The coordinator's standing direction (R405/#1109) is to **re-measure the quality
axis after de-castration** (FB-30 + FB-31 land). So this strengthened-EDGES may
itself shift once the descent/synthesis sites are un-bridled. FB-29 stands as a
valid *internal* check (its own before/after is honest), but it is not the final
quality measurement for the Epic.

---

## 7. Artifacts added (this verify lane, file-disjoint)

- `tests/unit/argumentation_analysis/agents/core/quality/test_fb29_adversarial_verify.py`
  — 6 load-bearing probes (5 inflation + 1 exhibit-audit). Uses a call-order stub
  (keys off the chain's sequential step1→step2→step3 call sequence, not prompt
  text) so it is robust to prompt wording and independent of po-2025's fixtures.
  All 6 PASS.
- This report.

No change to po-2025's `agentic_virtue_detectors.py`, `quality_evaluator.py`,
`run_fb29_agentic_headtohead.py`, or `FB29_QUALITY_BLINDSPOT_REPORT.md`. Lane:
po-2023 (verify only).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
