"""Unit tests for phase-scoped state plugins (#605).

Verifies that each phase-scoped class exposes only the intended @kernel_function
methods and that delegation to the underlying state works correctly.
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.core.phase_scoped_state import (
    _SharedStateBase,
    ExtractionPhaseState,
    FormalPhaseState,
    SynthesisPhaseState,
    AGENT_PHASE_MAP,
)
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kernel_function_names(cls) -> set[str]:
    """Return the set of @kernel_function method names on a class (own + inherited)."""
    names = set()
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if hasattr(method, "__kernel_function__") or hasattr(method, "__sk_function__"):
            names.add(name)
    return names


@pytest.fixture
def mock_state():
    """Create a mock RhetoricalAnalysisState (not spec-limited — state methods vary)."""
    state = MagicMock()
    state.get_state_snapshot.return_value = {"identified_arguments": []}
    state.add_task.return_value = "task_1"
    state.add_argument.return_value = "arg_1"
    state.add_fallacy.return_value = "fallacy_1"
    state.add_extract.return_value = "ext_1"
    state.add_belief_set.return_value = "bs_1"
    state.log_query.return_value = "log_1"
    state.add_nl_to_logic_translation.return_value = "tr_1"
    state.add_quality_score.return_value = "OK"
    state.add_dung_framework.return_value = "df_1"
    state.add_aspic_result.return_value = "as_1"
    state.add_belief_revision_result.return_value = "br_1"
    state.add_ranking_result.return_value = "rk_1"
    state.add_counter_argument.return_value = "ca_1"
    state.add_governance_decision.return_value = "gd_1"
    state.add_debate_transcript.return_value = "dt_1"
    state.add_neural_fallacy_score.return_value = "nf_1"
    state.designate_next_agent.return_value = None
    state.mark_task_as_answered.return_value = None
    state.add_answer.return_value = None
    state.set_conclusion.return_value = None
    state.add_identified_arguments.return_value = None
    state.add_identified_fallacies.return_value = None
    return state


# ---------------------------------------------------------------------------
# Test: Shared base methods
# ---------------------------------------------------------------------------

class TestSharedStateBase:
    def test_shared_methods_present_on_all_phases(self):
        """All 3 phase classes inherit the 5 shared methods."""
        shared = _kernel_function_names(_SharedStateBase)
        expected = {
            "get_current_state_snapshot",
            "add_analysis_task",
            "mark_task_as_answered",
            "add_answer",
            "designate_next_agent",
        }
        assert shared == expected

    def test_extraction_inherits_shared(self):
        shared = _kernel_function_names(_SharedStateBase)
        extraction = _kernel_function_names(ExtractionPhaseState)
        assert shared.issubset(extraction)

    def test_formal_inherits_shared(self):
        shared = _kernel_function_names(_SharedStateBase)
        formal = _kernel_function_names(FormalPhaseState)
        assert shared.issubset(formal)

    def test_synthesis_inherits_shared(self):
        shared = _kernel_function_names(_SharedStateBase)
        synthesis = _kernel_function_names(SynthesisPhaseState)
        assert shared.issubset(synthesis)


# ---------------------------------------------------------------------------
# Test: Phase-specific method isolation
# ---------------------------------------------------------------------------

class TestExtractionPhaseState:
    EXPECTED = {
        # Shared (5)
        "get_current_state_snapshot", "add_analysis_task", "mark_task_as_answered",
        "add_answer", "designate_next_agent",
        # Extraction-specific (6)
        "add_identified_argument", "add_identified_arguments",
        "add_identified_fallacy", "add_identified_fallacies",
        "add_extract", "add_neural_fallacy_score",
    }

    def test_exposes_only_expected_methods(self):
        actual = _kernel_function_names(ExtractionPhaseState)
        assert actual == self.EXPECTED

    def test_does_not_expose_formal_methods(self):
        actual = _kernel_function_names(ExtractionPhaseState)
        assert "add_belief_set" not in actual
        assert "jtms_create_belief" not in actual
        assert "add_dung_framework" not in actual

    def test_does_not_expose_synthesis_methods(self):
        actual = _kernel_function_names(ExtractionPhaseState)
        assert "add_counter_argument" not in actual
        assert "set_final_conclusion" not in actual
        assert "add_debate_transcript" not in actual

    def test_delegation_add_argument(self, mock_state):
        plugin = ExtractionPhaseState(state=mock_state)
        result = plugin.add_identified_argument("Test argument")
        mock_state.add_argument.assert_called_once_with("Test argument")
        assert result == "arg_1"

    def test_delegation_add_fallacy(self, mock_state):
        plugin = ExtractionPhaseState(state=mock_state)
        result = plugin.add_identified_fallacy("post_hoc", "Justification", "arg_1")
        mock_state.add_fallacy.assert_called_once_with("post_hoc", "Justification", "arg_1")
        assert result == "fallacy_1"


class TestFormalPhaseState:
    EXPECTED = {
        # Shared (5)
        "get_current_state_snapshot", "add_analysis_task", "mark_task_as_answered",
        "add_answer", "designate_next_agent",
        # Formal-specific (13)
        "add_belief_set", "log_query_result", "add_nl_to_logic_translation",
        "add_quality_score", "add_dung_framework", "add_aspic_result",
        "add_belief_revision_result", "add_ranking_result",
        "jtms_create_belief", "jtms_add_justification", "jtms_query_beliefs",
        "jtms_check_consistency", "jtms_retract_belief",
    }

    def test_exposes_only_expected_methods(self):
        actual = _kernel_function_names(FormalPhaseState)
        assert actual == self.EXPECTED

    def test_does_not_expose_extraction_methods(self):
        actual = _kernel_function_names(FormalPhaseState)
        assert "add_identified_argument" not in actual
        assert "add_identified_fallacy" not in actual
        assert "add_extract" not in actual

    def test_does_not_expose_synthesis_methods(self):
        actual = _kernel_function_names(FormalPhaseState)
        assert "add_counter_argument" not in actual
        assert "set_final_conclusion" not in actual

    def test_delegation_add_belief_set(self, mock_state):
        plugin = FormalPhaseState(state=mock_state)
        result = plugin.add_belief_set("propositional", "p => q")
        mock_state.add_belief_set.assert_called_once_with("Propositional", "p => q")
        assert result == "bs_1"

    def test_invalid_logic_type(self, mock_state):
        plugin = FormalPhaseState(state=mock_state)
        result = plugin.add_belief_set("modal", "[]p")
        assert "FUNC_ERROR" in result
        mock_state.add_belief_set.assert_not_called()


class TestSynthesisPhaseState:
    EXPECTED = {
        # Shared (5)
        "get_current_state_snapshot", "add_analysis_task", "mark_task_as_answered",
        "add_answer", "designate_next_agent",
        # Synthesis-specific (4)
        "add_counter_argument", "add_governance_decision",
        "add_debate_transcript", "set_final_conclusion",
    }

    def test_exposes_only_expected_methods(self):
        actual = _kernel_function_names(SynthesisPhaseState)
        assert actual == self.EXPECTED

    def test_does_not_expose_extraction_methods(self):
        actual = _kernel_function_names(SynthesisPhaseState)
        assert "add_identified_argument" not in actual
        assert "add_identified_fallacy" not in actual

    def test_does_not_expose_formal_methods(self):
        actual = _kernel_function_names(SynthesisPhaseState)
        assert "add_belief_set" not in actual
        assert "jtms_create_belief" not in actual

    def test_delegation_set_conclusion(self, mock_state):
        plugin = SynthesisPhaseState(state=mock_state)
        result = plugin.set_final_conclusion("Final analysis conclusion")
        mock_state.set_conclusion.assert_called_once_with("Final analysis conclusion")
        assert "OK" in result


# ---------------------------------------------------------------------------
# Test: Agent → Phase mapping
# ---------------------------------------------------------------------------

class TestAgentPhaseMap:
    def test_all_specialist_agents_mapped(self):
        expected_agents = {
            "ExtractAgent", "InformalAgent",
            "FormalAgent", "QualityAgent",
            "DebateAgent", "CounterAgent", "GovernanceAgent",
        }
        assert set(AGENT_PHASE_MAP.keys()) == expected_agents

    def test_project_manager_not_mapped(self):
        """PM is not mapped — it gets full StateManagerPlugin."""
        assert "ProjectManager" not in AGENT_PHASE_MAP

    def test_extraction_agents(self):
        assert AGENT_PHASE_MAP["ExtractAgent"] is ExtractionPhaseState
        assert AGENT_PHASE_MAP["InformalAgent"] is ExtractionPhaseState

    def test_formal_agents(self):
        assert AGENT_PHASE_MAP["FormalAgent"] is FormalPhaseState
        assert AGENT_PHASE_MAP["QualityAgent"] is FormalPhaseState

    def test_synthesis_agents(self):
        assert AGENT_PHASE_MAP["DebateAgent"] is SynthesisPhaseState
        assert AGENT_PHASE_MAP["CounterAgent"] is SynthesisPhaseState
        assert AGENT_PHASE_MAP["GovernanceAgent"] is SynthesisPhaseState


# ---------------------------------------------------------------------------
# Test: Method counts (regression guard)
# ---------------------------------------------------------------------------

class TestMethodCounts:
    def test_total_method_count(self):
        """Total methods across all phases should match expected count."""
        shared = _kernel_function_names(_SharedStateBase)
        extraction_only = _kernel_function_names(ExtractionPhaseState) - shared
        formal_only = _kernel_function_names(FormalPhaseState) - shared
        synthesis_only = _kernel_function_names(SynthesisPhaseState) - shared

        assert len(shared) == 5
        assert len(extraction_only) == 6
        assert len(formal_only) == 13
        assert len(synthesis_only) == 4
        # Total: 5 + 6 + 13 + 4 = 28
