# Design Spec — Track 1: Fallacy-Tier Selector (`--fallacy-tier`)

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `841ed091` (main, post-hierarchical reactivation)
**Effort**: S (1 session)
**Parent**: `docs/architecture/parametric_integration_map.md` (PR #885)

---

## Verdict

**GO** — The codebase already has 6 distinct fallacy detection strategies and partial tier toggling (`FrenchFallacyAdapter` constructor args). The gap is a **single CLI/pipe selector** that maps a user-facing tier name to the correct combination of detectors and pipeline phases. Effort is small because the detectors exist; we only need the routing layer.

---

## 1. Current State

### 1.1 Six Detection Strategies (existing)

| # | Strategy | Type | Location | LLM? |
|---|----------|------|----------|------|
| 1 | FrenchFallacyAdapter (5-tier hybrid) | Neural + Symbolic + LLM | `adapters/french_fallacy_adapter.py` | Optional |
| 2 | FallacyWorkflowPlugin (hierarchical taxonomy) | LLM iterative deepening | `plugins/fallacy_workflow_plugin.py` | Yes |
| 3 | Per-argument parallel detection | LLM parallel | `invoke_callables.py:_invoke_hierarchical_fallacy_per_argument` | Yes |
| 4 | TaxonomySophismDetector | Lexical keyword match | `agents/core/informal/taxonomy_sophism_detector.py` | No |
| 5 | ContextualFallacyDetector | Rule-based contextual | `agents/tools/analysis/new/contextual_fallacy_detector.py` | No |
| 6 | ComplexFallacyAnalyzer | Structural pattern | `agents/tools/analysis/complex_fallacy_analyzer.py` | No |

### 1.2 Current Selection Mechanism

**No centralized selector.** Each detector is instantiated independently:
- Pipeline always runs `_invoke_hierarchical_fallacy` (full LLM-based, strategy 2+3)
- `FrenchFallacyAdapter` has per-tier toggles (`enable_symbolic`, `enable_nli`, etc.) but **is not wired into pipeline phases**
- `AnalysisDepth` enum (`BASIC`/`STANDARD`/`COMPREHENSIVE`/`EXPERT`) exists in `fallacy_family_analyzer.py` but only governs the family analyzer, not other detectors

### 1.3 Gaps

1. No pipeline-level parameter to choose between lightweight vs deep detection
2. `FallacyWorkflowPlugin` constants (`MAX_DEPTH_PER_BRANCH=8`, `MAX_BRANCHES=4`) are hardcoded
3. `AnalysisDepth` enum not propagated to pipeline
4. `FrenchFallacyAdapter` tier toggling is isolated — not wired into pipeline phases

---

## 2. Proposed Design

### 2.1 Tier Definitions

| Tier | Label | Detectors | LLM Calls | Speed | Use Case |
|------|-------|-----------|-----------|-------|----------|
| `taxonomy` | Lexical only | TaxonomySophismDetector (#4) | 0 | Fastest (~ms) | CI/quick-scan, no API key |
| `hybrid` | Neural+Symbolic | FrenchFallacyAdapter (#1, symbolic+NLI tiers) | 0–1 (optional NLI) | Fast (~1s) | Batch analysis, constrained budget |
| `llm` | Full LLM | FallacyWorkflowPlugin (#2) + per-arg (#3) | Multiple (deepening) | Slow (~10–30s) | Deep analysis, production default |
| `full` | All combined | #1 + #2 + #3 + #5 + #6, merged | Yes (max) | Slowest (~30–60s) | Exhaustive audit, benchmarks |

**Default**: `llm` (matches current pipeline behavior — no breaking change).

### 2.2 CLI Integration

```python
# In run_orchestration.py argparse
parser.add_argument(
    "--fallacy-tier",
    type=str,
    choices=["taxonomy", "hybrid", "llm", "full"],
    default="llm",
    help="Fallacy detection depth: taxonomy (lexical, no LLM), "
         "hybrid (neural+symbolic, optional LLM), "
         "llm (full LLM iterative, default), "
         "full (all strategies merged)",
)
```

**Usage examples:**
```bash
# Quick scan without LLM (CI-safe, $0)
python run_orchestration.py --file text.txt --fallacy-tier taxonomy

# Budget-conscious hybrid
python run_orchestration.py --text "..." --fallacy-tier hybrid

# Default (unchanged behavior)
python run_orchestration.py --file text.txt --fallacy-tier llm

# Exhaustive (all detectors)
python run_orchestration.py --file text.txt --fallacy-tier full
```

### 2.3 Pipeline Integration

**Entry point**: `_invoke_hierarchical_fallacy()` in `invoke_callables.py` (line 3680).

Add a tier-dispatch at the top of the function:

```python
async def _invoke_hierarchical_fallacy(input_text, context):
    tier = context.get("fallacy_tier", "llm")

    if tier == "taxonomy":
        return await _invoke_taxonomy_only_fallacy(input_text, context)
    elif tier == "hybrid":
        return await _invoke_hybrid_fallacy(input_text, context)
    elif tier == "full":
        return await _invoke_full_fallacy(input_text, context)
    else:  # "llm" (default, current behavior)
        # ... existing code unchanged ...
```

**New invoke callables needed:**

| Function | What it does |
|----------|-------------|
| `_invoke_taxonomy_only_fallacy()` | Calls `TaxonomySophismDetector.detect_sophisms_from_taxonomy()` — no LLM, no SK kernel |
| `_invoke_hybrid_fallacy()` | Calls `FrenchFallacyAdapter.detect()` with `enable_llm=False, enable_nli=True` — no OpenAI calls |
| `_invoke_full_fallacy()` | Runs LLM pass + hybrid pass + taxonomy pass, merges by `taxonomy_pk`, keeps highest confidence |

**Context propagation**: `run_orchestration.py` passes `--fallacy-tier` value through to the pipeline context dict:
```python
context["fallacy_tier"] = args.fallacy_tier
```

### 2.4 Registry Integration

Register tier-specific capabilities:

```python
# registry_setup.py — add metadata to existing entry
registry.register_service(
    name="fallacy_detection",
    capabilities=[
        "fallacy_detection_taxonomy",    # NEW
        "fallacy_detection_hybrid",      # NEW
        "fallacy_detection_llm",         # existing
        "fallacy_detection_full",        # NEW
    ],
    metadata={"default_tier": "llm", "available_tiers": ["taxonomy", "hybrid", "llm", "full"]},
)
```

### 2.5 API Integration

Add `fallacy_tier` query parameter to the analysis endpoint:

```python
# api/agents.py or similar
@router.post("/api/v1/agents/full-analysis")
async def full_analysis(
    text: str,
    workflow: str = "standard",
    fallacy_tier: str = Query("llm", regex="^(taxonomy|hybrid|llm|full)$"),
):
    context = {"fallacy_tier": fallacy_tier}
    ...
```

---

## 3. Implementation Plan

| Step | File | Change | LOC |
|------|------|--------|-----|
| 1 | `run_orchestration.py` | Add `--fallacy-tier` argument + context propagation | ~10 |
| 2 | `invoke_callables.py` | Add tier dispatch in `_invoke_hierarchical_fallacy` | ~15 |
| 3 | `invoke_callables.py` | Add `_invoke_taxonomy_only_fallacy()` | ~25 |
| 4 | `invoke_callables.py` | Add `_invoke_hybrid_fallacy()` | ~30 |
| 5 | `invoke_callables.py` | Add `_invoke_full_fallacy()` (merge wrapper) | ~40 |
| 6 | `registry_setup.py` | Add tier capabilities metadata | ~5 |
| 7 | `api/` | Add `fallacy_tier` parameter to analysis endpoint | ~5 |
| 8 | Tests | Unit tests for tier dispatch + integration test taxonomy-only | ~80 |
| **Total** | | | **~210 LOC** |

---

## 4. Testing Plan

| Test | What | API Key? |
|------|------|----------|
| `test_fallacy_tier_taxonomy` | TaxonomySophismDetector produces results without LLM | No |
| `test_fallacy_tier_hybrid` | FrenchFallacyAdapter with LLM disabled | No (NLI optional) |
| `test_fallacy_tier_llm_default` | Existing behavior unchanged (default tier) | Yes |
| `test_fallacy_tier_full_merge` | Merged results deduped by taxonomy_pk | Yes |
| `test_fallacy_tier_cli_flag` | `--fallacy-tier taxonomy` parsed and propagated | No |
| `test_fallacy_tier_invalid` | Invalid tier → argparse error | No |

---

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Taxonomy-only misses most fallacies | Expected | Document as "quick-scan" — users choose depth explicitly |
| Hybrid tier needs NLI model download | Low | NLI is optional; falls back to symbolic-only |
| `full` tier doubles LLM cost | Expected | Default is `llm`; `full` is opt-in |
| Breaking change if default changes | None | Default stays `llm` (identical to current behavior) |

---

## 6. DoD

- [ ] `--fallacy-tier` CLI argument with 4 choices
- [ ] Pipeline dispatches to correct detector(s) per tier
- [ ] `taxonomy` tier works without API key (CI-safe)
- [ ] `llm` tier (default) produces identical results to current pipeline
- [ ] Registry metadata includes available tiers
- [ ] API endpoint accepts `fallacy_tier` parameter
- [ ] 6+ tests passing
- [ ] `## À valider par l'utilisateur`: Default tier choice (llm vs hybrid)

---

## À valider par l'utilisateur

1. **Default tier**: The design preserves `llm` as default (no change). Should `hybrid` be the default instead (cheaper, still good coverage)?
2. **Tier names**: `taxonomy` / `hybrid` / `llm` / `full` — are these intuitive enough, or prefer `light` / `standard` / `deep` / `exhaustive`?
