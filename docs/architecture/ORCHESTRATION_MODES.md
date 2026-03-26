# Orchestration Modes — Architecture Guide

> Created: 2026-03-24 as part of Epic #208 (Conversational Orchestration Restoration)

## Overview

The system supports **4 orchestration modes**, each suited to different analysis scenarios. Two are actively wired into the CLI/API; two have full infrastructure but are dormant (awaiting reactivation).

| Mode | Status | Key Class | Use Case |
|------|--------|-----------|----------|
| **Sequential (Pipeline)** | ACTIVE | `WorkflowExecutor` | Production analysis, benchmarks, API |
| **Conversational** | ACTIVE | `ConversationalOrchestrator` | Rich multi-agent dialogue with cross-KB synergies |
| **Hierarchical** | DORMANT | `HierarchicalTurnStrategy` | Strategic → Tactical → Operational delegation |
| **Cluedo** | ACTIVE | `CluedoExtendedOrchestrator` | Sherlock-Watson investigation game |

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
- `argumentation_analysis/orchestration/conversational_orchestrator.py` — Main orchestrator
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

## 3. Hierarchical Mode (Dormant)

**Status:** Infrastructure exists but not wired into `run_orchestration.py` or API.

**How it works:**
- 3-level hierarchy: **Strategic** (goals) → **Tactical** (plans) → **Operational** (agents)
- `StrategicTacticalInterface` translates high-level objectives into tactical directives
- `TacticalOperationalInterface` translates tasks into specific agent invocations
- Each level has its own communication channel
- Operational adapters wrap each agent type (InformalAgentAdapter, ExtractAgentAdapter, etc.)

**Use case:** Complex, goal-driven analyses where a strategic planner decomposes objectives into sub-tasks distributed across specialist agents.

**Key files:**
- `argumentation_analysis/orchestration/hierarchical/hierarchy_bridge.py`
- `docs/architecture/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md`
- `examples/orchestration/run_hierarchical_orchestration.py`

**Reactivation path:** Wire `HierarchicalOrchestrator` into `run_orchestration.py --mode hierarchical` and register operational adapters for all current agents.

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
- `argumentation_analysis/orchestration/cluedo_orchestrator.py` — 2-agent version
- `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py` — 3-agent + Oracle

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

# List available workflows
python run_orchestration.py --list-workflows

# Legacy mode (AnalysisRunner)
python run_orchestration.py --file text.txt --mode legacy
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
| Agent interaction | None (isolated phases) | Rich dialogue via GroupChat | Delegation chain | Cyclic turns |
| State model | UnifiedAnalysisState | Shared via StateManagerPlugin | Per-level state | EnqueteCluedoState |
| Plugin routing | All-to-all | Per-agent specialty | Via adapters | Domain-specific |
| LLM calls | 1 per phase | Multiple per round | Per level | Per agent turn |
| Cross-KB enrichment | Via context dict | Via state reads + prompts | Via interfaces | N/A |
| Convergence | Phase completion | PM designation + trace | Level completion | Oracle termination |
| Best for | Batch analysis, API | Deep interactive analysis | Goal decomposition | Investigation game |

---

## Post-Consolidation Status (Epic #208, March 2026)

### Archived Components
| Component | Archived To | Replacement | PR |
|-----------|-------------|-------------|-----|
| `RealLLMOrchestrator` (668 lines) | `docs/archives/orchestration_legacy/` | `UnifiedPipeline` / `ConversationalOrchestrator` | #246 |
| `RealLLMOrchestratorWrapper` (60 lines) | Deprecation shim in `pipelines/` | Same as above | #247 |
| Dead code in `pipeline_utils.py` | Removed (EnhancedPipeline, singletons) | `AnalysisCache` + `PipelineMetrics` kept | #255 |

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
