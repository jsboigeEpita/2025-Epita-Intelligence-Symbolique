# SCDA InformalAgent Taxonomy Injection — Report

**Date:** 2026-05-18
**Issue:** #600
**Branch:** `feat/informal-taxonomy-injection-600`
**Status:** DoD MET (unit tests + backward compat + multilingual support)

## Problem

Multi-corpus baseline (`762461a3`) revealed a **cascade bottleneck**: corpus B (German, ~50K chars) detected 0 fallacies despite 6 extracted arguments. Without typed fallacies, the JTMS retraction and Belief Revision formal layers never activate. Fallacy detection is the primary lever for closing Epic #530 on all 3 corpora.

**Root cause analysis:**

| Cause | Detail |
|-------|--------|
| No systematic family traversal | InformalAgent uses single-pass LLM-driven exploration — no code-level iteration through all 7 families |
| No German keyword support | `_map_fallacy_to_root_pk` had FR/EN patterns only — German fallacy names couldn't map to taxonomy PKs |
| Parent harness conditional | Tier 3 parent harness (`_invoke_hierarchical_fallacy_per_argument`) was registered but never automatically invoked after Detection phase |

## Solution

3 complementary interventions:

### Intervention 1: Per-family explicit injection

Modified `INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE` in `informal_definitions.py` to include:

1. **Systematic 7-family enumeration** — all 7 families listed with FR/EN names, descriptions, and examples
2. **Mandatory traversal process** — step-by-step instructions to call `list_fallacies_in_category` for each family
3. **Multilingual guidance** — explicit instruction to translate non-FR/EN text to English before taxonomy comparison

### Intervention 2: German keyword bridge

Added a `_DE_TO_EN_KEYWORDS` mapping (30+ entries) to `FallacyWorkflowPlugin` that bridges German fallacy names to English equivalents. The `_map_fallacy_to_root_pk` function now has a 3-pass strategy:

1. **Direct lookup** — exact match in roots_index
2. **German bridge** — DE keyword → EN keyword → roots_index lookup
3. **Pattern fuzzy matching** — existing FR/EN/DE substring patterns

### Intervention 3: Parent harness systematization

Added `_run_parent_harness_fallback()` function in `conversational_orchestrator.py` that:

- Automatically fires after the Detection phase when text > 5000 chars
- Invokes `_invoke_hierarchical_fallacy_per_argument` from `invoke_callables.py`
- Registers any new fallacies found into the shared state
- Falls back silently on ImportError or API unavailability
- Logs telemetry with `type: "parent_harness"`

## Implementation

### Files changed

| File | Change |
|------|--------|
| `argumentation_analysis/agents/core/informal/informal_definitions.py` | +30 lines: systematic 7-family enumeration, multilingual guidance in INFORMAL_AGENT_INSTRUCTIONS |
| `argumentation_analysis/plugins/fallacy_workflow_plugin.py` | +50 lines: `_DE_TO_EN_KEYWORDS` mapping, 3-pass strategy in `_map_fallacy_to_root_pk` |
| `argumentation_analysis/orchestration/conversational_orchestrator.py` | +70 lines: `_run_parent_harness_fallback()` function, auto-fire hook after Detection phase |
| `tests/unit/argumentation_analysis/orchestration/test_informal_taxonomy_injection_600.py` | NEW: 22 unit tests across 4 test classes |

### Test results

| Suite | Result |
|-------|--------|
| Unit (taxonomy injection #600) | **22 passed** |
| Unit (growth hook #597) | 14 passed (unchanged) |
| Unit (conversational orchestrator) | 36 passed, 3 pre-existing failures (AGENT_SPECIALITY_MAP) |
| Regression check | 0 new failures |

### Test classes

1. **TestInformalAgentInstructions** (5 tests) — verifies 7-family enumeration, EN names, systematic traversal section, multilingual guidance, preserved Gold Rule
2. **TestGermanKeywordCoverage** (11 tests) — verifies German keyword matching for 8 fallacy types, French/English backward compat
3. **TestParentHarnessFallback** (4 tests) — verifies no-fallacies, registration, ImportError handling, generic error handling
4. **TestTaxonomyFamilyCoverage** (3 tests) — verifies 7 families in CSV, required columns, no DE language columns yet

## Architecture

```
Detection Phase (Extraction & Detection)
├── InformalAgent
│   ├── Systematic 7-family traversal (NEW)
│   │   ├── list_fallacies_in_category("Insuffisance")
│   │   ├── list_fallacies_in_category("Influence")
│   │   ├── ... (5 more families)
│   │   └── Multilingual: translate DE→EN before compare
│   └── explore_fallacy_hierarchy → get_fallacy_details → add_identified_fallacy
│
├── Parent harness auto-fire (NEW)
│   ├── Triggered when text > 5000 chars AND phase contains "etection"
│   ├── _invoke_hierarchical_fallacy_per_argument
│   │   ├── _extract_arguments_for_parallel (from state)
│   │   └── asyncio.gather (per-argument FallacyWorkflowPlugin)
│   └── Register new fallacies into state
│
└── FallacyWorkflowPlugin
    ├── _wide_net_candidates → DE keywords bridge (NEW)
    │   └── _DE_TO_EN_KEYWORDS: 30+ DE→EN mappings
    └── _map_fallacy_to_root_pk (3-pass strategy)
        ├── Pass 1: Direct lookup
        ├── Pass 2: German → English bridge (NEW)
        └── Pass 3: Pattern fuzzy matching (FR/EN/DE)
```

## DoD Checklist

- [x] Per-family explicit injection in InformalAgent instructions
- [x] German keyword coverage for common fallacy types
- [x] Parent harness systematization (always-on for dense corpora)
- [x] Unit tests for taxonomy traversal coverage (22 tests, 7 families)
- [x] Backward compat: existing FR/EN keywords still work
- [x] Report: this document

## Note on sequencing with Track I (#601)

As the coordinator noted, po-2025's Track I (#601) re-runs multi-corpus with the growth hook from #597. If the growth hook alone closes the fallacy gap, the prompt-level changes (Intervention 1) become defense-in-depth. The German keyword bridge (Intervention 2) and parent harness systematization (Intervention 3) are infrastructure improvements regardless.
