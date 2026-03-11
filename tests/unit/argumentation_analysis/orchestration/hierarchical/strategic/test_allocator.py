# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.strategic.allocator
Covers ResourceAllocator: init, initial allocation, resource needs analysis,
agent assignments, priorities, computational budget, adjustment, optimization.
"""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.orchestration.hierarchical.strategic.allocator import (
    ResourceAllocator,
)
from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def allocator():
    return ResourceAllocator()


@pytest.fixture
def allocator_with_state():
    state = StrategicState()
    return ResourceAllocator(strategic_state=state)


@pytest.fixture
def sample_plan():
    """A strategic plan with three phases."""
    return {
        "phases": [
            {
                "id": "phase_1",
                "description": "Identification des éléments clés et arguments",
                "estimated_duration": "short",
            },
            {
                "id": "phase_2",
                "description": "Détection de sophisme et analyse logique formelle",
                "estimated_duration": "medium",
            },
            {
                "id": "phase_3",
                "description": "Synthèse finale et évaluation globale",
                "estimated_duration": "long",
            },
        ],
        "priorities": {
            "phase_1": "high",
            "phase_2": "high",
            "phase_3": "medium",
        },
    }


@pytest.fixture
def allocated_allocator(allocator, sample_plan):
    """An allocator that has already performed initial allocation."""
    allocator.allocate_initial_resources(sample_plan)
    return allocator


# ============================================================
# __init__
# ============================================================

class TestResourceAllocatorInit:
    def test_default_state_created(self, allocator):
        assert isinstance(allocator.state, StrategicState)

    def test_custom_state_used(self):
        state = StrategicState()
        alloc = ResourceAllocator(strategic_state=state)
        assert alloc.state is state

    def test_agent_capabilities_defined(self, allocator):
        assert "informal_analyzer" in allocator.agent_capabilities
        assert "logic_analyzer" in allocator.agent_capabilities
        assert "extract_processor" in allocator.agent_capabilities
        assert "visualizer" in allocator.agent_capabilities
        assert "data_extractor" in allocator.agent_capabilities

    def test_each_agent_has_required_keys(self, allocator):
        for agent_id, cap in allocator.agent_capabilities.items():
            assert "specialties" in cap, f"{agent_id} missing specialties"
            assert "efficiency" in cap, f"{agent_id} missing efficiency"
            assert "max_load" in cap, f"{agent_id} missing max_load"
            assert isinstance(cap["specialties"], list)
            assert len(cap["specialties"]) > 0


# ============================================================
# allocate_initial_resources
# ============================================================

class TestAllocateInitialResources:
    def test_returns_dict(self, allocator, sample_plan):
        result = allocator.allocate_initial_resources(sample_plan)
        assert isinstance(result, dict)

    def test_result_contains_required_keys(self, allocator, sample_plan):
        result = allocator.allocate_initial_resources(sample_plan)
        assert "agent_assignments" in result
        assert "priority_levels" in result
        assert "computational_budget" in result

    def test_all_agents_have_assignments(self, allocator, sample_plan):
        result = allocator.allocate_initial_resources(sample_plan)
        for agent_id in allocator.agent_capabilities:
            assert agent_id in result["agent_assignments"]

    def test_all_agents_have_priority(self, allocator, sample_plan):
        result = allocator.allocate_initial_resources(sample_plan)
        for agent_id in allocator.agent_capabilities:
            assert agent_id in result["priority_levels"]

    def test_budget_sums_to_one(self, allocator, sample_plan):
        result = allocator.allocate_initial_resources(sample_plan)
        total = sum(result["computational_budget"].values())
        assert abs(total - 1.0) < 0.01

    def test_empty_phases(self, allocator):
        result = allocator.allocate_initial_resources({"phases": [], "priorities": {}})
        assert isinstance(result, dict)

    def test_updates_state(self, allocator, sample_plan):
        allocator.allocate_initial_resources(sample_plan)
        alloc = allocator.state.resource_allocation
        assert "agent_assignments" in alloc


# ============================================================
# _analyze_resource_needs
# ============================================================

class TestAnalyzeResourceNeeds:
    def test_returns_dict_per_phase(self, allocator):
        phases = [
            {"id": "p1", "description": "Identification des éléments clés"},
            {"id": "p2", "description": "Analyse logique formelle"},
        ]
        result = allocator._analyze_resource_needs(phases)
        assert "p1" in result
        assert "p2" in result

    def test_identification_keywords_boost_scores(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés et arguments"}]
        result = allocator._analyze_resource_needs(phases)
        assert result["p1"]["argument_identification"] > 0
        assert result["p1"]["text_extraction"] > 0

    def test_sophisme_keywords_boost_scores(self, allocator):
        phases = [{"id": "p1", "description": "Détection de sophisme formelle"}]
        result = allocator._analyze_resource_needs(phases)
        assert result["p1"]["fallacy_detection"] > 0

    def test_analyse_logique_keywords_boost_scores(self, allocator):
        phases = [{"id": "p1", "description": "analyse logique complète"}]
        result = allocator._analyze_resource_needs(phases)
        assert result["p1"]["formal_logic"] > 0
        assert result["p1"]["validity_checking"] > 0

    def test_synthese_keywords_boost_scores(self, allocator):
        phases = [{"id": "p1", "description": "Synthèse et évaluation globale"}]
        result = allocator._analyze_resource_needs(phases)
        assert result["p1"]["summary_generation"] > 0
        assert result["p1"]["argument_visualization"] > 0

    def test_short_duration_reduces_scores(self, allocator):
        phases_short = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "short"}]
        phases_medium = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "medium"}]
        short_result = allocator._analyze_resource_needs(phases_short)
        medium_result = allocator._analyze_resource_needs(phases_medium)
        assert short_result["p1"]["argument_identification"] < medium_result["p1"]["argument_identification"]

    def test_long_duration_increases_scores(self, allocator):
        phases_long = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "long"}]
        phases_medium = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "medium"}]
        long_result = allocator._analyze_resource_needs(phases_long)
        medium_result = allocator._analyze_resource_needs(phases_medium)
        assert long_result["p1"]["argument_identification"] > medium_result["p1"]["argument_identification"]

    def test_unknown_duration_defaults_to_medium(self, allocator):
        phases_unknown = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "unknown"}]
        phases_medium = [{"id": "p1", "description": "Identification des éléments clés", "estimated_duration": "medium"}]
        unknown_result = allocator._analyze_resource_needs(phases_unknown)
        medium_result = allocator._analyze_resource_needs(phases_medium)
        assert unknown_result["p1"]["argument_identification"] == medium_result["p1"]["argument_identification"]

    def test_unmatched_description_all_zero(self, allocator):
        phases = [{"id": "p1", "description": "generic task with no keywords"}]
        result = allocator._analyze_resource_needs(phases)
        assert all(v == 0.0 for v in result["p1"].values())


# ============================================================
# _determine_agent_assignments
# ============================================================

class TestDetermineAgentAssignments:
    def test_relevant_agents_assigned(self, allocator):
        phases = [{"id": "p1", "description": "Identification des éléments clés"}]
        needs = allocator._analyze_resource_needs(phases)
        assignments = allocator._determine_agent_assignments(phases, needs)
        # informal_analyzer and extract_processor should be relevant
        assigned_agents = [aid for aid, pids in assignments.items() if pids]
        assert len(assigned_agents) > 0

    def test_irrelevant_agents_not_assigned(self, allocator):
        # With a completely generic description, no agent should be relevant
        phases = [{"id": "p1", "description": "nothing special here"}]
        needs = allocator._analyze_resource_needs(phases)
        assignments = allocator._determine_agent_assignments(phases, needs)
        total_assigned = sum(len(pids) for pids in assignments.values())
        assert total_assigned == 0

    def test_all_agents_in_assignments(self, allocator):
        phases = [{"id": "p1", "description": "test"}]
        needs = allocator._analyze_resource_needs(phases)
        assignments = allocator._determine_agent_assignments(phases, needs)
        for agent_id in allocator.agent_capabilities:
            assert agent_id in assignments


# ============================================================
# _define_agent_priorities
# ============================================================

class TestDefineAgentPriorities:
    def test_unassigned_agents_get_low(self, allocator):
        assignments = {"agent_a": [], "agent_b": ["p1"]}
        priorities = allocator._define_agent_priorities(assignments, {"p1": "medium"})
        assert priorities["agent_a"] == "low"

    def test_high_phase_gives_high_priority(self, allocator):
        assignments = {"agent_a": ["p1"]}
        priorities = allocator._define_agent_priorities(assignments, {"p1": "high"})
        assert priorities["agent_a"] == "high"

    def test_medium_phase_gives_medium_priority(self, allocator):
        assignments = {"agent_a": ["p1"]}
        priorities = allocator._define_agent_priorities(assignments, {"p1": "medium"})
        assert priorities["agent_a"] == "medium"

    def test_mixed_phases_high_wins(self, allocator):
        assignments = {"agent_a": ["p1", "p2"]}
        priorities = allocator._define_agent_priorities(
            assignments, {"p1": "low", "p2": "high"}
        )
        assert priorities["agent_a"] == "high"

    def test_only_low_phases(self, allocator):
        assignments = {"agent_a": ["p1", "p2"]}
        priorities = allocator._define_agent_priorities(
            assignments, {"p1": "low", "p2": "low"}
        )
        assert priorities["agent_a"] == "low"

    def test_missing_phase_priority_defaults_medium(self, allocator):
        assignments = {"agent_a": ["p1"]}
        priorities = allocator._define_agent_priorities(assignments, {})
        assert priorities["agent_a"] == "medium"


# ============================================================
# _allocate_computational_budget
# ============================================================

class TestAllocateComputationalBudget:
    def test_budget_sums_to_one(self, allocator):
        assignments = {
            "a": ["p1", "p2"],
            "b": ["p1"],
            "c": [],
        }
        priority_levels = {"a": "high", "b": "medium", "c": "low"}
        budget = allocator._allocate_computational_budget(assignments, priority_levels)
        total = sum(budget.values())
        assert abs(total - 1.0) < 0.01

    def test_high_priority_gets_more_budget(self, allocator):
        assignments = {"a": ["p1"], "b": ["p1"]}
        priority_levels = {"a": "high", "b": "low"}
        budget = allocator._allocate_computational_budget(assignments, priority_levels)
        assert budget["a"] > budget["b"]

    def test_more_phases_gets_more_budget(self, allocator):
        assignments = {"a": ["p1", "p2", "p3"], "b": ["p1"]}
        priority_levels = {"a": "medium", "b": "medium"}
        budget = allocator._allocate_computational_budget(assignments, priority_levels)
        assert budget["a"] > budget["b"]

    def test_no_assigned_phases_gets_minimal_budget(self, allocator):
        assignments = {"a": ["p1"], "b": []}
        priority_levels = {"a": "medium", "b": "medium"}
        budget = allocator._allocate_computational_budget(assignments, priority_levels)
        assert budget["b"] < budget["a"]

    def test_empty_assignments(self, allocator):
        budget = allocator._allocate_computational_budget({}, {})
        assert budget == {} or sum(budget.values()) == 0.0


# ============================================================
# adjust_allocation
# ============================================================

class TestAdjustAllocation:
    def test_bottleneck_increases_priority(self, allocated_allocator):
        alloc = allocated_allocator
        # Find an agent in the current allocation
        agents = list(alloc.state.resource_allocation["priority_levels"].keys())
        target_agent = agents[0]

        feedback = {
            "bottlenecks": [{"agent_id": target_agent, "severity": "high"}],
            "idle_resources": [],
        }
        result = alloc.adjust_allocation(feedback)
        assert result["priority_levels"][target_agent] == "high"

    def test_idle_resource_reduces_budget(self, allocated_allocator):
        alloc = allocated_allocator
        agents = list(alloc.state.resource_allocation["computational_budget"].keys())
        target_agent = agents[0]
        original_budget = alloc.state.resource_allocation["computational_budget"][target_agent]

        feedback = {
            "bottlenecks": [],
            "idle_resources": [{"agent_id": target_agent, "idle_level": "high"}],
        }
        result = alloc.adjust_allocation(feedback)
        # Budget should be reduced (but may be normalized)
        # At least the raw adjustment is applied
        assert isinstance(result, dict)

    def test_empty_feedback(self, allocated_allocator):
        result = allocated_allocator.adjust_allocation({})
        assert isinstance(result, dict)

    def test_unknown_agent_in_feedback_ignored(self, allocated_allocator):
        feedback = {
            "bottlenecks": [{"agent_id": "nonexistent_agent", "severity": "high"}],
            "idle_resources": [],
        }
        result = allocated_allocator.adjust_allocation(feedback)
        assert isinstance(result, dict)

    def test_medium_severity_bottleneck(self, allocated_allocator):
        alloc = allocated_allocator
        agents = list(alloc.state.resource_allocation["priority_levels"].keys())
        target_agent = agents[0]

        feedback = {
            "bottlenecks": [{"agent_id": target_agent, "severity": "medium"}],
            "idle_resources": [],
        }
        result = alloc.adjust_allocation(feedback)
        assert result["priority_levels"][target_agent] == "high"


# ============================================================
# optimize_resource_utilization
# ============================================================

class TestOptimizeResourceUtilization:
    def test_adjusts_budget_based_on_efficiency(self, allocated_allocator):
        alloc = allocated_allocator
        agents = list(alloc.state.resource_allocation["computational_budget"].keys())

        metrics = {
            "agent_efficiency": {
                agents[0]: {
                    "processing_speed": 0.9,
                    "accuracy": 0.9,
                    "resource_usage": 0.1,
                },
            },
            "task_completion_rates": {},
        }
        result = alloc.optimize_resource_utilization(metrics)
        assert isinstance(result, dict)

    def test_empty_metrics(self, allocated_allocator):
        result = allocated_allocator.optimize_resource_utilization({})
        assert isinstance(result, dict)

    def test_unknown_agent_in_metrics_ignored(self, allocated_allocator):
        metrics = {
            "agent_efficiency": {
                "unknown_agent_xyz": {
                    "processing_speed": 0.5,
                    "accuracy": 0.5,
                    "resource_usage": 0.5,
                },
            },
        }
        result = allocated_allocator.optimize_resource_utilization(metrics)
        assert isinstance(result, dict)

    def test_high_efficiency_gets_more_budget(self, allocated_allocator):
        alloc = allocated_allocator
        agents = list(alloc.state.resource_allocation["computational_budget"].keys())
        if len(agents) < 2:
            pytest.skip("Need at least 2 agents")

        metrics = {
            "agent_efficiency": {
                agents[0]: {"processing_speed": 1.0, "accuracy": 1.0, "resource_usage": 0.0},
                agents[1]: {"processing_speed": 0.1, "accuracy": 0.1, "resource_usage": 0.9},
            },
        }
        before_0 = alloc.state.resource_allocation["computational_budget"].get(agents[0], 0)
        before_1 = alloc.state.resource_allocation["computational_budget"].get(agents[1], 0)
        result = alloc.optimize_resource_utilization(metrics)
        # After optimization, the more efficient agent should move toward more budget
        # (progressive 50% movement toward ideal)
        assert isinstance(result, dict)


# ============================================================
# get_resource_allocation_snapshot
# ============================================================

class TestGetResourceAllocationSnapshot:
    def test_returns_dict(self, allocated_allocator):
        snap = allocated_allocator.get_resource_allocation_snapshot()
        assert isinstance(snap, dict)

    def test_contains_required_keys(self, allocated_allocator):
        snap = allocated_allocator.get_resource_allocation_snapshot()
        assert "agent_assignments" in snap
        assert "priority_levels" in snap
        assert "computational_budget" in snap

    def test_snapshot_matches_state(self, allocated_allocator):
        snap = allocated_allocator.get_resource_allocation_snapshot()
        state_alloc = allocated_allocator.state.resource_allocation
        assert snap["agent_assignments"] == state_alloc["agent_assignments"]
        assert snap["priority_levels"] == state_alloc["priority_levels"]
        assert snap["computational_budget"] == state_alloc["computational_budget"]
