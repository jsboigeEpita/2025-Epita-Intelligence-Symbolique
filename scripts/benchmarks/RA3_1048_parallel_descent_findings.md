# RA-3 #1048 item 4 — Parallel vs sequential recursive fallacy descent

**Task**: measure the wall-clock benefit of the `asyncio.gather` fan-out in
`FallacyWorkflowPlugin.run_guided_analysis` (Phase 2 branch exploration), and
use the result to decide the **item 2** question (should recursive descent
fan out further?).

**Harness**: [`bench_parallel_descent.py`](bench_parallel_descent.py). Runs the
**same engine** two ways on the **same input** — `parallel` (engine as-is) vs
`sequential` (`asyncio.gather` swapped for a cap=1 serial shim; the descent is
NOT disabled, only forced serial — anti-pendule #1019). Default mode injects a
fixed-latency LLM stub so each round-trip is a controlled `asyncio.sleep`; the
stub drives the **real** descent structurally (content-independent), so the
parallel/sequential ratio isolates the engine's concurrency structure at $0
token cost and zero dataset-privacy surface. `--mode real` is intentionally
**not wired** — the harness only drives the latency stub, so real mode aborts
loudly rather than emit stub timings under a "real" label (anti-théâtre #1019,
no fabricated numbers). sim is the accepted, primary measurement.

## Results (sim, latency 0.3 s/call, 3 runs median)

| branches | explored | llm_calls | seq (s) | par (s) | ratio |
|---------:|---------:|----------:|--------:|--------:|------:|
| 2        | 2        | 28        | 8.74    | 6.88    | 1.27x |
| 4        | 4        | 39        | 12.20   | 6.89    | 1.77x |
| 8        | 7        | 54        | 16.83   | 6.93    | 2.43x |

Detailed per-run timings are written to the gitignored
`argumentation_analysis/evaluation/results/` (timings + opaque metadata only,
no corpus content).

## Reading the numbers

- **Sequential grows linearly** with branch count (each branch's descent runs
  end-to-end before the next starts): ~8.7 s → 12.2 s → 16.8 s.
- **Parallel is flat at ~6.9 s** regardless of branch count — the branch
  descents overlap inside `gather`, so adding branches adds ~no wall-clock.
- **Speedup scales with branch count**: 1.27x (2) → 1.77x (4) → **2.43x (8)**.
  The **≥2x target is crossed at ~6–7 branches** — i.e. at realistic
  wide-net widths (`MAX_BRANCHES=4`, candidates up to `MAX_CANDIDATES=20`).

### Why parallel is flat (Amdahl floor)

The ~6.9 s parallel floor is **serial work that runs outside the fan-out**:

1. **Phase 1 wide-net** — 1 LLM call (serial in both configs).
2. **Phase 3b beam descent** — up to `BEAM_MAX_LLM_CALLS=15` calls (= ~4.5 s at
   0.3 s/call), run **outside** the `gather` (serial in both configs).

These dominate the parallel wall-clock once Phase 2 is overlapped. The fan-out
already extracts essentially all the available parallel benefit from Phase 2;
the residual cost is the serial Phase 1 + Phase 3b.

## Item 2 decision — should recursive descent fan out further?

Item 2 asked whether descent should fan out *beyond* the existing Phase 2
top-level `asyncio.gather`. There are two distinct further-fan-out levers; the
benchmark + a code read resolve them in opposite directions.

### The gate, read honestly

The ≥2x speedup is **not** met at every width: 1.27x (2 br) and **1.77x (4 br)
are below 2x**; only 2.43x (8 br) clears it. The crossover is ~6–7 branches. So
"≥2x" is *not* a property of the fan-out at small widths — it depends on the
operating point. The decisive fact is **where the engine actually operates**:
Phase 2 fans out over `candidate_pks[:MAX_CANDIDATES]` — **up to 20**, not
`MAX_BRANCHES=4`. At realistic wide-net widths the engine sits *past* the
crossover, so the parallel-flat regime (≥2x) is the normal case, not the
exception. The gate is met at the operating point; it is *not* met universally,
and this doc does not claim otherwise.

### Lever #3 — per-fork sub-branch fan-out — **IMPLEMENTED**

A code read surfaced a **prompt-vs-code mismatch**: the fork prompt's system
message explicitly instructs the LLM to *"PREFER exploring MULTIPLE children
(call explore_branch multiple times)"* — but `_explore_single_branch` kept a
**single** child and silently dropped the rest at every fork. The model was
being asked to surface several promising branches; the engine threw all but one
away. That is a recall leak, not a design choice.

Fixed in `fallacy_workflow_plugin.py`: at a fork the **top child stays the
primary path** (behaviour unchanged for that path) and the next few promising
children are explored as **bounded concurrent recursive sub-branches** whose
confirmed leaves merge back via the same dedup-by-leaf rule. Because this fan-out
rides the same `gather`-overlap mechanism the benchmark measured at the
operating point, the extra branches overlap in wall-clock rather than adding
latency.

The bound is the whole point (anti-pendule #1019 — *not* "parallelize
everything"):

- `SUBBRANCH_FANOUT_WIDTH = 2` — at most 2 extra children spawned per fork.
- `SUBBRANCH_FANOUT_BUDGET = 12` — a shared per-analysis ceiling on total
  sub-branches, consumed via `_BranchSupersessionTracker.try_consume_fanout()`.
- **Supersession pruning** — a sub-branch exploring an ancestor of an
  already-confirmed deeper node abandons early (existing #1048 mechanism).
- **Additive / reversible** — `ENABLE_SUBBRANCH_FANOUT=False`, a zero budget, or
  a `None` results-sink each restore the exact legacy single-path descent. The
  primary path is never regressed; fan-out only *adds* recall.

Tests: `tests/unit/argumentation_analysis/test_subbranch_fanout_1048.py`
(5 tests, $0 mocked LLM) prove a 2-way fork explores both children, the budget
decrements and stops at zero, and a zero budget / no-sink reproduces the legacy
single path.

### Lever #2 — parallelize the beam (Phase 3b) — **NOT NOW**

The remaining serial cost is the **beam descent (Phase 3b)**, the Amdahl floor
(~4.5 s at `BEAM_MAX_LLM_CALLS=15`). Parallelizing it *would* lift the ceiling —
but the beam is **deliberately token-capped** precisely to bound cost. Fanning
it out multiplies concurrent token spend against a cap that exists to prevent
exactly that. Poor ROI. **Lever, if ever needed**: parallelize the beam in
*bounded batches* (e.g. `BEAM_WIDTH` concurrent expansions per depth) so the
token cap is preserved while the depth-serial chain is shortened.

### Anti-pendule

Neither "parallelize everything" nor "the existing parallelism is wrong." The
data + code say: fan out at the fork where the prompt already asked for it and
the operating point makes it free (lever #3, bounded + pruned), and leave the
one intentional token guardrail (the beam, lever #2) alone. RA-3 closes here.
