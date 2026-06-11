# Phase 4 Verdict Rubric — Unified Closure Framework

**Track**: FB-17 #1037 (Epic #947 Phase 4 terminal)
**Author**: po-2023 worker
**Date**: 2026-06-10
**Consumed by**: Coordinator + user to gate Epic #947 closure

---

## 1. Purpose

Epic #947 Phase 4's terminal DoD is: *"spectacular reports that **DECIDE** vs 0-shot."*
This rubric provides the **single ordinal scale** and **closure checklist** that makes that judgment unambiguous. It reconciles the two existing evaluation axes:

| Axis | Corpus | Scale | Source |
|------|--------|-------|--------|
| **A** — corpus_X yardstick | `corpus_X` (manifesto) | D1–D10 × {MATCH, PARTIAL, MISSED, EXCEEDED} | FB-8 #953 → #1027 |
| **B** — CAPSTONE qualitative | doc_A/B/C (multiple) | 11 categories × {🟢 Strong, 🟡 Partial, 🔴 Missed} | #1033 |

Both axes measure pipeline output quality, but on different texts, with different granularities, and different scoring semantics. Without reconciliation, the Epic verdict is ambiguous.

---

## 2. Ordinal Scale: Pipeline vs 0-Shot

A single 4-level ordinal judgment is applied **per corpus**, then aggregated.

| Level | Label | Meaning |
|:-----:|-------|---------|
| **4** | **DECIDES** | Pipeline output is clearly superior to 0-shot. Structured, verified, actionable output where 0-shot is shallow or absent. Covers dimensions 0-shot cannot reach. |
| **3** | **EDGES** | Pipeline output is meaningfully better on balance, but not decisively so. Some categories clearly superior, others comparable to 0-shot. |
| **2** | **TIES** | Pipeline and 0-shot are roughly equivalent overall. Pipeline adds structure in some categories but loses to 0-shot's fluid prose in others. |
| **1** | **LOSES** | 0-shot output is better than the pipeline. Pipeline adds noise, misses key insights, or produces vacuous structured output where 0-shot delivers genuine analysis. |

**Key constraint (anti-theater)**: The rubric MUST be able to say LOSES or TIES honestly. If the current honest verdict is BELOW on corpus_X and the pipeline merely matches 0-shot on CAPSTONE categories, the aggregate verdict is TIES or LOSES — not DECIDES. Defining the bar to guarantee a pass would be theater (#1019 anti-pendule).

---

## 3. Mapping Axis A (corpus_X D1–D10) → Ordinal

### 3.1 Per-dimension band → contribution weight

| Band | Weight | Rationale |
|------|--------|-----------|
| EXCEEDED | +2 | Pipeline goes beyond the specialist analyst |
| MATCH | +1 | Pipeline covers the dimension equivalently |
| PARTIAL | 0 | Pipeline touches it but misses key aspects (neutral contribution) |
| MISSED | -1 | Pipeline does not address this dimension |

### 3.2 Aggregation rule

```
score_A = Σ(weight per dimension)  # range: [-10, +20]

ordinal_A:
  score_A ≥ +7   → DECIDES   (7+ net positive, majority MATCH+)
  score_A ≥ +3   → EDGES     (positive but not dominant)
  score_A ≥ -2   → TIES      (roughly balanced)
  score_A <  -2  → LOSES     (net negative — more MISSED than covered)
```

### 3.3 Worked example — corpus_X #1027 result

| Dim | Band | Weight |
|-----|------|--------|
| D1 Jargon | PARTIAL | 0 |
| D2 Contradictions | MATCH | +1 |
| D3 Populist | MISSED | -1 |
| D4 Value Instr. | MATCH | +1 |
| D5 Historical | PARTIAL | 0 |
| D6 Circular | MISSED | -1 |
| D7 Drive-Relief | MISSED | -1 |
| D8 Permission | PARTIAL | 0 |
| D9 Technofascism | PARTIAL | 0 |
| D10 Negation | PARTIAL | 0 |

**score_A = -1** → **ordinal_A = TIES**

Note: This is an honest assessment. The pipeline went from 10/10 MISSED (baseline #953) to 2 MATCH + 5 PARTIAL + 3 MISSED — significant improvement but still 3 gaps (D3/D6/D7). The verdict is TIES because the pipeline provides structure (Dung extensions, PL formalization) that 0-shot cannot, but 0-shot would likely match or exceed on the analytical depth of the 3 MISSED dimensions.

---

## 4. Mapping Axis B (CAPSTONE 11 categories) → Ordinal

### 4.1 Per-category scoring

| Symbol | Weight | Rationale |
|--------|--------|-----------|
| 🟢 Strong | +1 | Structured, verified, actionable output |
| 🟡 Partial | 0 | Present but incomplete (prose only, no structure) |
| 🔴 Missed | -1 | No output in this category |

### 4.2 Structural advantage bonus

6 of 11 categories are **structurally impossible** for 0-shot (require symbolic solvers, formal frameworks, or multi-agent orchestration):

| # | Category | Structural? |
|---|----------|:-----------:|
| 1 | Argument extraction | No |
| 2 | Fallacy detection (8-Family) | No |
| 3 | Formal reasoning (FOL + Modal + PL) | **Yes** |
| 4 | Dung Argumentation (11 Semantics) | **Yes** |
| 5 | ASPIC+ Analysis | **Yes** |
| 6 | Counter-Arguments (5 Strategies) | No |
| 7 | Quality Scoring (9 Virtues) | No |
| 8 | JTMS Beliefs | **Yes** |
| 9 | Governance (7 Voting Methods) | **Yes** |
| 10 | Debate (Adversarial Multi-Personality) | **Yes** |
| 11 | Narrative Synthesis | No |

Pipeline output in a structural category counts as **automatic +1** if non-empty (even 🟡 Partial), because 0-shot simply cannot produce it. If pipeline output is 🔴 Missed in a structural category, weight = 0 (not -1), because the absence is a pipeline gap, not a 0-shot advantage.

### 4.3 Aggregation rule

```
score_B = Σ(weight per category) + Σ(structural_bonus per structural category)
# raw range: [-5, +11], with structural bonus: [-5, +11]

ordinal_B:
  score_B ≥ 7   → DECIDES
  score_B ≥ 4   → EDGES
  score_B ≥ 1   → TIES
  score_B <  1  → LOSES
```

### 4.4 Worked example — hypothetical doc_A result

Assume: 🟢 on 4 structural cats (auto +1 each) + 🟢 on 3 non-structural + 🟡 on 2 non-structural + 🔴 on 2 non-structural.

```
Structural 🟢: 4 × (+1 weight + +1 bonus) = +8
Non-structural 🟢: 3 × +1 = +3
Non-structural 🟡: 2 × 0 = 0
Non-structural 🔴: 2 × -1 = -2

score_B = +9 → DECIDES
```

A realistic EDGES scenario: 🟢 on 3 structural, 🟡 on 3 structural (auto +1 each), 🟢 on 2 non-structural, 🟡 on 2 non-structural, 🔴 on 1 non-structural.

```
Structural 🟢: 3 × (+1 +1) = +6
Structural 🟡: 3 × (0 +1) = +3
Non-structural 🟢: 2 × +1 = +2
Non-structural 🟡: 2 × 0 = 0
Non-structural 🔴: 1 × -1 = -1

score_B = +10 → DECIDES
```

For LOSES to happen, the pipeline would need to fail across most categories while 0-shot produces good prose — unlikely given structural advantages, but not impossible if pipeline outputs are vacuous.

---

## 5. Cross-Axis Aggregation → Final Verdict

### 5.1 Per-corpus verdicts, then aggregate

Each corpus gets its own ordinal verdict. The **Epic #947 terminal verdict** is the aggregate:

```
Epic verdict = min(ordinal per corpus)

If only corpus_X is evaluated:
  Epic verdict = ordinal_A (Axis A alone)

If corpus_X + CAPSTONE doc_A/B/C are all evaluated:
  Epic verdict = min(ordinal_A, ordinal_B_doc_A, ordinal_B_doc_B, ordinal_B_doc_C)
```

The **min** rule is conservative: the Epic verdict is determined by the weakest corpus result. This prevents hiding a LOSES on one corpus behind a DECIDES on another.

### 5.2 Closure criteria

The Epic #947 DoD is **MET** if and only if:

| Criterion | Required | Current (#1027 + CAPSTONE pending) |
|-----------|----------|-------------------------------------|
| Epic verdict ≥ EDGES | ✅ Required | ⬜ ordinal_A = TIES (not yet) |
| No corpus at LOSES | ✅ Required | ✅ No corpus at LOSES |
| At least one corpus at DECIDES | Desired | ⬜ Not yet demonstrated |

**Current honest assessment**: corpus_X = TIES (score_A = -1). The Epic is NOT yet closable.

**What would move the needle**:
- D3/D6/D7 moving from MISSED → PARTIAL would shift score_A from -1 to +2 → still TIES
- D3/D6/D7 moving from MISSED → MATCH would shift score_A from -1 to +5 → EDGES
- Any EXCEEDED dimension adds +2 (replacing 0 or -1) → potential DECIDES

**Closure bar (explicit)**: The user declares DoD MET when satisfied the pipeline provides genuine analytical value beyond 0-shot. This rubric makes that judgment **legible and auditable**, but the user retains the final call. The numerical thresholds above are guidelines, notoverrides.

---

## 6. Cross-Reference Table

| Artifact | Issue/PR | Status | Role in rubric |
|----------|----------|--------|----------------|
| corpus_X yardstick (D1–D10) | #952 / #958 | CLOSED | Defines Axis A dimensions |
| corpus_X benchmark | #953 → #1027 | CLOSED | Provides Axis A scores |
| CAPSTONE rubric (11 categories) | #1033 | OPEN | Defines Axis B categories |
| CAPSTONE comparison | #1033 | In progress | Provides Axis B scores |
| Subsystem verdict | #957 | CLOSED | Grounds subsystem trustworthiness |
| FB-15 enrichment | #1032 / #1034 | MERGED | Enrichment attempt (no delta on corpus_X) |
| FB-15 integration value-gates | #1036 | MERGED | Proves enrichment load-bearing in pipeline chain |
| **This rubric** | **#1037** | **This PR** | **Unifies A + B → ordinal → closure** |

---

## 7. Privacy Compliance

- Opaque IDs only: `corpus_X`, `doc_A/B/C`, `Speaker_A`, `D1`–`D10`
- No source names, authors, URLs, dates
- No `raw_text`, `full_text`, `full_text_segment`
- Scoring tables contain only band symbols and dimension labels
- grep-clean (verified before commit)

---

## 8. Anti-Theater Commitment

This rubric is designed to produce **honest verdicts**:

1. **The current corpus_X result is TIES, not DECIDES.** The rubric says so. If the pipeline improves, the rubric will reflect that. If it doesn't, the rubric won't inflate the score.

2. **LOSES is a possible verdict.** If pipeline output is genuinely worse than 0-shot on a corpus (vacuous structure, missed insights), the rubric produces LOSES. This is not failure — it's honest measurement.

3. **The closure bar requires ≥EDGES.** TIES is not enough. The pipeline must demonstrate clear analytical value beyond 0-shot on every evaluated corpus. The user may override, but the rubric's default position is: prove it.

4. **The min rule prevents cherry-picking.** One good corpus cannot hide a bad corpus. Every evaluated text contributes to the verdict.

5. **Structural advantages are real but bounded.** The 6 solver-dependent categories give the pipeline genuine advantages that 0-shot cannot match. But these advantages only count if the pipeline actually produces non-trivial output in those categories. Vacuous output scores 0, not +1.
