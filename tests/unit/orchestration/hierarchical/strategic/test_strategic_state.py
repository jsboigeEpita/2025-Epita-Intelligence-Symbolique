# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.strategic.state
Covers StrategicState: init, setters, update methods, snapshot, serialization.
"""

import pytest
import json

from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)


@pytest.fixture
def state():
    return StrategicState()


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_default_values(self, state):
        assert state.raw_text is None
        assert state.global_objectives == []
        assert state.final_conclusion is None
        assert state.strategic_decisions_log == []

    def test_strategic_plan_structure(self, state):
        assert "phases" in state.strategic_plan
        assert "dependencies" in state.strategic_plan
        assert "priorities" in state.strategic_plan
        assert "success_criteria" in state.strategic_plan

    def test_resource_allocation_structure(self, state):
        assert "agent_assignments" in state.resource_allocation
        assert "priority_levels" in state.resource_allocation
        assert "computational_budget" in state.resource_allocation

    def test_global_metrics_structure(self, state):
        assert state.global_metrics["progress"] == 0.0
        assert "quality_indicators" in state.global_metrics
        assert "resource_utilization" in state.global_metrics

    def test_rhetorical_summary_keys(self, state):
        expected = {
            "complex_fallacy_summary", "contextual_fallacy_summary",
            "fallacy_severity_summary", "argument_structure_summary",
            "argument_coherence_summary", "semantic_argument_summary",
        }
        assert set(state.rhetorical_analysis_summary.keys()) == expected


# ============================================================
# set_raw_text
# ============================================================

class TestSetRawText:
    def test_sets_text(self, state):
        state.set_raw_text("Hello World")
        assert state.raw_text == "Hello World"

    def test_overwrite(self, state):
        state.set_raw_text("first")
        state.set_raw_text("second")
        assert state.raw_text == "second"


# ============================================================
# add_global_objective
# ============================================================

class TestAddGlobalObjective:
    def test_adds_objective(self, state):
        obj = {"id": "obj-1", "description": "Test", "priority": "high"}
        state.add_global_objective(obj)
        assert len(state.global_objectives) == 1
        assert state.global_objectives[0]["id"] == "obj-1"

    def test_multiple_objectives(self, state):
        for i in range(3):
            state.add_global_objective({"id": f"obj-{i}", "description": f"Obj {i}", "priority": "medium"})
        assert len(state.global_objectives) == 3


# ============================================================
# update_strategic_plan
# ============================================================

class TestUpdateStrategicPlan:
    def test_update_phases(self, state):
        state.update_strategic_plan({"phases": [{"id": "p1"}]})
        assert state.strategic_plan["phases"] == [{"id": "p1"}]

    def test_merge_dict_values(self, state):
        state.update_strategic_plan({"dependencies": {"p1": ["p0"]}})
        assert state.strategic_plan["dependencies"]["p1"] == ["p0"]

    def test_unknown_key_ignored(self, state):
        state.update_strategic_plan({"unknown_key": "value"})
        assert "unknown_key" not in state.strategic_plan


# ============================================================
# update_resource_allocation
# ============================================================

class TestUpdateResourceAllocation:
    def test_update_agent_assignments(self, state):
        state.update_resource_allocation({"agent_assignments": {"a1": "task1"}})
        assert state.resource_allocation["agent_assignments"]["a1"] == "task1"

    def test_merge_dict(self, state):
        state.update_resource_allocation({"priority_levels": {"p1": "high"}})
        state.update_resource_allocation({"priority_levels": {"p2": "low"}})
        assert "p1" in state.resource_allocation["priority_levels"]
        assert "p2" in state.resource_allocation["priority_levels"]


# ============================================================
# update_global_metrics
# ============================================================

class TestUpdateGlobalMetrics:
    def test_update_progress(self, state):
        state.update_global_metrics({"progress": 0.5})
        assert state.global_metrics["progress"] == 0.5

    def test_merge_quality_indicators(self, state):
        state.update_global_metrics({"quality_indicators": {"accuracy": 0.9}})
        assert state.global_metrics["quality_indicators"]["accuracy"] == 0.9


# ============================================================
# update_rhetorical_analysis_summary
# ============================================================

class TestUpdateRhetoricalSummary:
    def test_update_summary(self, state):
        state.update_rhetorical_analysis_summary({"complex_fallacy_summary": {"count": 3}})
        assert state.rhetorical_analysis_summary["complex_fallacy_summary"]["count"] == 3

    def test_unknown_key_ignored(self, state):
        state.update_rhetorical_analysis_summary({"nonexistent": "val"})
        assert "nonexistent" not in state.rhetorical_analysis_summary


# ============================================================
# set_final_conclusion / log_strategic_decision
# ============================================================

class TestConclusionAndDecisions:
    def test_set_conclusion(self, state):
        state.set_final_conclusion("The argument is fallacious.")
        assert state.final_conclusion == "The argument is fallacious."

    def test_log_decision(self, state):
        decision = {"timestamp": "2025-01-01", "description": "Increase priority", "rationale": "Too slow"}
        state.log_strategic_decision(decision)
        assert len(state.strategic_decisions_log) == 1

    def test_multiple_decisions(self, state):
        for i in range(5):
            state.log_strategic_decision({"timestamp": f"t{i}", "description": f"D{i}", "rationale": f"R{i}"})
        assert len(state.strategic_decisions_log) == 5


# ============================================================
# get_snapshot
# ============================================================

class TestGetSnapshot:
    def test_snapshot_structure(self, state):
        snap = state.get_snapshot()
        assert "raw_text_length" in snap
        assert "global_objectives" in snap
        assert "strategic_plan" in snap
        assert "resource_allocation" in snap
        assert "global_metrics" in snap
        assert "final_conclusion" in snap
        assert "strategic_decisions_count" in snap

    def test_text_length_zero_when_none(self, state):
        snap = state.get_snapshot()
        assert snap["raw_text_length"] == 0

    def test_text_length_correct(self, state):
        state.set_raw_text("Hello")
        snap = state.get_snapshot()
        assert snap["raw_text_length"] == 5

    def test_decisions_count(self, state):
        state.log_strategic_decision({"timestamp": "t", "description": "d", "rationale": "r"})
        snap = state.get_snapshot()
        assert snap["strategic_decisions_count"] == 1


# ============================================================
# to_json / from_json
# ============================================================

class TestSerialization:
    def test_to_json_returns_string(self, state):
        j = state.to_json()
        assert isinstance(j, str)
        data = json.loads(j)
        assert "global_objectives" in data

    def test_roundtrip(self, state):
        state.set_raw_text("Test text")
        state.add_global_objective({"id": "obj-1", "description": "Test", "priority": "high"})
        state.update_global_metrics({"progress": 0.75})
        state.set_final_conclusion("Done")
        state.log_strategic_decision({"timestamp": "t", "description": "d", "rationale": "r"})

        j = state.to_json()
        restored = StrategicState.from_json(j)

        assert len(restored.global_objectives) == 1
        assert restored.global_objectives[0]["id"] == "obj-1"
        assert restored.global_metrics["progress"] == 0.75
        assert restored.final_conclusion == "Done"
        assert len(restored.strategic_decisions_log) == 1

    def test_from_json_partial(self):
        partial = json.dumps({"global_objectives": [{"id": "x"}]})
        restored = StrategicState.from_json(partial)
        assert len(restored.global_objectives) == 1

    def test_from_json_empty(self):
        restored = StrategicState.from_json("{}")
        assert restored.global_objectives == []
        assert restored.final_conclusion is None
