"""Tests for UnifiedAnalysisState cross-referencing query methods (#302)."""

import pytest
from argumentation_analysis.core.shared_state import (
    ArgumentProfile,
    UnifiedAnalysisState,
)


def _make_state() -> UnifiedAnalysisState:
    """Create a state populated with 3 arguments, fallacies, quality, counter-args."""
    state = UnifiedAnalysisState("Sample text for testing cross-referencing.")

    # 3 arguments
    a1 = state.add_argument("The economy is growing due to increased exports")
    a2 = state.add_argument("Immigration has no effect on wages")
    a3 = state.add_argument("Climate change requires immediate policy action")

    # 2 fallacies targeting arg_1 and arg_2
    state.add_fallacy(
        "Ad Hominem", "Attacks the source not the claim", target_arg_id=a1
    )
    state.add_fallacy(
        "Straw Man", "Misrepresents the original position", target_arg_id=a2
    )

    # Quality scores for all 3 (arg_1 weak, arg_2 medium, arg_3 strong)
    state.add_quality_score(a1, {"clarity": 3.0, "relevance": 4.0}, overall=3.5)
    state.add_quality_score(a2, {"clarity": 6.0, "relevance": 5.0}, overall=5.5)
    state.add_quality_score(a3, {"clarity": 8.0, "relevance": 9.0}, overall=8.5)

    # 1 counter-argument targeting arg_1 (by text match)
    state.add_counter_argument(
        original_arg="The economy is growing due to increased exports",
        counter_content="Export growth is offset by rising import costs",
        strategy="counter-example",
        score=7.0,
    )

    # 1 JTMS belief referencing arg_1
    state.add_jtms_belief(
        name=f"belief_{a1}_economy_growth",
        valid=True,
        justifications=["export data 2025"],
    )

    # 1 NL-to-logic translation for arg_3
    state.add_nl_to_logic_translation(
        original_text="Climate change requires immediate policy action",
        formula="requires(climate_change, immediate_policy)",
        logic_type="FOL",
        is_valid=True,
    )

    return state


class TestArgumentProfile:
    """Tests for the ArgumentProfile dataclass."""

    def test_dataclass_defaults(self):
        p = ArgumentProfile(arg_id="arg_1", description="test")
        assert p.arg_id == "arg_1"
        assert p.description == "test"
        assert p.fallacies == []
        assert p.quality_score is None
        assert p.counter_arguments == []
        assert p.jtms_beliefs == []
        assert p.formal_results == []


class TestGetArgumentProfile:
    """Tests for get_argument_profile()."""

    def test_profile_with_fallacy_and_quality(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_1")

        assert profile.arg_id == "arg_1"
        assert "economy" in profile.description.lower()
        assert len(profile.fallacies) == 1
        assert profile.fallacies[0]["type"] == "Ad Hominem"
        assert profile.quality_score is not None
        assert profile.quality_score["overall"] == 3.5

    def test_profile_has_counter_argument(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_1")
        assert len(profile.counter_arguments) == 1
        assert profile.counter_arguments[0]["strategy"] == "counter-example"

    def test_profile_has_jtms_belief(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_1")
        assert len(profile.jtms_beliefs) == 1
        assert profile.jtms_beliefs[0]["valid"] is True

    def test_profile_has_formal_results(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_3")
        assert len(profile.formal_results) == 1
        assert profile.formal_results[0]["logic_type"] == "FOL"

    def test_profile_no_fallacy(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_3")
        assert len(profile.fallacies) == 0

    def test_profile_unknown_arg_id(self):
        state = _make_state()
        profile = state.get_argument_profile("arg_999")
        assert profile.description == ""
        assert profile.fallacies == []
        assert profile.quality_score is None


class TestGetWeakArguments:
    """Tests for get_weak_arguments()."""

    def test_default_threshold(self):
        state = _make_state()
        weak = state.get_weak_arguments(threshold=5.0)
        assert len(weak) == 1
        assert weak[0].arg_id == "arg_1"

    def test_higher_threshold(self):
        state = _make_state()
        weak = state.get_weak_arguments(threshold=6.0)
        assert len(weak) == 2
        ids = {w.arg_id for w in weak}
        assert ids == {"arg_1", "arg_2"}

    def test_zero_threshold(self):
        state = _make_state()
        weak = state.get_weak_arguments(threshold=0.0)
        assert len(weak) == 0

    def test_no_quality_scores(self):
        state = UnifiedAnalysisState("text")
        state.add_argument("some argument")
        weak = state.get_weak_arguments(threshold=5.0)
        assert len(weak) == 0


class TestGetFallaciousArguments:
    """Tests for get_fallacious_arguments()."""

    def test_returns_only_targeted(self):
        state = _make_state()
        fallacious = state.get_fallacious_arguments()
        assert len(fallacious) == 2
        ids = {f.arg_id for f in fallacious}
        assert ids == {"arg_1", "arg_2"}

    def test_profiles_include_fallacy_data(self):
        state = _make_state()
        fallacious = state.get_fallacious_arguments()
        for profile in fallacious:
            assert len(profile.fallacies) >= 1

    def test_no_fallacies(self):
        state = UnifiedAnalysisState("text")
        state.add_argument("clean argument")
        assert state.get_fallacious_arguments() == []

    def test_fallacy_targeting_unknown_arg_excluded(self):
        state = UnifiedAnalysisState("text")
        state.add_argument("known argument")
        # Add fallacy targeting non-existent arg
        state.add_fallacy("Red Herring", "irrelevant", target_arg_id="arg_999")
        fallacious = state.get_fallacious_arguments()
        assert len(fallacious) == 0


class TestGetEnrichmentSummary:
    """Tests for get_enrichment_summary()."""

    def test_counts_correct(self):
        state = _make_state()
        summary = state.get_enrichment_summary()

        assert summary["total_arguments"] == 3
        assert summary["with_fallacy_analysis"] == 2
        assert summary["with_quality_score"] == 3
        assert summary["with_counter_argument"] == 1
        assert summary["with_formal_verification"] == 1
        assert summary["with_jtms_belief"] == 1

    def test_gaps_reported(self):
        state = _make_state()
        summary = state.get_enrichment_summary()
        gaps = summary["gaps"]

        # arg_1 and arg_2 have no formal verification
        formal_gaps = [g for g in gaps if "formal verification" in g]
        assert len(formal_gaps) == 2

        # All args have quality scores, so no quality gaps
        quality_gaps = [g for g in gaps if "quality score" in g]
        assert len(quality_gaps) == 0

    def test_empty_state(self):
        state = UnifiedAnalysisState("text")
        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] == 0
        assert summary["gaps"] == []

    def test_all_enriched(self):
        """State where every argument has every enrichment => no gaps."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("Argument one about topic X")
        state.add_quality_score(a1, {"clarity": 8.0}, overall=8.0)
        state.add_nl_to_logic_translation(
            original_text="Argument one about topic X",
            formula="p(x)",
            logic_type="FOL",
            is_valid=True,
        )
        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] == 1
        assert summary["with_quality_score"] == 1
        assert summary["with_formal_verification"] == 1
        assert len(summary["gaps"]) == 0
