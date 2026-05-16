"""Tests for JTMS belief sync bridge — _jtms_session → state.jtms_beliefs (#562).

Validates that:
- jtms_create_belief() also writes to state.jtms_beliefs dict
- jtms_retract_belief() also updates state.jtms_beliefs dict
- _retract_fallacious_beliefs() also updates state.jtms_beliefs dict
- Enrichment summary counts beliefs from both paths
- Re-analysis trigger detects retractions via synced dict
"""

import json
import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.services.jtms.extended_belief import JTMSSession


class TestJTMSBeliefSync:
    """Bridge: jtms_create_belief → state.jtms_beliefs dict."""

    def setup_method(self):
        self.state = UnifiedAnalysisState("Test text for JTMS sync")
        self.plugin = StateManagerPlugin(self.state)

    def test_create_belief_syncs_to_dict(self):
        """jtms_create_belief writes to both session AND state.jtms_beliefs."""
        result = self.plugin.jtms_create_belief(
            belief_name="arg_1",
            agent_source="ExtractAgent",
            confidence=0.8,
        )
        assert "OK" in result

        # Session should have it
        assert hasattr(self.state, "_jtms_session")
        assert "arg_1" in self.state._jtms_session.extended_beliefs

        # Dict should also have it (the bridge)
        assert len(self.state.jtms_beliefs) >= 1
        dict_names = [b["name"] for b in self.state.jtms_beliefs.values()]
        assert "arg_1" in dict_names

    def test_create_belief_dict_has_valid_true(self):
        """Synced dict entry starts with valid=True."""
        self.plugin.jtms_create_belief("arg_test", agent_source="Test")
        for bid, bdata in self.state.jtms_beliefs.items():
            if bdata.get("name") == "arg_test":
                assert bdata["valid"] is True
                return
        pytest.fail("arg_test not found in state.jtms_beliefs")

    def test_multiple_beliefs_synced(self):
        """Multiple jtms_create_belief calls all sync to dict."""
        for i in range(5):
            self.plugin.jtms_create_belief(f"arg_{i}", agent_source="Extract")

        dict_names = [b["name"] for b in self.state.jtms_beliefs.values()]
        for i in range(5):
            assert f"arg_{i}" in dict_names

    def test_enrichment_summary_counts_synced_beliefs(self):
        """Enrichment summary with_jtms count reflects synced beliefs."""
        # add_argument takes only description, auto-generates ID
        arg_id = self.state.add_argument("Socrates is mortal")
        # Create belief with matching name pattern
        self.plugin.jtms_create_belief(arg_id, agent_source="Extract")

        enrichment = self.state.get_enrichment_summary()
        assert enrichment["with_jtms_belief"] >= 1

    def test_enrichment_summary_zero_without_sync(self):
        """Without the bridge, enrichment would show 0."""
        arg_id = self.state.add_argument("Socrates is mortal")
        # Create belief via session only (bypassing plugin)
        session = JTMSSession(session_id="test", owner_agent="test")
        self.state._jtms_session = session
        session.add_belief(arg_id, agent_source="Extract")

        # Session has it but dict doesn't
        assert arg_id in session.extended_beliefs
        assert len(self.state.jtms_beliefs) == 0

        enrichment = self.state.get_enrichment_summary()
        assert enrichment["with_jtms_belief"] == 0


class TestJTMSRetractionSync:
    """Bridge: retraction updates state.jtms_beliefs dict."""

    def setup_method(self):
        self.state = UnifiedAnalysisState("Test text for retraction sync")
        self.plugin = StateManagerPlugin(self.state)

    def test_retract_belief_updates_dict(self):
        """jtms_retract_belief sets valid=False in state.jtms_beliefs."""
        self.plugin.jtms_create_belief("arg_1", agent_source="Extract")
        session = self.state._jtms_session
        session.set_fact("arg_1", is_true=True)

        # Find the dict entry
        dict_entry = None
        for bid, bdata in self.state.jtms_beliefs.items():
            if bdata.get("name") == "arg_1":
                dict_entry = bdata
                break
        assert dict_entry is not None
        assert dict_entry["valid"] is True

        # Retract
        result = self.plugin.jtms_retract_belief("arg_1", reason="fallacy: test")
        parsed = json.loads(result)
        assert parsed["retracted_belief"] == "arg_1"

        # Dict entry should now show retracted
        assert dict_entry["valid"] is False
        assert dict_entry.get("retracted") is True
        assert "test" in dict_entry.get("retraction_reason", "")

    def test_retraction_visible_in_dict(self):
        """After retract via plugin, state.jtms_beliefs has valid=False."""
        arg_id = self.state.add_argument("Test argument text")
        self.plugin.jtms_create_belief(arg_id, agent_source="Extract")

        session = self.state._jtms_session
        session.set_fact(arg_id, is_true=True)
        self.plugin.jtms_retract_belief(arg_id, reason="fallacy: test")

        # Check dict has the retraction
        has_retraction = False
        for bid, bdata in self.state.jtms_beliefs.items():
            if bdata.get("valid") is False:
                has_retraction = True
                break
        assert has_retraction


class TestRetractFallaciousBeliefsSync:
    """Bridge: _retract_fallacious_beliefs updates state.jtms_beliefs."""

    def test_orchestrator_retraction_syncs_to_dict(self):
        """_retract_fallacious_beliefs also syncs retraction to state.jtms_beliefs."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        state = UnifiedAnalysisState("Test text")
        session = JTMSSession(session_id="test", owner_agent="test")
        state._jtms_session = session

        # Create argument via auto-ID
        arg_id = state.add_argument("Test argument")
        # Create belief in session AND sync to dict
        session.add_belief(arg_id, agent_source="Extract")
        session.set_fact(arg_id, is_true=True)
        state.add_jtms_belief(name=arg_id, valid=True, justifications=[])

        # Add fallacy targeting the argument
        state.add_fallacy("ad_hominem", "Attacks the person", target_arg_id=arg_id)

        result = _retract_fallacious_beliefs(state, "phase_1")
        assert result is not None

        # Dict should show retracted
        for bid, bdata in state.jtms_beliefs.items():
            if bdata.get("name") == arg_id:
                assert bdata["valid"] is False
                assert bdata.get("retracted") is True
                return
        pytest.fail(f"{arg_id} not found in state.jtms_beliefs after retraction")


class TestJTMSBeliefPerArgument:
    """End-to-end: every identified_argument gets a JTMS belief."""

    def test_all_arguments_get_beliefs(self):
        """After wiring, jtms_beliefs count >= identified_arguments count."""
        state = UnifiedAnalysisState("Test text for per-argument beliefs")
        plugin = StateManagerPlugin(state)

        # Simulate argument extraction (auto-generated IDs)
        arg_ids = []
        descriptions = [
            "First argument about X",
            "Second argument about Y",
            "Third argument about Z",
        ]
        for desc in descriptions:
            arg_id = state.add_argument(desc)
            arg_ids.append(arg_id)
            plugin.jtms_create_belief(arg_id, agent_source="ExtractAgent")

        # Verify each argument has a corresponding belief
        dict_names = {b["name"] for b in state.jtms_beliefs.values()}
        for arg_id in arg_ids:
            assert arg_id in dict_names

        # Enrichment should count all
        enrichment = state.get_enrichment_summary()
        assert enrichment["with_jtms_belief"] == len(arg_ids)
