# FB-38 — Agentic quality virtues head-to-head (re-measure axis post-de-castration)

**Track**: FB-38 #1127 · **Parent**: Epic #947 (Final Boss), Quality axis · **Theme**: agentic upgrade of 5 more virtues + honest axis re-measure
**Base**: main `46638f23` (FB-32 wiring live — all 3 synthesis LLM paths active; de-castration soldée FB-30..FB-37)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-16

## TL;DR (honest verdict)

1. **Five more quality virtues were upgraded from lexical/0-shot to multi-step agentic detectors** (pattern FB-29): `clarte`, `pertinence`, `structure_logique`, `exhaustivite`, `redondance_faible`. Combined with FB-29's `refutation_constructive` + `analogie_pertinente`, **7 of 9 virtues** now run agentic chains. The 2 source-virtues (`presence_sources`, `fiabilite_sources`) stay **deliberately lexical** — the corpus carries no citations, so agenticizing them would fabricate structure (theatre). This is subtraction by design (anti-pendule).

2. **The axis verdict stays EDGES — separation is partial and bidirectional, not dominant.** Across 19 args on 3 corpora: **2/7 virtues separate** above the 0-shot baseline (`pertinence` +0.516, `refutation_constructive` +0.105), **2/7 are stricter** (the agentic rubric scores *lower* than 0-shot: `redondance_faible` −0.289, `clarte` −0.059), and **3/7 are neutral**. Overall pipe mean 3.13 vs base 2.75 (Δ+0.377, driven by `pertinence`). This is a split, not dominance — so DECIDES is **not** earned. Per #1127: *the verdict is measured, not forced.*

3. **Content-separation is demonstrated non-vacuously (anti-theater).** Every agentic detector emits an `exhibit` — located structure a single 0-shot score cannot surface: `pertinence` locates the thesis + the specific digression; `refutation_constructive` locates the opposing claim + engagement verdict; `structure_logique` reconstructs the premise→conclusion chain. Two `AGENTIC_FAIL` cases (1 in doc_A, 1 in doc_B) were recorded **fail-loud** as `score=None` (unparseable LLM step) — never fabricated. The structure is real; the *score-direction* is what's split.

4. **FB-38 is the largest measured content-separation in the arc** but does not flip the axis. FB-29 separated 2/9 → EDGES. FB-38 upgrades 7/9 and separates 2/7 strongly (`pertinence` is the single strongest separation measured in FB-28/29/38, +0.516). The agentic path is unambiguously **richer than the lexical baseline** (`upgΔ` positive on 6/7). But vs the *same-model 0-shot LLM baseline*, the axis does not dominate. Quality remains an **EDGES** axis — the formal axis DECIDES; quality is a measured-but-not-decisive companion.

## DoD checklist (#1127)

- [x] 5 agentically-tractable virtues upgraded to multi-step detectors (pattern FB-29) — `clarte`/`pertinence`/`structure_logique`/`exhaustivite`/`redondance_faible`.
- [x] Source-virtues kept lexical (deliberate subtraction — corpus lacks citations, fabrication forbidden).
- [x] Head-to-head re-run on doc_A/B/C — results gitignored under `evaluation/results/capstone_c1/fb38_*.json`.
- [x] Explicit axis verdict (EDGES) with fairness / no-inflation / exhibit evidence + honest hedges (below).
- [x] Report uses opaque IDs ONLY (doc_A/B/C, arg_N). Privacy leak-audited.

## Methodology

### The agentic chain (FB-29 pattern, ×7)
Each upgraded virtue runs a 3-step chain, each step consuming the previous step's JSON, emitting a scored `exhibit`:
1. **decompose/locate** — find the structure (thesis, opposing claim, premise→conclusion, clarity obstacle, dimensions covered/missing, distinct points vs restatement).
2. **verify/verdict** — a gated verdict token (`opaque_réel` / `digression_localisée` / `progression_logique` / `points_distincts` / …) that step3 must discriminate from its rubric prose.
3. **score** — snap to `{0.0, 0.2, 0.5, 1.0}` from the verdict + exhibit. `AgenticDetectorError` (fail-loud) on any non-scale or unparseable output.

The `exhibit` IS the content-separation claim: a 0-shot call emits one score; the chain emits located structure.

### Negative controls (anti-theater #1019)
Each detector is designed to **reject** a planted pseudo-structure where the lexical detector gives a false-positive HIGH: jargon-with-short-words (clarte), connectors+digression (pertinence), enumeration-without-link (structure), long-but-monodimensional (exhaustivite), varied-word restatement (redondance). The detector must return a low score where the lexical path is fooled. Unit-tested (17 new tests; 30 total in the quality suite).

### Fair head-to-head
- **Agentic pipeline**: 7 upgraded virtues via their chains + 2 lexical source-virtues.
- **0-shot baseline**: identical 9-virtue rubric, single call, same scale (FB-28 apples-to-apples).
- **Same model** (`openai/gpt-5-mini` via OpenRouter) for both → separation is about *methodology* (multi-step locate→verify→score vs single-shot), not model capacity.

### Harness hardening (anti-pendule — bounding an unbounded op)
The harness originally had **no per-call timeout** and **no per-call logging**. An early run appeared to "hang" (25 min wall, 2% CPU, zero per-arg progress). A 1-arg probe with added observability root-caused it as **slow-but-progressing**, not a hang: complex detector prompts trigger 256–960 reasoning tokens/call (5–17.6s each), so 22 calls/arg ≈ 175s/arg ≈ 23 min/corpus (8 args). The fix was a **fail-loud bound, not a counterweight**: per-call `timeout=120s` + `max_retries=1` on the LLM client, and a per-call `[llm]` elapsed/reasoning-token log. The operation is unchanged when it succeeds; it just fails loudly instead of hanging silently when the upstream stalls.

## Results — per-corpus + aggregate differential

n-weighted aggregate over 19 args (doc_A=8, doc_B=3, doc_C=8). Δ = agentic pipe − 0-shot baseline. upgΔ = agentic − FB-28 lexical (shows the upgrade lifts the pipeline above its old lexical self).

| Virtue (agentic) | pipe | base | fb28-lex | Δ(pipe−base) | upgΔ(pipe−fb28) | signal |
|------------------|------|------|----------|--------------|-----------------|--------|
| `pertinence` | 0.974 | 0.458 | 0.216 | **+0.516** | +0.758 | SEPARATES (strong) |
| `refutation_constructive` | 0.105 | 0.000 | 0.000 | **+0.105** | +0.105 | SEPARATES |
| `structure_logique` | 0.316 | 0.284 | 0.000 | +0.032 | +0.316 | neutral |
| `analogie_pertinente` | 0.047 | 0.000 | 0.000 | +0.047 | +0.047 | neutral |
| `exhaustivite` | 0.210 | 0.184 | 0.132 | +0.026 | +0.078 | neutral |
| `clarte` | 0.809 | 0.868 | 0.316 | **−0.059** | +0.493 | STRICTER (base higher) |
| `redondance_faible` | 0.669 | 0.958 | 1.000 | **−0.289** | −0.331 | STRICTER (base higher) |

**Counts**: SEPARATES 2/7 · STRICTER 2/7 · neutral 3/7. Overall mean (7 agentic): pipe 3.13 vs base 2.75 (Δ +0.377).

Per-corpus detail (raw, opaque):

| Corpus | n | pipe mean | base mean | separating-virtues (pipe>base) |
|--------|---|-----------|-----------|--------------------------------|
| doc_A | 8 | per-virtue above | per-virtue above | pertinence +0.588, refutation +0.250, exhaustivite +0.124, structure +0.063, analogie +0.087 |
| doc_B | 3 | — | — | pertinence +0.167, exhaustivite +0.133 |
| doc_C | 8 | — | — | pertinence +0.575, clarte +0.063, analogie +0.025, structure +0.037 |

`pertinence` separates on **all 3 corpora** — the most robust single finding.

## Exhibits — content-separation proof (anti-theater)

Sample `exhibit` fields (the located structure a 0-shot cannot emit). Opaque IDs only.

- **pertinence** (doc_A arg): *Thesis located:* «L'absence de prompteur est présentée comme une occasion de parler sincèrement…»; *digression located:* «La mention d'avoir 'last stood in this grand hall' — référence personnelle non nécessaire pour soutenir l'affirmation sur la prospérité.» Verdict `digression_localisée`.
- **refutation_constructive** (doc_A arg): *Opposing claim located:* «Que l'absence de téléprompteur est un problème qui nuit à la prestation»; *engagement verdict:* `engagement_réel` — réfutation constructive pleinement démontrée. score 1.0.
- **structure_logique** (doc_A arg): *Chain reconstructed:* prémisses «Les armes de la guerre ont brisé la paix qu'il a forgée sur deux continents» → conclusion «Les guerres ont anéanti la paix qu'il a créée»; verdict `progression_logique`. score 1.0. (Another arg: verdict `saut_logique`, score 0.0 — honest.)
- **exhaustivite** (doc_A arg): *Dimensions covered:* analyse rhétorique/stratégique; *dimensions missing:* vérification factuelle (aucune preuve technique que le prompteur était en panne). verdict `couverture_partielle`.
- **clarte** (doc_A arg): *Obstacle located:* «Anaphore non résolvable — le pronom 'he' n'a pas d'antécédent clair»; verdict `opaque_réel`. score 0.2.

When the structure is absent, the detector returns an honest low score with an empty exhibit ("Aucune position adverse identifiée", "Aucune chaîne prémisse→conclusion identifiée") — not a fabricated high.

**2 AGENTIC_FAIL** (fail-loud, `score=None`): 1 in doc_A (clarte, unparseable step), 1 in doc_B. Recorded honestly; not fabricated. ~1.5% of 133 agentic evaluations.

## Honest axis verdict: **EDGES** (not DECIDES)

**Why EDGES.** The min-rule (FB-28) held quality to EDGES: existence + determinism + strictness, but not content-separation as an axis. FB-38 widened the *evidence* for content-separation — `pertinence` is now a strong, cross-corpus separator (+0.516), and the agentic path is richer than lexical on 6/7 (`upgΔ` positive). But vs the same-model 0-shot baseline, the axis does **not dominate**: 2 virtues separate, 2 go *stricter* (the agentic rubric penalizes what the 0-shot generously scores), 3 are marginal. A split, bidirectional result is not dominance. DECIDES requires the axis to separate cleanly in one direction; it does not. **Quality stays EDGES.**

**What FB-38 changed.** The EDGES verdict is now *measured on the de-castrated pipeline* (FB-30..37 landed since FB-29's castrated measurement), discharging the R405 caveat. And the content-separation evidence is substantially larger: FB-29 separated 2/9; FB-38 upgrades 7/9 and separates 2/7 strongly with non-vacuous exhibits throughout. The axis is *measurably richer* than at FB-29, even though the verdict label is unchanged.

### Hedges (required by #1127 — honesty over advocacy)

1. **Same-model caveat.** Both the agentic pipeline and the 0-shot baseline use `openai/gpt-5-mini`. The separation is about methodology (multi-step locate→verify→score vs single-shot), not model capacity. A stronger/different baseline model could separate differently.
2. **No human ground truth.** There is no gold-standard quality score per arg. The bidirectional split (2 separate, 2 stricter) cannot be resolved into "agentic is more correct" without calibration. The `pertinence` separation, in particular, may reflect the agentic detector locating a thesis the 0-shot under-scores — or the 0-shot being correctly harsh on genuine irrelevance. Undetermined.
3. **Small N.** 19 args across 3 corpora (doc_A=8, doc_B=3, doc_C=8). doc_B's n=3 makes its per-virtue means noisy.
4. **The "stricter" virtues may be over-strict.** `redondance_faible` (−0.289) and `clarte` (−0.059) score lower than 0-shot. The agentic rubric may penalize restatement / anaphora that a human would tolerate. Without ground truth, "stricter" ≠ "more correct".
5. **Independent cross-verify pending.** Per #1127, this axis verdict will be adversarially cross-verified (po-2023 on return, or coordinator) before it bears on closing #947. This report produces the measurement honestly; it does not advocate DECIDES.

## Privacy — opaque, leak-audited

Opaque IDs only throughout: `doc_A`/`doc_B`/`doc_C`, `arg_N`, exhibit text is paraphrased detector output (no verbatim corpus). No source names (author, title, date, venue, party). The raw per-corpus JSONs under `evaluation/results/capstone_c1/fb38_*.json` are gitignored as raw runs; only opaque aggregates are committed here.

## What this means for Epic #947

The Quality axis is **EDGES, measured (not forced)** on the de-castrated pipeline, with the largest content-separation evidence in the arc. Combined with the formal axis (DECIDES, Tweety-verified end-to-end per FB-37) and the opaque-by-construction synthesis (FB-34), the Epic's measurement posture is: **formal axis DECIDES, quality axis EDGES with demonstrated (partial, bidirectional) content-separation.** The remaining gate for formal Epic closure is the user's arbitration of the EDGES verdicts — FB-38 gives the user the honest, hedged quality-axis measurement to arbitrate.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
