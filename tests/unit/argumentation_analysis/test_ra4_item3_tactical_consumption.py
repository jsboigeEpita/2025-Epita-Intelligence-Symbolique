"""RA-4 #1049 item 3 — Tactical consumption of strategic objectives.

Verifies that invoke callables can read strategic objectives from the state
object passed via context, and that their output references the objective IDs.

Chain: PM writes objectives → bridge syncs to UnifiedAnalysisState →
       callable reads via _get_strategic_directives → output includes IDs.

These tests are UNIT-level: they test the helper and the injection wiring
without making LLM calls (mocked plugin/client).
"""

import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _get_strategic_directives,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Layer 6: _get_strategic_directives unit tests
# ---------------------------------------------------------------------------
class TestGetStrategicDirectives:
    """Unit tests for the strategic directives extraction helper."""

    def test_no_state_object_returns_empty(self):
        """Without _state_object, must return empty text and empty IDs."""
        text, ids = _get_strategic_directives({})
        assert text == ""
        assert ids == []

    def test_no_objectives_returns_empty(self):
        """With state but no objectives, must return empty."""
        state = MagicMock()
        state.strategic_objectives = []
        text, ids = _get_strategic_directives({"_state_object": state})
        assert text == ""
        assert ids == []

    def test_completed_objectives_filtered_out(self):
        """Objectives with status='completed' must not appear."""
        state = MagicMock()
        state.strategic_objectives = [
            {"objective_id": "obj-1", "description": "Done", "status": "completed"},
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert text == ""
        assert ids == []

    def test_active_objective_formatted(self):
        """Active objective must be formatted with ID and priority."""
        state = MagicMock()
        state.strategic_objectives = [
            {
                "objective_id": "obj-fallacy-1",
                "description": "Focus on ad hominem detection",
                "status": "active",
                "priority": "high",
            },
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert "obj-fallacy-1" in text
        assert "ad hominem detection" in text
        assert "high" in text
        assert ids == ["obj-fallacy-1"]

    def test_in_progress_objective_included(self):
        """Objectives with status='in_progress' must be included."""
        state = MagicMock()
        state.strategic_objectives = [
            {"id": "obj-42", "text": "Analyser la cohérence", "status": "in_progress"},
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert "obj-42" in text
        assert ids == ["obj-42"]

    def test_cap_at_five_objectives(self):
        """More than 5 active objectives must be capped."""
        state = MagicMock()
        state.strategic_objectives = [
            {"objective_id": f"obj-{i}", "description": f"Task {i}", "status": "active"}
            for i in range(10)
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert len(ids) == 5
        assert "obj-0" in text
        assert "obj-4" in text
        # obj-5 through obj-9 should NOT be present
        assert "obj-9" not in text

    def test_header_present_when_objectives_exist(self):
        """The STRATEGIC DIRECTIVES header must be present when objectives exist."""
        state = MagicMock()
        state.strategic_objectives = [
            {"objective_id": "obj-1", "description": "Test", "status": "active"},
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert "STRATEGIC DIRECTIVES" in text

    def test_description_fallback_to_text_key(self):
        """If 'description' is missing, fall back to 'text' key."""
        state = MagicMock()
        state.strategic_objectives = [
            {"objective_id": "obj-X", "text": "From text key", "status": "active"},
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert "From text key" in text

    def test_objective_without_description_skipped(self):
        """Objectives without description or text must be skipped."""
        state = MagicMock()
        state.strategic_objectives = [
            {"objective_id": "obj-empty", "status": "active"},
        ]
        text, ids = _get_strategic_directives({"_state_object": state})
        assert text == ""
        assert ids == []


# ---------------------------------------------------------------------------
# Layer 7: Write→Read chain (PM writes O → callable reads O → output refs O)
# ---------------------------------------------------------------------------
class TestWriteReadChain:
    """End-to-end chain: state has objectives → callable output references them."""

    def test_fallacy_callable_includes_strategic_ids(self):
        """_invoke_hierarchical_fallacy output must include strategic_objective_ids
        when the state has active objectives."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy,
        )

        # Build a real UnifiedAnalysisState with objectives
        state = UnifiedAnalysisState("Test text for strategic fallacy analysis.")
        state.strategic_objectives = [
            {
                "objective_id": "obj-fallacy-focus",
                "description": "Prioritize ad populum detection in political discourse",
                "status": "active",
                "priority": "high",
            },
        ]

        context = {
            "_state_object": state,
            "arguments": ["arg1", "arg2"],
        }

        # Mock the plugin to avoid LLM calls
        mock_result = json.dumps({
            "fallacies": [
                {
                    "fallacy_type": "ad_populum",
                    "confidence": 0.85,
                    "explanation": "Detected via strategic directive focus",
                }
            ],
            "exploration_method": "taxonomy_guided",
        })

        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(return_value=mock_result)

        # Mock at the import source — FallacyWorkflowPlugin is imported locally
        with patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.FallacyWorkflowPlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.core.llm_service.create_llm_service",
            return_value=MagicMock(),
        ), patch(
            "semantic_kernel.kernel.Kernel",
            return_value=MagicMock(),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_hierarchical_fallacy_per_argument",
            side_effect=ImportError("no enrichment"),
        ):
            result = _run(_invoke_hierarchical_fallacy("Test input", context))

        # Value-gate: output MUST reference the strategic objective
        assert "strategic_objective_ids" in result, (
            "Output must include strategic_objective_ids when state has active objectives"
        )
        assert "obj-fallacy-focus" in result["strategic_objective_ids"], (
            "strategic_objective_ids must contain the objective ID from state"
        )

    def test_fallacy_callable_no_ids_without_objectives(self):
        """When state has no objectives, output must NOT include strategic_objective_ids."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy,
        )

        state = UnifiedAnalysisState("Test text.")
        state.strategic_objectives = []

        context = {
            "_state_object": state,
            "arguments": ["arg1"],
        }

        mock_result = json.dumps({
            "fallacies": [],
            "exploration_method": "taxonomy_guided",
        })

        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(return_value=mock_result)

        with patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.FallacyWorkflowPlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.core.llm_service.create_llm_service",
            return_value=MagicMock(),
        ), patch(
            "semantic_kernel.kernel.Kernel",
            return_value=MagicMock(),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_hierarchical_fallacy_per_argument",
            side_effect=ImportError("no enrichment"),
        ):
            result = _run(_invoke_hierarchical_fallacy("Test input", context))

        assert "strategic_objective_ids" not in result, (
            "Output must NOT include strategic_objective_ids when no active objectives"
        )

    def test_fallacy_receives_directives_in_prompt(self):
        """Verify the LLM actually receives strategic directives in the argument_text."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy,
        )

        state = UnifiedAnalysisState("Test text.")
        state.strategic_objectives = [
            {
                "objective_id": "obj-directive-check",
                "description": "MANDATORY: detect appeal_to_authority",
                "status": "active",
                "priority": "high",
            },
        ]

        context = {"_state_object": state}

        mock_result = json.dumps({"fallacies": [], "exploration_method": "test"})
        mock_plugin = MagicMock()
        mock_plugin.run_guided_analysis = AsyncMock(return_value=mock_result)

        with patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.FallacyWorkflowPlugin",
            return_value=mock_plugin,
        ), patch(
            "argumentation_analysis.core.llm_service.create_llm_service",
            return_value=MagicMock(),
        ), patch(
            "semantic_kernel.kernel.Kernel",
            return_value=MagicMock(),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_hierarchical_fallacy_per_argument",
            side_effect=ImportError("no enrichment"),
        ):
            _run(_invoke_hierarchical_fallacy("Original input text", context))

        # The plugin must have been called with directives prepended
        call_args = mock_plugin.run_guided_analysis.call_args
        actual_text = call_args.kwargs.get("argument_text", "")
        assert "STRATEGIC DIRECTIVES" in actual_text, (
            "Plugin must receive strategic directives in argument_text"
        )
        assert "obj-directive-check" in actual_text, (
            "Plugin argument_text must contain the objective ID"
        )
        assert "Original input text" in actual_text, (
            "Original input text must be preserved after directives"
        )
