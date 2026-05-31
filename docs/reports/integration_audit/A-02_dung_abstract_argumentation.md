# Audit A-02: Dung Abstract Argumentation

**Issue**: #165 (CLOSED) | **SUIVI**: Score 60% (revised ~85%) | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project 1.2.1 (Da Silva, Badraoui, Jeyakumar) delivered a Dung argumentation framework implementation. The original delegated all computation to Tweety via JPype. During integration, the algorithms were rewritten in pure Python as a JVM-free fallback.

## What exists in `argumentation_analysis/`

| File | Lines | Description |
|------|-------|-------------|
| `agents/core/logic/dung_native.py` | 278 | `DungFramework` class with 5 semantics: `grounded_extension()`, `admissible_sets()`, `complete_extensions()`, `preferred_extensions()`, `stable_extensions()` |
| `agents/core/logic/af_handler.py` | — | `AFHandler` wrapping Tweety for 11 semantics (primary path when JVM available) |
| `core/shared_state.py` | :404 | `dung_frameworks` field + `add_dung_framework()` on `UnifiedAnalysisState` |
| `orchestration/workflows.py` | — | `dung_extensions` capability wired into 4 workflow definitions |
| `orchestration/registry_setup.py` | :459 | `dung_extensions_service` registered in CapabilityRegistry |
| `orchestration/invoke_callables.py` | :5123 | Pipeline fallback: tries AFHandler (Tweety) first, falls back to inline grounded-only |
| `orchestration/conversational_orchestrator.py` | :2008 | Conversational path uses `dung_native.grounded_extension()` correctly |

## Preservation Assessment

- All 5 Dung semantics preserved in `dung_native.py` (grounded, preferred, stable, complete, admissible)
- Pure-Python implementation ensures operation without JVM dependency
- State management (`dung_frameworks` on `UnifiedAnalysisState`) fully wired
- Registry and workflow integration complete (4 workflows, capability registration)
- Conversational orchestrator correctly imports and delegates to `dung_native`

## Gap Analysis

1. **Pipeline fallback re-implements grounded-only** (`invoke_callables.py:5123`) instead of delegating to `dung_native` for all 5 semantics. The fallback path duplicates logic rather than importing from `dung_native`.
2. **Conversational path under-utilizes semantics** -- calls only `grounded_extension()` (1 of 5 available). Other semantics (preferred, stable, complete, admissible) are reachable only via direct module usage.
3. **No unified Dung service with automatic Tweety-to-native fallback.** The two implementations (Tweety `AFHandler` and pure Python `dung_native`) coexist but lack a single facade that tries Tweety first and transparently falls back to native for any requested semantics.

## Recommended Action

Create a `DungService` facade that delegates to `AFHandler` when JVM is available and falls back to `dung_native` for all 5 semantics, replacing the inline grounded-only fallback in `invoke_callables.py`. This would close the gap at minimal cost and make all semantics uniformly accessible.

## Source Files

- `argumentation_analysis/agents/core/logic/dung_native.py`
- `argumentation_analysis/agents/core/logic/af_handler.py`
- `argumentation_analysis/core/shared_state.py`
- `argumentation_analysis/orchestration/workflows.py`
- `argumentation_analysis/orchestration/registry_setup.py`
- `argumentation_analysis/orchestration/invoke_callables.py`
- `argumentation_analysis/orchestration/conversational_orchestrator.py`
