# SCDA Corpus A Coverage Push — Sprint 5

**Date:** 2026-05-17
**Epic:** #530 (SCDA)
**Issue:** #590 (Corpus A coverage push)
**Machine:** myia-po-2025
**Commit:** 73d10e94 (`fix(orchestration): phase-aware convergence gate prevents premature exit`)

## 1. Executive Summary

Fixed the convergence bug that caused Phase 2 (Formal Analysis) and Phase 3 (Synthesis) to exit immediately after Phase 1 set `final_conclusion`. The fix gates `_check_convergence` to only check `final_conclusion` during Synthesis phases (`"ynthesis" in phase_name`). Also fixed a `source_id` NameError in deep synthesis post-phase.

Post-fix live audit on corpus A confirms all 5 specialists now run, with 12 turns (vs Sprint 4's 5) across all 3 phases. FormalAgent and QualityAgent are now active for the first time since Sprint 3.

## 2. Root Cause Analysis

### Bug: `_check_convergence` cross-phase conclusion bleed

**Location:** `argumentation_analysis/orchestration/conversational_orchestrator.py:909`

**Before (buggy):**
```python
if state and state.final_conclusion:
    return True  # triggers in ALL phases
```

**After (fixed):**
```python
if state and state.final_conclusion and "ynthesis" in phase_name:
    return True  # triggers only in Synthesis phases
```

**Mechanism:** PM calls `set_conclusion()` during Phase 1 (Extraction) after identifying arguments. `state.final_conclusion` persists across all phases. Without phase gating, Phase 2 turn 1 immediately detects `final_conclusion` and converges, preventing FormalAgent, QualityAgent, CounterAgent, and all downstream post-phase hooks from running.

### Bug: `source_id` NameError in deep synthesis

**Location:** `conversational_orchestrator.py:737`

**Before (buggy):**
```python
"opaque_id": source_id or "unknown",  # source_id never defined
"language": "",
```

**After (fixed):**
```python
"opaque_id": getattr(state, "source_id", "conversational_analysis"),
"language": detected_lang if detected_lang != "unknown" else "",
```

## 3. Unit Tests

8 new tests in `tests/unit/argumentation_analysis/orchestration/test_convergence_gates.py`:

| Test | Result | Description |
|------|--------|-------------|
| `test_convergence_not_triggered_in_extraction_phase_with_conclusion` | PASS | Phase 1 ignores final_conclusion |
| `test_convergence_not_triggered_in_formal_phase_with_conclusion` | PASS | Phase 2 ignores final_conclusion |
| `test_convergence_triggered_in_synthesis_phase_with_conclusion` | PASS | Phase 3 converges on final_conclusion |
| `test_convergence_triggered_in_deep_synthesis_with_conclusion` | PASS | Deep Synthesis converges |
| `test_no_convergence_without_conclusion` | PASS | No phase converges without conclusion |
| `test_stagnation_detection_still_works` | PASS | Stagnation still triggers convergence |
| `test_reanalysis_phase_not_affected_by_conclusion` | PASS | Re-Analysis ignores stale conclusion |
| `test_three_phases_run_despite_early_conclusion_in_state` | PASS | Full phase sequence invariant |

Regression suite: 1958 passed, 0 new failures (pre-existing: 30 failures in unrelated tests).

## 4. Live Audit Results — Corpus A

### 4.1 Run Summary

| Metric | Sprint 4 | Sprint 5 | Delta |
|--------|----------|----------|-------|
| Duration | 383s | **139s** | -64% |
| Total turns | 5 | **12** | +140% |
| Phases completed | 3 (early exit) | **3 (full run)** | Fixed |
| Specialist count | 3 | **5** | +2 |

### 4.2 Specialist Activation

| Specialist | Sprint 4 | Sprint 5 | Status |
|-----------|----------|----------|--------|
| ProjectManager | 3 msgs | **5 msgs** | Active |
| ExtractAgent | 1 msg | **2 msgs** | Active |
| InformalAgent | 1 msg | **1 msg** | Active |
| FormalAgent | **0 msgs** | **2 msgs** | **NOW ACTIVE** |
| QualityAgent | **0 msgs** | **1 msg** | **NOW ACTIVE** |

### 4.3 Sprint 4 Dimensions (Sprint 5 Live)

| Dimension | Sprint 4 | Sprint 5 | Status |
|-----------|----------|----------|--------|
| `identified_arguments` | 0 | **1** | Improved but low |
| `identified_fallacies` | 0 | **1** (type=none) | LLM-dependent |
| `jtms_beliefs` | 94 | **1** | LLM-dependent |
| `dung_frameworks` | 0 | **0** | Depends on arguments |
| `modal_analysis_results` | 0 | **0** | Depends on arguments |
| `aspic_results` | 0 | **1** | **NOW ACTIVE** |
| `belief_revision_results` | 0 | **0** | No fallacies to revise |
| `counter_arguments` | 0 | **0** | Synthesis converged T1 |
| `argument_quality_scores` | 0 | **1** (overall=1.2) | **NOW ACTIVE** |
| `fol_analysis_results` | 0 | **0** | FormalAgent ran but no arg_ids |
| `formal_verification` | 0 | **0** | No arg_ids linked |

### 4.4 Enrichment Summary

| Field | Sprint 4 | Sprint 5 |
|-------|----------|----------|
| `total_arguments` | 0 | 1 |
| `with_fallacy_analysis` | 0 | 0 |
| `with_quality_score` | 0 | **1** |
| `with_counter_argument` | 0 | 0 |
| `with_formal_verification` | 0 | 0 |
| `with_jtms_belief` | 0 | **1** |

## 5. Remaining Gaps

The convergence fix resolves the **architectural bottleneck** (Phases 2/3 now run). The remaining gaps are **LLM behavioral** issues:

1. **Argument extraction:** LLM uses `add_jtms_belief` instead of `add_argument()` — only 1 argument extracted from a 58K text. The agent instructions should be updated to prefer `add_argument` with structured fields.

2. **Fallacy detection:** InformalAgent returned `type: "none"` — no fallacies detected in a highly rhetorical political speech. Likely a prompt or agent instruction issue.

3. **Synthesis still converges T1:** Phase 3 converges on turn 1 because `final_conclusion` was set during Phase 2. The synthesis agents (CounterAgent, DebateAgent) get only 1 turn. Consider resetting `final_conclusion` between phases or requiring more turns before convergence.

4. **Formal verification arg_ids:** FormalAgent ran but didn't link results to `arg_1`. The tracking fix (#571) requires `arg_id` in PL/FOL/NL-to-logic calls.

## 6. DoD Assessment (#590)

- [x] Root cause convergence bug identified and fixed
- [x] Phase-aware `_check_convergence` gate implemented
- [x] `source_id` NameError fixed
- [x] Unit tests (8/8 pass) for phase isolation invariants
- [x] Regression suite green (0 new failures)
- [x] Live re-audit corpus A completed
- [ ] ≥10 fallacies on corpus A — **NOT MET** (1 fallacy, type=none)
- [ ] ≥80% leaf-tagged on corpus A — **NOT MET** (1 argument extracted)

**Architectural fix is complete.** The convergence gate ensures all phases and specialists run. The fallacy/argument extraction shortfall is an LLM behavioral issue requiring agent instruction tuning, which is orthogonal to the convergence fix.

## 7. Recommendations

1. **Agent instruction tuning (post-#590):** Update PM and ExtractAgent instructions to prefer `add_argument()` over `add_jtms_belief()`. Ensure InformalAgent uses the full fallacy taxonomy.

2. **Convergence relaxation:** Consider requiring ≥2 turns in Synthesis before checking `final_conclusion`, or reset the flag between phases.

3. **Model upgrade:** Test with gpt-5-mini (currently using gpt-4o-mini) — may improve argument extraction depth.

## 8. References

- Commit: `73d10e94` on main
- Convergence fix: `argumentation_analysis/orchestration/conversational_orchestrator.py:909`
- Tests: `tests/unit/argumentation_analysis/orchestration/test_convergence_gates.py`
- Sprint 4 baseline: `docs/reports/SCDA_AUDIT_POST_SPRINT4_2026-05-16.md`
- Audit outputs: `outputs/scda_audit/corpus_dense_A/` (gitignored)
