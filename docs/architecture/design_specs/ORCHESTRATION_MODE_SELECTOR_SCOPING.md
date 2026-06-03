# Orchestration Mode Selector Scoping — Design Spec

**ID**: orchestration-mode-selector
**Issue**: #912 (North-Star, po-2023 conceptual lane)
**Effort**: S (scoping only — implementation deferred to po-2025 argparse lane)
**Owner**: po-2023 (scoping) → po-2025 (implementation)
**Date**: 2026-06-03

---

## Summary

Scope the `--mode` selector for making all orchestration modes CLI-selectable and
comparable. This document audits the real invocation paths, identifies gaps between
documentation and code, and provides the exact consumer signatures for each mode
so that the implementation (po-2025) cannot produce an inert selector.

---

## 1. Audit — Real Invocation Paths

### Methodology

Grepped `run_orchestration.py` dispatch table (`run_orchestration.py:496-640`)
against each orchestrator's actual entry point. Verified that:
1. The argparse `choices` list includes the mode
2. The dispatch `elif` branch calls a real function
3. The called function exists and is importable

### Results

| Mode | argparse choice | Dispatch branch | Entry point called | Import verified | Tag |
|------|----------------|-----------------|-------------------|----------------|-----|
| `pipeline` | ✅ (:327) | implicit (default) | `run_unified_analysis()` (:79, :159) | ✅ `unified_pipeline.py` | **cli-selectable** |
| `conversational` | ✅ (:328) | `:545` | `run_conversational_analysis()` | ✅ `conversational_orchestrator.py` | **cli-selectable** |
| `hierarchical` | ✅ (:329) | `:611` | `run_hierarchical_analysis()` | ✅ `hierarchical/orchestrator.py:224` | **cli-selectable** |
| `sherlock_modern` | ✅ (:331) | `:502` | `SherlockModernOrchestrator.investigate()` | ✅ `sherlock_modern_orchestrator.py:48` | **cli-selectable** (undocumented) |
| `legacy` | ✅ (:330) | `:500` | `run_legacy_analysis()` → **hardcoded error** (:256) | ✅ exists but **always raises** | **inert** (dead code) |
| `cluedo` | ❌ not in choices | N/A | scripts + `__main__` | ✅ `cluedo_extended_orchestrator.py` | **script-only** |

### Key Findings

1. **`legacy` is inert**: `run_legacy_analysis()` at `:246` raises a hardcoded
   `"Le mode legacy (AnalysisRunner) a été supprimé"` error every time. It should
   be removed from `choices` or converted to a deprecation stub that redirects to
   `pipeline`.

2. **`sherlock_modern` is undocumented**: Fully functional dispatch with rich output
   formatting (`:507-539`) but absent from `ORCHESTRATION_MODES.md`. Needs a section.

3. **`cluedo` is not CLI-selectable**: Only reachable via `__main__` on
   `cluedo_extended_orchestrator.py` or dedicated example scripts. Adding `--mode cluedo`
   requires wiring `run_cluedo_oracle_game()` into the dispatch table.

4. **4/6 modes are genuinely CLI-selectable**: pipeline, conversational, hierarchical,
   sherlock_modern. The user can already compare these via `--mode`.

---

## 2. Consumer Signatures (Anti-Inerte Contract)

Per the R321 anti-inerte contract, each selectable mode must name its **exact consumer**
— the line that reads `context["mode"]` and dispatches. Currently, the dispatch is in
`run_orchestration.py` via an `if/elif` chain, NOT via a context key. This means:

**Current wiring**: `args.mode` → `if/elif` chain → direct function call
**North-Star wiring** (future): `context["orchestration_mode"]` → factory/registry lookup

### Per-Mode Consumer Signatures

| Mode | Current Dispatch (run_orchestration.py) | Future Consumer Key |
|------|----------------------------------------|---------------------|
| pipeline | `:79` / `:159` calls `run_unified_analysis()` | `context.get("orchestration_mode", "pipeline")` |
| conversational | `:545` calls `run_conversational_analysis()` | same key, value `"conversational"` |
| hierarchical | `:611` calls `run_hierarchical_analysis()` | same key, value `"hierarchical"` |
| sherlock_modern | `:502` calls `orchestrator.investigate()` | same key, value `"sherlock_modern"` |
| cluedo | N/A (script-only) | same key, value `"cluedo"` → needs `run_cluedo_oracle_game()` dispatch |

### Implementation Note

The dispatch chain is already a working `if/elif` on `args.mode`. The north-star
parametric contract requires:
1. Propagating `args.mode` → `context["orchestration_mode"]` (already implicit)
2. Each mode's entry function accepting `**kwargs` / `context` for parametric overrides
3. Tests that call the endpoint with `mode=cluedo` and verify the dispatch reaches the real function

**Point of wiring**: `run_orchestration.py:496` (the `mode` variable derived from `args.mode`)

---

## 3. Gap Analysis — ORCHESTRATION_MODES.md vs Code

| Aspect | Doc says | Code reality | Fix |
|--------|----------|-------------|-----|
| Number of modes | 4 | 6 (incl. sherlock_modern, legacy) | Add sections for both |
| Cluedo "ACTIVE" | Listed as active orchestration mode | Script-only, no `--mode` entry | Add "script-only" qualifier |
| CLI-selectable column | Missing | 4 truly selectable, 1 inert, 1 script-only | Added in #912 update |
| sherlock_modern | Absent | Fully wired dispatch with rich output | Add section §5 |
| legacy | Absent | Listed in `choices` but always errors | Document as deprecated/inert |

---

## 4. Recommendations

### 4.1. Immediate (scoping, this PR)

- ✅ Update `ORCHESTRATION_MODES.md` with CLI-selectable column + 6 modes
- ✅ This spec doc with consumer signatures
- ✅ Open sub-issues for implementation

### 4.2. Implementation (po-2005 argparse lane)

| Issue | Scope | LOC est. | Priority |
|-------|-------|----------|----------|
| `--mode cluedo` | Add `cluedo` to argparse choices + dispatch branch calling `run_cluedo_oracle_game()` | ~30 | Medium |
| Remove `legacy` from choices | Replace with deprecation message or remove entirely | ~5 | Low |
| Document `sherlock_modern` | Add §5 to ORCHESTRATION_MODES.md (already done in scoping update) | ~30 | Low |
| Mode selector test | Test each `--mode` value reaches the correct dispatch function | ~80 | Medium |

### 4.3. API Parity (po-2023 future lane)

Expose `orchestration_mode` on `CustomWorkflowRequest`:
```python
orchestration_mode: Literal["pipeline", "conversational", "hierarchical",
                            "sherlock_modern", "cluedo"] = "pipeline"
```

Consumer: `run_orchestration.py:496` dispatch chain → same key.

---

## 5. Backward Compatibility

- Adding `cluedo` to `--mode` choices: backward-compatible (new value, no default change)
- Removing `legacy` from choices: breaking if someone passes `--mode legacy` (but it errors anyway)
- Default remains `pipeline` — no change

---

## 6. DoD Checklist

- [x] Audit real invocation paths for each orchestrator
- [x] Tag each mode: cli-selectable / script-only / inert
- [x] Reconcile ORCHESTRATION_MODES.md with CLI-selectable column
- [x] Consumer signatures with exact line numbers
- [ ] ≥1 sub-issue opened for po-2025 implementation
- [ ] PR with `## À valider par l'utilisateur`
