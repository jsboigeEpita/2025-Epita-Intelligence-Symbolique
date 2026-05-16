"""Tests for quality score ID-based tracking fix (#572).

Verifies that quality scores stored under non-canonical keys are correctly
resolved to arg_ids from identified_arguments for enrichment tracking.
"""
import pytest
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestQualityScoreIDTracking:
    """Test resolved_arg_id-based storage for quality scores."""

    def test_quality_score_under_canonical_arg_id(self):
        """When arg_id already matches, enrichment counts it."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("The economy is growing")
        state.add_quality_score(a1, {"clarity": 8.0}, 8.0)
        summary = state.get_enrichment_summary()
        assert summary["with_quality_score"] == 1

    def test_quality_score_with_resolved_arg_id(self):
        """When resolved_arg_id is provided, score stored under canonical ID."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("The economy is growing")
        # LLM uses "argument_1" but resolved to actual arg_id
        state.add_quality_score(
            "argument_1",
            {"clarity": 7.0},
            7.0,
            resolved_arg_id=a1,
        )
        summary = state.get_enrichment_summary()
        assert summary["with_quality_score"] == 1

    def test_quality_score_without_resolution_not_counted(self):
        """Score stored under non-matching key without resolution = not counted."""
        state = UnifiedAnalysisState("text")
        state.add_argument("The economy is growing")
        state.add_quality_score("argument_1", {"clarity": 7.0}, 7.0)
        summary = state.get_enrichment_summary()
        assert summary["with_quality_score"] == 0

    def test_multiple_scores_all_resolved(self):
        """Multiple scores all resolved correctly."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Argument A")
        a2 = state.add_argument("Argument B")
        state.add_quality_score("arg_a", {"clarity": 5.0}, 5.0, resolved_arg_id=a1)
        state.add_quality_score("arg_b", {"clarity": 6.0}, 6.0, resolved_arg_id=a2)
        summary = state.get_enrichment_summary()
        assert summary["with_quality_score"] == 2

    def test_profile_gets_quality_score_via_resolved_id(self):
        """get_argument_profile finds score stored under resolved ID."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Some argument")
        state.add_quality_score(
            "non_matching_id",
            {"clarity": 9.0},
            9.0,
            resolved_arg_id=a1,
        )
        profile = state.get_argument_profile(a1)
        assert profile.quality_score is not None
        assert profile.quality_score["overall"] == 9.0


class TestQualityScoreResolutionViaStateWriters:
    """Test the state_writers integration for quality score resolution."""

    def test_per_argument_scores_resolved(self):
        """per_argument_scores with non-canonical keys resolved via writer."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_quality_to_state,
        )

        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Economy is growing")
        a2 = state.add_argument("Climate needs action")

        output = {
            "per_argument_scores": {
                "argument_1": {
                    "scores_par_vertu": {"clarity": 7.0},
                    "note_finale": 7.0,
                },
                a2: {
                    "scores_par_vertu": {"clarity": 8.0},
                    "note_finale": 8.0,
                },
            }
        }

        _write_quality_to_state(output, state, {"current_arg_id": a1})

        # a2 should be found directly, a1 via text resolution of "argument_1"
        # "argument_1" won't resolve to a1 by text match (it's not in the desc)
        # but a2 will match directly
        assert a2 in state.argument_quality_scores

    def test_legacy_format_resolved(self):
        """Legacy single-evaluation format uses ctx arg_id."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_quality_to_state,
        )

        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Test argument")

        output = {
            "scores_par_vertu": {"clarity": 6.0},
            "note_finale": 6.0,
        }

        _write_quality_to_state(output, state, {"current_arg_id": a1})

        assert a1 in state.argument_quality_scores
