# Orchestration Modes — Architecture Guide

> Created: 2026-03-24 as part of Epic #208 (Conversational Orchestration Restoration)

## Overview

The system supports **5 orchestration modes**, each suited to different analysis scenarios. Four are wired into the CLI (`--mode`); one is active but dedicated to investigation scenarios via scripts.

| Mode | CLI-selectable | Status | Key Class | Use Case |
|------|---------------|--------|-----------|----------|
| **Sequential (Pipeline)** | ✅ `--mode pipeline` (default) | ACTIVE | `WorkflowExecutor` | Production analysis, benchmarks, API |
| **Conversational** | ✅ `--mode conversational` | ACTIVE | `ConversationalOrchestrator` | Rich multi-agent dialogue with cross-KB synergies |
| **Hierarchical** | ✅ `--mode hierarchical [--hierarchical-mode {bridge,delegation}]` | ACTIVE | `HierarchicalOrchestrator` (M2) / `DelegationOrchestrator` (M3) | Strategic planning → Lego execution (M2, default) or true S→T→O delegation (M3, RA-10) |
| **Sherlock Modern** | ✅ `--mode sherlock_modern` | ACTIVE | `SherlockModernOrchestrator` | Investigation multi-agent (#357) |
| **Cluedo** | ❌ script-only | ACTIVE | `CluedoExtendedOrchestrator` | Sherlock-Watson investigation game |

> **Note (scoping #912):** Cluedo is not reachable via `--mode` — it uses dedicated scripts and `__main__` entry points. Making it CLI-selectable requires an implementation issue (lane argparse, po-2025).

---

## 1. Sequential (Pipeline) Mode

**Entry points:**
- CLI: `python run_orchestration.py --file text.txt --workflow standard`
- API: `POST /api/v1/agents/full-analysis`

**How it works:**
- Uses `CapabilityRegistry` + `WorkflowDSL` + `WorkflowExecutor`
- Phases execute sequentially following a dependency DAG
- Each phase invokes a registered capability (agent, plugin, or service)
- `UnifiedAnalysisState` accumulates results across phases
- Phase outputs passed via `context["phase_{name}_output"]`

**Workflow catalog:**

| Workflow | Phases | Description |
|----------|--------|-------------|
| `light` | extract → quality → counter | Quick 3-phase analysis |
| `standard` | extract → quality → counter → jtms → governance → debate | Full 6-phase pipeline with optional formal reasoning |
| `full` | All components including formal, ASPIC+, DELP, etc. | Exhaustive analysis |
| `collaborative` | extract → quality → counter → critic → validator → synthesis | Multi-agent debate with Skeptic/Scholar/Synthesis roles |

**Key files:**
- `argumentation_analysis/orchestration/unified_pipeline.py` — Pipeline engine (~4000 lines)
- `argumentation_analysis/orchestration/workflow_dsl.py` — `WorkflowBuilder` fluent API
- `argumentation_analysis/core/capability_registry.py` — `CapabilityRegistry` + `ServiceDiscovery`

**Architecture pattern:**
```
WorkflowBuilder → WorkflowDefinition (phases + deps)
     ↓
WorkflowExecutor → resolves phases via CapabilityRegistry
     ↓
_invoke_X() → LLM enrichment + Python fallback
     ↓
_write_X_to_state() → updates UnifiedAnalysisState
```

---

## 2. Conversational Mode

**Entry points:**
- CLI: `python run_orchestration.py --text "..." --mode conversational`
- API: (planned — not yet wired)

**How it works:**
- Uses Semantic Kernel's `AgentGroupChat` with `FunctionChoiceBehavior.Auto()`
- Agents converse in **3 macro-phases**: Extraction & Detection → Formal Analysis → Synthesis
- ProjectManager orchestrates by reading shared state and designating the next agent
- Each agent has **specialized plugins** (not all plugins on all agents)
- `StateManagerPlugin` serves as the shared communication medium
- Cross-KB enrichment: agents read each other's outputs to improve their own analysis

**Agent-Plugin mapping:**

| Agent | Plugins | Role |
|-------|---------|------|
| ProjectManager | StateManager | Coordination, phase transitions |
| ExtractAgent | StateManager | Fact extraction from text |
| InformalAgent | FrenchFallacyPlugin + StateManager | Sophism detection (8 families) |
| FormalAgent | TweetyLogicPlugin + StateManager | Propositional/FOL validation |
| QualityAgent | QualityScoringPlugin + StateManager | 9-virtue argument quality |
| DebateAgent | DebatePlugin + StateManager | Adversarial Walton-Krabbe debate |
| CounterAgent | CounterArgumentPlugin + StateManager | 5-strategy counter-arguments |
| GovernanceAgent | GovernancePlugin + StateManager | 7 voting methods, consensus |

**Cross-KB synergies (#208-I):**
- Quality reads sophism detections → adjusts scores for fallacious arguments
- JTMS reads quality scores → weights justification strength
- Counter-argument reads sophisms + quality → targets weakest arguments
- Governance reads debate transcript → evaluates consensus
- Formal reads NL-to-logic output → validates translations

**Trace analyzer:**
- `ConversationalTraceAnalyzer` captures phase transitions, turn counts, state snapshots
- Produces convergence metrics and quality reports per round

**Key files:**

- `argumentation_analysis/orchestration/conversational_executor.py` — Turn execution
- `argumentation_analysis/orchestration/trace_analyzer.py` — Trace capture and analysis

**Architecture pattern:**
```
ConversationalOrchestrator
     ↓
AgentGroupChat (SK native) with FunctionChoiceBehavior.Auto()
     ↓
Agents invoke @kernel_function plugins → tool_calls
     ↓
StateManagerPlugin updates shared state
     ↓
ProjectManager reads state → designates next agent
     ↓
TraceAnalyzer captures snapshots per round
```

---

## 3. Hierarchical Mode

**Entry points:**

- CLI: `python run_orchestration.py --text "..." --mode hierarchical [--hierarchical-mode {bridge,delegation}]`
- API: (planned — not yet wired)

This mode now exposes **two comparable, selectable axes** (RA-10 #1069, anti-pendule #1019 /
north-star R311 "stratégies comparables"). The DAG/bridge path (M2) is the default and is
**not discarded** — the true 3-tier delegation chain (M3) is restored *beside* it.

### M2 — bridge (default, `--hierarchical-mode bridge`)

**How it works (bridge approach, R311-B4):**

- Uses `StrategicManager` for high-level objective planning
- Translates objectives into a `WorkflowDefinition` via `objectives_to_workflow()`
- Executes via `WorkflowExecutor` (backed by `CapabilityRegistry`)
- `StrategicManager.evaluate_final_results()` produces the final conclusion
- This "bridge" approach reuses the Lego Architecture; the 3-tier control structure is
  short-circuited (tactical/operational tiers are not traversed)

**Flow:**

```text
HierarchicalOrchestrator
     ↓
StrategicManager.initialize_analysis(text) → objectives + plan
     ↓
objectives_to_workflow(objectives, registry) → WorkflowDefinition
     ↓
WorkflowExecutor.execute(workflow, text) → phase results
     ↓
StrategicManager.evaluate_final_results(results) → conclusion
```

### M3 — delegation (`--hierarchical-mode delegation`, RA-10 #1069)

**How it works (explicit sequential 3-tier calls):**

- Drives the tiers by **explicit S→T→O sequential calls** (no pub/sub). The 3-tier
  decomposition/translation logic is fully intact; the chain was dormant only because two
  pub/sub auto-subscriptions are deliberately commented out
  (`tactical/coordinator.py:257`, `operational/manager.py:310`).
- **Strategic NL objective flows S→T→O**: decomposition carries only `objective_id`, so
  `DelegationOrchestrator.analyze()` re-attaches the originating objective's NL description
  onto each operational command (`strategic_objective_description`).
- **Fail-loud (#1019)**: empty strategic objectives / zero tactical tasks / absent operational
  tier → `DelegationError` (not a heuristic fallback). Missing capability provider → honest
  per-task `status="failed"`, never a fabricated result. M3 reuses RA-4's existing
  `_fallback_objectives()` (tagged `source="degraded"`); it introduces **zero** new hardcoded
  objectives.

**Flow:**

```text
DelegationOrchestrator.analyze(text)
  S: StrategicManager.initialize_analysis(text) → objectives      (FAIL LOUD if empty)
  T: TaskCoordinator.process_strategic_objectives(objectives)     → tasks  (FAIL LOUD if 0)
  T→O: for task: interface.translate_task_to_command(task)
       command["strategic_objective_description"] = objective.description   # NL thread S→T→O
       operational_executor(command)        # CapabilityRegistry via RegistryBackedOperationalRegistry
  O→T→S: aggregate per-objective success_rate → StrategicManager.evaluate_final_results()
```

A detailed M3-vs-M2 comparison on a reference corpus (opaque IDs, provenance header) lives in
`docs/reports/RA10_M3_vs_M2_delegation_note.md`.

**Use case:** Complex, goal-driven analyses where a strategic planner decomposes objectives
into sub-tasks distributed across specialist agents. M2 when the DAG/Lego execution is wanted;
M3 when the true S→T→O delegation chain (with strategic NL reaching the operational tier) is
the comparable axis under study.

**Key files:**

- `argumentation_analysis/orchestration/hierarchical/orchestrator.py` — `HierarchicalOrchestrator` (M2) + `run_hierarchical_analysis(mode=...)` selector
- `argumentation_analysis/orchestration/hierarchical/delegation_orchestrator.py` — `DelegationOrchestrator` + `DelegationError` + `make_registry_operational_executor` (M3, RA-10)
- `argumentation_analysis/orchestration/hierarchical/hierarchy_bridge.py` — `objectives_to_workflow()`, `RegistryBackedOperationalRegistry` (shared by both axes)
- `argumentation_analysis/orchestration/hierarchical/strategic/manager.py` — `StrategicManager`
- `docs/architecture/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md` — 3-tier architecture reference

**Reactivation status (R311):** COMPLETE. All 5 blockers fixed:

- B1: `rhetorical_tools_adapter` import fix
- B2: `PLAgentAdapter` rewritten against real API
- B3: `informal_agent_adapter` de-stubbed (AgentFactory wiring)
- B4: `HierarchicalOrchestrator` bridge class + CLI `--mode hierarchical`
- B5: Documentation updated

**RA-10 #1069 (ORC-2):** M3 true 3-tier delegation restored as a selectable axis
(`--hierarchical-mode delegation`). The dormant pub/sub-wired chain is *bypassed* (not
re-enabled — its message-bus races motivated the deactivation); M3 drives the tiers by explicit
sequential calls. The legacy skip-marked test suite (Strategic→Tactical→Operational pub/sub
path) remains dormant; M3's behavior is covered by
`tests/unit/orchestration/test_hierarchical_delegation.py` (9 zero-API tests).

---

## 4. Cluedo Mode

**Entry points:**
- Dedicated scripts in `examples/`
- `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py`

**How it works:**
- Cyclic turn-taking: **Sherlock** → **Watson** → **Moriarty** (Oracle)
- Uses `CyclicSelectionStrategy` for agent selection
- Uses `OracleTerminationStrategy` for solution convergence
- Separate state model: `EnqueteCluedoState` / `CluedoOracleState`
- Each agent has domain-specific plugins (SherlockTools, WatsonTools, OracleTools)

**Agents:**

| Agent | Plugin | Role |
|-------|--------|------|
| SherlockEnqueteAgent | SherlockTools | Hypothesis generation, deduction |
| WatsonLogicAssistant | WatsonTools | Logical validation, step-by-step reasoning |
| MoriartyInterrogatorAgent | OracleTools | Query authorization, card reveal |

**Key difference:** Operates on the Cluedo dataset (suspects, weapons, rooms) rather than rhetorical text analysis. Uses its own state model, not `UnifiedAnalysisState`.

**Key files:**

- `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py` — 3-agent + Oracle (active)
- `docs/archives/orchestration_legacy/cluedo_orchestrator_base.py` — 2-agent version (archived, superseded by Extended)

---

## CLI Quick Reference

```bash
# Sequential pipeline (default)
python run_orchestration.py --file text.txt
python run_orchestration.py --file text.txt --workflow light
python run_orchestration.py --file text.txt --workflow standard
python run_orchestration.py --file text.txt --workflow full
python run_orchestration.py --file text.txt --workflow collaborative

# Conversational mode
python run_orchestration.py --text "Your argument text" --mode conversational

# Hierarchical mode (strategic planning → Lego execution)
python run_orchestration.py --text "Your argument text" --mode hierarchical                         # M2 bridge (default)
python run_orchestration.py --text "Your argument text" --mode hierarchical --hierarchical-mode delegation  # M3 true 3-tier (RA-10)

# List available workflows
python run_orchestration.py --list-workflows
```

## API Quick Reference

```bash
# Full pipeline analysis
curl -X POST http://localhost:8000/api/v1/agents/full-analysis \
  -H "Content-Type: application/json" \
  -d '{"text": "Your argument text", "workflow": "standard"}'

# Quality evaluation only
curl -X POST http://localhost:8000/api/v1/agents/quality \
  -H "Content-Type: application/json" \
  -d '{"text": "Your argument text"}'

# Debate simulation
curl -X POST http://localhost:8000/api/v1/agents/debate \
  -H "Content-Type: application/json" \
  -d '{"text": "Your argument text"}'
```

---

## Comparison Matrix

| Aspect | Sequential | Conversational | Hierarchical | Cluedo |
|--------|-----------|---------------|-------------|--------|
| Agent interaction | None (isolated phases) | Rich dialogue via GroupChat | M2 bridge: Strategic → Lego DAG; M3 delegation: S→T→O sequential | Cyclic turns |
| State model | UnifiedAnalysisState | Shared via StateManagerPlugin | StrategicState + (WorkflowResults \| operational_results) | EnqueteCluedoState |
| Plugin routing | All-to-all | Per-agent specialty | Via CapabilityRegistry (both M2 & M3) | Domain-specific |
| LLM calls | 1 per phase | Multiple per round | M2: 1 per phase (WorkflowExecutor); M3: per operational command | Per agent turn |
| Cross-KB enrichment | Via context dict | Via state reads + prompts | M2: objectives → capabilities map; M3: strategic NL → operational command | N/A |
| Convergence | Phase completion | PM designation + trace | Objective success rate (both axes) | Oracle termination |
| Best for | Batch analysis, API | Deep interactive analysis | Goal decomposition (M2 DAG) / true S→T→O delegation study (M3) | Investigation game |

---

## Post-Consolidation Status (Epic #208, March 2026)

### Archived Components
| Component | Archived To | Replacement | PR |
|-----------|-------------|-------------|-----|
| `RealLLMOrchestrator` (668→124 LOC shim) | `docs/archives/orchestration_legacy/real_llm_orchestrator_shim.py` | `UnifiedPipeline` + `WorkflowDSL` | #246, #886 |
| `RealLLMOrchestratorWrapper` (60 lines) | Deprecation shim in `pipelines/` | Same as above | #247 |
| Dead code in `pipeline_utils.py` | Removed (EnhancedPipeline, singletons) | `AnalysisCache` + `PipelineMetrics` kept | #255 |
| `ConversationOrchestrator` (1044 LOC) | `docs/archives/orchestration_legacy/conversation_orchestrator.py` | 8-agent SK system via `CapabilityRegistry` | #886 |
| `CluedoOrchestrator` base 2-agent (488 LOC) | `docs/archives/orchestration_legacy/cluedo_orchestrator_base.py` | `CluedoExtendedOrchestrator` (3-agent + Oracle) | #886 |
| `LogiqueComplexeOrchestrator` (108 LOC stub) | `docs/archives/orchestration_legacy/logique_complexe_orchestrator.py` | `FOLLogicAgent` + `TweetyLogicPlugin` | #886 |

### Consolidated Components
| Component | New Location | Description | PR |
|-----------|-------------|-------------|-----|
| `ExtendedBelief` + `JTMSSession` | `services/jtms/extended_belief.py` | Agent-aware beliefs with confidence and audit trail | #254 |
| `ConflictResolver` (5 strategies) | `services/jtms/conflict_resolution.py` | Standalone conflict resolution for multi-agent JTMS | #254 |
| JTMS imports | `services/jtms/` | Fixed from `1.4.1-JTMS/` sys.path hack to canonical import | #254 |

### Confirmed Active (NOT archived)
| File | Why Active |
|------|-----------|
| `enhanced_pm_analysis_runner.py` | Used by `analysis_runner_v2.py`, `trace_analyzer.py`, integration tests |
| `hierarchy_bridge.py` | Used by `conversational_executor.py`, `run_agentic_eval.py` |
| `turn_protocol.py` | Used by `conversational_executor.py`, evaluation module, 7 files total |
| `direct_executor.py` | Used by `MainOrchestrator` (hierarchical mode), 3 test files |
| `conversational_executor.py` | Used by hierarchy_bridge, evaluation modules |

### Pipeline Utilities (added #215)
- `AnalysisCache`: TTL-based caching with LFU eviction
- `PipelineMetrics`: Structured metrics collection with per-type aggregation
- `run_batch_analysis()`: Semaphore-controlled concurrent batch processing
