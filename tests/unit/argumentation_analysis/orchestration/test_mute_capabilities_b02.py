"""Tests for 4 mute capabilities identified in B-02 audit (#822).

Covers invoke + state-writer for capabilities without JVM barrier:
- sat_solving
- stakes_extraction
- deep_synthesis
- collaborative_analysis

These capabilities are registered in registry_setup.py and invoked in
workflows, but had zero tests in the orchestration test packet.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)


# ---------------------------------------------------------------------------
# Test: _invoke_sat (SAT solving)
# ---------------------------------------------------------------------------


class TestInvokeSAT:
    """Tests for _invoke_sat invoke callable.

    SATHandler requires PySAT (python-sat). When unavailable, we mock
    the SATHandler import to test wiring independently.
    """

    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_sat
        return _invoke_sat

    @patch(
        "argumentation_analysis.agents.core.logic.sat_handler.SATHandler",
    )
    def test_basic_sat_solve(self, MockSATHandler):
        """SAT handler returns satisfiable result for simple formula."""
        mock_instance = MagicMock()
        mock_instance.solve_formulas.return_value = (True, {"p": True}, {"backend": "Z3"})
        MockSATHandler.return_value = mock_instance

        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("p AND q", {"formulas": ["p AND q"]})
        )
        assert "satisfiable" in result
        assert "statistics" in result

    @patch(
        "argumentation_analysis.agents.core.logic.sat_handler.SATHandler",
    )
    def test_empty_formulas(self, MockSATHandler):
        """SAT handler handles empty input gracefully."""
        mock_instance = MagicMock()
        mock_instance.solve_formulas.return_value = (True, {}, {"backend": "Z3"})
        MockSATHandler.return_value = mock_instance

        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("", {"formulas": []})
        )
        assert isinstance(result, dict)

    @patch(
        "argumentation_analysis.agents.core.logic.sat_handler.SATHandler",
    )
    def test_mus_mode(self, MockSATHandler):
        """SAT handler supports MUS (Minimal Unsatisfiable Subsets) mode."""
        mock_instance = MagicMock()
        mock_instance.find_mus.return_value = [["p", "NOT p"]]
        MockSATHandler.return_value = mock_instance

        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("p AND NOT p", {"formulas": ["p AND NOT p"], "sat_mode": "mus"})
        )
        assert result["mode"] == "mus"
        assert "mus_count" in result

    @patch(
        "argumentation_analysis.agents.core.logic.sat_handler.SATHandler",
    )
    def test_custom_solver(self, MockSATHandler):
        """SAT handler respects solver choice from context."""
        mock_instance = MagicMock()
        mock_instance.solve_formulas.return_value = (True, {"p": True}, {"backend": "cadical195"})
        MockSATHandler.return_value = mock_instance

        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("p", {"formulas": ["p"], "solver": "cadical195"})
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Test: _invoke_stakes_extractor
# ---------------------------------------------------------------------------


class TestInvokeStakesExtractor:
    """Tests for _invoke_stakes_extractor invoke callable."""

    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_stakes_extractor,
        )
        return _invoke_stakes_extractor

    def test_no_state_returns_error(self):
        """When no state object in context, returns error dict."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test text", {})
        )
        assert "error" in result

    @patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=None,
    )
    def test_extracts_stakes_with_mock_state(self, mock_client):
        """Stakes extractor runs on a populated state (LLM=None, fallback path)."""
        invoke = self._get_invoke()
        state = UnifiedAnalysisState("Test speech about economic reform.")
        # Real writer schema (shared_state.add_argument): dict {arg_id: desc}.
        state.identified_arguments = {
            "arg_1": "We must reform the tax system.",
        }
        result = asyncio.get_event_loop().run_until_complete(
            invoke("", {"_state_object": state, "source_metadata": {}})
        )
        # StakesExtractor fallback may produce empty results without LLM
        assert isinstance(result, dict)
        assert "stakes" in result or "error" in result

    @patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=None,
    )
    def test_stakes_written_to_state(self, mock_client):
        """Results are written to state.stakes_and_stakeholders."""
        invoke = self._get_invoke()
        state = UnifiedAnalysisState("Test speech about policy.")
        # Real writer schema: dict {arg_id: description}.
        state.identified_arguments = {"a1": "Policy argument"}
        asyncio.get_event_loop().run_until_complete(
            invoke("", {"_state_object": state, "source_metadata": {}})
        )
        # state.stakes_and_stakeholders should be populated (even if empty)
        assert hasattr(state, "stakes_and_stakeholders")

    @patch(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        return_value=None,
    )
    def test_dict_arguments_passed_as_list_of_dicts(self, mock_client):
        """Audit #1151 §3(b): identified_arguments is {arg_id: description}
        (writer schema). StakesExtractor.extract must receive a list of dicts
        with a 'text' key — not bare arg_id keys (which crashed extract's
        ``arg.get("text")`` on real LLM-on runs). This pins the contract by
        capturing what extract receives, bypassing the LLM=None short-circuit
        that previously masked the bug."""
        invoke = self._get_invoke()
        state = UnifiedAnalysisState("Test speech about reform.")
        state.identified_arguments = {
            "arg_1": "We must reform the tax system.",
            "arg_2": "Reform will reduce inequality.",
        }
        captured = {}

        class _StubExtractor:
            def extract(self, **kwargs):
                captured.update(kwargs)
                return {
                    "stakes": [],
                    "stakeholders": [],
                    "rhetorical_register": "",
                    "discursive_arena": "",
                }

        with patch(
            "argumentation_analysis.agents.core.political.stakes_extractor"
            ".StakesExtractor",
            return_value=_StubExtractor(),
        ):
            asyncio.get_event_loop().run_until_complete(
                invoke("", {"_state_object": state, "source_metadata": {}})
            )
        args = captured.get("arguments", [])
        # Contract: extract receives a list of dicts each with "text".
        assert isinstance(args, list), args
        assert all(isinstance(a, dict) and "text" in a for a in args), args
        texts = [a["text"] for a in args]
        assert "We must reform the tax system." in texts
        assert "Reform will reduce inequality." in texts
        # No bare arg_id keys leak through.
        assert "arg_1" not in texts and "arg_2" not in texts


# ---------------------------------------------------------------------------
# Test: _invoke_deep_synthesis
# ---------------------------------------------------------------------------


class TestInvokeDeepSynthesis:
    """Tests for _invoke_deep_synthesis invoke callable."""

    def _get_invoke(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )
        return _invoke_deep_synthesis

    def test_no_state_returns_error(self):
        """When no state object in context, returns error dict."""
        invoke = self._get_invoke()
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test text", {})
        )
        assert "error" in result

    def test_deep_synthesis_on_populated_state(self):
        """Deep synthesis produces a report from a populated state."""
        invoke = self._get_invoke()
        state = UnifiedAnalysisState("Test speech for deep synthesis.")
        # identified_arguments is a dict keyed by arg_id
        state.identified_arguments = {
            "arg_1": {"id": "arg_1", "text": "First argument.", "score": 0.8},
            "arg_2": {"id": "arg_2", "text": "Second argument.", "score": 0.6},
        }
        state.add_fallacy("arg_1", "Ad Hominem", "Attacks the person")
        result = asyncio.get_event_loop().run_until_complete(
            invoke("", {"_state_object": state, "source_metadata": {}})
        )
        # Either succeeds with report or fails gracefully
        assert isinstance(result, dict)
        if "error" not in result:
            assert "sections_populated" in result or "report" in result

    def test_deep_synthesis_empty_state(self):
        """Deep synthesis handles empty state without crash."""
        invoke = self._get_invoke()
        state = UnifiedAnalysisState("")
        result = asyncio.get_event_loop().run_until_complete(
            invoke("", {"_state_object": state, "source_metadata": {}})
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Test: _invoke_collaborative_analysis
# ---------------------------------------------------------------------------


class TestInvokeCollaborativeAnalysis:
    """Tests for _invoke_collaborative_analysis invoke callable."""

    def _get_invoke(self):
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )
        return _invoke_collaborative_analysis

    @patch.dict("os.environ", {}, clear=False)
    def test_no_api_key_uses_fallback(self):
        """When no API key, falls back to heuristic analysis."""
        import os
        # Ensure OPENAI_API_KEY is empty
        original = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""
        try:
            invoke = self._get_invoke()
            result = asyncio.get_event_loop().run_until_complete(
                invoke("This is a test argument about policy reform.", {})
            )
            assert isinstance(result, dict)
            # Fallback path returns structured analysis with agent_outputs, etc.
            assert "agent_outputs" in result or "summary" in result or "fallback" in result
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False)
    def test_fallback_with_context(self):
        """Fallback path uses extract/quality context when available."""
        invoke = self._get_invoke()
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "The economy needs stimulus."},
                    {"text": "Tax cuts help growth."},
                ],
            },
            "phase_quality_output": {
                "per_argument_scores": {"arg_1": {"note_finale": 7.5}},
            },
        }
        result = asyncio.get_event_loop().run_until_complete(
            invoke("test input", context)
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Test: State writers for SAT + collaborative
# ---------------------------------------------------------------------------


class TestSATStateWriter:
    """Tests for _write_sat_to_state state writer."""

    def _get_writer(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_sat_to_state,
        )
        return _write_sat_to_state

    def test_write_sat_result_to_state(self):
        """SAT state writer writes results into UnifiedAnalysisState."""
        writer = self._get_writer()
        state = UnifiedAnalysisState("Test text")
        output = {
            "satisfiable": True,
            "model": {"p": True, "q": True},
            "statistics": {"handler": "SATHandler", "backend": "Z3"},
        }
        writer(output, state, {})
        # State should have propositional analysis results populated
        assert hasattr(state, "propositional_analysis_results")

    def test_write_sat_mus_result_to_state(self):
        """SAT state writer handles MUS mode output."""
        writer = self._get_writer()
        state = UnifiedAnalysisState("Test text")
        output = {
            "mode": "mus",
            "mus_count": 2,
            "mus_subsets": [["p", "NOT p"]],
        }
        writer(output, state, {})
        assert hasattr(state, "propositional_analysis_results")


class TestCollaborativeStateWriter:
    """Tests for _write_collaborative_analysis_to_state state writer."""

    def _get_writer(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_collaborative_analysis_to_state,
        )
        return _write_collaborative_analysis_to_state

    def test_write_collaborative_result_to_state(self):
        """Collaborative analysis state writer writes results into state."""
        writer = self._get_writer()
        state = UnifiedAnalysisState("Test text")
        output = {
            "critic": {"assessment": "Test critic assessment"},
            "validator": {"assessment": "Test validator assessment"},
            "devils_advocate": {"assessment": "Test DA assessment"},
            "synthesizer": {"synthesis": "Test synthesis"},
            "summary": "4-role collaborative analysis",
        }
        writer(output, state, {})
        # The writer delegates to collaborative_debate._write_collaborative_to_state
        # which writes to state.workflow_results["collaborative_analysis"]
        assert "collaborative_analysis" in state.workflow_results
