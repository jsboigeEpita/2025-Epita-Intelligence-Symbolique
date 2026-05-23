# Track WW (#678) — JTMS-retracte Signal 4 Sombre sur Corpus C

**Date**: 2026-05-23
**Worker**: po-2025
**Status**: DIAGNOSED — plumbing correct in synthetic tests, likely authentique (upstream fallacy format mismatch on live run)

---

## Executive Summary

13 tests confirm that the entire chain `_invoke_jtms → state writer → compute_argument_convergence` correctly propagates `valid=False` and triggers signal 4 ("JTMS retracte") when fallacies are present. The plumbing is NOT broken at the convergence layer.

The most likely explanation for corpus C's 0 fires is **authentique**: the live pipeline's `phase_hierarchical_fallacy_output` may not populate `target_argument` (free text) on corpus C's fallacies, and the fallback index matching may produce retractions that are reflected in the JTMS session but the state writer path has a subtle ordering issue.

## Diagnosis

### Architecture trace

```
_invoke_jtms (invoke_callables.py:932)
  ├─ Creates LOCAL JTMSSession (NOT state._jtms_session)
  ├─ Prefixes arg beliefs: f"arg_{i+1}:{text[:66]}" (LL fix #662, line 1002)
  ├─ Retracts beliefs for detected_fallacies (lines 1049-1099)
  │   ├─ target_arg_text = f.get("target_argument", "") (line 1069)
  │   ├─ Substring match against arg_beliefs (line 1072-1074)
  │   └─ Fallback: min(i, len(arg_beliefs)-1) (line 1079)
  └─ Returns beliefs_output with valid from JTMS core

_persist_to_state → _write_jtms_to_state (state_writers.py:197)
  ├─ For each belief in output: state.add_jtms_belief(name, valid, justifications)
  └─ state.jtms_beliefs gets {"name": "arg_1:text...", "valid": False, ...}

compute_argument_convergence (narrative_synthesis_plugin.py:329)
  ├─ For each arg_id in identified_arguments
  ├─ jtms_prefix = f"{arg_id}:"
  ├─ Checks name.startswith(jtms_prefix) AND valid is False
  └─ Appends ("JTMS retracte", count) signal
```

### Key findings from tests

| Test | Result | What it proves |
|------|--------|---------------|
| State writer preserves `valid=False` | PASS | `_write_jtms_to_state` correctly copies retraction |
| State writer preserves `valid=None` | PASS | `None` is NOT treated as `False` |
| State writer handles legacy string | PASS | `"False"` string parsed correctly |
| _invoke_jtms fallback retraction | PASS | Fallback index produces ≥2 retractions with 2 fallacies |
| _invoke_jtms text matching retraction | PASS | Substring match finds correct arg |
| _invoke_jtms no fallacies | PASS | 0 retractions when no fallacies |
| Signal 4 fires after state writer | PASS | End-to-end: output → state → convergence = signal 4 |
| Signal 4 does NOT fire on `None` | PASS | `valid=None` correctly excluded |
| Post-phase hook finds arg_N belief | PASS | `_retract_fallacious_beliefs` matches `"arg_1" in "arg_1:text"` |
| Post-phase hook skips retracted | PASS | Already-retracted beliefs not double-retracted |
| Convergence reads state not session | PASS | Direct state.jtms_beliefs with valid=False fires signal 4 |

### Hypothesis assessment

| Hypothesis | Verdict | Evidence |
|-----------|---------|----------|
| (a) Plumbing: arg_N prefix missing in state | **ELIMINATED** | Tests prove prefix preserved through state writer |
| (b) Plumbing: valid=None instead of False | **ELIMINATED** | _invoke_jtms line 1099 sets `False` (not `None`); state writer preserves it |
| (c) Plumbing: state writer not called | **ELIMINATED** | `_persist_to_state` is called after JTMS phase |
| (d) Authentique: no fallacies with target_argument on C | **POSSIBLE** | Live data: 14 fallacies on C but signal fires 0 — fallacies may lack `target_argument` text AND fallback produces retractions but they may not survive to state |
| (e) Upstream: phase_hierarchical_fallacy_output empty on C | **MOST LIKELY** | The 14 fallacies are in `state.identified_fallacies` (set by state writer), but `phase_hierarchical_fallacy_output` may be structured differently on C, causing `detected_fallacies` to be empty or malformed |

### Remaining unknown

Without a live pipeline run, we cannot confirm hypothesis (e). The synthetic tests prove that IF `_invoke_jtms` receives fallacies in the expected format, signal 4 fires correctly. The gap is between what the live pipeline produces and what `_invoke_jtms` expects.

### Recommended verification

A live re-run with `phase_hierarchical_fallacy_output` logging would confirm whether the fallacies have `target_argument` or `target_argument_id` keys, and whether the format differs from what `_invoke_jtms` expects.

## Test Coverage

`tests/unit/argumentation_analysis/test_track_ww_jtms_retracte_signal.py` — 13 tests

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| TestStateWriterPreservesRetraction | 3 | valid=False/None/Legacy preserved by _write_jtms_to_state |
| TestInvokeJtmsRetractionPath | 3 | Fallback index, text matching, no fallacies |
| TestConvergenceSignal4EndToEnd | 3 | Full chain output→state→convergence |
| TestRetractFallaciousBeliefsPath | 2 | Post-phase hook finds/skips arg_N beliefs |
| TestDualSessionGap | 2 | Architecture documentation + state-based check |

All 13 pass (7.7s).

---

## Deliverable

Per DoD: the plumbing is verified correct. Signal 4 fires reliably when the pipeline provides fallacies with matching arguments. The 0-fire on corpus C is most likely an **upstream data format issue** (hypothesis e), not a convergence/plumbing bug. Live verification needed.
