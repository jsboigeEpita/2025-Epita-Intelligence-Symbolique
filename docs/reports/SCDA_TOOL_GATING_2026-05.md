# SCDA Tool Gating Report — Phase-Scoped StateManagerPlugin

**Date:** 2026-05-18
**Issue:** #605 (Track N)
**Status:** Implementation complete, pending PR review

## 1. Summary

Implements phase-scoped state plugins to restrict which `@kernel_function` methods each agent can invoke, restoring the V0 architectural principle that agents should only see tools relevant to their role. The mechanism uses composition (not runtime filters) — each agent receives a dedicated state plugin class that exposes only its phase's methods.

## 2. Problem

All 8 conversational agents receive the full `StateManagerPlugin` with ~30 `@kernel_function` methods. This means:
- InformalAgent (Phase 1) can see `add_dung_framework()`, `add_belief_set()`, `set_final_conclusion()` — formal and synthesis tools
- FormalAgent (Phase 2) can see `add_identified_argument()`, `add_counter_argument()` — extraction and synthesis tools
- Agents have ~30 tool definitions in their prompt context, causing pollution and potential hallucinated tool calls

`AGENT_SPECIALITY_MAP` already scopes per-agent plugins correctly, but StateManagerPlugin is shared and unscoped.

## 3. Solution

### 3.1 Phase-Scoped State Classes

New file: `argumentation_analysis/core/phase_scoped_state.py`

| Class | Phase | Methods | Description |
|-------|-------|---------|-------------|
| `_SharedStateBase` | All | 5 | Read, task control, turn designation |
| `ExtractionPhaseState` | Phase 1 | 5 + 6 = 11 | + argument, extract, fallacy writes |
| `FormalPhaseState` | Phase 2 | 5 + 13 = 18 | + belief, formal, JTMS, quality writes |
| `SynthesisPhaseState` | Phase 3 | 5 + 4 = 9 | + counter, governance, debate, conclusion |

### 3.2 Method Distribution

| Category | Methods | Shared | Extraction | Formal | Synthesis |
|----------|---------|--------|------------|--------|-----------|
| Read | `get_current_state_snapshot` | ✅ | ✅ | ✅ | ✅ |
| Task control | `add_analysis_task`, `mark_task_as_answered`, `add_answer` | ✅ | ✅ | ✅ | ✅ |
| Turn control | `designate_next_agent` | ✅ | ✅ | ✅ | ✅ |
| Arguments | `add_identified_argument`, `add_identified_arguments` | | ✅ | | |
| Fallacies | `add_identified_fallacy`, `add_identified_fallacies`, `add_neural_fallacy_score` | | ✅ | | |
| Extracts | `add_extract` | | ✅ | | |
| Logic | `add_belief_set`, `log_query_result`, `add_nl_to_logic_translation` | | | ✅ | |
| Quality | `add_quality_score` | | | ✅ | |
| Dung | `add_dung_framework` | | | ✅ | |
| ASPIC | `add_aspic_result` | | | ✅ | |
| Belief revision | `add_belief_revision_result` | | | ✅ | |
| Ranking | `add_ranking_result` | | | ✅ | |
| JTMS | `jtms_create_belief`, `jtms_add_justification`, `jtms_query_beliefs`, `jtms_check_consistency`, `jtms_retract_belief` | | | ✅ | |
| Counter | `add_counter_argument` | | | | ✅ |
| Governance | `add_governance_decision` | | | | ✅ |
| Debate | `add_debate_transcript` | | | | ✅ |
| Conclusion | `set_final_conclusion` | | | | ✅ |

### 3.3 Agent Mapping

| Agent | Phase | State Plugin |
|-------|-------|-------------|
| ExtractAgent | Extraction | `ExtractionPhaseState` |
| InformalAgent | Extraction | `ExtractionPhaseState` |
| FormalAgent | Formal | `FormalPhaseState` |
| QualityAgent | Formal | `FormalPhaseState` |
| DebateAgent | Synthesis | `SynthesisPhaseState` |
| CounterAgent | Synthesis | `SynthesisPhaseState` |
| GovernanceAgent | Synthesis | `SynthesisPhaseState` |
| **ProjectManager** | **All** | **`StateManagerPlugin`** (full access) |

ProjectManager retains the full StateManagerPlugin because it participates in all 3 phases as the coordinating agent.

### 3.4 Tool Surface Reduction

| Agent | Before (tools visible) | After (tools visible) | Reduction |
|-------|----------------------|----------------------|-----------|
| ExtractAgent | ~30 | 11 | 63% |
| InformalAgent | ~30 | 11 | 63% |
| FormalAgent | ~30 | 18 | 40% |
| QualityAgent | ~30 | 18 | 40% |
| DebateAgent | ~30 | 9 | 70% |
| CounterAgent | ~30 | 9 | 70% |
| GovernanceAgent | ~30 | 9 | 70% |
| ProjectManager | ~30 | ~30 | 0% |

## 4. Implementation Details

### 4.1 Backward Compatibility

- `enable_tool_gating: bool = False` — default OFF, zero impact on existing runs
- Env var override: `ENABLE_TOOL_GATING=1` enables gating
- Full `StateManagerPlugin` is unchanged — backward compat for all existing code

### 4.2 Modified Files

| File | Change |
|------|--------|
| `argumentation_analysis/core/phase_scoped_state.py` | NEW — 4 classes, 28 methods, agent mapping |
| `argumentation_analysis/agents/factory.py` | `get_plugin_instances()` accepts `state_plugin_class` param |
| `argumentation_analysis/orchestration/conversational_orchestrator.py` | `enable_tool_gating` param + env var + `agent_state_class` dict |

### 4.3 Test Coverage

File: `tests/unit/argumentation_analysis/core/test_phase_scoped_state.py`

| Test Class | Tests | Validates |
|-----------|-------|-----------|
| `TestSharedStateBase` | 4 | Shared methods present on all phases |
| `TestExtractionPhaseState` | 5 | Method set, isolation, delegation |
| `TestFormalPhaseState` | 5 | Method set, isolation, delegation |
| `TestSynthesisPhaseState` | 4 | Method set, isolation, delegation |
| `TestAgentPhaseMap` | 5 | Agent→phase mapping correctness |
| `TestMethodCounts` | 1 | Regression guard (5+6+13+4=28) |

**24 tests, all passing.**

## 5. DoD Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Per-phase tool sets declared | ✅ MET | `phase_scoped_state.py` with 3 classes |
| Filter wired into agent creation | ✅ MET | `factory.py` + `orchestrator.py` `agent_state_class` |
| Test coverage | ✅ MET | 24 unit tests, 0 failures |
| Telemetry | ✅ MET | Logger shows `state=<ClassName>` at agent creation |
| Backward compat flag | ✅ MET | `enable_tool_gating=False` default + env var |
| Report | ✅ MET | This file |
| PR | Pending | Coordinator review required (core orchestrator code) |

## 6. Files

| File | Description |
|------|-------------|
| `argumentation_analysis/core/phase_scoped_state.py` | Phase-scoped state plugin classes |
| `argumentation_analysis/agents/factory.py` | Updated `get_plugin_instances()` |
| `argumentation_analysis/orchestration/conversational_orchestrator.py` | Updated `run_conversational_analysis()` + `create_conversational_agents()` |
| `tests/unit/argumentation_analysis/core/test_phase_scoped_state.py` | 24 unit tests |
| `docs/reports/SCDA_TOOL_GATING_2026-05.md` | This report |
