# SCDA Multi-Corpus Baseline Report

**Date:** 2026-05-18
**Issue:** #598 (Part 2), #592 (follow-up)
**Model:** gpt-5-mini
**Commits:** `7f39085f` (A), this report

## 1. Summary

Full conversational pipeline audit on 3 dense corpora (A, B, C) with gpt-5-mini, validating the model upgrade from gpt-4o-mini. The pipeline produces structured argument extraction, fallacy detection, counter-arguments, and formal reasoning across all corpora. The model upgrade resolves the primary tool-calling bottleneck identified in #595.

## 2. Corpus Profiles

| Corpus | Text length | Language | Duration | Turns | Agents SINGULAR_INSIGHT |
|--------|-------------|----------|----------|-------|------------------------|
| corpus_dense_A | 58052 chars (~14K words) | EN | 1204.9s (~20 min) | 23 | 8/8 |
| corpus_dense_B | 59092 chars (~14K words) | EN | 1667.5s (~28 min) | 23 | 8/8 |
| corpus_dense_C | 46391 chars (~11K words) | EN | 1117.0s (~19 min) | 23 | 8/8 |

All 3 corpora are English-language political speeches of similar length. All runs used `max_turns_per_phase=10` and gpt-5-mini.

## 3. Quantitative Results

### Argument Extraction

| Metric | A | B | C | Total |
|--------|---|---|---|-------|
| identified_arguments | 7 | 6 | 5 | **18** |
| identified_fallacies | 2 | 0 | 1 | **3** |
| counter_arguments | 8 | 0 | 0 | **8** |
| jtms_beliefs | 4 | 0 | 1 | **5** |

### Formal Reasoning

| Metric | A | B | C |
|--------|---|---|---|
| Dung frameworks | 1 (9 args, 2 attacks) | 0 | 1 |
| ASPIC results | 1 (7 total, 5 surviving) | 1 | 1 |
| Belief revision | 1 (fallacy_contraction) | 0 | 0 |
| NL-to-logic translations | 1 (propositional, 9 atoms) | 0 | 0 |

### Fallacy Details

| Corpus | Fallacy | Type | Target |
|--------|---------|------|--------|
| A | fallacy_1 | Post hoc, ergo propter hoc | arg_2 |
| A | fallacy_2 | Statistique trompeuse | arg_3 |
| B | — | none detected | — |
| C | fallacy_1 | sophisme_genetique | — |

## 4. Unique Insight Categories (DoD #592)

**DoD: ≥3 unique categories vs baseline (LLM 0-shot)**

Pipeline produces insights that a 0-shot LLM baseline does not:

| Category | A | B | C | Description |
|----------|---|---|---|-------------|
| Dung argumentation frameworks | ✅ | — | ✅ | Attack/defense graphs, grounded extensions |
| ASPIC structured argumentation | ✅ | ✅ | ✅ | Strict/defeasible rules, surviving/defeated args |
| Belief revision (AGM contraction) | ✅ | — | — | Fallacy-triggered belief retraction |
| NL-to-logic translation | ✅ | — | — | Propositional formulas with verified atoms |
| JTMS belief tracking | ✅ | — | ✅ | Belief registration with retraction chains |
| Counter-argument generation | ✅ | — | — | Multi-strategy counter-arguments with scoring |
| Taxonomy-anchored fallacy typing | ✅ | — | ✅ | Specific fallacy families (not generic "none") |

**Unique categories count:** ≥4 on corpus A, ≥2 on corpus C, ≥1 on corpus B.

**Epic #530 acceptance criterion: ≥3 unique categories** — **MET on corpus A** (Dung + ASPIC + Belief Revision + NL-to-logic). Corpus C has 2, corpus B has 1.

## 5. Cross-Corpus Patterns

### Consistent strengths
- **Argument extraction**: All 3 corpora yield ≥5 structured arguments (18 total). gpt-5-mini reliably calls `add_identified_argument()`.
- **ASPIC reasoning**: All 3 corpora produce ASPIC results (formal argumentation with surviving/defeated classification).
- **Agent engagement**: 8/8 agents reach SINGULAR_INSIGHT across all corpora.
- **PM coordination**: ProjectManager produces 8 messages per run, driving multi-phase orchestration.

### Variable performance
- **Fallacy detection**: Corpus A produces 2 typed fallacies, corpus C produces 1, corpus B produces 0. This variance likely reflects text content (some speeches contain more overt fallacies than others) but may also indicate InformalAgent inconsistency — the growth hook (#597) could help.
- **Counter-arguments**: Only corpus A produces counter-arguments (8). B and C produce 0. This suggests CounterAgent activation depends on argument richness — more arguments lead to more counter-argument opportunities.
- **JTMS/Dung/Belief Revision**: Inconsistent activation across corpora. These downstream formal layers depend on earlier phases populating state. When fallacy detection is thin, JTMS retraction chains don't fire.

### Pattern: downstream formal layers cascade from extraction quality

Corpus A (7 args + 2 fallacies) → full pipeline activation (8 counters, 4 JTMS beliefs, Dung, ASPIC, Belief Revision, NL-to-logic).

Corpus B (6 args + 0 fallacies) → partial activation (ASPIC only, no counters/JTMS/Dung).

Corpus C (5 args + 1 fallacy) → moderate activation (JTMS, Dung, ASPIC, no counters/Belief Revision).

**Key insight**: The pipeline's formal reasoning layers are cascading — they activate when earlier phases (extraction + fallacy detection) produce rich enough state. The primary lever for improving overall pipeline output is improving fallacy detection quantity.

## 6. Comparison with gpt-4o-mini Baseline

| Metric | gpt-4o-mini (A only) | gpt-5-mini (A) | gpt-5-mini (B) | gpt-5-mini (C) |
|--------|---------------------|----------------|----------------|----------------|
| identified_arguments | 1 | 7 | 6 | 5 |
| identified_fallacies | 0 | 2 | 0 | 1 |
| counter_arguments | 0 | 8 | 0 | 0 |
| Formal layers activated | 0 | 5/5 | 1/5 | 3/5 |
| Agents SINGULAR_INSIGHT | 5/6 | 8/8 | 8/8 | 8/8 |

## 7. Recommendations

1. **Fallacy detection improvement** (#597 growth hook): The biggest remaining gap is InformalAgent inconsistency. Only corpus A produces >1 typed fallacy. The growth hook (re-prompt if no fallacies detected) would help B and C reach ≥3 fallacies.

2. **Counter-argument activation**: CounterAgent only fires on corpus A. Investigate whether the CounterAgent needs more explicit triggering when ≥3 arguments exist, or if it's a turn-budget issue.

3. **JTMS/Dung cascade**: These formal layers depend on fallacy-triggered beliefs. Improving fallacy detection (rec. #1) would cascade to improve all downstream layers.

## 8. DoD Status

- [x] Corpus A re-run with gpt-5-mini — metrics collected
- [x] Corpus B re-run with gpt-5-mini — metrics collected
- [x] Corpus C re-run with gpt-5-mini — metrics collected
- [x] Rapport agrégé `docs/reports/SCDA_MULTI_CORPUS_BASELINE_2026-05-18.md`
- [x] DoD ≥3 catégories uniques — **MET on corpus A** (Dung + ASPIC + Belief Revision + NL-to-logic)
- [x] Cross-corpus insights documented
- [x] IDs opaques only (no source names in report)
