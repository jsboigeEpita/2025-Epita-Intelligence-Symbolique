"""Tests for modal logic bridge — _detect_and_run_modal_analysis (#563).

Validates that:
- Modal markers (epistemic/deontic/alethic) are detected in argument text
- Detected arguments produce modal_analysis_result entries
- Results are persisted to state.modal_analysis_results
- Skip when no modal markers present
- Skip when results already populated (idempotent)
- Both French and English markers are detected
- Enrichment summary reflects modal results
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestModalMarkerDetection:

    def _make_state_with_args(self, descriptions):
        """Helper: create state with arguments from descriptions."""
        state = UnifiedAnalysisState("Test text for modal analysis")
        arg_ids = []
        for desc in descriptions:
            arg_ids.append(state.add_argument(desc))
        return state, arg_ids

    def test_returns_none_for_empty_state(self):
        """No arguments → no modal analysis."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state = UnifiedAnalysisState("Test")
        result = _detect_and_run_modal_analysis(state)
        assert result is None

    def test_returns_none_without_modal_markers(self):
        """Arguments without modal language → no results."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._make_state_with_args([
            "The sky is blue",
            "Water boils at 100 degrees",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is None
        assert len(state.modal_analysis_results) == 0

    def test_detects_epistemic_english(self):
        """'believes/knows' triggers epistemic modality."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, arg_ids = self._make_state_with_args([
            "The witness knows the suspect was present",
            "The sky is blue",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        assert result["modal_results"] >= 1
        assert "epistemic" in result["modalities_found"]
        assert len(state.modal_analysis_results) >= 1

        # Verify the formula format
        ml = state.modal_analysis_results[0]
        assert "K(agent," in ml["formulas"][0]

    def test_detects_deontic_english(self):
        """'must/should' triggers deontic modality."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, arg_ids = self._make_state_with_args([
            "Citizens must pay taxes",
            "It rains often",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        assert "deontic" in result["modalities_found"]

        ml = state.modal_analysis_results[0]
        assert "O(" in ml["formulas"][0]

    def test_detects_alethic_english(self):
        """'possible/necessary' triggers alethic modality."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, arg_ids = self._make_state_with_args([
            "It is possible that the outcome changes",
            "Gravity exists",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        assert "alethic" in result["modalities_found"]

        ml = state.modal_analysis_results[0]
        assert "<>" in ml["formulas"][0]

    def test_detects_french_markers(self):
        """French modal markers (doit, possible) are detected."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._make_state_with_args([
            "Le citoyen doit respecter la loi",
            "Il est possible que la situation change",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        assert "deontic" in result["modalities_found"]
        assert "alethic" in result["modalities_found"]

    def test_multiple_modalities_single_argument(self):
        """An argument with both epistemic and deontic markers."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._make_state_with_args([
            "The expert knows that citizens should vote",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None

        ml = state.modal_analysis_results[0]
        assert len(ml["modalities"]) >= 2
        assert len(ml["formulas"]) >= 2

    def test_skip_if_already_populated(self):
        """Idempotent: skips if modal_analysis_results already has entries."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._make_state_with_args([
            "The witness believes the suspect is guilty",
        ])
        # Pre-populate
        state.add_modal_analysis_result(
            formulas=["K(existing)"], valid=True, modalities=["epistemic"]
        )
        result = _detect_and_run_modal_analysis(state)
        assert result is None
        assert len(state.modal_analysis_results) == 1  # Only the pre-existing one

    def test_persists_to_state_modal_analysis_results(self):
        """Results appear in state.modal_analysis_results list."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, arg_ids = self._make_state_with_args([
            "One must consider the possibility of error",
        ])
        _detect_and_run_modal_analysis(state)

        assert len(state.modal_analysis_results) >= 1
        ml = state.modal_analysis_results[0]
        assert "id" in ml
        assert "formulas" in ml
        assert "valid" in ml
        assert "modalities" in ml

    def test_state_snapshot_includes_modal_results(self):
        """State snapshot includes modal_analysis_count."""
        state = UnifiedAnalysisState("Test")
        state.add_argument("The expert knows the outcome is possible")
        state.add_modal_analysis_result(
            formulas=["K(agent, prop)"], valid=True, modalities=["epistemic"]
        )

        snapshot = state.get_state_snapshot(summarize=True)
        assert snapshot.get("modal_analysis_count", 0) >= 1

    def test_mixed_arguments_only_modal_get_results(self):
        """Only arguments with modal markers produce results."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_and_run_modal_analysis,
        )

        state, _ = self._make_state_with_args([
            "The cat sat on the mat",
            "Everyone must follow the rules",
            "The sun is bright",
            "Scientists believe the theory is correct",
        ])
        result = _detect_and_run_modal_analysis(state)
        assert result is not None
        # Only 2 arguments have modal markers
        assert result["modal_results"] == 2
        assert len(state.modal_analysis_results) == 2
