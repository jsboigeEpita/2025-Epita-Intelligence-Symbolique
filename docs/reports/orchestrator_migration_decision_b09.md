# B-09: Pre-CapabilityRegistry Orchestrator Migration Decision

**Track**: B-09 #799 (Epic B #743)
**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Scope**: 4 pre-Registry orchestrators + 31 tests

---

## Executive Summary

Of the 4 pre-CapabilityRegistry orchestrators evaluated, only `CluedoExtendedOrchestrator` is actively used in production. The other 3 are deprecated shims or dormant stubs whose callers have been migrated to `UnifiedPipeline` + `CapabilityRegistry`. The recommendation is: **archive 3, keep 1, no migration needed**.

---

## Orchestrator Status

### 1. RealLLMOrchestrator — ARCHIVE

| Field | Value |
|-------|-------|
| **Source** | `argumentation_analysis/orchestration/real_llm_orchestrator.py` (125 LOC shim) |
| **Status** | DEPRECATED — Sprint 13 batch 1-3 cleanup (#735-#740) |
| **Production** | Dormant — 3 callers (`service_manager.py`, `main_orchestrator.py`, `unified_pipeline.py`) instantiate dead shims that raise `NotImplementedError` |
| **Registry replacement** | `UnifiedPipeline` with `WorkflowDSL` + `CapabilityRegistry` |
| **Tests** | 4 xfail (strict=True) in `test_unified_orchestrations.py` |

**Decision**: All callers should be replaced with `UnifiedPipeline`. The shim provides zero functional value (deprecation warning + NotImplementedError). Sprint 13.C proposal has the migration plan. Archive after caller migration.

---

### 2. ConversationOrchestrator — ARCHIVE

| Field | Value |
|-------|-------|
| **Source** | `argumentation_analysis/orchestration/conversation_orchestrator.py` (1045 LOC) |
| **Status** | DORMANT — explicit `DeprecationWarning` on `run_orchestration()` |
| **Production** | Dormant — `service_manager.py` initializes but never calls; `unified_pipeline.py` has legacy path |
| **Registry replacement** | 8-agent SK system (`AgentGroupChat` with PM, Extract, Informal, Formal, Quality, Debate, Counter, Governance) |
| **Tests** | 17 tests in `test_unified_orchestrations.py`, 2 in `test_specialized_orchestrators.py` |

**Decision**: The `real` mode uses new agents but the `demo`/`trace`/`enhanced`/`micro` modes use `SimulatedAgent` classes that are pre-CapabilityRegistry. The 8-agent SK system supersedes all modes. Archive after migrating the ~5 callers to the new system.

---

### 3. CluedoOrchestrator (base, 2-agent) — ARCHIVE

| Field | Value |
|-------|-------|
| **Source** | `argumentation_analysis/orchestration/cluedo_orchestrator.py` (489 LOC) |
| **Status** | DORMANT — explicit `DeprecationWarning` on `run_cluedo_game()` |
| **Production** | Superseded by `CluedoExtendedOrchestrator` (3-agent + Oracle) |
| **Registry replacement** | No — Cluedo is a unique workflow mode, not a capability pipeline |
| **Tests** | 2 tests in `test_specialized_orchestrators.py` (import ExtendedOrchestrator aliased as CluedoOrchestrator) |

**Decision**: The base 2-agent version is fully superseded by the 3-agent ExtendedOrchestrator which is actively used (`ORCHESTRATION_MODES.md` lists Cluedo as ACTIVE). The `service_manager.py` already aliases `CluedoExtendedOrchestrator as CluedoOrchestrator`. Archive the base class.

### 3b. CluedoExtendedOrchestrator (3-agent) — KEEP

| Field | Value |
|-------|-------|
| **Source** | `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py` |
| **Status** | ACTIVE |
| **Production** | Active — CLI (`--mode cluedo`), `service_manager.py`, `main_orchestrator.py` |
| **Registry replacement** | Not applicable — unique investigation workflow |

**Decision**: Keep as-is. No migration needed.

---

### 4. LogiqueComplexeOrchestrator — REMOVE

| Field | Value |
|-------|-------|
| **Source** | `argumentation_analysis/orchestration/logique_complexe_orchestrator.py` (109 LOC stub) |
| **Status** | DEPRECATED — minimal stub, `DeprecationWarning` on `__init__` |
| **Production** | Dormant — `run_einstein_puzzle()` does `await asyncio.sleep(0.01)` and returns hardcoded mock |
| **Registry replacement** | `FOLLogicAgent` + `TweetyLogicPlugin` via CapabilityRegistry |
| **Tests** | 2 tests in `test_specialized_orchestrators.py` (mocked initialization only) |

**Decision**: Remove entirely. The class is a stub with zero functional value. All production callers have `ImportError` guards. The einstein puzzle mode is absorbed into formal verification workflows.

---

## Test File Disposition

| Test File | Tests | Recommendation |
|-----------|-------|----------------|
| `test_unified_orchestrations.py` | 23 | Skip ConversationOrchestrator demo tests (17) + remove RealLLM xfail tests (4) + keep authentic integration (3, skipif) |
| `test_specialized_orchestrators.py` | 8 | Skip Cluedo (2, tests alias) + ConversationOrchestrator (2) + LogiqueComplexe (2) + integration (2) |

---

## Action Items (ordered by priority)

| # | Action | Issue | Priority |
|---|--------|-------|----------|
| 1 | Remove `LogiqueComplexeOrchestrator` shim + wrapper + callers | NEW | MEDIUM |
| 2 | Skip `test_specialized_orchestrators.py` (8 tests, all pre-Lego) | NEW | LOW |
| 3 | Skip ConversationOrchestrator tests in `test_unified_orchestrations.py` (17 tests) | NEW | LOW |
| 4 | Migrate `RealLLMOrchestrator` callers → `UnifiedPipeline` (Sprint 13.C) | SPRINT-13C | MEDIUM |
| 5 | Archive base `CluedoOrchestrator` (2-agent) after ExtendedOrchestrator is sole import | NEW | LOW |
| 6 | Archive `ConversationOrchestrator` after caller migration | NEW | LOW |

---

## Conclusion

**No immediate migration required.** The pre-Registry orchestrators are already dormant (shims, stubs, deprecated warnings). The active system uses `UnifiedPipeline` + `CapabilityRegistry` for pipeline analysis and `CluedoExtendedOrchestrator` for the investigation game. The recommended approach is progressive cleanup during Sprint 13.C + follow-up, not a dedicated migration sprint.
