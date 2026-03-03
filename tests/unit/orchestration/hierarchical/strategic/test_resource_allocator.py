# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.strategic.allocator
Covers ResourceAllocator: init, resource needs analysis, agent assignments,
priorities, budget allocation, adjustment, optimization, snapshot.
"""

import pytest

from argumentation_analysis.orchestration.hierarchical.strategic.allocator import (
    ResourceAllocator,
)
from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)


@pytest.fixture
def state():
    return StrategicState()


@pytest.fixture
def allocator(state):
    return ResourceAllocator(strategic_state=state)


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_default_state(self):
        a = ResourceAllocator()
        assert isinstance(a.state, StrategicState)

    def test_custom_state(self, state):
        a = ResourceAllocator(strategic_state=state)
        assert a.state is state

    def test_agent_capabilities_populated(self, allocator):
        assert "informal_analyzer" in allocator.agent_capabilities
        assert "logic_analyzer" in allocator.agent_capabilities
        assert "extract_processor" in allocator.agent_capabilities
        assert "visualizer" in allocator.agent_capabilities
        assert "data_extractor" in allocator.agent_capabilities

    def test_agent_has_specialties(self, allocator):
        for agent_id, info in allocator.agent_capabilities.items():
            assert "specialties" in info
            assert "efficiency" in info
            assert "max_load" in info


# ============================================================
# _analyze_resource_needs
# ============================================================

class TestAnalyzeResourceNeeds:
    def test_empty_phases(self, allocator):
        needs = allocator._analyze_resource_needs([])
        assert needs == {}

    def test_identification_phase(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés"}]
        needs = allocator._analyze_resource_needs(phases)
        assert needs["p1"]["argument_identification"] > 0
        assert needs["p1"]["text_extraction"] > 0

    def test_sophisme_phase(self, allocator):
        phases = [{"id": "p1", "description": "Détection de sophisme et analyse logique"}]
        needs = allocator._analyze_resource_needs(phases)
        assert needs["p1"]["fallacy_detection"] > 0
        assert needs["p1"]["formal_logic"] > 0

    def test_synthese_phase(self, allocator):
        phases = [{"id": "p1", "description": "Synthèse et évaluation finale"}]
        needs = allocator._analyze_resource_needs(phases)
        assert needs["p1"]["consistency_analysis"] > 0
        assert needs["p1"]["summary_generation"] > 0

    def test_short_duration_factor(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "short"}]
        needs = allocator._analyze_resource_needs(phases)
        # Short duration uses 0.7 factor
        assert needs["p1"]["argument_identification"] == pytest.approx(0.8 * 0.7)

    def test_long_duration_factor(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "long"}]
        needs = allocator._analyze_resource_needs(phases)
        assert needs["p1"]["argument_identification"] == pytest.approx(0.8 * 1.3)

    def test_unmatched_description_zeros(self, allocator):
        phases = [{"id": "p1", "description": "Faire quelque chose"}]
        needs = allocator._analyze_resource_needs(phases)
        # All values should be 0.0 since no keywords matched
        assert all(v == 0.0 for v in needs["p1"].values())

    def test_multiple_phases(self, allocator):
        phases = [
            {"id": "p1", "description": "Identification des éléments clés"},
            {"id": "p2", "description": "Synthèse et évaluation"},
        ]
        needs = allocator._analyze_resource_needs(phases)
        assert "p1" in needs
        assert "p2" in needs


# ============================================================
# _determine_agent_assignments
# ============================================================

class TestDetermineAgentAssignments:
    def test_empty_phases(self, allocator):
        assignments = allocator._determine_agent_assignments([], {})
        # All agents get empty lists
        for agent_id in allocator.agent_capabilities:
            assert assignments[agent_id] == []

    def test_relevant_agent_assigned(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés"}]
        needs = allocator._analyze_resource_needs(phases)
        assignments = allocator._determine_agent_assignments(phases, needs)
        # extract_processor should be assigned (text_extraction > 0.5)
        assert "p1" in assignments["extract_processor"]

    def test_irrelevant_agent_not_assigned(self, allocator):
        phases = [{"id": "p1", "description": "Faire quelque chose de nouveau"}]
        needs = allocator._analyze_resource_needs(phases)
        assignments = allocator._determine_agent_assignments(phases, needs)
        # No agent should be assigned (all needs are 0)
        for agent_id, assigned in assignments.items():
            assert assigned == []


# ============================================================
# _define_agent_priorities
# ============================================================

class TestDefineAgentPriorities:
    def test_no_assignments_low_priority(self, allocator):
        assignments = {"agent1": []}
        priorities = allocator._define_agent_priorities(assignments, {})
        assert priorities["agent1"] == "low"

    def test_high_phase_priority(self, allocator):
        assignments = {"agent1": ["p1"]}
        phase_priorities = {"p1": "high"}
        priorities = allocator._define_agent_priorities(assignments, phase_priorities)
        assert priorities["agent1"] == "high"

    def test_medium_default(self, allocator):
        assignments = {"agent1": ["p1"]}
        phase_priorities = {"p1": "medium"}
        priorities = allocator._define_agent_priorities(assignments, phase_priorities)
        assert priorities["agent1"] == "medium"

    def test_mixed_high_wins(self, allocator):
        assignments = {"agent1": ["p1", "p2"]}
        phase_priorities = {"p1": "low", "p2": "high"}
        priorities = allocator._define_agent_priorities(assignments, phase_priorities)
        assert priorities["agent1"] == "high"

    def test_missing_phase_defaults_medium(self, allocator):
        assignments = {"agent1": ["p_unknown"]}
        priorities = allocator._define_agent_priorities(assignments, {})
        assert priorities["agent1"] == "medium"


# ============================================================
# _allocate_computational_budget
# ============================================================

class TestAllocateComputationalBudget:
    def test_budget_sums_to_one(self, allocator):
        assignments = {"a1": ["p1"], "a2": ["p1", "p2"]}
        priorities = {"a1": "medium", "a2": "high"}
        budget = allocator._allocate_computational_budget(assignments, priorities)
        assert sum(budget.values()) == pytest.approx(1.0)

    def test_high_priority_gets_more(self, allocator):
        assignments = {"a1": ["p1"], "a2": ["p1"]}
        priorities = {"a1": "low", "a2": "high"}
        budget = allocator._allocate_computational_budget(assignments, priorities)
        assert budget["a2"] > budget["a1"]

    def test_no_phases_minimal_budget(self, allocator):
        assignments = {"a1": [], "a2": ["p1"]}
        priorities = {"a1": "medium", "a2": "medium"}
        budget = allocator._allocate_computational_budget(assignments, priorities)
        assert budget["a1"] < budget["a2"]

    def test_all_empty_no_budget(self, allocator):
        assignments = {"a1": [], "a2": []}
        priorities = {"a1": "medium", "a2": "medium"}
        budget = allocator._allocate_computational_budget(assignments, priorities)
        # total_score > 0 because phase_count_factor = 0.1 for empty
        assert all(v >= 0 for v in budget.values())


# ============================================================
# allocate_initial_resources
# ============================================================

class TestAllocateInitialResources:
    def test_basic_plan(self, allocator, state):
        plan = {
            "phases": [
                {"id": "p1", "description": "Identification des éléments clés"},
                {"id": "p2", "description": "Analyse logique des sophismes"},
                {"id": "p3", "description": "Synthèse et évaluation"},
            ],
            "priorities": {"p1": "high", "p2": "medium", "p3": "low"},
        }
        result = allocator.allocate_initial_resources(plan)
        assert "agent_assignments" in result
        assert "priority_levels" in result
        assert "computational_budget" in result

    def test_updates_state(self, allocator, state):
        plan = {
            "phases": [{"id": "p1", "description": "Identification"}],
            "priorities": {},
        }
        allocator.allocate_initial_resources(plan)
        assert state.resource_allocation["agent_assignments"] != {}

    def test_empty_plan(self, allocator):
        result = allocator.allocate_initial_resources({"phases": [], "priorities": {}})
        assert "agent_assignments" in result


# ============================================================
# adjust_allocation
# ============================================================

class TestAdjustAllocation:
    def test_no_feedback_unchanged(self, allocator, state):
        # First, set up initial allocation
        plan = {
            "phases": [{"id": "p1", "description": "Identification"}],
            "priorities": {"p1": "medium"},
        }
        allocator.allocate_initial_resources(plan)
        result = allocator.adjust_allocation({"bottlenecks": [], "idle_resources": []})
        assert "agent_assignments" in result

    def test_bottleneck_increases_priority(self, allocator, state):
        plan = {
            "phases": [{"id": "p1", "description": "Identification des éléments clés"}],
            "priorities": {"p1": "medium"},
        }
        allocator.allocate_initial_resources(plan)
        # Use an agent that's in the allocation
        agent_id = list(state.resource_allocation["priority_levels"].keys())[0]
        feedback = {
            "bottlenecks": [{"agent_id": agent_id, "severity": "high"}],
            "idle_resources": [],
        }
        allocator.adjust_allocation(feedback)
        # Priority should be adjusted
        assert state.resource_allocation["priority_levels"][agent_id] == "high"

    def test_idle_resource_reduces_budget(self, allocator, state):
        plan = {
            "phases": [{"id": "p1", "description": "Identification des éléments clés"}],
            "priorities": {"p1": "medium"},
        }
        allocator.allocate_initial_resources(plan)
        agent_id = list(state.resource_allocation["computational_budget"].keys())[0]
        original_budget = state.resource_allocation["computational_budget"][agent_id]
        feedback = {
            "bottlenecks": [],
            "idle_resources": [{"agent_id": agent_id, "idle_level": "high"}],
        }
        allocator.adjust_allocation(feedback)
        # Budget should be reduced
        new_budget = state.resource_allocation["computational_budget"].get(agent_id, 0)
        assert new_budget <= original_budget


# ============================================================
# optimize_resource_utilization
# ============================================================

class TestOptimizeResourceUtilization:
    def test_no_metrics_unchanged(self, allocator, state):
        plan = {
            "phases": [{"id": "p1", "description": "Identification"}],
            "priorities": {"p1": "medium"},
        }
        allocator.allocate_initial_resources(plan)
        result = allocator.optimize_resource_utilization({"agent_efficiency": {}})
        assert "computational_budget" in result

    def test_efficiency_adjusts_budget(self, allocator, state):
        plan = {
            "phases": [{"id": "p1", "description": "Identification des éléments clés"}],
            "priorities": {"p1": "medium"},
        }
        allocator.allocate_initial_resources(plan)
        agent_ids = list(state.resource_allocation["computational_budget"].keys())
        if len(agent_ids) >= 2:
            metrics = {
                "agent_efficiency": {
                    agent_ids[0]: {"processing_speed": 0.9, "accuracy": 0.9, "resource_usage": 0.2},
                    agent_ids[1]: {"processing_speed": 0.1, "accuracy": 0.1, "resource_usage": 0.9},
                }
            }
            allocator.optimize_resource_utilization(metrics)
            # The more efficient agent should get a higher budget
            b1 = state.resource_allocation["computational_budget"].get(agent_ids[0], 0)
            b2 = state.resource_allocation["computational_budget"].get(agent_ids[1], 0)
            assert b1 > b2


# ============================================================
# get_resource_allocation_snapshot
# ============================================================

class TestGetSnapshot:
    def test_snapshot_structure(self, allocator):
        snap = allocator.get_resource_allocation_snapshot()
        assert "agent_assignments" in snap
        assert "priority_levels" in snap
        assert "computational_budget" in snap

    def test_snapshot_reflects_state(self, allocator, state):
        state.update_resource_allocation({"agent_assignments": {"a1": "t1"}})
        snap = allocator.get_resource_allocation_snapshot()
        assert snap["agent_assignments"]["a1"] == "t1"
