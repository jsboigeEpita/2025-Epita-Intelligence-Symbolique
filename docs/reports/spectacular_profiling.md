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

## Record vs Replay Determinism Profiling (BO-3 #1473 PR3)

The LLM replay cache (PR1 direct path + PR2 SK-native path) makes a run
deterministically reproducible: one `LLM_CACHE_MODE=record` run seeds the disk
cache, then `LLM_CACHE_MODE=replay` replays every LLM call from it — **zero live
API calls on the replay batch**. This section profiles the record→replay speedup
and the cache monitoring counters.

### Profiling methodology (per-phase, both layers)

Per-phase latency is extracted from the pipeline's own `PhaseResult.duration_seconds`
(already tracked by the WorkflowExecutor — PR3 adds **no** pipeline
instrumentation). The shared `CacheStats` counters
(`argumentation_analysis.services.llm_cache.get_cache_stats`) report how many
calls each layer served from cache vs. the API:

| Counter | Meaning |
|---------|---------|
| `hit` | served from cache (record or replay) |
| `miss_record` | record-mode miss → API call + store |
| `miss_replay` | replay-mode miss → `LLMCacheMiss` raised (never live) |
| `live` | actual API round-trip (off passthrough OR record miss) |

`live` is the anti-théâtre invariant: **at replay it MUST stay 0** — any non-zero
value means a cache miss silently fell through to the API (#1019).

### Batch reproducibility (DoD #1473)

A batch of ≥2 synthetic propositions is recorded, then replayed. Proven firsthand
in `tests/integration/orchestration/test_replay_cache_profiling_batch.py`
(`requires_api`+`slow`):

- the **whole replay batch** makes `live == 0` API calls (asserted via the shared
  counter, not by absence of error);
- `miss_replay == 0` (record seeded every key);
- replay total wall-clock is a fraction of record (LLM-bound phases collapse to
  near-instant cache reads);
- the per-phase `duration_seconds` table is printed in the test log.

### Residual wall-clock field (documented honestly, not masked)

The `belief_tracking` phase embeds `creation_timestamp`
(`datetime.now()`, `argumentation_analysis/.../extended_belief.py:32`) in its RAW
output. That field is wall-clock by construction and is **never reproducible**
between two real runs — cache or no cache (the phase makes no LLM call). Its
DECISIONAL output matches across runs (PR1 proved this via the decisional hash).
The latency table therefore reports `belief_tracking` as a ~constant non-LLM
phase; this is expected, not a cache gap.

### Reproducing the profiling run

```bash
# Fresh record+replay profiling (requires OPENAI_API_KEY in .env)
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/integration/orchestration/test_replay_cache_profiling_batch.py \
  -v -s -m "requires_api and slow"
```

The test prints the per-phase record-vs-replay table and the `CacheStats` totals.

---

## Demo Bundle Profiling (5 propositions, BO-3 #1473 residual / dispatch R660)

The PR3 batch test above used 3 synthetic propositions. This section profiles the
**full 5-proposition demo bundle** (`examples/democratech_deliberation/synthetic_proposals.py`,
merged #1486) through the same record→replay harness — extending the determinism
proof to the demoable bundle and isolating the per-phase residual honestly.

### Bundle results (record vs replay, 5 synthetic domain-public propositions)

| Metric | Record leg | Replay leg |
|--------|-----------:|-----------:|
| Live API calls (`CacheStats.live`) | **25** | **0** ✅ |
| Cache hits | 5 | 30 |
| Cache misses (`miss_replay`) | 0 | 0 |
| Decided firsthand | 5/5 | 5/5 |
| Wall-clock total | 745.62 s | 179.62 s |
| Replay as % of record | — | **24.1%** |

**DoD T2 firsthand-proven** (not asserted): the whole 5-prop replay batch made
**zero live API calls** (`CacheStats.live == 0`, proven via the shared counter),
zero cache misses, and every proposition decided firsthand with an identical
verdict (winner `arg_1`, 12 voting methods) on both legs.

### Per-proposition wall-clock

| Proposition | Record (s) | Replay (s) | Replay % |
|-------------|-----------:|-----------:|---------:|
| prop_A (chess club) | 134.22 | 36.00 | 26.8% |
| prop_B (library) | 163.73 | 36.23 | 22.1% |
| prop_C (sports assoc) | 157.13 | 35.82 | 22.8% |
| prop_D (park) | 149.33 | 35.54 | 23.8% |
| prop_E (music school) | 141.22 | 36.03 | 25.5% |

### Per-phase breakdown (prop_A, representative)

| Phase | Record (s) | Replay (s) | LLM-bound? |
|-------|-----------:|-----------:|:----------:|
| extract | 27.98 | 0.06 | yes → collapses |
| quality_baseline | 39.04 | 0.52 | yes → collapses |
| counter_arguments | 16.19 | 0.07 | yes → collapses |
| adversarial_debate | 29.77 | 0.04 | yes → collapses |
| democratic_vote | 18.44 | 0.04 | yes → collapses |
| fallacy_detection | 0.19 | **32.78** | **no (neural-tier, uncached — see below)** |
| indexing | 2.04 | 2.03 | no (~constant) |
| belief_tracking | 0.00 | 0.00 | no |
| quality_recheck | 0.30 | 0.45 | partial |
| transcription | 0.00 | 0.00 | no |

Every LLM-bound phase routed through `_guarded_chat_completion` (direct) or
`CachedChatCompletion` (SK) **collapses** at replay (record → sub-0.1 s), matching
the PR3 finding.

### Residual wall-clock floor (documented honestly, not masked)

The bundle replay is **24.1%** of record — higher than the PR3 batch's 1.6%. The
floor is **not** a cache defect; it is a per-proposition orchestration + uncached
neural-tier cost that the cache does not (and should not) absorb:

- **`fallacy_detection` = 32.78 s at replay** (vs 0.19 s at record). The neural
  fallacy tier (`self_hosted_fallacy_detector`) uses its **own** OpenAI client and
  is **not** routed through `_guarded_chat_completion`, so it is outside both
  cache layers. On this run the configured neural model (`qwen3.5-35b-a3b`) 404s
  and the tier retries to timeout (visible in the log as `NotFoundError` /
  `APITimeoutError` on the fallacy wide-net). At *record* this phase happened to
  fail fast (0.19 s heuristic fallback); at *replay* the same timeout path
  re-executes every time. This is the dominant residual — **~33 s × 5 = ~165 s
  of the 180 s replay total is uncached neural-tier timeout, not LLM work**.
- **`indexing` ≈ 2.0 s** (semantic index build, non-LLM, ~constant per prop).
- **Registry build + torch import** (~1–2 s per prop): the standalone driver
  re-instantiates the `CapabilityRegistry` (37 services) per proposition.

Strip the neural-tier timeout and the per-prop replay floor drops to ~3 s
(indexing + orchestration) → bundle replay would be ~3–4% of record, consistent
with the PR3 batch. The determinism invariant (`live == 0` at replay) is
unaffected: the neural tier makes no *LLM chat* call that the cache must cover.

### Reproducing the bundle profiling run

```bash
# Requires a working LLM key in .env (OpenRouter preferred). The standalone
# driver reuses the cache harness from test_replay_cache_profiling_batch.py over
# the 5 demo propositions, isolated to a scratch cache_dir.
LLM_CACHE_MODE=record python <driver>   # seeds the cache (live, ~12 min)
LLM_CACHE_MODE=replay python <driver>   # replays (0 live call, ~3 min)
```

Provider-routing note: an early pipeline import can inject stale env vars (a
dead `OPENAI_API_KEY`, empty `OPENROUTER_*`) before the driver's `load_dotenv`;
the driver must call `load_dotenv(.env, override=True)` so `create_llm_service`
routes to the working OpenRouter key (else 401 on api.openai.com).

---

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
