# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.strategic.planner
Covers StrategicPlanner: plan creation, text complexity, objective decomposition,
phase dependencies, priorities, success criteria, plan adjustment.
"""

import pytest

from argumentation_analysis.orchestration.hierarchical.strategic.planner import (
    StrategicPlanner,
)
from argumentation_analysis.orchestration.hierarchical.strategic.state import (
    StrategicState,
)


@pytest.fixture
def state():
    s = StrategicState()
    s.add_global_objective(
        {"id": "obj-1", "description": "Identifier les arguments", "priority": "high"}
    )
    s.add_global_objective(
        {"id": "obj-2", "description": "Détecter les sophismes", "priority": "medium"}
    )
    s.add_global_objective(
        {"id": "obj-3", "description": "Évaluer la cohérence", "priority": "low"}
    )
    return s


@pytest.fixture
def planner(state):
    return StrategicPlanner(strategic_state=state)


# ============================================================
# __init__
# ============================================================


class TestPlannerInit:
    def test_default_state(self):
        p = StrategicPlanner()
        assert isinstance(p.state, StrategicState)

    def test_custom_state(self, state):
        p = StrategicPlanner(strategic_state=state)
        assert p.state is state


# ============================================================
# _assess_text_complexity
# ============================================================


class TestAssessTextComplexity:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_low_complexity(self, planner):
        metadata = {
            "length": 500,
            "avg_sentence_length": 10,
            "vocabulary_diversity": 0.3,
        }
        assert planner._assess_text_complexity(metadata) == "low"

    def test_medium_complexity(self, planner):
        metadata = {
            "length": 3000,
            "avg_sentence_length": 18,
            "vocabulary_diversity": 0.6,
        }
        assert planner._assess_text_complexity(metadata) == "medium"

    def test_high_complexity(self, planner):
        metadata = {
            "length": 10000,
            "avg_sentence_length": 25,
            "vocabulary_diversity": 0.8,
        }
        assert planner._assess_text_complexity(metadata) == "high"

    def test_empty_metadata_defaults_low(self, planner):
        assert planner._assess_text_complexity({}) == "low"

    def test_boundary_medium(self, planner):
        metadata = {
            "length": 2001,
            "avg_sentence_length": 16,
            "vocabulary_diversity": 0.51,
        }
        assert planner._assess_text_complexity(metadata) == "medium"


# ============================================================
# _decompose_objectives_into_phases
# ============================================================


class TestDecomposeObjectives:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_low_complexity_three_phases(self, planner):
        objectives = [{"id": "o1", "description": "Identifier les éléments"}]
        phases = planner._decompose_objectives_into_phases(objectives, "low")
        assert len(phases) == 3

    def test_high_complexity_adds_intermediate_phase(self, planner):
        objectives = [{"id": "o1", "description": "Analyser le contexte"}]
        phases = planner._decompose_objectives_into_phases(objectives, "high")
        assert len(phases) == 4
        phase_ids = [p["id"] for p in phases]
        assert "phase-2b" in phase_ids

    def test_identifier_goes_to_phase1(self, planner):
        objectives = [{"id": "o1", "description": "Identifier les arguments"}]
        phases = planner._decompose_objectives_into_phases(objectives, "low")
        assert "o1" in phases[0]["objectives"]

    def test_detecter_goes_to_phase2(self, planner):
        objectives = [{"id": "o1", "description": "Détecter les sophismes"}]
        phases = planner._decompose_objectives_into_phases(objectives, "low")
        assert "o1" in phases[1]["objectives"]

    def test_evaluer_goes_to_phase3(self, planner):
        objectives = [{"id": "o1", "description": "Évaluer la qualité"}]
        phases = planner._decompose_objectives_into_phases(objectives, "low")
        assert "o1" in phases[2]["objectives"]

    def test_unknown_description_defaults_to_phase2(self, planner):
        objectives = [{"id": "o1", "description": "Faire quelque chose"}]
        phases = planner._decompose_objectives_into_phases(objectives, "low")
        assert "o1" in phases[1]["objectives"]

    def test_estimated_duration_varies(self, planner):
        objectives = []
        low_phases = planner._decompose_objectives_into_phases(objectives, "low")
        high_phases = planner._decompose_objectives_into_phases(objectives, "high")
        assert low_phases[0]["estimated_duration"] == "short"
        assert high_phases[1]["estimated_duration"] == "long"


# ============================================================
# _establish_phase_dependencies
# ============================================================


class TestEstablishDependencies:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_sequential_dependencies(self, planner):
        phases = [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
        deps = planner._establish_phase_dependencies(phases)
        assert deps["p2"] == ["p1"]
        assert deps["p3"] == ["p2"]
        assert "p1" not in deps

    def test_single_phase_no_deps(self, planner):
        phases = [{"id": "p1"}]
        deps = planner._establish_phase_dependencies(phases)
        assert deps == {}


# ============================================================
# _define_phase_priorities
# ============================================================


class TestDefinePhaPriorities:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_high_priority_objective(self, planner):
        phases = [{"id": "p1", "objectives": ["o1"]}]
        objectives = [{"id": "o1", "priority": "high"}]
        priorities = planner._define_phase_priorities(phases, objectives)
        assert priorities["p1"] == "high"

    def test_medium_when_no_high(self, planner):
        phases = [{"id": "p1", "objectives": ["o1"]}]
        objectives = [{"id": "o1", "priority": "medium"}]
        priorities = planner._define_phase_priorities(phases, objectives)
        assert priorities["p1"] == "medium"

    def test_empty_objectives_defaults_medium(self, planner):
        phases = [{"id": "p1", "objectives": []}]
        priorities = planner._define_phase_priorities(phases, [])
        assert priorities["p1"] == "medium"

    def test_mixed_priorities_high_wins(self, planner):
        phases = [{"id": "p1", "objectives": ["o1", "o2"]}]
        objectives = [
            {"id": "o1", "priority": "low"},
            {"id": "o2", "priority": "high"},
        ]
        priorities = planner._define_phase_priorities(phases, objectives)
        assert priorities["p1"] == "high"


# ============================================================
# _define_success_criteria
# ============================================================


class TestDefineSuccessCriteria:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_uses_objective_criteria(self, planner):
        phases = [{"id": "p1", "name": "Test", "objectives": ["o1"]}]
        objectives = [{"id": "o1", "success_criteria": "90% accuracy"}]
        criteria = planner._define_success_criteria(phases, objectives)
        assert "90% accuracy" in criteria["p1"]

    def test_default_for_preliminary_phase(self, planner):
        phases = [{"id": "p1", "name": "Analyse préliminaire", "objectives": ["o1"]}]
        objectives = [{"id": "o1"}]
        criteria = planner._define_success_criteria(phases, objectives)
        assert "80%" in criteria["p1"]

    def test_default_for_approfondie_phase(self, planner):
        phases = [{"id": "p1", "name": "Analyse approfondie", "objectives": ["o1"]}]
        objectives = [{"id": "o1"}]
        criteria = planner._define_success_criteria(phases, objectives)
        assert "70%" in criteria["p1"]

    def test_default_for_synthese_phase(self, planner):
        phases = [{"id": "p1", "name": "Synthèse et évaluation", "objectives": ["o1"]}]
        objectives = [{"id": "o1"}]
        criteria = planner._define_success_criteria(phases, objectives)
        assert "cohérente" in criteria["p1"]

    def test_empty_objectives_default(self, planner):
        phases = [{"id": "p1", "name": "X", "objectives": []}]
        criteria = planner._define_success_criteria(phases, [])
        assert criteria["p1"] == "Complétion de la phase"


# ============================================================
# create_analysis_plan (integration)
# ============================================================


class TestCreateAnalysisPlan:
    def test_creates_plan(self, planner, state):
        metadata = {
            "length": 1000,
            "avg_sentence_length": 12,
            "vocabulary_diversity": 0.4,
        }
        plan = planner.create_analysis_plan(metadata, state.global_objectives)
        assert "phases" in plan
        assert len(plan["phases"]) >= 3
        assert "dependencies" in plan
        assert "priorities" in plan

    def test_plan_stored_in_state(self, planner, state):
        metadata = {"length": 500}
        planner.create_analysis_plan(metadata, state.global_objectives)
        assert len(state.strategic_plan["phases"]) >= 3


# ============================================================
# decompose_objective
# ============================================================


class TestDecomposeObjective:
    def test_identifier_arguments(self, planner, state):
        subs = planner.decompose_objective("obj-1")
        assert len(subs) == 3
        assert all(s["parent_id"] == "obj-1" for s in subs)
        assert any("prémisses explicites" in s["description"] for s in subs)

    def test_detecter_sophismes(self, planner, state):
        subs = planner.decompose_objective("obj-2")
        assert len(subs) == 3
        assert any("sophismes formels" in s["description"] for s in subs)

    def test_evaluer_coherence(self, planner, state):
        subs = planner.decompose_objective("obj-3")
        assert len(subs) == 3
        assert any("cohérence interne" in s["description"] for s in subs)

    def test_unknown_objective(self, planner):
        subs = planner.decompose_objective("nonexistent")
        assert subs == []

    def test_generic_decomposition(self, planner, state):
        state.add_global_objective(
            {"id": "obj-generic", "description": "Faire le café", "priority": "medium"}
        )
        subs = planner.decompose_objective("obj-generic")
        assert len(subs) == 2


# ============================================================
# adjust_plan
# ============================================================


class TestAdjustPlan:
    def test_no_feedback_no_change(self, planner, state):
        metadata = {"length": 500}
        planner.create_analysis_plan(metadata, state.global_objectives)
        original_phases = len(state.strategic_plan["phases"])
        planner.adjust_plan({"progress": {}, "issues": []})
        assert len(state.strategic_plan["phases"]) == original_phases

    def test_insufficient_progress_increases_priority(self, planner, state):
        metadata = {"length": 500}
        planner.create_analysis_plan(metadata, state.global_objectives)
        feedback = {
            "progress": {
                "phase-2": {"completion_rate": 0.2, "expected_completion_rate": 0.8}
            },
            "issues": [],
        }
        planner.adjust_plan(feedback)
        # Plan should be adjusted
        assert state.strategic_plan is not None


# ============================================================
# _identify_problematic_phases
# ============================================================


class TestIdentifyProblematicPhases:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_insufficient_progress(self, planner):
        progress = {"p1": {"completion_rate": 0.3, "expected_completion_rate": 0.8}}
        result = planner._identify_problematic_phases(progress, [])
        assert "p1" in result
        assert result["p1"][0]["type"] == "insufficient_progress"

    def test_no_problems(self, planner):
        progress = {"p1": {"completion_rate": 0.9, "expected_completion_rate": 0.8}}
        result = planner._identify_problematic_phases(progress, [])
        assert result == {}

    def test_issues_added_to_phases(self, planner):
        issues = [{"phase_id": "p2", "type": "resource_shortage", "details": {}}]
        result = planner._identify_problematic_phases({}, issues)
        assert "p2" in result


# ============================================================
# _create_phase_adjustment
# ============================================================


class TestCreatePhaseAdjustment:
    @pytest.fixture
    def planner(self):
        return StrategicPlanner()

    def test_insufficient_progress(self, planner):
        problems = [{"type": "insufficient_progress", "details": {}}]
        adj = planner._create_phase_adjustment("p1", problems)
        assert adj["phase_updates"]["estimated_duration"] == "long"
        assert adj["priority"] == "high"

    def test_resource_shortage_no_adjustment(self, planner):
        problems = [{"type": "resource_shortage", "details": {}}]
        adj = planner._create_phase_adjustment("p1", problems)
        assert adj == {}

    def test_objective_unrealistic(self, planner):
        problems = [
            {
                "type": "objective_unrealistic",
                "details": {"suggested_criteria": "50% accuracy"},
            }
        ]
        adj = planner._create_phase_adjustment("p1", problems)
        assert adj["success_criteria"] == "50% accuracy"
