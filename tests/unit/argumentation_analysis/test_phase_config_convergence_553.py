"""Tests for #553: phase max_turns configurability + _check_convergence field mapping fix."""

import inspect
import pytest

from argumentation_analysis.orchestration.conversational_orchestrator import (
    run_conversational_analysis,
)
from argumentation_analysis.orchestration.trace_analyzer import ConversationalTraceAnalyzer


class TestConvergenceFieldMapping:
    """Fix 1: _check_convergence reports correct arguments_found from dict state."""

    def test_arguments_found_from_dict(self):
        """identified_arguments is a Dict[str, str], not a list — must be counted."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {
            "identified_arguments": {
                "arg_001": "First argument",
                "arg_002": "Second argument",
                "arg_003": "Third argument",
            }
        }
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.arguments_found == 3

    def test_arguments_found_from_list_backwards_compat(self):
        """If someone passes a list, still works."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {"identified_arguments": ["arg1", "arg2"]}
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.arguments_found == 2

    def test_arguments_found_zero_when_missing(self):
        """No identified_arguments key → 0."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {"other_field": "value"}
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.arguments_found == 0

    def test_arguments_found_zero_when_empty_dict(self):
        """Empty dict → 0."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {"identified_arguments": {}}
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.arguments_found == 0

    def test_fallacies_still_counted(self):
        """identified_fallacies (list) should still work."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {
            "identified_fallacies": [
                {"type": "ad_hominem"},
                {"type": "straw_man"},
            ]
        }
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.fallacies_found == 2

    def test_counter_arguments_counted(self):
        """counter_arguments (list) should still work."""
        analyzer = ConversationalTraceAnalyzer()
        snapshot = {
            "counter_arguments": [
                {"strategy": "reductio"},
                {"strategy": "counter_example"},
            ]
        }
        metrics = analyzer.compute_convergence(snapshot)
        assert metrics.counter_arguments_count == 2


class TestPhaseMaxTurnsConfigurable:
    """Fix 2: phase max_turns are configurable via function params."""

    def test_function_accepts_four_turn_params(self):
        """run_conversational_analysis has extraction/formal/synthesis/reanalysis params."""
        sig = inspect.signature(run_conversational_analysis)
        assert "extraction_max_turns" in sig.parameters
        assert "formal_max_turns" in sig.parameters
        assert "synthesis_max_turns" in sig.parameters
        assert "reanalysis_max_turns" in sig.parameters

    def test_defaults_match_previous_hardcoded(self):
        """Defaults should match the previous hardcoded values (7, 5, 10, 5)."""
        sig = inspect.signature(run_conversational_analysis)
        assert sig.parameters["extraction_max_turns"].default == 7
        assert sig.parameters["formal_max_turns"].default == 5
        assert sig.parameters["synthesis_max_turns"].default == 10
        assert sig.parameters["reanalysis_max_turns"].default == 5

    def test_no_hardcoded_max_turns_in_phase_configs_source(self):
        """Verify hardcoded integers are removed from phase_configs in source."""
        import argumentation_analysis.orchestration.conversational_orchestrator as mod

        source = inspect.getsource(mod)
        # Check that the phase config section uses the param names, not literals
        # The pattern '"max_turns": 7,' or '"max_turns": 5,' should NOT appear
        # (only the param references like extraction_max_turns should)
        for hardcoded in ['"max_turns": 7,', '"max_turns": 5,', '"max_turns": 10,']:
            assert hardcoded not in source, (
                f"Found hardcoded {hardcoded} in source — should use param instead"
            )
