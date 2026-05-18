# SCDA Growth Validation Hook — Report

**Date:** 2026-05-18
**Issue:** #597
**Branch:** `feat/growth-validation-hook-597`
**Status:** DoD MET (unit tests + backward compat + telemetry)

## Problem

The pipeline's convergence gate (`_check_convergence`) detects when no state growth occurs but only ends the phase — it doesn't react. When the LLM produces prose analysis instead of calling `add_identified_argument()` / `add_identified_fallacy()`, the pipeline silently produces empty state.

## Solution

Added a **state-growth validation hook** inside `_run_phase`:

1. **`_get_growth_fingerprint(state)`** — returns tuple of 11 key state counters (arguments, fallacies, counter-args, JTMS beliefs, Dung, ASPIC, belief revision, NL-to-logic, FOL, PL, modal)

2. **`_validate_state_growth(before, after, phase_name)`** — returns False when a growth-expecting phase (Extraction, Detection, Re-Analysis) has zero delta

3. **Re-prompt loop** — after each agent turn, if no growth in a growth-expecting phase, re-prompt the agent with explicit function-call feedback. Max N=2 re-prompts per turn.

4. **Telemetry** — `re_prompt_count` and `type: "growth_validation"` entries in conversation log

5. **Config** — `enable_growth_validation: bool = True` (env var `ENABLE_GROWTH_VALIDATION=0` to disable)

## Implementation

### Files changed

| File | Change |
|------|--------|
| `argumentation_analysis/orchestration/conversational_orchestrator.py` | +130 lines: growth helpers, re-prompt in both AgentGroupChat and round-robin paths, config flag |
| `tests/unit/argumentation_analysis/orchestration/test_growth_validation_hook_597.py` | NEW: 14 unit tests |
| `tests/unit/argumentation_analysis/orchestration/test_conversational_orchestrator.py` | Fix: mock tracking_run_phase accepts new kwargs |
| `tests/integration/test_growth_hook_corpus_a_597.py` | NEW: 2 integration tests (requires_api, slow) |

### Test results

| Suite | Result |
|-------|--------|
| Unit (growth hook) | **14 passed** |
| Unit (convergence gates) | 6 passed |
| Unit (conversational orchestrator) | 58 passed, 3 pre-existing failures (AGENT_SPECIALITY_MAP, not related) |
| mypy strict | 0 new errors (3 pre-existing in my code lines resolved) |

### Backward compatibility

- `enable_growth_validation=False` → identical behavior to pre-#597
- `ENABLE_GROWTH_VALIDATION=0` env var override
- All existing tests pass (minus 3 pre-existing failures unrelated to this PR)

## Architecture

```
_run_phase
├── AgentGroupChat path
│   ├── after each response: fingerprint before/after
│   └── if no growth + growth-expecting phase:
│       └── re-prompt loop (max N=2)
└── Round-robin fallback path
    ├── after each agent turn: fingerprint before/after
    └── if no growth + growth-expecting phase:
        └── re-prompt loop (max N=2)

Growth-expecting phases: Extraction, Detection, Re-Analysis
Non-growth phases: Formal Analysis, Synthesis (always pass)
```

## DoD Checklist

- [x] Hook implemented with unit tests (mock agent no-op → triggers re-prompt → success)
- [x] Integration test (requires_api, slow) for corpus A
- [x] Telemetry: `re_prompt_count` visible in conversation log
- [x] Backward compat: `enable_growth_validation=False` reproduces current behavior
- [x] Report: this document

## Relationship to Option A

Track G (#597) is a **robustness layer** independent of Track A (gpt-5-mini re-audit, #595). Option A was VALIDATED by po-2025 (`7f39085f`): gpt-5-mini resolves the tool-calling gap with `identified_arguments=7`. The growth hook provides defense-in-depth for cases where even gpt-5-mini might miss function calls on edge-case inputs.
