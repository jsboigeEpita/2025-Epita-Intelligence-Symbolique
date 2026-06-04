# Capstone Qualitative Rubric — Per-Brick Output Bar & Superiority Criteria

> Created: 2026-06-04 · Issue #929 · Part of Epic #923 (Capstone intégral vs 0-shot)
> Grounding: chains from #927 (11/11 state→writer→invoke→phase, zero fictive)
> Companion: `scripts/capstone_brick_health.py` (#928, brick-health harness, po-2025)
> Privacy: opaque IDs only (`arg_1`, `src0_ext0`, `doc_A`) — no raw text, no speaker names

## Purpose

This document defines, **per insight category (11)**, two things:

1. **Output bar** — the minimum non-trivial output a brick must produce to count as "working".
   This bar is used by the brick-health harness (#928) to PASS/FAIL each component in <10min.
2. **Superiority criteria** — the qualitative dimensions by which the pipeline integral output
   is judged **superior** to a 0-shot LLM baseline. For each category, we specify what the
   pipeline captures that the 0-shot fundamentally **cannot**.

**Design principle**: the 0-shot baseline is given a fair, exhaustive prompt (see
`CAPSTONE_INTEGRAL_VS_ZEROSHOT.md` §Baseline). The comparison is about **structural depth**,
not model quality — both use the same model (`gpt-5-mini`).

---

## Scoring Convention

Each category is scored on the 3-point rubric from the scaffold:

| Score | Meaning |
|-------|---------|
| 🔴 **Missed** | No output in this category (empty state field, or trivial/zero results) |
| 🟡 **Partial** | Output present but incomplete — prose only, no structure, low confidence |
| 🟢 **Strong** | Structured, verified (Tweety/consensus), actionable, meets output bar below |

A category scores 🟢 **only if** every criterion in its "Output bar" is met.
The pipeline is judged superior to 0-shot on a category if it scores 🟢 where 0-shot scores 🟡 or 🔴.

---

## Per-Category Rubric

### 1. Argument Extraction

**State fields**: `identified_arguments`, `extracts` (grounded: `_write_fact_extraction_to_state:567`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Count | ≥ 3 structured arguments per corpus | 0-shot describes args in prose; pipeline produces `arg_id` + premises + thesis as structured fields |
| Premise identification | Each argument has ≥ 1 explicit premise + optional implicit premise | 0-shot may list premises but cannot separate explicit/implicit structurally |
| Thesis linkage | Each argument's thesis is a discrete, citable claim | 0-shot embeds thesis in narrative; pipeline extracts as independent, queryable entity |
| Cross-reference | Arguments are ID-indexed (`arg_1`, `arg_2`) for downstream consumption | 0-shot has no ID scheme — cannot be referenced by fallacy/Dung/JTMS phases |

**Gap 0-shot cannot bridge**: Structured `arg_id` indexing that downstream formal phases
(Dung attack-relations, JTMS belief names, fallacy per-argument) depend on. Without IDs,
no formal reasoning chain can be constructed.

---

### 2. Fallacy Detection (8-Family Taxonomy)

**State field**: `identified_fallacies` (grounded: `_write_hierarchical_fallacy_to_state:367`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Detection | ≥ 1 fallacy detected per corpus | Both detect fallacies; pipeline adds structure |
| Taxonomy classification | Each fallacy classified into one of 8 families (appeal to authority, straw man, false dilemma, slippery slope, ad hominem, circular reasoning, hasty generalization, false cause) | 0-shot names fallacies in prose but without a fixed taxonomy — cross-corpus comparison impossible |
| Per-argument localization | Fallacy linked to specific `arg_id` with text-ID | 0-shot identifies fallacious passages but cannot link to structured argument IDs |
| Confidence score | Numeric confidence per detection | 0-shot provides subjective assessment ("strong"/"weak") — non-comparable |
| Commentary | Generated justification for the classification | Comparable to 0-shot prose, but structured alongside taxonomy + confidence |

**Gap 0-shot cannot bridge**: Fixed 8-family taxonomy with per-argument localization via `arg_id`.
This enables systematic cross-corpus comparison ("corpus_A has 3 straw men, corpus_B has none")
and downstream aggregation — the 0-shot's free-form naming cannot be tabulated.

---

### 3. Formal Reasoning (FOL + Modal + Propositional Logic)

**State fields**: `fol_analysis_results`, `modal_analysis_results`, `propositional_analysis_results`
(grounded: writers at :624/:650/:610, invokes at :4896/:5354/:4495)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Formula generation | ≥ 1 valid formula per logic type (PL, FOL, or Modal) per corpus | **0-shot produces no formal formulas at all** — this is structurally impossible for prose generation |
| Tweety verification | ≥ 1 formula verified by Tweety solver (sat/unsat/valid) | **Pipeline-unique** — symbolic verification requires a solver, not an LLM |
| Validity annotation | Each formula annotated as sat/unsat/valid with solver output | **Pipeline-unique** |
| Natural language mapping | Each formula accompanied by the natural language premise it formalizes | Maps between prose and formal — 0-shot has only prose |

**Gap 0-shot cannot bridge**: **Formal verification is structurally impossible for a 0-shot LLM.**
Generating a FOL formula is LLM work, but **checking** whether `∀x(P(x)→Q(x)) ∧ P(a) ⊢ Q(a)`
requires a solver (Tweety/EProver/SPASS), not prose generation. The pipeline produces
formulas **and proves them** — the 0-shot can only assert plausibility without verification.

---

### 4. Dung Argumentation (11 Semantics)

**State field**: `dung_frameworks` (grounded: `_write_dung_extensions_to_state:683`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Framework construction | Attack relations defined between ≥ 2 arguments | **Pipeline-unique** — 0-shot has no attack-relation formalism |
| Extension computation | ≥ 1 extension (grounded, preferred, stable, complete, semi-stable, stage, ideal, eager, cf2, stage2, naive) | **Pipeline-unique** — computing extensions requires symbolic computation |
| Acceptability status | Each argument labeled accepted/rejected per semantics | **Pipeline-unique** — formal acceptability status |
| Multi-semantics comparison | Extensions under ≥ 2 different semantics | **Pipeline-unique** — 0-shot has single opinion, not formal comparison |

**Gap 0-shot cannot bridge**: **Dung argumentation frameworks are a formal structure.**
Computing that argument `A` is accepted under grounded semantics but rejected under preferred
requires symbolic computation over an attack graph. The 0-shot can express opinions about
argument strength, but cannot formally derive acceptability from attack relations across
11 different semantics.

---

### 5. ASPIC+ Analysis

**State field**: `aspic_results` (grounded: `_write_aspic_to_state:466`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Structured arguments | ≥ 1 ASPIC+ structured argument (premises → rule → conclusion) | **Pipeline-unique** — 0-shot has no rule-based argument structure |
| Undercutters | ≥ 1 undercutter identified (attack on inference rule) | **Pipeline-unique** — 0-shot cannot distinguish attack on premise vs attack on inference |
| Defeat status | Arguments evaluated for defeat (defeated/undefeated) | **Pipeline-unique** |
| Rule instantiation | Inference rules linked to argument components | **Pipeline-unique** |

**Gap 0-shot cannot bridge**: **ASPIC+ distinguishes between attacking a premise and attacking
an inference rule** (undercutters). The 0-shot can say "this reasoning is flawed" but cannot
formally represent that the flaw is in the *inference step* rather than in the *premise*.
This distinction is critical for legal/ethical argumentation analysis.

---

### 6. Counter-Arguments (5 Strategies)

**State field**: `counter_arguments` (grounded: `_write_counter_argument_to_state:138`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Count | ≥ 1 counter-argument per weak argument | Comparable — both can generate counter-arguments |
| Strategy variety | ≥ 2 of 5 strategies used (reductio ad absurdum, counter-example, distinction, reformulation, concession) | Pipeline applies a known strategy framework; 0-shot generates ad-hoc responses |
| Targeting | Counter-arguments linked to specific `arg_id` | Pipeline targets structurally; 0-shot targets topically |
| Evaluator score | Each counter-argument scored on 5 criteria with weighted evaluation | Pipeline provides quantitative evaluation; 0-shot provides qualitative prose |

**Gap 0-shot cannot bridge**: The pipeline's **5-strategy framework** ensures coverage of
distinct rhetorical approaches. The 0-shot may produce a good counter-argument but cannot
systematically ensure all 5 strategies are explored. Combined with per-argument targeting
via `arg_id`, the pipeline provides a **complete attack surface map**.

---

### 7. Quality Scoring (9 Virtues)

**State field**: `argument_quality_scores` (grounded: `_write_quality_to_state:58`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Virtue coverage | ≥ 5 of 9 virtues scored per argument (clarity, coherence, relevance, sufficiency, acceptability, credibility, completeness, objectivity, effectiveness) | Pipeline covers a fixed virtue set; 0-shot covers ad-hoc quality dimensions |
| Numeric scores | Score per virtue (quantitative) | Pipeline provides comparable numbers; 0-shot provides prose assessment |
| Per-argument | Scores linked to `arg_id` | Pipeline scores each argument; 0-shot scores the text globally |
| Cross-argument comparison | Quality profile enables ranking arguments by virtue | **Pipeline-unique** — enables "arg_3 is weakest on sufficiency" |

**Gap 0-shot cannot bridge**: **Quantified 9-virtue profiling per argument** enables
objective comparison across texts and arguments. The 0-shot can say "the argumentation
is generally strong" but cannot produce "arg_3 scores 4/10 on sufficiency, 8/10 on clarity".
This quantification is required for any systematic quality benchmarking.

---

### 8. JTMS Beliefs (Justification Tracking)

**State fields**: `jtms_beliefs`, `jtms_retraction_chain` (grounded: `_write_jtms_to_state:198`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Belief creation | ≥ 2 beliefs derived from argument premises | **Pipeline-unique** — 0-shot has no belief tracking |
| Justification chains | ≥ 1 multi-step justification (belief A supports belief B) | **Pipeline-unique** — dependency tracking |
| Retraction cascade | ≥ 1 retraction demonstrated (removing a premise cascades to dependent beliefs) | **Pipeline-unique** — the 0-shot cannot simulate belief retraction |
| Conflict detection | Contradictions identified between beliefs | **Pipeline-unique** |

**Gap 0-shot cannot bridge**: **Belief retraction cascades** reveal argument dependency
failures that are invisible to a single-pass analysis. When premise P₁ is challenged,
the JTMS shows which downstream conclusions become invalid — the 0-shot cannot track
these dependency chains. This is critical for understanding argument fragility.

---

### 9. Governance (7 Voting Methods)

**State field**: `governance_decisions` (grounded: `_write_governance_to_state:291`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Voting methods | ≥ 2 of 7 methods applied (majority, Borda, Condorcet, approval, Copeland, plurality, IRV) | **Pipeline-unique** — 0-shot has single opinion |
| Consensus metrics | consensus_rate + fairness_index computed | **Pipeline-unique** |
| Conflict resolution | Disagreements between methods identified and resolved | **Pipeline-unique** |
| Decision trace | Vote distribution per method recorded | **Pipeline-unique** |

**Gap 0-shot cannot bridge**: **Social choice theory applied to analysis positions.**
The 0-shot produces one opinion; the pipeline runs 7 voting methods over multiple agent
positions and computes consensus metrics. This reveals whether analysis conclusions are
robust (high consensus) or contentious (low consensus, method-dependent) — a dimension
completely absent from 0-shot analysis.

---

### 10. Debate (Adversarial Multi-Personality)

**State field**: `debate_transcripts` (grounded: `_write_debate_to_state:264`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Turn count | ≥ 4 debate turns (attack + response) | **Pipeline-unique** — 0-shot is single-pass |
| Personality diversity | ≥ 2 adversarial personalities with distinct positions | **Pipeline-unique** |
| Argument scoring | Arguments scored during debate exchanges | **Pipeline-unique** |
| Weakness exposure | Debate reveals weaknesses not caught in single-pass analysis | **Pipeline-unique** — adversarial stress-testing |

**Gap 0-shot cannot bridge**: **Adversarial cross-examination** surfaces weaknesses that
a single-pass analysis cannot discover. The debate transcript shows how arguments hold
up under challenge — the 0-shot can identify fallacies but cannot *test whether they
survive counter-attack*. This is the difference between auditing and stress-testing.

---

### 11. Narrative Synthesis (Cross-Method Convergence)

**State field**: `narrative_synthesis` (grounded: `_write_narrative_synthesis_to_state:868`)

| Dimension | Output bar (pipeline must produce) | Superiority vs 0-shot |
|-----------|-----------------------------------|-----------------------|
| Cross-method integration | Synthesis references ≥ 3 different analysis dimensions | Pipeline integrates across formal results; 0-shot integrates impressionistically |
| Convergence analysis | Identifies where methods agree/disagree | **Pipeline-unique** — requires multiple methods to converge |
| Qualitative verdict | Overall assessment grounded in specific phase outputs | Comparable, but pipeline grounds in structured data |
| Actionability | Specific recommendations linked to analysis findings | Pipeline links to arg_ids + formal results; 0-shot links to prose impressions |

**Gap 0-shot cannot bridge**: **Cross-method convergence analysis** — the pipeline can
report that "the Dung framework rejects arg_3 under grounded semantics, the JTMS flags
its supporting belief as contested, and the quality scorer rates it 3/10 on sufficiency —
all three methods converge on arg_3 being the weakest link." The 0-shot has only one
method (prose reasoning) and cannot demonstrate convergence from independent analyses.

---

## Summary: Pipeline-Unique vs Comparable Categories

| # | Category | Pipeline-unique capabilities | 0-shot ceiling |
|---|----------|------------------------------|----------------|
| 1 | Argument extraction | `arg_id` indexing, structured fields | 🟡 Prose description |
| 2 | Fallacy detection | 8-family taxonomy, per-arg localization, confidence | 🟡 Named in prose, no taxonomy |
| 3 | Formal reasoning | FOL/Modal/PL formulas + Tweety verification | 🔴 **Impossible** — no solver |
| 4 | Dung argumentation | 11 semantics, extensions, acceptability | 🔴 **Impossible** — no framework |
| 5 | ASPIC+ analysis | Rule-based arguments, undercutters | 🔴 **Impossible** — no formalism |
| 6 | Counter-arguments | 5 strategies, per-arg targeting, scored | 🟡 Generic prose suggestions |
| 7 | Quality scoring | 9 virtues, numeric, per-arg | 🟡 Subjective prose |
| 8 | JTMS beliefs | Justification chains, retraction cascades | 🔴 **Impossible** — no tracking |
| 9 | Governance | 7 voting methods, consensus metrics | 🔴 **Impossible** — single opinion |
| 10 | Debate | Adversarial multi-personality stress-test | 🔴 **Impossible** — single-pass |
| 11 | Narrative synthesis | Cross-method convergence analysis | 🟡 Single-pass synthesis |

**Verdict**: 6 of 11 categories (3, 4, 5, 8, 9, 10) are **structurally impossible** for
a 0-shot LLM — they require symbolic computation, multi-agent orchestration, or belief
tracking that prose generation cannot provide. 3 categories (1, 2, 6) are **partially
comparable** (both produce outputs, but pipeline adds structure/taxonomy/targeting).
2 categories (7, 11) are **enhancement-over** (both produce assessments, but pipeline
produces quantified/structured versions).

The pipeline's qualitative superiority is **irreducible** for the 6 impossible categories
— no prompt engineering can give a 0-shot LLM a Tweety solver, a Dung framework, or
a JTMS belief tracker.

---

## À valider par l'utilisateur

1. **Output bars** — Are the minimum thresholds above reasonable? Too strict (may false-FAIL
   healthy bricks)? Too lenient (may PASS trivially broken ones)?
2. **Superiority criteria** — Is the "pipeline-unique" classification honest? Are there
   dimensions where the 0-shot could match with better prompting?
3. **Category coverage** — Are 11 categories the right decomposition, or should some be
   merged (e.g., FOL+Modal+PL → "formal reasoning") or split (e.g., governance → voting +
   conflict resolution)?
4. **Scoring granularity** — 3-point rubric (Missed/Partial/Strong) sufficient for the
   Capstone verdict, or should each criterion be scored individually?
5. **The "6 impossible" claim** — Is it fair to say these are structurally impossible for
   0-shot, or could tool-augmented LLMs (with solver access) close the gap?
