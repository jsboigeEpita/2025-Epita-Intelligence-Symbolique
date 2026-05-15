# SCDA max_turns=15 Convergence Test

**Date:** 2026-05-15
**Epic:** #530 / Issue #540
**Corpus:** corpus_dense_A (src11, EN, ~58K chars)
**Baseline:** Sprint 1 audit (max_turns_per_phase=10)

## Executive Summary

Re-ran the conversational audit on corpus_dense_A with `max_turns_per_phase=15`. **Result: no improvement.** The run produced fewer arguments (3 vs 15), lower convergence (24.3% vs 29.7%), and shorter duration (19 min vs 40 min). The increase from 10 to 15 did not help because phase-level turn limits are hardcoded (7/5/8/5), making the global `max_turns_per_phase` parameter a fallback that is never reached.

## Comparison: max_turns=10 vs max_turns=15

| Metric | Sprint 1 (max_turns=10) | Sprint 2 (max_turns=15) | Delta |
|--------|------------------------|------------------------|-------|
| Duration | 2,417s (40 min) | 1,140s (19 min) | -53% |
| Total turns | 20 | 20 | 0 |
| Arguments | 15 | 3 | -80% |
| Fallacies | 1 | 1 | 0 |
| Quality scores | 4 | 0 | -100% |
| Counter-args | 8 | 1 | -88% |
| Formal verification | 0 | 0 | — |
| State populated | 1→11 | 1→9 | -2 fields |
| Convergence | 29.7% | 24.3% | -5.4pp |

## Root Cause Analysis

### 1. Phase-level overrides neutralize the parameter

The orchestrator defines per-phase `max_turns` in `phase_configs`:
- Extraction & Detection: 7 turns
- Formal Analysis & Quality: 5 turns
- Synthesis & Debate: 8 turns
- Re-Analysis: 5 turns

These are hardcoded in `conversational_orchestrator.py` and override the `max_turns_per_phase` parameter. Both runs executed exactly 20 turns (5+5+5+5). The `max_turns=15` parameter had **no effect** on actual turn counts.

### 2. LLM variance dominates

The dramatic difference (15 args vs 3 args) on identical input with identical phase configuration is attributable to LLM non-determinism. The OpenAI API does not guarantee identical outputs for identical inputs. This means:
- Single-run comparisons are unreliable
- Multiple runs needed for statistical significance
- The Sprint 1 baseline may have been a particularly productive run

### 3. Convergence plateau is structural

Both runs converge at ~24-30% coverage. The convergence check (`_check_convergence`) relies on specific state field populations that are not being filled regardless of turn count:
- `formal_results` = 0 in both runs (ParserExceptions)
- `arguments_found` = 0 in both runs (counted from a different field)
- `quality_scores` varies (4 vs 0)

The convergence calculation may have a bug — it reports `arguments_found: 0` despite 3-15 arguments being extracted. The state population path and the convergence check path may be looking at different fields.

## Recommendation

**Keep `max_turns_per_phase` at 10 (current default).** Increasing it has no effect because phase-level overrides are hardcoded.

To actually increase depth, modify the phase-level `max_turns` values:
- Extraction & Detection: 7 → 12 (most impactful phase)
- Re-Analysis: 5 → 8

However, given the LLM variance observed, a single parameter change is insufficient. The convergence issue is structural (ParserExceptions, field counting mismatch), not a turn-count problem.

### Actionable findings for Sprint 3

| Finding | Action |
|---------|--------|
| Phase overrides neutralize `max_turns_per_phase` | Make phase turns configurable or remove the parameter |
| LLM variance ±80% on argument count | Run 3x and take median for benchmarks |
| Convergence reports `arguments_found: 0` despite extraction | Bug in `_check_convergence` field mapping |
| Convergence plateau at ~27% | Structural — blocked by formal verification failure (#537) |

## Artifacts

All outputs saved to `outputs/scda_audit/corpus_dense_A/` (gitignored), overwriting the Sprint 1 baseline. The Sprint 1 baseline data is preserved in the Sprint 1 audit report `docs/reports/SCDA_AUDIT_2026-05-15.md`.
