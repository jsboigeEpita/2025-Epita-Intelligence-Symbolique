"""Tests for counter-argument ID-based tracking fix (#570).

Verifies that counter-arguments linked by target_arg_id are correctly
counted in get_enrichment_summary() even when text matching fails.
"""
import pytest
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _make_state_with_id_tracking():
    """Create a state with 5 arguments and 5 counter-arguments linked by ID.

    The counter-argument original_argument texts are intentionally different
    from the argument descriptions to prove ID-based matching works.
    """
    state = UnifiedAnalysisState("Full text for testing counter-argument tracking.")

    args = []
    descriptions = [
        "The economy is growing due to increased exports",
        "Immigration has no effect on wages",
        "Climate change requires immediate policy action",
        "Education funding should be tripled",
        "Universal basic income reduces poverty",
    ]
    for desc in descriptions:
        args.append(state.add_argument(desc))

    # Counter-arguments with mismatched text but correct target_arg_id
    ca_data = [
        ("Exports are not the main driver", "reductio_ad_absurdum", 0.8),
        ("Wage studies show mixed results", "counter-example", 0.7),
        ("Policy alone is insufficient", "distinction", 0.9),
        ("Tripling is not cost-effective", "reformulation", 0.6),
        ("UBI creates dependency loops", "reductio_ad_absurdum", 0.85),
    ]
    for ca_text, strategy, score, arg_id in zip(
        [d[0] for d in ca_data],
        [d[1] for d in ca_data],
        [d[2] for d in ca_data],
        args,
    ):
        state.add_counter_argument(
            original_arg=ca_text,
            counter_content=f"Counter to {ca_text}",
            strategy=strategy,
            score=score,
            target_arg_id=arg_id,
        )

    return state, args


class TestCounterArgumentIDTracking:
    """Test that target_arg_id-based linking works for enrichment summary."""

    def test_id_tracking_all_5_matched(self):
        """5 CAs with target_arg_id → with_counter_argument == 5."""
        state, args = _make_state_with_id_tracking()
        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] == 5
        assert summary["with_counter_argument"] == 5

    def test_id_tracking_text_mismatch_doesnt_matter(self):
        """Even when text doesn't match, ID linkage works."""
        state, args = _make_state_with_id_tracking()
        for ca in state.counter_arguments:
            assert ca["target_arg_id"] in args
            # Verify text doesn't match (proof ID is needed)
            original = ca["original_argument"]
            arg_desc = state.identified_arguments[ca["target_arg_id"]]
            assert original != arg_desc

    def test_profile_gets_counter_args_by_id(self):
        """get_argument_profile returns CAs linked by ID."""
        state, args = _make_state_with_id_tracking()
        for arg_id in args:
            profile = state.get_argument_profile(arg_id)
            assert len(profile.counter_arguments) == 1

    def test_mixed_id_and_text_matching(self):
        """CAs with target_arg_id AND text-matching both counted."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Argument about X")
        a2 = state.add_argument("Argument about Y")

        # CA1: linked by ID (text doesn't match)
        state.add_counter_argument(
            "Completely different text",
            "Counter 1",
            "counter-example",
            0.8,
            target_arg_id=a1,
        )
        # CA2: linked by text match (no target_arg_id)
        state.add_counter_argument(
            "Argument about Y",
            "Counter 2",
            "reformulation",
            0.7,
        )

        summary = state.get_enrichment_summary()
        assert summary["with_counter_argument"] == 2

    def test_no_target_arg_id_falls_back_to_text(self):
        """Without target_arg_id, text matching still works."""
        state = UnifiedAnalysisState("text")
        state.add_argument("The economy is growing due to increased exports")
        state.add_counter_argument(
            "The economy is growing due to increased exports",
            "Counter content",
            "counter-example",
            0.7,
        )
        summary = state.get_enrichment_summary()
        assert summary["with_counter_argument"] == 1

    def test_invalid_target_arg_id_ignored(self):
        """target_arg_id pointing to non-existent arg falls back to text."""
        state = UnifiedAnalysisState("text")
        state.add_argument("Real argument text here")
        state.add_counter_argument(
            "Real argument text here",
            "Counter",
            "counter-example",
            0.7,
            target_arg_id="arg_999",
        )
        summary = state.get_enrichment_summary()
        # Falls back to text matching and succeeds
        assert summary["with_counter_argument"] == 1


class TestCounterArgumentIDTrackingViaStateWriters:
    """Test the _resolve_target_arg_id helper from state_writers."""

    def test_resolve_by_exact_id(self):
        from argumentation_analysis.orchestration.state_writers import (
            _resolve_target_arg_id,
        )

        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Some argument")
        result = _resolve_target_arg_id(state, a1)
        assert result == a1

    def test_resolve_by_text_match(self):
        from argumentation_analysis.orchestration.state_writers import (
            _resolve_target_arg_id,
        )

        state = UnifiedAnalysisState("text")
        state.add_argument("The economy is growing due to exports")
        result = _resolve_target_arg_id(state, "The economy is growing due to exports")
        assert result is not None
        assert result.startswith("arg_")

    def test_resolve_by_prefix_match(self):
        from argumentation_analysis.orchestration.state_writers import (
            _resolve_target_arg_id,
        )

        state = UnifiedAnalysisState("text")
        state.add_argument("This is a long argument about climate policy reform")
        # Text is a prefix of the arg description (60 chars match)
        result = _resolve_target_arg_id(state, "This is a long argument about climate policy reform")
        assert result is not None

    def test_resolve_returns_none_for_no_match(self):
        from argumentation_analysis.orchestration.state_writers import (
            _resolve_target_arg_id,
        )

        state = UnifiedAnalysisState("text")
        state.add_argument("Something about cats")
        result = _resolve_target_arg_id(state, "Something completely different about dogs")
        assert result is None

    def test_resolve_empty_target(self):
        from argumentation_analysis.orchestration.state_writers import (
            _resolve_target_arg_id,
        )

        state = UnifiedAnalysisState("text")
        state.add_argument("Some argument")
        result = _resolve_target_arg_id(state, "")
        assert result is None
