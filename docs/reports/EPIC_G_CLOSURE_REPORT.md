# Epic G — Closure Report: Liberation Lego

**Date**: 2026-05-14
**Status**: COMPLETE (14/14 issues, 16 PRs merged)
**Main commit**: `68aa1e29`

## Summary

Epic G restored the **Text → KB → Tweety → KB → NL** chain by wiring dormant Semantic Kernel plugins into active kernels, adding 11 new `@kernel_function` methods, enabling auto function calling, hardening iterative deepening, and building the full formal analysis pipeline with external solvers.

## Root Cause

Since commit `b0ab2941` (PR #91, March 2026), the project maintained two parallel paths:
1. **Callable path** (`_invoke_*`): canonized, locked at `f78fa383`
2. **Plugin path** (`@kernel_function`): declared in registry but **never wired via `kernel.add_plugin()`**

22 `@kernel_function` Tweety methods sat inert. 15+ state `add_*` methods were unexposed. The Lego architecture was documented but not operational.

## Deliverables

### Workstream A — SK Reliability + State Liberation (po-2025, 6 issues)

| Issue | Description | PR | Tests Added |
|-------|-------------|-----|-------------|
| G.6 #473 | Rename ATMS capability to `atms_reasoning` | #482 | 2 (duality invariant) |
| G.5 #472 | Capability duality invariant test | #482 | 4 |
| G.1 #468 | Wire 5 SK plugins into factory registry | #483 | 30 |
| G.2 #469 | 11 new `@kernel_function` on StateManagerPlugin (18→29) | #483 | — |
| G.3 #470 | `enable_auto_function_calling=True` by default | #483 | — |
| G.4 #471 | Hardened iterative deepening + extracted `IterativeDeepeningOrchestrator` | #483 | 7 |
| #459 | FOL N-to-1 sanitization collision fix | #483 | 4 |

### Workstream B — Formal Chain + External Tools (po-2023, 8 issues)

| Issue | Description | PR | Tests Added |
|-------|-------------|-----|-------------|
| G.11 #478 | Dung 11 semantics via `analyze_multi_semantics` | #484 | — |
| G.13 #480 | `formal_extended` workflow (15 phases) + spectacular MVP | #490 | 24 |
| G.14 #481 | Pre/post baseline comparison tools | #491 | — |
| G.10 #477 | LogicAgentPlugin with real FOL/Modal validation | #492 | 31 |
| G.12 #479 | External solvers: ASP/Clingo + EProver/Prover9/SPASS routing | #495 | 19 |
| G.9 #476 | TweetyResultInterpretationPlugin (formal → NL) | #499 | 46 |
| G.7 #474 | TextToKBPlugin (NL → KB extraction) | #500 | 57 |
| G.8 #475 | KBToTweetyPlugin (KB → Tweety formulas) | #500 | — |

### Epic E — Hardening (po-2025, 4 issues)

| Issue | Description | PR | Tests Added |
|-------|-------------|-----|-------------|
| E.1 #451 | Pipeline checkpoint/resume for batch runs | #466 | 17 |
| E.3 #453 | OpenAPI contract snapshot + 6 CI smoke tests | #496 | 6 |
| E.2 #452 | Multi-model benchmark script | #497 | — |
| E.4 #454 | Structured logging with correlation IDs | #498 | 12 |

## Metrics

| Metric | Before Epic G | After Epic G |
|--------|--------------|-------------|
| Active `@kernel_function` (StateManager) | 18 | 29 |
| Plugins wired in factory registry | 8 | 13 |
| Tweety semantics in `_invoke_dung_extensions` | 2 | 11 |
| External solvers routed | 0 | 3+ (ASP/EProver/Prover9/SPASS) |
| Workflow phases (spectacular) | 8 | 11+ |
| Workflow phases (formal_extended) | 0 | 15 |
| Correlation ID in logs | No | Yes (structured JSON) |
| API contract protection | No | Yes (6 snapshot tests) |
| Tests added (Epic G + E) | — | ~260 |

## Key Architecture Changes

1. **Plugin Registry Expansion** (`factory.py`): 5 new entries (ranking, aspic, belief_revision, narrative_synthesis, toulmin) + `AGENT_SPECIALITY_MAP` covering all 10 agent types
2. **Auto Function Calling**: `FunctionChoiceBehavior.Auto(auto_invoke=True)` enabled by default on all agents
3. **IterativeDeepeningOrchestrator**: Extracted reusable pattern with `TaxonomyLike`/`LeafConfirmer` protocols, 30s timeout on all LLM calls
4. **FOL Sanitization**: Collision detection with `_v2`/`_v3` disambiguation suffixes for distinct surface forms that collapse to same ASCII name
5. **Structured Logging**: `PhaseLogger` adapter with `correlation_id` + `phase_name` propagation, JSON/human output via `LOG_FORMAT` env var
6. **Formal Pipeline**: Complete chain TextToKB → KBToTweety → Tweety execution → TweetyResultInterpretation → state writing

## Lessons Learned

1. **Registry ≠ Runtime**: Having plugins in a registry is necessary but insufficient — they must be wired into active kernels via `kernel.add_plugin()`. The duality invariant test (#472) prevents future drift.
2. **Stack Hygiene**: Stacked PRs that share files (especially `factory.py`, `registry_setup.py`) create merge conflicts. Clean independent branches from main are worth the extra effort.
3. **1 Issue = 1 PR**: Bundling 5 issues into PR #483 worked because commits were atomic and logically dependent, but it made review harder. The coordinator accepted it as an exception.
4. **DLL Load Order**: Windows `WinError 182` requires torch/transformers loaded before jpype. Scripts that mock jpype must also handle the spacy → thinc → torch import chain.
5. **No-Op Validators**: `validate_formula` that always returns `is_valid:True` is worse than no validator — it masks real errors. Real validation (Tweety `check_consistency`) is essential.

## Workers Performance

| Worker | Issues | PRs | Tests Added |
|--------|--------|-----|-------------|
| po-2025 | 10 (G.1-G.6 + E.1-E.4 + #459) | 6 | ~76 |
| po-2023 | 8 (G.7-G.14) | 8 (3 reworked) | ~177 |

## Post-Epic G Validation

Baseline comparison (pre/post) on 3 opaque documents pending po-2023 execution. The tooling (#481) is merged and ready.

---

*Report by po-2025 (Claude Code @ myia-po-2025) — 2026-05-14*
