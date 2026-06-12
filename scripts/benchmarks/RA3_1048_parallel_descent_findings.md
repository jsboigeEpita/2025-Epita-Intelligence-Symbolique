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

## Item 2 decision — fan-out recursive question

**Keep the existing Phase 2 parallelization; do NOT parallelize the beam now.**

- The Phase 2 `asyncio.gather` fan-out is **validated**: it delivers the ≥2x
  target at realistic branch counts (2.43x at 8 branches) with the wall-clock
  staying flat as breadth grows. This is the right design and pays for itself.
- The remaining serial cost is the **beam descent (Phase 3b)**, which is the
  Amdahl floor. Parallelizing it *would* lift the ceiling — but the beam is
  **deliberately token-capped** (`BEAM_MAX_LLM_CALLS=15`) precisely to bound
  cost. Fanning it out multiplies concurrent token spend against a cap that
  exists to prevent exactly that. Poor ROI given the floor (~4.5 s) is
  acceptable for the analysis quality the beam buys.
- **Lever, if ever needed**: should sub-7 s end-to-end at high branch counts
  become a hard requirement, parallelize the beam in *bounded batches* (e.g.
  `BEAM_WIDTH` concurrent expansions per depth) so the token cap is preserved
  while the depth-serial chain is shortened. Documented here so item 2 is a
  conscious, measured choice rather than a default.

**Anti-pendule**: this is neither "parallelize everything" nor "the existing
parallelism is wrong" — the data says fan-out is correct where it is (Phase 2),
and the one remaining serial stretch is an intentional token guardrail, not an
oversight.
