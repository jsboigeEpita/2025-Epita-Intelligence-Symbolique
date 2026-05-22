# Static Audit Report — Track TT (#672)

**Date**: 2026-05-22
**Base commit**: `606fa622` (post-SS)
**Scope**: Text-label ↔ canonical arg_id boundary audit
**Method**: Static code analysis, no API calls

---

## 1. Background

LL (#662) and RR (#670) revealed the same bug class: upstream objects named by **free text** (e.g., "The policy increases...") while downstream lookups use **canonical arg_id** (`arg_1`, `arg_2`, ...) → silently dead signals. 2 of 5 convergence signals were dead from origin.

This audit systematically checks ALL text↔arg_id boundaries in the pipeline.

---

## 2. Audit Methodology

For each site where arg identifiers appear as dict keys, set lookups, or string matching:
- **Producer**: what format is the key? (canonical `arg_N` or free text)
- **Consumer**: what format does the lookup expect?
- **Verdict**: SAFE (consistent), AT-RISK (mismatch possible), BUG (confirmed mismatch)

---

## 3. Findings

### BUG A2: cross_reference_graph.py — key name mismatch
**File**: `argumentation_analysis/reporting/cross_reference_graph.py` (lines 155, 164)
**Pattern**: `"target_arg_id"` lookup but fallacy dicts store `"target_argument_id"`
**Impact**: No fallacy→argument edges in cross-reference graph. 0 edges ever created.
**Fix**: Changed key from `"target_arg_id"` to `"target_argument_id"`.

### BUG A1: conversational_orchestrator.py — ASPIC+ positional index
**File**: `argumentation_analysis/orchestration/conversational_orchestrator.py` (lines 2039-2050, 2068-2078)
**Pattern**: `arg_ids[i]` positional comparison instead of canonical `f"arg_{i+1}"`
**Impact**: Fallacy undermining classification only works when fallacy targets the i-th argument by position. Defeated-by-fallacy classification in ASPIC+ is unreliable.
**Fix**: Replaced `arg_ids[i]` with `current_arg_id = f"arg_{i+1}"` derived from loop index.

### BUG IC5: invoke_callables.py — ATMS hypothesis quality lookup
**File**: `argumentation_analysis/orchestration/invoke_callables.py` (lines 1414-1432)
**Pattern**: `per_arg_scores.get(arg_name)` where `arg_name` is free text and keys are canonical
**Impact**: `h_high_quality` ATMS hypothesis never populated from actual quality scores.
**Fix**: Positional mapping `f"arg_{idx+1}"` as primary lookup key.

### BUG IC6: invoke_callables.py — social scoring quality lookup
**File**: `argumentation_analysis/orchestration/invoke_callables.py` (line 2571)
**Pattern**: `quality_scores.get(arg)` where `arg` is free text and keys are canonical
**Impact**: Social AF fallback never incorporates quality signal.
**Fix**: Positional mapping `f"arg_{i+1}"` as primary lookup key.

---

## 4. AT-RISK Sites (no fix applied — documented for awareness)

| ID | File | Pattern | Risk |
|----|------|---------|------|
| N1-1 | narrative_synthesis_plugin.py:266 | Dung arg resolution heuristic | Resolution may fail for heavily-truncated text; graceful degradation |
| N1-4 | narrative_synthesis_plugin.py:295 | Fallacy target_argument_id from LLM | LLM may return free text; `add_fallacy` validates but doesn't resolve |
| SW3 | state_writers.py:86 | Legacy ctx default `"arg_input"` | Quality score orphaned under `"arg_input"` key |
| IC4 | invoke_callables.py:1054 | JTMS fallacy substring match | May match wrong belief for short target text |
| DA2 | deep_synthesis_agent.py:907 | Adjudication target format | Same root cause as N1-4 |
| DA3 | deep_synthesis_agent.py:204 | Argument map fallacy target | Same root cause as N1-4 |
| DA6 | deep_synthesis_agent.py:390 | Counter-arg target_arg_ids field name | Possible list vs string mismatch |

---

## 5. SAFE Sites (confirmed correct)

| # | File | Site | Why safe |
|---|------|------|----------|
| N1-3 | narrative_synthesis_plugin.py | JTMS `startswith(arg_N:)` | Explicit canonical prefix by design |
| SW1 | state_writers.py | `_resolve_target_arg_id` | Resolver function, returns canonical or None |
| SW2 | state_writers.py | Quality key iteration | Both sides canonical |
| SW5 | state_writers.py | JTMS storage | `startswith` matching, robust |
| IC1 | invoke_callables.py | Quality arg_id gen | `f"arg_{i+1}"` canonical |
| IC3 | invoke_callables.py | JTMS belief naming | `f"arg_{i+1}:"` canonical prefix |
| IC7/IC8 | invoke_callables.py | Parallel arg extraction | Canonical from state or generated |
| DA1 | deep_synthesis_agent.py | Convergence import | Canonical from upstream |
| DA4 | deep_synthesis_agent.py | Counter-arg text match | Substring against descriptions, canonical ID result |
| DA5 | deep_synthesis_agent.py | Weak args detection | Canonical key iteration |
| A4 | cross_reference_graph.py | Counter-arg edges | Correct key `"target_arg_id"` for counter-args |
| A5 | conversational_orchestrator.py | Dung framework build | Canonical iteration + text fallback |
| A8-A14 | Various | Export/render/state tools | Count-only, export-only, or canonical-aware |

---

## 6. Summary

| Category | Count |
|----------|-------|
| **BUG (fixed)** | 4 |
| **AT-RISK (documented)** | 7 |
| **SAFE** | 15 |
| **Total sites audited** | 26 |

All 4 BUG fixes use the same pattern: replace free-text lookup with positional canonical key `f"arg_{idx+1}"` (matching the `add_argument` ID generation convention). No API calls required.
