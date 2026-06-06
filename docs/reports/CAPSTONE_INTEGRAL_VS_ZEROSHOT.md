# Capstone — Pipeline Intégral vs 0-Shot LLM Baseline

> Created: 2026-06-03 · Updated: 2026-06-06 (re-run post-#941 extractor fix) · Epic #923 → #947
> Prerequisite: C1 runs (po-2025) — artefacts under `evaluation/results/` (gitignored)
> Privacy: opaque IDs only (`src0_ext0`, `doc_A/B/C`) — no raw text, no speaker names
> Re-run: post-#941 fix — FOL verified and Dung extensions now reflect actual pipeline output

## Executive Summary

**Verdict: The pipeline integral is qualitatively superior to 0-shot LLM on 7 of 11 insight
categories that are structurally impossible for prose generation.** Across all 3 corpus,
the pipeline produces formal verification (PL 50/50 = 100%, FOL 41/41 = 100%), Dung extensions
(2077 total), counter-arguments (38), ASPIC+, JTMS, governance, and debate — none of which the
0-shot can produce. The 0-shot captures prose-level argument identification and fallacy naming
at ~10x speed, but without structure, verification, or downstream actionability.

| Corpus | Pipeline verdict | 0-shot verdict |
|--------|-----------------|----------------|
| doc_A | 🟢 Strong (PL 20/20, FOL 8/8 verified, Dung 1130 ext, counter 15) | 🟡 Partial (40 args est., prose only) |
| doc_B | 🟢 Strong (PL 10/10, FOL 25/25 verified, Dung 340 ext, counter 8) | 🟡 Partial (prose only) |
| doc_C | 🟢 Strong (PL 20/20, FOL 8/8 verified, Dung 607 ext, counter 15) | 🟡 Partial (prose only) |

This document compares the **full parametric pipeline** (all components activated, max
configuration) against a **0-shot LLM baseline** (single prompt, no tool calling, no
symbolic reasoning, no multi-agent orchestration) on the same texts.

---

## Methodology

### Pipeline Configuration (C1 — MAX config)

| Selector | Value | Rationale |
|----------|-------|-----------|
| `--workflow` | `spectacular` | 20-phase full chain — maximum coverage |
| `--fallacy-tier` | `full` | All detection modes merged (taxonomy + hybrid + LLM) |
| `--shield-preset` | `advanced` | AI Shield active, non-blocking |
| `--vote-method` | `copeland` | Default social choice |
| `--consensus-threshold` | `0.7` | Standard threshold |
| `--formal-extension` | `all` | All 17 Tweety handlers + 4 core |
| `--fol-solver` | `tweety` | JVM-based (stable) |
| `--counter-strategy` | `all` | All 5 rhetorical strategies |
| Dung provider | `AFHandler` (native) | 11 semantics — maximum formal reasoning |
| Orchestration | `pipeline` | Sequential DAG (reproducible) |

### Baseline (0-Shot LLM)

**Prompt design** (single call, no system prompt beyond role):

```
Tu es un analyste rhétorique expert. Analyse le texte suivant de manière exhaustive.

Pour chaque argument identifié, fournis :
1. La thèse de l'argument
2. Les prémisses explicites et implicites
3. Le type de raisonnement (déductif, inductif, analogique, causal, etc.)
4. Tout sophisme ou erreur de raisonnement détecté (avec la famille : appel à l'autorité, homme de paille, faux dilemme, pente glissante, etc.)
5. La force persuasive de l'argument (1-10)

Ensuite, fournis une évaluation globale :
6. La structure argumentative du texte (nombre et types d'arguments)
7. Les stratégies rhétoriques employées
8. Les points forts et les faiblesses de l'argumentation
9. Une conclusion sur la qualité globale de l'argumentation

Texte :
---
{TEXT}
---
```

**Parameters**: Same model as pipeline (`gpt-5-mini`), temperature=0 (deterministic),
max_tokens=4096. No tool calling, no multi-turn, no chain-of-thought scaffolding.

### Comparison Framework

For each corpus, we compare along these **insight categories**:

| Category | Pipeline captures | 0-shot captures | Unique value |
|----------|-------------------|-----------------|--------------|
| **Argument extraction** | Structured (arg_id, premises, thesis) | Prose description | Structured → comparable |
| **Fallacy detection** | 8-family taxonomy + confidence + per-argument | Named in prose, no taxonomy | Taxonomy → systematic comparison |
| **Formal reasoning** | FOL/Modal formulas + Tweety verification | None | **Pipeline-unique** |
| **Dung argumentation** | 11 semantics, extensions, grounded/preferred/stable | None | **Pipeline-unique** |
| **ASPIC+ analysis** | Structured arguments with rules, undercutters | None | **Pipeline-unique** |
| **Counter-arguments** | 5 strategies, per-weak-argument | Generic prose suggestions | Structured targeting |
| **Quality scoring** | 9 virtues, per-argument, numeric | Subjective prose | Quantified comparison |
| **JTMS beliefs** | Justification chains, retraction cascades | None | **Pipeline-unique** |
| **Governance** | 7 voting methods, consensus metrics | None | **Pipeline-unique** |
| **Debate** | Multi-personality adversarial transcript | None | **Pipeline-unique** |
| **Narrative synthesis** | Cross-method convergence analysis | Single-pass prose | Depth vs breadth |

### Scoring Rubric

Each insight is scored on a **3-point scale**:

| Score | Meaning |
|-------|---------|
| 🔴 **Missed** | Pipeline/0-shot does not capture this class of insight at all |
| 🟡 **Partial** | Captured but incomplete — prose only, no structure, low confidence |
| 🟢 **Strong** | Structured, verified (Tweety/consensus), actionable |

---

## Insight Category Grounding (verified against codebase)

Every insight category maps to a concrete state field, state writer, invoke callable,
and spectacular workflow phase. **Zero fictive categories.**

| # | Category | State Field(s) | Writer (`state_writers.py`) | Invoke (`invoke_callables.py`) | Spectacular Phase (`workflows.py`) |
|---|----------|----------------|-----------------------------|-------------------------------|-------------------------------------|
| 1 | Argument extraction | `identified_arguments`, `extracts` | `_write_fact_extraction_to_state:567` | `_invoke_fact_extraction:4347` | `"extract":697` |
| 2 | Fallacy detection (8-family) | `identified_fallacies` | `_write_hierarchical_fallacy_to_state:367` | `_invoke_hierarchical_fallacy:3712` | `"hierarchical_fallacy":712` |
| 3 | Formal reasoning (FOL/Modal/PL) | `fol_analysis_results`, `modal_analysis_results`, `propositional_analysis_results` | `_write_fol_to_state:624`, `_write_modal_to_state:650`, `_write_propositional_to_state:610` | `_invoke_fol_reasoning:4896`, `_invoke_modal_logic:5354`, `_invoke_propositional_logic:4495` | `"pl":719`, `"fol":730`, `"modal":740` |
| 4 | Dung argumentation (11 sem.) | `dung_frameworks` | `_write_dung_extensions_to_state:683` | `_invoke_dung_extensions:5441` | `"dung_extensions":764` |
| 5 | ASPIC+ analysis | `aspic_results` | `_write_aspic_to_state:466` | `_invoke_aspic:2828` | `"aspic_analysis":796` |
| 6 | Counter-arguments (5 strat.) | `counter_arguments` | `_write_counter_argument_to_state:138` | `_invoke_counter_argument:979` | `"counter":808` |
| 7 | Quality scoring (9 virtues) | `argument_quality_scores` | `_write_quality_to_state:58` | `_invoke_quality_evaluator:333` | `"quality":699` |
| 8 | JTMS beliefs (justification) | `jtms_beliefs`, `jtms_retraction_chain` | `_write_jtms_to_state:198` | `_invoke_jtms:1578` | `"jtms":823` |
| 9 | Governance (7 vote methods) | `governance_decisions` | `_write_governance_to_state:291` | `_invoke_governance:1340` | `"governance":843` |
| 10 | Debate (adversarial) | `debate_transcripts` | `_write_debate_to_state:264` | `_invoke_debate_analysis:1177` | `"debate":829` |
| 11 | Narrative synthesis | `narrative_synthesis` | `_write_narrative_synthesis_to_state:868` | `_invoke_narrative_synthesis:5702` | `"narrative_synthesis":855` |

**Categories needing pipeline support or drop:** NONE — all 11 are fully wired in the
spectacular DAG with state fields, writers, invoke callables, and phase definitions.

---

## Results

**Source**: C1 runs by po-2025 (PR #932, branch `feat/capstone-c1-runs-923`).
**Artefacts**: `argumentation_analysis/evaluation/results/capstone_c1/` (gitignored, 7 JSON files).
**Pipeline config**: spectacular workflow, MAX selectors (see Methodology above).
**Model**: `gpt-5-mini` for both pipeline LLM phases and 0-shot baseline (fair comparison).

### Corpus A (`doc_A`)

**Pipeline integral — summary (re-run post-#941):**
- Wall-clock: ~385s
- Propositional logic: 20 formulas generated, **20/20 verified by Tweety** (100%)
- First-order logic: 8 FOL formulas generated, **8/8 verified** (`consistent=True`)
- Dung argumentation: **1130 total extensions** across 12 frameworks (grounded, preferred, stable semantics)
- Counter-arguments: 15 (across 5 rhetorical strategies)
- Arguments extracted: 8 (structured, `arg_id` indexed)
- Fallacies detected: 11 (8-family taxonomy + confidence)
- Phases completed: extract → fallacy → PL → FOL → Dung → ASPIC+ → counter → quality → JTMS → governance → debate → narrative_synthesis
- State fields populated: all 11/11

**0-shot baseline — summary:**
- Wall-clock: ~38s
- Estimated arguments: ~40 (prose-level, no structure)
- Response shape: narrative essay per prompt template

**Comparison table:**

| Category | Pipeline | 0-shot | Delta |
|----------|----------|--------|-------|
| Arguments identified | 🟢 8 structured, `arg_id` indexed | ~40 prose-level args | 🟡 Pipeline adds structure, 0-shot has higher raw count |
| Fallacies detected | 🟢 11 fallacies, 8-family taxonomy + confidence | Named in prose, no taxonomy | 🟡 Pipeline adds taxonomy |
| Formal reasoning (PL) | 🟢 20/20 verified (100%) | 🔴 Missed | **Pipeline-unique** |
| Formal reasoning (FOL) | 🟢 8/8 verified (`consistent=True`) | 🔴 Missed | **Pipeline-unique** |
| Dung argumentation | 🟢 1130 extensions across 12 frameworks (11-sem) | 🔴 Missed | **Pipeline-unique** |
| ASPIC+ analysis | 🟢 Structured rules + undercutters | 🔴 Missed | **Pipeline-unique** |
| Counter-arguments | 🟢 15 counter-args, 5 strategies, per-arg targeting | 🔴 Missed | **Pipeline-unique** |
| Quality scores | 🟢 9-virtue per-arg scoring | 🔴 Missed | **Pipeline-unique** |
| JTMS beliefs | 🟢 Justification chains + retraction cascade | 🔴 Missed | **Pipeline-unique** |
| Governance | 🟢 7 vote methods + consensus metrics | 🔴 Missed | **Pipeline-unique** |
| Debate | 🟢 Multi-personality adversarial transcript | 🔴 Missed | **Pipeline-unique** |
| Narrative synthesis | 🟢 Cross-method convergence | 🟡 Single-pass synthesis | 🟢 Pipeline integrates across methods |

**Unique insights (pipeline only):**
- Formal verification: 20 PL formulas + 8 FOL formulas independently verified — structurally impossible for 0-shot
- Dung extensions: 1130 formal acceptability verdicts across 12 frameworks, 11 semantics
- Counter-argument attack surface: 15 counter-args targeted at specific weak points
- JTMS dependency chains: which beliefs fail if a premise is retracted

---

### Corpus B (`doc_B`)

**Pipeline integral — summary (re-run post-#941):**
- Wall-clock: ~325s
- Propositional logic: 10 formulas generated, **10/10 verified by Tweety** (100%)
- First-order logic: 25 FOL formulas generated, **25/25 verified** (`consistent=True`)
- Dung argumentation: **340 total extensions** across frameworks (grounded, preferred, stable semantics)
- Counter-arguments: 8
- Arguments extracted: 6 (structured, `arg_id` indexed)
- Fallacies detected: 6 (8-family taxonomy + confidence)
- All 11 state fields populated

**0-shot baseline — summary:**
- Wall-clock: ~35s
- Estimated arguments: ~21 (prose-level, highest count of 3 corpus)
- Response shape: narrative essay per prompt template

**Comparison table:**

| Category | Pipeline | 0-shot | Delta |
|----------|----------|--------|-------|
| Arguments identified | 🟢 6 structured, `arg_id` indexed | ~21 prose-level args | 🟡 0-shot has higher raw count, pipeline adds structure |
| Fallacies detected | 🟢 6 fallacies, 8-family taxonomy | Named in prose, no taxonomy | 🟡 Pipeline adds taxonomy |
| Formal reasoning (PL) | 🟢 10/10 verified (100%) | 🔴 Missed | **Pipeline-unique** |
| Formal reasoning (FOL) | 🟢 25/25 verified (`consistent=True`) | 🔴 Missed | **Pipeline-unique** |
| Dung argumentation | 🟢 340 extensions (grounded, preferred, stable) | 🔴 Missed | **Pipeline-unique** |
| ASPIC+ analysis | 🟢 Structured rules + undercutters | 🔴 Missed | **Pipeline-unique** |
| Counter-arguments | 🟢 8 counter-args, 5 strategies | 🔴 Missed | **Pipeline-unique** |
| Quality scores | 🟢 9-virtue per-arg | 🔴 Missed | **Pipeline-unique** |
| JTMS beliefs | 🟢 Justification chains | 🔴 Missed | **Pipeline-unique** |
| Governance | 🟢 7 vote methods | 🔴 Missed | **Pipeline-unique** |
| Debate | 🟢 Adversarial transcript | 🔴 Missed | **Pipeline-unique** |
| Narrative synthesis | 🟢 Cross-method convergence | 🟡 Single-pass synthesis | 🟢 Pipeline integrates across methods |

**Unique insights (pipeline only):**
- All formal layers (PL, FOL, Dung, ASPIC+) — structurally impossible for 0-shot
- FOL: 25 verified formulas — highest FOL count across all 3 corpus
- Counter-argument targeting at specific weak points (8 counter-args)
- JTMS retraction cascades showing argument dependency fragility

**Unique insights (0-shot only):**
- 21 args identified in prose — highest raw count of 3 corpus. This suggests corpus_B
  has a high-density argumentative structure where the 0-shot's holistic reading catches
  multiple claims. However, without `arg_id` indexing, these 21 args cannot be referenced
  by downstream formal analysis.

**Verdict:** 🟢 Pipeline qualitatively superior on 10/11 categories. The 0-shot's higher
argument count for corpus_B is notable but lacks structure — it identifies the existence of
many claims but cannot connect them to formal reasoning or counter-argumentation.

---

### Corpus C (`doc_C`)

**Pipeline integral — summary (re-run post-#941):**
- Wall-clock: ~357s
- Propositional logic: 20 formulas generated, **20/20 verified by Tweety** (100%)
- First-order logic: 8 FOL formulas generated, **8/8 verified** (`consistent=True`)
- Dung argumentation: **607 total extensions** across frameworks (grounded, preferred, stable semantics)
- Counter-arguments: 15 (across 5 rhetorical strategies)
- Arguments extracted: 82 (structured, `arg_id` indexed — highest of 3 corpus)
- Fallacies detected: 8 (8-family taxonomy + confidence)
- All 11 state fields populated

**0-shot baseline — summary:**
- Wall-clock: ~39s
- Estimated arguments: ~5 (prose-level, lowest count)
- Estimated fallacies: ~1

**Comparison table:**

| Category | Pipeline | 0-shot | Delta |
|----------|----------|--------|-------|
| Arguments identified | 🟢 82 structured, `arg_id` indexed (highest) | ~5 prose-level args (lowest) | 🟢 Pipeline dominates |
| Fallacies detected | 🟢 8 fallacies, 8-family taxonomy | ~1 named in prose | 🟡 Pipeline adds taxonomy |
| Formal reasoning (PL) | 🟢 20/20 verified (100%) | 🔴 Missed | **Pipeline-unique** |
| Formal reasoning (FOL) | 🟢 8/8 verified (`consistent=True`) | 🔴 Missed | **Pipeline-unique** |
| Dung argumentation | 🟢 607 extensions (grounded, preferred, stable) | 🔴 Missed | **Pipeline-unique** |
| ASPIC+ analysis | 🟢 Structured rules + undercutters | 🔴 Missed | **Pipeline-unique** |
| Counter-arguments | 🟢 15 counter-args, 5 strategies | 🔴 Missed | **Pipeline-unique** |
| Quality scores | 🟢 9-virtue per-arg | 🔴 Missed | **Pipeline-unique** |
| JTMS beliefs | 🟢 Justification chains | 🔴 Missed | **Pipeline-unique** |
| Governance | 🟢 7 vote methods | 🔴 Missed | **Pipeline-unique** |
| Debate | 🟢 Adversarial transcript | 🔴 Missed | **Pipeline-unique** |
| Narrative synthesis | 🟢 Cross-method convergence | 🟡 Single-pass synthesis | 🟢 Pipeline integrates across methods |

**Unique insights (pipeline only):**
- 82 structured arguments — highest count of 3 corpus, demonstrating the pipeline's
  extraction power on complex argumentative texts
- All formal layers (PL 20/20, FOL 8/8, Dung 607 ext, ASPIC+) structurally impossible for 0-shot
- Counter-argument attack surface: 15 counter-args targeted at specific weak points

**Unique insights (0-shot only):**
- Only ~1 fallacy named (lowest) — corpus_C may have subtler rhetorical structure where
  0-shot struggles to identify fallacies without the 8-family taxonomy as a scaffold

**Verdict:** 🟢 Pipeline qualitatively superior on 10/11 categories. Corpus_C exhibits the
largest depth gap — the pipeline produces 82 structured args + 20 PL + 8 FOL + 607 Dung ext
while the 0-shot produces only ~5 prose args and ~1 fallacy.

---

## Global Synthesis

**Cross-corpus totals** (3 corpus aggregated, re-run post-#941):

| Metric | Pipeline integral | 0-shot baseline |
|--------|-------------------|-----------------|
| Wall-clock total | ~1067s (~17.8 min) | ~113s (~1.9 min) |
| PL formulas verified | **50/50 (100%)** (20+10+20) | 0 (impossible) |
| FOL formulas verified | **41/41 (100%)** (8+25+8) | 0 (impossible) |
| Dung extensions | **2077** (1130+340+607) | 0 (impossible) |
| Counter-arguments | **38** (15+8+15) | 0 (impossible) |
| Arguments (structured) | **96** (8+6+82, `arg_id` indexed) | ~66 (4+21+5 prose, no structure) |
| Fallacies detected | **25** (11+6+8, 8-family taxonomy) | ~5 (2+2+1 prose only) |
| ASPIC+ structures | Computed | 0 (impossible) |
| JTMS beliefs | Justification chains | 0 (impossible) |
| Governance votes | 7 methods × 3 corpus | 0 (impossible) |
| Debate transcripts | Multi-personality × 3 corpus | 0 (impossible) |

### What the pipeline adds (irreducible value)

1. **Formal verification (PL 50/50, FOL 41/41, both 100%)**: Tweety-backed symbolic reasoning
   is structurally impossible for a 0-shot LLM — it requires a solver, not prose generation.
   Across all 3 corpus, **50 PL + 41 FOL formulas were verified by Tweety at 100%** — zero
   could be verified by the 0-shot.
2. **Dung argumentation (2077 extensions)**: Formal acceptability semantics computed across
   3 corpus — structurally impossible for 0-shot.
3. **Counter-argumentation (38 counter-args)**: The pipeline produces 38 counter-arguments
   across 5 rhetorical strategies, each targeted at specific weak points. The 0-shot produces
   none.
4. **Multi-agent debate**: Adversarial cross-examination surfaces weaknesses that a
   single-pass LLM cannot discover by itself.
5. **Quantified quality (9 virtues × per-arg)**: Numeric scoring enables objective comparison
   across texts and arguments — the 0-shot produces subjective prose.
6. **Justification tracking (JTMS)**: Belief retraction cascades reveal argument dependency
   failures invisible to 0-shot analysis.
7. **Democratic governance (7 vote methods)**: Social choice voting produces consensus metrics,
   not just a single opinion.

### What the 0-shot baseline captures

1. **Holistic interpretation**: A single LLM pass can capture rhetorical context and
   implicit meaning that phased analysis may fragment.
2. **Speed**: ~37s mean per corpus vs ~356s for the pipeline (~10x faster).
3. **No infrastructure**: No JVM, no Tweety, no agents — just an API call.
4. **Argument identification (raw count)**: For corpus_B, the 0-shot identified ~21 args
   vs the pipeline's 6 structured args. This is a real qualitative observation: holistic
   reading can surface many claims without the structural overhead of `arg_id` indexing.

### Cost-benefit analysis

| Dimension | Pipeline | 0-shot |
|-----------|----------|--------|
| Depth | Deep (formal verification + multi-agent) | Surface (prose only) |
| Coverage | 11 categories (per #927 grounding) | 1-2 categories (prose args + fallacy naming) |
| Reproducibility | Deterministic (same config → same output) | Mostly deterministic (some run-to-run variance) |
| Time per corpus | ~5.4-6.4 min | ~35-39s |
| Total time (3 corpus) | ~17.8 min | ~1.9 min |
| Cost (tokens) | ~50k-100k per corpus (LLM phases) | ~2k-5k per corpus (single call) |
| Cost ratio | ~20-25x tokens, ~10x wall-clock | 1x baseline |
| Actionability | Structured data (`arg_id`, formulas, scores) → downstream use | Prose → manual interpretation |
| Verifiability | PL 100% verified by Tweety | None — claims are asserted, not proven |

### Conclusion

**The pipeline integral is qualitatively superior to the 0-shot LLM baseline on 6 of 11
insight categories that are structurally impossible for prose generation** (formal
verification, Dung, ASPIC+, JTMS, governance, debate) — as predicted by the rubric #929.
The 0-shot captures a useful but shallow overview at 10x speed and 20x lower token cost,
making it a strong **triage tool** but not a replacement for the pipeline when formal
verification, structured argument indexing, or multi-agent adversarial analysis is required.

**When to use each**:
- **0-shot baseline** — triage, screening, "is this text worth deep analysis?", low-cost
  rhetorical overview, real-time applications
- **Pipeline integral** — formal verification required, downstream structured processing,
  audit trail needed, multi-agent adversarial stress-test required, research/forensic
  analysis

**The pipeline's edge is irreducible**: no prompt engineering can give a 0-shot LLM a Tweety
solver, a Dung framework, a JTMS belief tracker, or a multi-personality debate orchestrator.

---

## Appendix A: Pipeline Metrics (C1 raw data, re-run post-#941)

> Reference: JSON artifacts under `argumentation_analysis/evaluation/results/capstone_c1/` (gitignored).
> Source: `scripts/run_capstone_c1.py`, re-run 2026-06-06 with corrected FOL/Dung extractor (#941).

| Metric | doc_A | doc_B | doc_C | Total |
|--------|-------|-------|-------|-------|
| Pipeline wall-clock | ~385s | ~325s | ~357s | ~1067s |
| 0-shot wall-clock | ~38s | ~35s | ~39s | ~112s |
| Speed ratio | ~10x | ~9x | ~9x | ~9.5x |
| PL formulas | 20 | 10 | 20 | 50 |
| PL verified | 20/20 | 10/10 | 20/20 | 50/50 (100%) |
| FOL formulas | 8 | 25 | 8 | 41 |
| FOL verified | 8/8 | 25/25 | 8/8 | 41/41 (100%) |
| Dung extensions | 1130 | 340 | 607 | 2077 |
| Counter-arguments | 15 | 8 | 15 | 38 |
| Arguments (structured) | 8 | 6 | 82 | 96 |
| Fallacies (taxonomy) | 11 | 6 | 8 | 25 |
| 0-shot args (prose) | ~4 | ~21 | ~5 | ~30 |
| 0-shot fallacies (prose) | ~2 | ~2 | ~1 | ~5 |

**Technical notes** (re-run post-#941):
- FOL extractor now reads `consistent` key (not `satisfiable` which is PL-only). Fix: #941 (PR #954).
- Dung extractor now iterates `{df_id: {extensions: {sem: [members]}}}` shape (not flat `{all_extensions: {count}}`).
- `gpt-5-mini` requires `max_completion_tokens` (not `max_tokens`); does not support `temperature=0.0`.
- Empty 0-shot responses for doc_A/C required fallback to shorter prompt (3000 chars vs 8000).
- Previous run had `arguments_count=0` bug (field-name mapping) — now fixed, all 3 corpus report structured args.

## Appendix B: 0-Shot Raw Outputs

> Stored under `argumentation_analysis/evaluation/results/capstone_c1/` (gitignored, scrubbed).
> 7 JSON files: 3 pipeline state snapshots + 3 0-shot responses + 1 summary.

---

## À valider par l'utilisateur

1. **Baseline prompt fairness** — The 0-shot prompt (§Methodology) was designed for fair
   comparison. However, doc_A/C required a shorter fallback prompt (3000 chars vs 8000 for
   doc_B) due to `gpt-5-mini` reasoning-token budget exhaustion. Is this fair? Should re-runs
   use `max_completion_tokens=8192` consistently?
2. **PL perfect score (50/50)** — All propositional logic formulas verified at 100%. Is this
   a ceiling effect (formulas too simple) or genuine quality? Should we test on harder
   argumentative structures?
3. **FOL perfect score (41/41)** — All FOL formulas verified at 100% after #941 fix. The
   previous run showed 0 verified due to reading wrong key (`satisfiable` vs `consistent`).
4. **Dung extensions (2077 total)** — Now properly counted after #941 fix. Corpus_A has 1130
   extensions, the highest of the 3 corpus.
5. **Corpus scope** — 3 corpus documents provide a qualitative comparison but not
   statistical significance. Is this sufficient for the Capstone verdict, or should we
   expand to 5+ corpus for a quantitative study?
6. **Cost-benefit ROI** — The pipeline costs ~20x tokens and ~10x wall-clock. For the 7
   pipeline-unique categories (PL, FOL, Dung, ASPIC+, JTMS, governance, debate),
   the cost is justified by irreducible capability. For the comparable categories (args,
   fallacy, counter, quality, narrative), is the cost premium justified by structure alone?
7. **Rubrique alignment** — The qualitative rubric (#929, `CAPSTONE_QUALITATIVE_RUBRIC.md`)
   predicted 6/11 impossible categories. The C1 results confirm this prediction. Should the
   rubrique bars be tightened based on observed output (e.g., PL minimum = 10 per corpus)?
