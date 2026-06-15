# FB-29 — Agentic Blindspot-Virtue Detection (multi-step refutation + analogy vs 0-shot)

**Issue**: #1105 (Epic #947). **Dispatch**: R404 (ai-01, mandate user « pousser les vertus aveugles »).
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique.
**Base**: main `ae122434`. **Date**: 2026-06-15.

> Privacy: aggregate-only, opaque IDs (`doc_A/B/C`, `arg_N`). No raw_text, no
> speaker names, no corpus titles. Raw per-arg results are gitignored under
> `argumentation_analysis/evaluation/results/capstone_c1/fb29_*`.

## 1. Question

FB-28 (#1103, merged) proved the pipeline's 9-virtue radar is **stricter, not
richer** than a 0-shot baseline (Δ agg −1.39, baseline ≥ pipeline on 18/19
args), and identified **4 virtues at joint-zero** — both pipeline AND baseline
score 0.0: `refutation_constructive`, `analogie_pertinente`,
`presence_sources`, `fiabilite_sources`. Those are blindspots, not pipeline
wins. The **only honest route to quality→DECIDES** (#1105 DoD) is to make the
pipeline detect *structure a single 0-shot call cannot surface*.

**FB-29 mandate**: upgrade the 2 analyzable blindspot virtues
(`refutation_constructive`, `analogie_pertinente`) to **multi-step agentic
detection** — structured reasoning chains a 0-shot call cannot replicate — then
re-test for **content separation**.

- `refutation_constructive`: decompose → locate the opposing claim → verify the
  rebuttal engages THAT claim (not a strawman) → score on demonstrated engagement.
- `analogie_pertinente`: identify source/target domains → map the structural
  correspondence → score on mapping quality (reject surface `comme X`).

The other 7 virtues stay deterministic/lexical. The source-citation virtues
(`presence_sources`, `fiabilite_sources`) stay lexical: the corpus plausibly
lacks external citations, and fabricating them is forbidden (#1105 DoD).

## 2. Method — multi-step agentic chain vs 0-shot single call

The agentic detectors (``agentic_virtue_detectors.py``) run a **3-step chain**
per virtue, each step consuming the previous step's structured JSON output:

| Step | refutation_constructive | analogie_pertinente |
|------|-------------------------|---------------------|
| 1 | DECOMPOSE: locate opposing claim | DOMAINS: source + target domain |
| 2 | VERIFY: engagement vs strawman/non-sequitur | MAPPING: structural correspondence |
| 3 | SCORE on demonstrated engagement | SCORE on mapping quality |

A 0-shot baseline emits **one score** per virtue; the agentic chain emits a
**demonstrated structure** (located target + verdict / domains + mapping) as an
**exhibit**. That exhibit is the content-separation claim — it can be shown on
real args where the baseline returned only a number.

Both the agentic pipeline and the 0-shot baseline judge the SAME extracted args
(FB-25 artifacts) on the SAME 9 virtues + SAME scale `{0.0, 0.2, 0.5, 1.0}`.
The differential isolates the agentic upgrade.

Anti-théâtre (#1105): higher numbers ALONE do not count. The chain was NOT tuned
to score higher; the detectors REJECT planted strawmen / surface `comme X`
(negative controls, mandatory, load-bearing tests). The deliverable is the
honest fork.

## 3. Differential — upgraded virtues (agentic pipeline vs 0-shot baseline)

`Δ(pipe−base)` = agentic_pipeline_mean − baseline_0shot_mean. `upgradeΔ` = agentic − FB-28 lexical (isolates the upgrade). Both sides judge the SAME extracted args, SAME rubric, SAME scale.

| Corpus | n | Virtue | Agentic pipe | 0-shot base | FB-28 lex | Δ(pipe−base) | upgradeΔ |
|--------|---|--------|--------------|-------------|-----------|---------------|----------|
| doc_A | 8 | refutation_constructive | **0.250** | 0.0 | 0.0 | **+0.250** | +0.250 |
| doc_A | 8 | analogie_pertinente | **0.125** | 0.0 | 0.0 | **+0.125** | +0.125 |
| doc_B | 3 | refutation_constructive | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| doc_B | 3 | analogie_pertinente | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| doc_C | 8 | refutation_constructive | **0.250** | 0.0 | 0.0 | **+0.250** | +0.250 |
| doc_C | 8 | analogie_pertinente | **0.025** | 0.0 | 0.0 | **+0.025** | +0.025 |

**The differential is POSITIVE on the upgraded virtues** (where structure was found) — the **opposite** of FB-28's system-wide negative (Δ agg −1.39). The agentic upgrade created separation where the lexical radar and the 0-shot baseline both scored 0.0 (the FB-28 §4 joint blindspot).

## 4. The content-separation question — structure DEMONSTRATED (not score inflation)

The DoD fork is strict: higher numbers ALONE do not count (FB-28 proved stricter≠better). Content-dominance requires **shown structure the 0-shot missed**, for ≥K args. Examining every arg where pipe>0, base=0:

**refutation_constructive — 4/19 args with demonstrated structure** (all pipe=1.0, base=0.0):
- doc_A arg_1: located opposing claim = *« l'absence de téléprompteur est un problème »*; verdict = `engagement_réel`.
- doc_A arg_8: located opposing claim = *« l'administration précédente n'avait pas laissé une calamité économique »*; verdict = `engagement_réel`.
- doc_C arg_1: located opposing claim = *« l'Ukraine est un pays distinct, identité nationale séparée de la Russie »*; verdict = `engagement_réel`.
- doc_C arg_8: located opposing claim = *« l'explication historique n'est pas nécessaire »*; verdict = `engagement_réel`.

**analogie_pertinente — 3/19 args with demonstrated structure** (pipe>0, base=0.0):
- doc_A arg_3 (pipe=0.5): domains = guerre/armes → la paix; mapping = *guns → acteurs violents, shattered → …* (partial structural mapping).
- doc_A arg_7 (pipe=0.5): domains = âge d'or → période actuelle US; mapping = *âge d'or ↔ prospérité généralisée*.
- doc_C arg_2 (pipe=0.2): domains = liens personnels → Ukrainiens; mapping = identification directe (projection — weak, hence 0.2).

**The exhibits are non-vacuous.** Each cites a specific claim/domain located *in that argument* (teleprompter, economic calamity, Ukrainian identity, war/peace imagery, golden age) and a structural verdict — not a generic "refutation detected". The 0-shot baseline emitted a single `0.0` on each. **This is content-separation with demonstrated structure, the DoD success criterion for the upgraded virtues.**

The negative-control discipline holds: the chain REJECTS where structure is absent (corpus_B: 0/3, no false positives; the 15/19 args with no located structure scored a measured 0.0, not inflated).

## 5. Verdict fork (DoD) — upgraded virtues SEPARATE; quality AXIS stays EDGES (partial content-separation, not axis-DECIDES)

**On the 2 upgraded virtues**: content-separation is **DEMONSTRATED** — 7/19 args (37%) with located structure (4 refutation + 3 analogy), positive differential, non-vacuous exhibits, baseline=0.0, no false positives. The DoD's "≥K args with shown structure the 0-shot missed" is met (K=7 aggregate; 4 on refutation, 3 on analogy).

**On the quality axis (9 virtues)**: **EDGES stands, but strengthened.** Axis-level DECIDES would require content-dominance across the category. The other 7 virtues still do not separate (FB-28 holds: pipeline ≤ baseline there). 2/9 virtues moving from joint-blindspot to demonstrated-separation is a genuine measured improvement — it closes the gap FB-28 §4 identified — but it does **not** make the axis uniformly content-dominant. Per anti-auto-promotion (#1019), 2/9 is not axis-DECIDES.

**Net**: the agentic upgrade turned the quality axis from *EDGES-by-existence* (FB-28: stricter not richer, all virtues) into *EDGES-with-partial-content-separation* (FB-29: 2 hardest blindspot virtues now demonstrate structure the 0-shot misses). The Epic #947 min-rule binding constraint (quality = the capping axis) is **better-substantiated** but **not lifted**.

## 6. Consequence for Epic #947

Epic #947 terminal verdict (FB-26 §5, R403): **EDGES (min-rule)** — formal block DECIDES, quality axis EDGES (the binding constraint). **FB-29 does not amend §5.** The quality axis is still EDGES, now with stronger evidence: the 2 hardest blindspot virtues are no longer a joint-zero gap but a demonstrated content-separation on a minority of args. The honest read is that quality is a *measured, partially-separating* EDGES — better than FB-28's reasoned-only EDGES, still short of axis-DECIDES.

The remaining theoretical route to quality→DECIDES (per R403 §6): either (a) scale the agentic detection to more virtues where the corpus has structure (idle-fallback lane), or (b) an accuracy-vs-ground-truth study to show the located structure is *correct* (not just that it separates). FB-29 shows separation; correctness-against-human-judgment is the next bar and is not measured here.

## 7. Honest hedges

- **N is small** (19 args, 3 for corpus_B). The 7/19 separation rate is consistent across A and C but corpus_B (3 args) found nothing — could be a genuinely source-light sample or insufficient N.
- **Same-model** (`gpt-5-mini`) for both agentic chain and baseline. A multi-model baseline would strengthen the "0-shot cannot surface this" claim.
- **No human ground truth.** The located structures *read* as genuine (specific claims/domains from the text), and the negative controls reject correctly, but we have not verified against a human-graded rubric that the located opposing claims are the *correct* opposing claims. Separation is shown; correctness-against-ground-truth is the next bar.
- **doc_B zero.** No separation on corpus_B (0/3 args). Either corpus_B lacks these structures or the 3-arg sample is too small — flagged honestly, not hand-waved.
- **7/9 virtues unchanged.** The agentic upgrade is surgical (2 virtues). The FB-28 result holds for the other 7; this report does not re-litigate them.

## 8. Reproducibility

- Harness: `scripts/run_fb29_agentic_headtohead.py` (file-disjoint from FB-28).
- Agentic detectors: `argumentation_analysis/agents/core/quality/agentic_virtue_detectors.py`.
- Evaluator upgrade: `ArgumentQualityEvaluator.evaluate(text, agentic_llm=...)`.
- Pipeline side: replayed from FB-25 artifacts + live agentic LLM chain (`gpt-5-mini`).
- Baseline side: `evaluation/results/capstone_c1/fb29_agentic_{A,B,C}.json` (gitignored).
- Load-bearing tests: `tests/unit/argumentation_analysis/agents/core/quality/test_agentic_virtue_detectors.py` (13 tests: positive control MATCH + negative control REJECT + fail-loud + evaluator routing).
- Budget: OpenRouter $161.26 → $161.18 (FB-29 spend ~$0.08 — 19 args × (6 agentic steps + 1 baseline call)). Verified real via credits API.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
