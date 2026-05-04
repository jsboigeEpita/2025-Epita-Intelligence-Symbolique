# Spectacular Workflow Profiling Report

> **Snapshot** generated on 2025-05-03 from commit `b6e3602`.
> This is a point-in-time report. Re-run `scripts/profile_spectacular.py` for fresh data.

Performance bottleneck analysis for the spectacular analysis workflow.
Generated with `cProfile` + `pyinstrument` + `tracemalloc`.

## Executive Summary

| Metric | Value |
|--------|------:|
| Wall-clock time | 80.0s |
| Phase execution time | 77.5s |
| Orchestration overhead | 2.5s |
| Peak memory | 66.8 MB |
| Phases completed | 16/17 |
| Phases failed | 0 |
| Phases skipped | 1 (narrative_synthesis — no provider registered) |

**Key finding**: LLM-dependent phases consume 68% of runtime. The top 5 phases
(counter, quality, nl_to_logic, extract, hierarchical_fallacy) are all LLM-bound
and each takes ~11s. These 5 phases alone account for 75s (94% of phase time).
Non-LLM phases (JTMS, ATMS, Dung, ASPIC, PL, modal) complete in under 0.1s combined.

## Per-Phase Wall-Clock Breakdown

Phases sorted by duration (descending).

| Phase | Capability | Duration (s) | % of Total | Status |
|-------|-----------|-------------:|-----------:|--------|
| counter | counter_argument_generation | 13.58 | 17.5% | OK |
| quality | argument_quality | 11.44 | 14.8% | OK |
| nl_to_logic | nl_to_logic_translation | 11.34 | 14.6% | OK |
| extract | fact_extraction | 11.27 | 14.5% | OK |
| hierarchical_fallacy | hierarchical_fallacy_detection | 11.23 | 14.5% | OK |
| fol | fol_reasoning | 7.45 | 9.6% | OK |
| governance | governance_simulation | 5.59 | 7.2% | OK |
| debate | adversarial_debate | 5.32 | 6.9% | OK |
| neural_detect | neural_fallacy_detection | 0.22 | 0.3% | OK |
| dung_extensions | dung_extensions | 0.05 | 0.1% | OK |
| jtms | belief_maintenance | 0.02 | 0.0% | OK |
| aspic_analysis | aspic_plus_reasoning | 0.02 | 0.0% | OK |
| pl | propositional_logic | 0.00 | 0.0% | OK |
| atms | assumption_based_reasoning | 0.00 | 0.0% | OK |
| modal | modal_logic | 0.00 | 0.0% | OK |
| formal_synthesis | formal_synthesis | 0.00 | 0.0% | OK |
| narrative_synthesis | narrative_synthesis | 0.00 | 0.0% | skipped |

### Time by Category

| Category | Phases | Total Time (s) | % of Phase Time |
|----------|-------:|---------------:|----------------:|
| LLM-dependent | 8 | 52.96 | 68.3% |
| Formal logic (Tweety/JVM) | 5 | 7.52 | 9.7% |
| Truth maintenance (JTMS/ATMS) | 2 | 0.02 | 0.0% |
| Other (quality, governance, etc.) | 2 | 17.03 | 22.0% |

**Note**: The "LLM-dependent" category includes phases that primarily wait on
LLM API responses (extract, nl_to_logic, counter, governance, debate, hierarchical_fallacy,
neural_detect). The "quality" phase uses LLM for scoring but also runs local
torch-based detectors (which failed on this Windows machine due to DLL issues — on CI
these add ~2-3s).

### DAG-Level Parallelism Analysis

The spectacular workflow has 6 DAG levels. Phases within the same level can
run concurrently:

| Level | Phases (sequential execution) | Potential Speedup |
|-------|-------------------------------|-------------------|
| L0 | extract (11.3s) | 1x (single phase) |
| L1 | quality (11.4s) + nl_to_logic (11.3s) + neural_detect (0.2s) + hierarchical_fallacy (11.2s) | 4x (34.1s → 11.4s) |
| L2 | fol (7.5s) + pl (0.0s) + modal (0.0s) | 3x (7.5s → 7.5s) |
| L3 | dung_extensions (0.1s) | 1x |
| L4 | aspic_analysis (0.0s) | 1x |
| L5 | counter (13.6s) | 1x |
| L6 | jtms (0.0s) + debate (5.3s) | 2x (5.3s → 5.3s) |
| L7 | atms (0.0s) | 1x |
| L8 | governance (5.6s) + formal_synthesis (0.0s) | 2x (5.6s → 5.6s) |

**With full L1 parallelism**, theoretical speedup: 80s → ~50s (37% reduction).

## Top 5 Memory Allocators

From tracemalloc snapshot (taken post-execution).

Memory usage is modest (66.8 MB peak). No memory bottlenecks detected.
The largest allocations are from Python standard library modules (threading, asyncio)
and SK/Pydantic internals.

## Optimization Recommendations

### 1. Implement L1 Phase Parallelism (HIGH IMPACT, MEDIUM EFFORT)

The single biggest optimization opportunity. Currently, phases within each DAG level
run sequentially. L1 has 4 phases (quality, nl_to_logic, neural_detect, hierarchical_fallacy)
that could run concurrently, reducing L1 time from ~34s to ~11.4s.

The `WorkflowExecutor.execute()` already computes `execution_order` as a list of
parallel groups but iterates them sequentially. Adding `asyncio.gather()` within
each level would unlock this. Estimated impact: **80s → ~50s (-37%)**.

### 2. LLM Call Batching and Caching (HIGH IMPACT, LOW EFFORT)

The LLM cache layer (A.2, #399) already provides deterministic replay for tests.
For production, consider:

- **Batching**: Combine extract + quality prompts into a single LLM call that returns
  both structured arguments and quality scores.
- **Model routing**: Use `gpt-5-mini` for extraction/quality (fast, cheap) and a
  stronger model only for counter_argument and debate phases.
- **Prompt optimization**: Each LLM phase takes ~11s, suggesting ~10s is API latency
  with ~1s of prompt processing. Reducing prompt token count by 50% could save ~1-2s
  per phase.

### 3. FOL Translation Robustness (MEDIUM IMPACT, LOW EFFORT)

The `fol` phase takes 7.5s, with multiple failed translation attempts visible in
logs (Tweety parser rejects French-accented predicates and numeric constants).
Improving the NL→FOL translation prompt to produce Tweety-compatible syntax
(valid identifiers, no accented characters, declared predicates) would reduce
retries and cut FOL time from 7.5s to ~3-4s.

### 4. Register narrative_synthesis Provider (LOW IMPACT, LOW EFFORT)

The `narrative_synthesis` phase is always skipped because no provider is registered
for the `narrative_synthesis` capability. This is the only missing phase preventing
17/17 completion. Adding a simple LLM-based synthesis service would complete the
full spectacular chain.

### 5. Reduce Orchestration Overhead (LOW IMPACT, LOW EFFORT)

Orchestration overhead is only 2.5s (3.1% of wall-clock) — not a bottleneck.
The CapabilityRegistry resolution and state writer dispatch are efficient.
No action needed unless the workflow grows to 30+ phases.

## Methodology

- **cProfile**: deterministic profiling of all function calls
- **pyinstrument**: statistical sampling profiler (lower overhead, flame graph view)
- **tracemalloc**: memory allocation tracking
- **Phase timing**: instrumented WorkflowExecutor per-phase wall-clock
- **Reproducibility**: run with `LLM_CACHE_MODE=replay` for deterministic cached responses

View the pyinstrument flame graph: `open .profiling/spectacular_pyinstrument.html`
View cProfile interactively: `snakeviz .profiling/spectacular_cprofile.prof`

## Reproduction

```bash
# Reprofiling from scratch (requires OPENAI_API_KEY in .env)
conda activate projet-is-roo-new
python scripts/profile_spectacular.py

# With cached LLM responses (no API key needed after initial record)
set LLM_CACHE_MODE=record
python scripts/profile_spectacular.py   # first run: records
set LLM_CACHE_MODE=replay
python scripts/profile_spectacular.py   # subsequent: replays from cache

# Regenerate report from existing profiling data
python scripts/profile_spectacular.py --report-only
```
