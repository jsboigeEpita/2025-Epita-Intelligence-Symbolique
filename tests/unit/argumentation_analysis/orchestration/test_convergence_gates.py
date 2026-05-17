"""Tests for convergence gate invariants (#590).

Verifies that _check_convergence does NOT cause premature phase exit
when final_conclusion is set during non-Synthesis phases.
"""
import pytest
from unittest.mock import MagicMock


class TestConvergencePhaseIsolation:
    """final_conclusion set in Phase 1 must NOT cause Phase 2/3 convergence."""

    def _make_state(self, final_conclusion=None):
        state = MagicMock()
        state.final_conclusion = final_conclusion
        return state

    def test_convergence_not_triggered_in_extraction_phase_with_conclusion(self):
        """Phase 1 (Extraction) should NOT converge just because final_conclusion is set."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion="Some early conclusion")
        messages = [
            {"content": "Extracting argument structures from the source text"},
            {"content": "Found multiple argument types in this passage"},
            {"content": "Completed initial extraction of premises and conclusions"},
        ]

        result = _check_convergence(state, "Extraction & Detection", messages)
        assert result is False, "Extraction phase must NOT converge on final_conclusion"

    def test_convergence_not_triggered_in_formal_phase_with_conclusion(self):
        """Phase 2 (Formal Analysis) should NOT converge just because final_conclusion is set."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion="Some early conclusion")
        messages = [
            {"content": "Performing formal verification of argument logic"},
            {"content": "Quality score computed for all extracted arguments"},
        ]

        result = _check_convergence(state, "Formal Analysis & Quality", messages)
        assert result is False, "Formal Analysis phase must NOT converge on final_conclusion"

    def test_convergence_triggered_in_synthesis_phase_with_conclusion(self):
        """Phase 3 (Synthesis) SHOULD converge when final_conclusion is set."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion="Final analysis complete")
        messages = [{"content": "Debate synthesis producing comprehensive analysis results"}]

        result = _check_convergence(state, "Synthesis & Debate", messages)
        assert result is True, "Synthesis phase SHOULD converge on final_conclusion"

    def test_convergence_triggered_in_deep_synthesis_with_conclusion(self):
        """Deep Synthesis phase should also converge on final_conclusion."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion="Deep synthesis complete")
        messages = [{"content": "Deep synthesis producing final integrated report"}]

        result = _check_convergence(state, "Deep Synthesis", messages)
        assert result is True

    def test_no_convergence_without_conclusion(self):
        """No phase converges without final_conclusion (barring stagnation)."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion=None)
        messages = [{"content": "Normal processing result with sufficient content length"}]

        for phase_name in [
            "Extraction & Detection",
            "Formal Analysis & Quality",
            "Synthesis & Debate",
            "Re-Analysis",
        ]:
            result = _check_convergence(state, phase_name, messages)
            assert result is False, f"Phase '{phase_name}' converged without conclusion"

    def test_stagnation_detection_still_works(self):
        """Stagnation (2 consecutive short messages) still triggers convergence."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion=None)
        messages = [
            {"content": "normal analysis result here"},
            {"content": "another result"},
            {"content": "(empty)"},
            {"content": ""},
        ]

        result = _check_convergence(state, "Extraction & Detection", messages)
        assert result is True, "Stagnation should still trigger convergence"

    def test_reanalysis_phase_not_affected_by_conclusion(self):
        """Re-Analysis phase should NOT converge on final_conclusion from prior phase."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state(final_conclusion="Set during earlier phase")
        messages = [{"content": "Re-analyzing arguments with updated context information"}]

        result = _check_convergence(state, "Re-Analysis", messages)
        assert result is False, "Re-Analysis phase must NOT converge on stale final_conclusion"


class TestPhaseSequenceInvariants:
    """Verify that phases 1-3 all get a chance to run with realistic state."""

    def test_three_phases_run_despite_early_conclusion_in_state(self):
        """Simulate the full phase loop and verify all 3 phases get turns."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _check_convergence,
        )

        state = self._make_state_with_conclusion_after_phase1()

        phase_names = [
            "Extraction & Detection",
            "Formal Analysis & Quality",
            "Synthesis & Debate",
        ]

        results = []
        messages = [{"content": "Turn result with enough content to avoid stagnation"}]
        for phase_name in phase_names:
            converged = _check_convergence(state, phase_name, messages)
            results.append((phase_name, converged))

        # Only Synthesis should have converged
        assert results[0][1] is False, f"{results[0][0]} converged prematurely"
        assert results[1][1] is False, f"{results[1][0]} converged prematurely"
        assert results[2][1] is True, f"{results[2][0]} did not converge"

    def _make_state_with_conclusion_after_phase1(self):
        """Simulate state after Phase 1 has set final_conclusion."""
        state = MagicMock()
        state.final_conclusion = (
            "Tous les arguments identifiés et analysés. "
            "Aucun sophisme détecté."
        )
        return state
