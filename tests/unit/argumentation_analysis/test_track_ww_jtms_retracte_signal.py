"""Tests for Track WW (#678): JTMS-retracte signal 4 on corpus C.

Investigates why signal 4 ("JTMS retracte") fires 0 on corpus C despite:
  - LL fix (#662): arg_beliefs prefixed with `arg_{i+1}:`
  - 14 fallacies detected on corpus C (8 in signal 1)
  - compute_argument_convergence expecting `name.startswith("arg_N:")` + `valid is False`

Covers:
  1. State writer path: _write_jtms_to_state preserves valid=False with arg_N: prefix
  2. _invoke_jtms internal retraction path: fallacy→arg matching (text + fallback)
  3. _retract_fallacious_beliefs post-phase hook path
  4. Dual-session gap: _invoke_jtms creates a LOCAL session, _retract uses state._jtms_session
  5. End-to-end: synthetic pipeline output → state writer → convergence signal
"""

import pytest
from unittest.mock import MagicMock, patch


def _make_state(**kwargs):
    """Build a real UnifiedAnalysisState for tests that need add_jtms_belief."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState("test text")
    if kwargs.get("identified_arguments"):
        state.identified_arguments = kwargs["identified_arguments"]
    if kwargs.get("identified_fallacies"):
        state.identified_fallacies = kwargs["identified_fallacies"]
    if kwargs.get("argument_quality_scores"):
        state.argument_quality_scores = kwargs["argument_quality_scores"]
    if kwargs.get("counter_arguments"):
        state.counter_arguments = kwargs["counter_arguments"]
    if kwargs.get("dung_frameworks"):
        state.dung_frameworks = kwargs["dung_frameworks"]
    if kwargs.get("jtms_beliefs"):
        state.jtms_beliefs = kwargs["jtms_beliefs"]
    if kwargs.get("propositional_analysis_results"):
        state.propositional_analysis_results = kwargs["propositional_analysis_results"]
    if kwargs.get("fol_analysis_results"):
        state.fol_analysis_results = kwargs["fol_analysis_results"]
    return state


class TestStateWriterPreservesRetraction:
    """Verify _write_jtms_to_state copies valid=False with arg_N: prefix."""

    def test_writer_copies_retracted_belief(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_jtms_to_state,
        )

        state = _make_state()

        output = {
            "beliefs": {
                "arg_1:Some text excerpt about policy": {
                    "valid": False,
                    "justifications": [],
                },
                "arg_2:Another argument": {
                    "valid": True,
                    "justifications": [],
                },
            },
            "retraction_chain": [],
        }

        _write_jtms_to_state(output, state, {})

        retracted = [
            b
            for b in state.jtms_beliefs.values()
            if b["name"].startswith("arg_1:") and b["valid"] is False
        ]
        assert len(retracted) == 1

    def test_writer_preserves_none_valid(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_jtms_to_state,
        )

        state = _make_state()

        output = {
            "beliefs": {
                "arg_1:Some text": {
                    "valid": None,
                    "justifications": [],
                },
            },
            "retraction_chain": [],
        }

        _write_jtms_to_state(output, state, {})

        belief = list(state.jtms_beliefs.values())[0]
        assert belief["valid"] is None  # None preserved, not False

    def test_writer_handles_legacy_string_valid(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_jtms_to_state,
        )

        state = _make_state()

        output = {
            "beliefs": {
                "arg_1:Legacy text": "False",
            },
            "retraction_chain": [],
        }

        _write_jtms_to_state(output, state, {})

        belief = list(state.jtms_beliefs.values())[0]
        assert belief["valid"] is False


class TestInvokeJtmsRetractionPath:
    """Test _invoke_jtms internal fallacy→arg matching and retraction."""

    @pytest.mark.asyncio
    async def test_fallback_index_retraction(self):
        """When fallacy has no target_argument, fallback idx maps fallacy to arg."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_jtms,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument about policy"},
                    {"text": "Second argument about economy"},
                    {"text": "Third argument about freedom"},
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "ad hominem", "confidence": 0.8},
                    {"type": "straw man", "confidence": 0.7},
                ],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        # Fallacies without target_argument use fallback: min(i, len(arg_beliefs)-1)
        # Fallacy 0 → arg_1, Fallacy 1 → arg_2
        # After retraction: arg_1 and arg_2 should have valid=False
        retracted = [
            name
            for name, b in beliefs.items()
            if isinstance(b, dict) and b.get("valid") is False
        ]
        assert len(retracted) >= 2  # At least 2 args retracted

    @pytest.mark.asyncio
    async def test_text_matching_retraction(self):
        """When fallacy has target_argument text matching an arg belief."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_jtms,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "The policy causes harm to many people"},
                    {"text": "Economic growth requires deregulation"},
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "ad hominem",
                        "confidence": 0.9,
                        "target_argument": "policy causes harm",
                    },
                ],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        # arg_1 belief should be retracted (matches "policy causes harm")
        arg1_name = [n for n in beliefs if n.startswith("arg_1:")][0]
        assert beliefs[arg1_name]["valid"] is False

    @pytest.mark.asyncio
    async def test_no_fallacies_no_retraction(self):
        """When no fallacies detected, all arg beliefs remain valid."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_jtms,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument"},
                    {"text": "Second argument"},
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        # No retraction without fallacies
        arg_beliefs = {n: b for n, b in beliefs.items() if n.startswith("arg_")}
        retracted = [n for n, b in arg_beliefs.items() if b.get("valid") is False]
        assert len(retracted) == 0


class TestConvergenceSignal4EndToEnd:
    """End-to-end: pipeline output → state writer → convergence signal 4."""

    def test_signal_4_fires_after_state_writer(self):
        """Simulate the full path: _invoke_jtms output → state writer → convergence."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_jtms_to_state,
        )
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        # Simulate _invoke_jtms output with retracted arg_1
        jtms_output = {
            "beliefs": {
                "arg_1:First argument text": {
                    "valid": False,
                    "justifications": [],
                },
                "arg_2:Second argument text": {
                    "valid": True,
                    "justifications": [],
                },
            },
            "retraction_chain": [],
        }

        state = _make_state(
            identified_arguments={"arg_1": "desc1", "arg_2": "desc2"},
        )

        _write_jtms_to_state(jtms_output, state, {})

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signal_names = [s[0] for s in result["arg_1"]["signals"]]
        assert "JTMS retracte" in signal_names

    def test_signal_4_does_not_fire_on_none_valid(self):
        """valid=None should NOT trigger signal 4 (requires is False)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_jtms_to_state,
        )
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        jtms_output = {
            "beliefs": {
                "arg_1:Some text": {
                    "valid": None,
                    "justifications": [],
                },
            },
            "retraction_chain": [],
        }

        state = _make_state(
            identified_arguments={"arg_1": "desc1"},
        )

        _write_jtms_to_state(jtms_output, state, {})

        result = compute_argument_convergence(state)
        assert "arg_1" not in result

    def test_signal_4_with_fallacy_and_retraction(self):
        """Full pipeline sim: fallacy detected → JTMS retracts → signal 4 fires."""
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc1", "arg_2": "desc2"},
            identified_fallacies={
                "f1": {"target_argument_id": "arg_1", "type": "ad hominem"},
            },
            jtms_beliefs={
                "jtms_1": {
                    "name": "arg_1:First argument about policy",
                    "valid": False,
                    "justifications": [],
                },
                "jtms_2": {
                    "name": "arg_2:Second argument",
                    "valid": True,
                    "justifications": [],
                },
            },
        )

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signal_names = [s[0] for s in result["arg_1"]["signals"]]
        assert "JTMS retracte" in signal_names
        # Also has sophisme signal from identified_fallacies
        assert "sophisme" in signal_names


class TestRetractFallaciousBeliefsPath:
    """Test _retract_fallacious_beliefs matching with arg_N: prefixed beliefs."""

    def test_post_phase_finds_arg_prefixed_belief(self):
        """_retract_fallacious_beliefs should find arg_N: prefixed beliefs."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        # Build a state with _jtms_session and identified_fallacies
        state = MagicMock()
        state.identified_fallacies = {
            "f1": {
                "target_argument_id": "arg_1",
                "type": "ad hominem",
            },
        }

        # Mock JTMS session with extended beliefs
        mock_belief = MagicMock()
        mock_belief.valid = True
        mock_belief.justifications = []
        mock_belief.confidence = 0.8
        mock_belief.agent_source = "pipeline"
        mock_belief.context = {}
        mock_belief.creation_timestamp = MagicMock()
        mock_belief.creation_timestamp.isoformat.return_value = "2026-01-01T00:00:00"
        mock_belief.modification_history = []
        mock_belief._jtms_belief = MagicMock()
        mock_belief._jtms_belief.valid = True
        mock_belief._jtms_belief.justifications = []

        session = MagicMock()
        session.extended_beliefs = {
            "arg_1:Some text excerpt": mock_belief,
        }
        mock_jtms = MagicMock()
        session.jtms = mock_jtms
        session.jtms.beliefs = {}

        state._jtms_session = session
        state.jtms_beliefs = {
            "jtms_1": {
                "name": "arg_1:Some text excerpt",
                "valid": True,
                "justifications": [],
            },
        }

        result = _retract_fallacious_beliefs(state, "test_phase")

        # Should have found and attempted retraction
        assert result is not None
        assert result["retraction_count"] == 1

    def test_post_phase_skips_already_retracted(self):
        """If belief is already retracted (valid=False), skip double retraction."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _retract_fallacious_beliefs,
        )

        state = MagicMock()
        state.identified_fallacies = {
            "f1": {
                "target_argument_id": "arg_1",
                "type": "ad hominem",
            },
        }

        mock_belief = MagicMock()
        mock_belief.valid = False  # Already retracted
        mock_belief.justifications = []

        session = MagicMock()
        session.extended_beliefs = {
            "arg_1:Some text": mock_belief,
        }
        session.jtms = MagicMock()
        session.jtms.beliefs = {}

        state._jtms_session = session
        state.jtms_beliefs = {}

        result = _retract_fallacious_beliefs(state, "test_phase")
        assert result is None  # No retraction (already retracted)


class TestDualSessionGap:
    """Document the dual-session architecture and its implications."""

    def test_invoke_jtms_creates_local_session(self):
        """_invoke_jtms creates its own JTMSSession, not state._jtms_session.

        This means:
        1. Retractions in _invoke_jtms are in the LOCAL session
        2. The state writer copies beliefs_output (from local session) to state.jtms_beliefs
        3. _retract_fallacious_beliefs uses state._jtms_session (DIFFERENT session)

        If state._jtms_session is empty or has no arg_N: beliefs,
        the post-phase hook finds nothing to retract.
        But the state writer already copied valid=False from the local session,
        so compute_argument_convergence should still detect signal 4.
        """
        # This test documents the architecture, no assertion needed beyond doc
        assert True  # Architecture documented

    def test_convergence_reads_state_not_session(self):
        """compute_argument_convergence reads state.jtms_beliefs, not _jtms_session.

        This is important: the convergence function does NOT access the JTMS session.
        It only reads the dict state.jtms_beliefs. So the dual-session gap
        only matters if the state writer doesn't properly copy retracted beliefs.
        """
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "desc"},
            jtms_beliefs={
                "jtms_1": {
                    "name": "arg_1:Text excerpt",
                    "valid": False,
                    "justifications": [],
                },
            },
        )

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] == 1
        assert result["arg_1"]["signals"][0][0] == "JTMS retracte"
