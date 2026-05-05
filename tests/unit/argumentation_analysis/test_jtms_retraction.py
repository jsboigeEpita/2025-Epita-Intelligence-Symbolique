"""Tests for JTMS retraction in StateManagerPlugin and ConversationalOrchestrator.

Validates that:
- StateManagerPlugin.jtms_retract_belief() correctly retracts beliefs and propagates
- _retract_fallacious_beliefs() scans state.identified_fallacies and retracts matching beliefs
- _resolve_phase_conflicts() detects fallacy-vs-quality conflicts
- ExtendedBelief attributes are used correctly (valid, context, record_modification)
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.services.jtms.extended_belief import JTMSSession


class TestStateManagerJTMSMethods:
    """Unit tests for JTMS @kernel_function methods in StateManagerPlugin."""

    def setup_method(self):
        self.state = RhetoricalAnalysisState("Test text for JTMS")
        self.plugin = StateManagerPlugin(self.state)

    def test_jtms_create_belief(self):
        """jtms_create_belief creates an ExtendedBelief in the session."""
        result = self.plugin.jtms_create_belief(
            belief_name="arg_1",
            agent_source="ExtractAgent",
            confidence=0.8,
            context='{"type": "premise"}',
        )
        assert "OK" in result
        assert hasattr(self.state, "_jtms_session")
        session = self.state._jtms_session
        assert "arg_1" in session.extended_beliefs
        eb = session.extended_beliefs["arg_1"]
        assert eb.agent_source == "ExtractAgent"
        assert eb.confidence == 0.8
        assert eb.context.get("type") == "premise"

    def test_jtms_create_belief_initializes_session(self):
        """First call creates the JTMS session on state."""
        assert not hasattr(self.state, "_jtms_session")
        self.plugin.jtms_create_belief("test_belief")
        assert hasattr(self.state, "_jtms_session")
        assert isinstance(self.state._jtms_session, JTMSSession)

    def test_jtms_add_justification(self):
        """jtms_add_justification creates a justification between beliefs."""
        self.plugin.jtms_create_belief("premise_A", agent_source="Extract")
        self.plugin.jtms_create_belief("conclusion_B", agent_source="Extract")
        result = self.plugin.jtms_add_justification(
            in_list=["premise_A"],
            out_list=[],
            conclusion="conclusion_B",
            agent_source="FormalAgent",
        )
        assert "OK" in result

    def test_jtms_query_beliefs_returns_json(self):
        """jtms_query_beliefs returns valid JSON with belief metadata."""
        self.plugin.jtms_create_belief(
            "belief_X", agent_source="Agent1", confidence=0.9
        )
        result = self.plugin.jtms_query_beliefs()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "belief_X"
        assert parsed[0]["agent_source"] == "Agent1"
        assert parsed[0]["confidence"] == 0.9

    def test_jtms_query_beliefs_with_filter(self):
        """jtms_query_beliefs filters by agent_source."""
        self.plugin.jtms_create_belief("b1", agent_source="Agent1")
        self.plugin.jtms_create_belief("b2", agent_source="Agent2")
        result = self.plugin.jtms_query_beliefs(agent_filter="Agent1")
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "b1"

    def test_jtms_check_consistency(self):
        """jtms_check_consistency returns valid JSON with consistency info."""
        self.plugin.jtms_create_belief("test_belief")
        result = self.plugin.jtms_check_consistency()
        parsed = json.loads(result)
        assert "is_consistent" in parsed
        assert "total_beliefs" in parsed
        assert parsed["total_beliefs"] == 1

    def test_jtms_retract_belief_success(self):
        """jtms_retract_belief sets validity to None and records retraction.

        After fix #296, ExtendedBelief.valid now reads from the same core JTMS
        belief object, so set_fact and retraction work correctly via the wrapper.
        """
        self.plugin.jtms_create_belief("arg_1", agent_source="Extract", confidence=0.8)
        session = self.state._jtms_session
        session.set_fact("arg_1", is_true=True)
        eb = session.extended_beliefs["arg_1"]
        # After #296 fix, wrapper reads from core JTMS belief
        assert eb.valid is True

        result = self.plugin.jtms_retract_belief(
            belief_name="arg_1", reason="fallacy: appeal to authority"
        )
        parsed = json.loads(result)
        assert parsed["retracted_belief"] == "arg_1"
        assert parsed["was_valid"] is True
        assert "appeal to authority" in parsed["reason"]

        # Verify retraction recorded in context
        assert eb.context.get("retracted") is True
        assert "appeal to authority" in eb.context.get("retraction_reason", "")

        # Verify modification history
        assert len(eb.modification_history) > 0
        last_mod = eb.modification_history[-1]
        assert last_mod["action"] == "retract"

        # Verify belief is now retracted (validity set to None)
        assert eb.valid is None

    def test_jtms_retract_belief_partial_match(self):
        """jtms_retract_belief finds beliefs by partial name match."""
        self.plugin.jtms_create_belief("argument_about_climate", agent_source="Extract")
        session = self.state._jtms_session
        session.set_fact("argument_about_climate", is_true=True)

        result = self.plugin.jtms_retract_belief(
            belief_name="climate", reason="fallacy: hasty generalization"
        )
        parsed = json.loads(result)
        assert parsed["retracted_belief"] == "argument_about_climate"

    def test_jtms_retract_belief_not_found(self):
        """jtms_retract_belief returns error for unknown belief."""
        self.plugin.jtms_create_belief("existing_belief")
        result = self.plugin.jtms_retract_belief(
            belief_name="nonexistent_xyz", reason="test"
        )
        assert "FUNC_ERROR" in result

    def test_jtms_retract_no_session(self):
        """jtms_retract_belief returns error when no session exists."""
        result = self.plugin.jtms_retract_belief(belief_name="anything", reason="test")
        assert "FUNC_ERROR" in result

    def test_add_belief_set_fol(self):
        """add_belief_set accepts 'fol' logic type."""
        result = self.plugin.add_belief_set(
            logic_type="fol", content="forall X: (Human(X) => Mortal(X))"
        )
        assert "FUNC_ERROR" not in result
        # FOL belief sets get prefix "fol_bs_" from shared_state
        assert "bs_" in result

    def test_add_belief_set_first_order(self):
        """add_belief_set accepts 'first_order' logic type."""
        result = self.plugin.add_belief_set(
            logic_type="first_order", content="exists X: Mortal(X)"
        )
        assert "FUNC_ERROR" not in result

    def test_add_belief_set_propositional(self):
        """add_belief_set accepts 'propositional' and 'pl' types."""
        r1 = self.plugin.add_belief_set(logic_type="propositional", content="p => q")
        r2 = self.plugin.add_belief_set(logic_type="pl", content="p && q")
        assert "FUNC_ERROR" not in r1
        assert "FUNC_ERROR" not in r2

    def test_add_belief_set_invalid_type(self):
        """add_belief_set rejects unknown logic types."""
        result = self.plugin.add_belief_set(logic_type="modal_s5", content="[]p")
        assert "FUNC_ERROR" in result


class TestRetractFallaciousBeliefs:
    """Tests for _retract_fallacious_beliefs in conversational_orchestrator."""

    def setup_method(self):
        self.state = RhetoricalAnalysisState("Test text")
        self.session = JTMSSession(session_id="test_jtms", owner_agent="test")
        self.state._jtms_session = self.session

    def test_retract_matching_fallacy(self):
        """Fallacy with target_argument_id matching a belief triggers retraction.

        Note: _retract_fallacious_beliefs checks ext_belief.valid (wrapper).
        Due to the dual-Belief design, we must set the wrapper's _jtms_belief
        to True for the retraction guard to pass.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        # Add a belief and set to valid — after #296, wrapper syncs with core
        self.session.add_belief("arg_1", agent_source="Extract", confidence=0.8)
        self.session.set_fact("arg_1", is_true=True)
        eb = self.session.extended_beliefs["arg_1"]
        assert eb.valid is True  # Works after #296 fix

        # Add a fallacy targeting arg_1
        self.state.add_fallacy(
            "appeal_to_authority",
            "Argument relies on authority rather than evidence",
            target_arg_id="arg_1",
        )

        result = _retract_fallacious_beliefs(self.state, "phase_1")
        assert result is not None
        assert result["retraction_count"] >= 1
        assert result["retractions"][0]["belief"] == "arg_1"
        assert result["retractions"][0]["fallacy_type"] == "appeal_to_authority"

        # Verify retraction metadata was recorded
        assert eb.context.get("retracted") is True

    def test_no_fallacies_returns_none(self):
        """No fallacies in state → returns None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        result = _retract_fallacious_beliefs(self.state, "phase_1")
        assert result is None

    def test_no_jtms_session_returns_none(self):
        """No JTMS session on state → returns None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        state_no_jtms = RhetoricalAnalysisState("Test")
        state_no_jtms.add_fallacy("type", "justification", "target")
        result = _retract_fallacious_beliefs(state_no_jtms, "phase_1")
        assert result is None

    def test_fallacy_without_matching_belief_skipped(self):
        """Fallacy targeting non-existent belief is skipped."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        self.session.add_belief("arg_1", agent_source="Extract")
        self.state.add_fallacy(
            "ad_hominem", "Attacks the person", target_arg_id="arg_999"
        )

        result = _retract_fallacious_beliefs(self.state, "phase_1")
        assert result is None  # No matching belief → no retraction

    def test_already_retracted_not_double_retracted(self):
        """Belief already retracted (valid=False/None) is not retracted again."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        self.session.add_belief("arg_1", agent_source="Extract")
        # Don't set_fact → belief starts with default validity (not True)
        self.state.add_fallacy("type", "just", target_arg_id="arg_1")

        result = _retract_fallacious_beliefs(self.state, "phase_1")
        # Belief was never set as fact (valid), so retraction is skipped
        assert result is None


class TestResolvePhaseConflicts:
    """Tests for _resolve_phase_conflicts in conversational_orchestrator."""

    @pytest.mark.asyncio
    async def test_no_conflicts_when_empty_state(self):
        """Empty state → no conflicts detected."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _resolve_phase_conflicts,
        )

        state = RhetoricalAnalysisState("Test")
        result = await _resolve_phase_conflicts(state, "phase_1")
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_identified_fallacies_not_fallacies(self):
        """Conflict detector reads state.identified_fallacies (dict), not state.fallacies."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _resolve_phase_conflicts,
        )

        state = RhetoricalAnalysisState("Test")
        # Add fallacy and quality score for same argument
        state.add_fallacy("ad_hominem", "Attacks person", target_arg_id="arg_1")

        # The function should access state.identified_fallacies without error
        # Even if no quality_scores exist, it should not raise AttributeError
        result = await _resolve_phase_conflicts(state, "phase_1")
        assert isinstance(result, list)
