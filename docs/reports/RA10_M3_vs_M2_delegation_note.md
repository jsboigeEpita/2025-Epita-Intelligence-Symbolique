<!--
PROVENANCE (Cleanup Gate / global CLAUDE.md "Consolider != Archiver")
  Role:        report / design — comparison note for a deactivation-reversal restore
  Origin:      RA-10 #1069 (ORC-2) — "Restore hierarchical 3-tier delegation as a
               comparable, selectable orchestration axis"
  Restores:    the dormant strategic→tactical→operational chain (M3), NOT a new design
  Base:        58d1fcba
  Author:      Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
  Date:        2026-06-12
  Privacy:     opaque corpus IDs only; no raw_text / author / title (dataset discipline)
-->

# RA-10 #1069 — M3 (true 3-tier delegation) vs M2 (bridge/DAG): comparison note

## 0. TL;DR

`--mode hierarchical` now exposes **two comparable, selectable axes** via
`--hierarchical-mode {bridge,delegation}` (default `bridge`, backward-compatible):

| Axis | Flag | Control flow | Objective source | Degraded behavior |
|------|------|--------------|------------------|-------------------|
| **M2** (shipped) | `--hierarchical-mode bridge` | Strategic objectives → `objectives_to_workflow` → `WorkflowExecutor` (Lego/DAG) | LLM if kernel, else hardcoded 4-objective fallback injected at `orchestrator.py:102-128` | Silently substitutes 4 default objectives |
| **M3** (restored, RA-10) | `--hierarchical-mode delegation` | Explicit S→T→O sequential calls through the 3 tiers | LLM if kernel, else RA-4 `_fallback_objectives()` tagged `source="degraded"` | **Fails loud** (`DelegationError`) when the chain is truly empty / has no operational tier |

This is the anti-pendule requirement of #1019 / north-star R311 honored: **the DAG
is not thrown away** — M3 is added beside it, both runnable from the same entry point.

---

## 1. Why the 3-tier chain was dormant (audit)

The decomposition / translation logic across the three tiers is **fully intact**.
The chain was dormant only because two pub/sub auto-subscription points were
**deliberately commented out**:

- `TaskCoordinator._subscribe_to_strategic_directives` — `tactical/coordinator.py:257`
  (`# self.adapter.subscribe_to_directives(handle_directive)`, "disabled due to API changes").
- `OperationalManager._subscribe_to_messages` — `operational/manager.py:310`.

**Design consequence:** rather than re-enable async pub/sub (and reintroduce the
message-bus races that motivated the deactivation), M3 drives the tiers by
**explicit sequential calls**. This is deterministic, unit-testable, and reuses
every existing translation method untouched (`process_strategic_objectives`,
`_decompose_objective_to_tasks`, `translate_task_to_command`,
`process_operational_result`, `evaluate_final_results`).

---

## 2. The two paths, side by side

### M2 — bridge (`HierarchicalOrchestrator.analyze`, `orchestrator.py`)

```
StrategicManager.initialize_analysis(text)        # objectives (LLM or hardcoded-4)
  └─> objectives_to_workflow(objectives, registry) # objectives → Lego workflow (DAG)
        └─> WorkflowExecutor.execute()             # phases run in DAG order
              └─> evaluate_final_results()         # success_rate per phase → conclusion
```
The 3-tier control structure is **short-circuited**: tactical/operational tiers are
not traversed; the DAG executor maps objective keywords → capabilities directly.

### M3 — delegation (`DelegationOrchestrator.analyze`, `delegation_orchestrator.py`)

```
S:  StrategicManager.initialize_analysis(text)            # objectives
    └─ FAIL LOUD if objectives == []  (DelegationError)   # ← contrast to M2's hardcoded-4
T:  TaskCoordinator.process_strategic_objectives(objs)    # objectives → tactical_state.tasks["pending"]
    └─ FAIL LOUD if 0 tasks  (DelegationError)
T→O: for task in pending:
       command = interface.translate_task_to_command(task)
       command["strategic_objective_description"] = obj_map[task.objective_id].description  # ← S→T→O NL thread
       result  = await operational_executor(command)      # registry providers OR injected stub
       interface.process_operational_result(command, result)  # bottom-up
O→T→S: aggregate per-objective success_rate → StrategicManager.evaluate_final_results()
```

**Key restoration detail — the NL thread.** `_decompose_objective_to_tasks` carries
only `objective_id` into each task (not the strategic NL description). M3 re-attaches
the originating objective's description onto the operational command
(`strategic_objective_description`) so the **strategic intent reaches the operational
tier** — this is the "strategic NL objective flows S→T→O" DoD item, and it is the
property the write→read chain test asserts.

---

## 3. Reference corpus comparison (opaque ID: `corpus_ref_A`)

`corpus_ref_A` = the single opaque reference text used for both invocations. Run the
two axes against the **same** input and diff the run summaries:

```bash
# M2 (bridge / DAG)
conda run -n projet-is --no-capture-output python argumentation_analysis/run_orchestration.py \
    --mode hierarchical --hierarchical-mode bridge \
    --file <corpus_ref_A> --output results/ra10/corpus_ref_A_m2.json   # results/ is gitignored

# M3 (true 3-tier delegation)
conda run -n projet-is --no-capture-output python argumentation_analysis/run_orchestration.py \
    --mode hierarchical --hierarchical-mode delegation \
    --file <corpus_ref_A> --output results/ra10/corpus_ref_A_m3.json
```

### 3.1 Structural comparison — VERIFIED from code

| Dimension | M2 (bridge) | M3 (delegation) |
|-----------|-------------|-----------------|
| Tiers traversed | S → DAG executor | S → T → O → T → S (all three) |
| Objective→work mapping | `_OBJECTIVE_CAPABILITY_MAP` keyword → capability (DAG) | `_decompose_objective_to_tasks` keyword → task, then `translate_task_to_command` → operational command |
| Operational dispatch | `WorkflowExecutor` over `CapabilityRegistry` | `operational_executor` over the **same** `CapabilityRegistry` (via `RegistryBackedOperationalRegistry.invoke_capability`) |
| Strategic NL reaches O tier | No (DAG consumes capabilities, not the NL objective) | **Yes** (`strategic_objective_description` threaded onto each command) |
| Empty-objective handling | Injects hardcoded 4 (`orchestrator.py:102-128`) | `DelegationError` (fail loud) |
| Missing-provider handling | Phase failure inside DAG | Per-task `status="failed"`, `reason="no_provider_for_required_capabilities"`, surfaced upward (no fabrication) |
| Result shape | `summary{total/completed/failed}`, `conclusion` | `operational_results[]`, `tasks_created`, `evaluation`, `conclusion`, `mode="delegation"` |

### 3.2 Empirical chain evidence — VERIFIED (unit, zero-API)

The S→T→O NL-flow and fail-loud properties are proven deterministically by
`tests/unit/orchestration/test_hierarchical_delegation.py` (9 tests, all passing,
no API key required):

- `test_strategic_objective_flows_s_to_t_to_o` — a unique strategic-intent marker set
  at tier S surfaces verbatim on the operational command after crossing the **real**
  tactical decomposition + translation tiers (the write→read chain).
- `test_multiple_objectives_each_thread_their_intent` — per-objective intent isolation
  (no cross-talk).
- `test_empty_objectives_fails_loud`, `test_absent_operational_tier_fails_loud`,
  `test_run_delegation_analysis_routes_to_chain` — `DelegationError` instead of a
  degraded silent result.
- `test_registry_executor_missing_provider_is_honest_failure` — honest `status="failed"`,
  not a heuristic substitution.
- `test_registry_executor_invokes_real_provider_with_intent` — the default registry
  executor routes the strategic NL intent through to the provider.
- `test_run_hierarchical_analysis_unknown_mode_raises` /
  `test_run_hierarchical_analysis_delegation_mode_dispatches` — the mode selector
  routes correctly and M3 fails loud where M2 would not.

### 3.3 Live LLM run — NOT executed on this machine (RAPPORTE)

A funded API key was not available on the executing machine (`myia-po-2023`, API
quota tight). The end-to-end LLM-driven comparison numbers (objective counts,
per-objective success rates, conclusions on `corpus_ref_A`) are therefore **not
filled in here** rather than fabricated (SDDD scepticism: VERIFIED vs RAPPORTE).
The recipe in §3 reproduces the run once a funded key is present; the structural
(§3.1) and unit-chain (§3.2) evidence already establishes that both axes are
runnable and that M3 traverses all three tiers with the NL thread intact.

---

## 4. Anti-pendule ledger (#1019 / R311)

- **Added, not replaced.** `HierarchicalOrchestrator` remains pure-M2; M3 lives in a
  new `delegation_orchestrator.py`. The selector is additive (`mode="bridge"` default).
- **No new hardcoded objective list.** M3 consumes RA-4's existing `_fallback_objectives()`
  (tagged `source="degraded"`); it introduces zero new hardcoded objectives.
- **Degraded = loud.** Empty chain → `DelegationError`; missing provider → honest
  `status="failed"`. No heuristic substitution anywhere in the M3 path.
- **DAG preserved.** The Lego/`WorkflowExecutor` path is untouched and still the default.
