# Audit A-09: Qualite Argumentative

**Issue**: #35 | **SUIVI**: Score 90% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project `2.3.5_argument_quality/` delivered an argument quality evaluation system based on 9 rhetorical "virtues" (criteria). The system evaluates arguments against each virtue and produces both individual scores and an aggregate quality assessment. The design follows a detector-per-virtue pattern where each virtue is an independent evaluator that can be called individually or composed.

Original 9 virtues: clarte, pertinence, presence_sources, refutation_constructive, structure_logique, analogie_pertinente, fiabilite_sources, exhaustivite, redondance_faible.

## What exists in argumentation_analysis/

### Core evaluator

- **`agents/core/quality/quality_evaluator.py`** — `ArgumentQualityEvaluator` class implementing all 9 virtue detectors:
  1. `clarte` (clarity)
  2. `pertinence` (relevance)
  3. `presence_sources` (source presence)
  4. `refutation_constructive` (constructive refutation)
  5. `structure_logique` (logical structure)
  6. `analogie_pertinente` (pertinent analogy)
  7. `fiabilite_sources` (source reliability)
  8. `exhaustivite` (exhaustiveness)
  9. `redondance_faible` (low redundancy)

### Semantic Kernel plugin

- **`plugins/quality_scoring_plugin.py`** — `QualityScoringPlugin` with **4** `@kernel_function` methods (not 3 as documented in CLAUDE.md):
  - `evaluate_argument_quality` — full quality evaluation
  - `get_quality_score` — single-score convenience method
  - `evaluate_with_cross_kb_context` — evaluation enriched with cross-knowledge-base context
  - `list_virtues` — enumerate available virtue detectors

### Registration

- **`agents/core/quality/__init__.py`** — `register_with_capability_registry()` function for Lego Architecture integration.
- **`core/capability_registry.py` / `registry_setup.py:107-124`** — `quality_evaluator` agent registered in the `CapabilityRegistry` with proper capability declarations.

### Tests

- Unit tests cover individual virtue detectors, aggregate scoring, and plugin wiring.

## Preservation Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| 9 virtues | **1:1 preserved** | All 9 detectors match student originals by name and function |
| Evaluation logic | **Preserved + improved** | Graceful degradation added (student original threw on missing data) |
| Resource files | **Byte-identical** | YAML/JSON resources unchanged from student source |
| Plugin surface | **Expanded** | 4 kernel functions vs student's direct-call pattern |
| Registry integration | **New** | Lego Architecture registration added during integration |

All 9 virtues are preserved 1:1. Resource files are byte-identical. The integrated version improves on the student original with graceful degradation (handles missing or malformed input without raising) and adds Semantic Kernel `@kernel_function` decorators for Lego Architecture compatibility.

## Gap Analysis

No significant gaps. The integration is faithful to the student deliverable and adds only infrastructure wiring required by the capability registry pattern.

Minor documentation drift: CLAUDE.md states "3 `@kernel_function` methods" but the actual count is 4 (`list_virtues` is the undocumented fourth).

## Recommended Action

1. **Fix CLAUDE.md** — Update `quality_scoring_plugin.py` description from "3" to "4 `@kernel_function` methods" to match reality.
2. No code changes needed — integration is complete and functional.

## Source Files

| File | Role |
|------|------|
| `argumentation_analysis/agents/core/quality/quality_evaluator.py` | Core evaluator with 9 virtue detectors |
| `argumentation_analysis/agents/core/quality/__init__.py` | Registry registration |
| `argumentation_analysis/plugins/quality_scoring_plugin.py` | SK plugin (4 @kernel_function) |
| `argumentation_analysis/core/capability_registry.py` | Lego Architecture registry |
| `2.3.5_argument_quality/` | Student project source (reference) |
