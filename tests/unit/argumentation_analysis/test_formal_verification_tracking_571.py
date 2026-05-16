"""Tests for formal verification ID-based tracking fix (#571).

Verifies that PL/FOL/NL-to-logic translations linked by arg_id are correctly
counted in get_enrichment_summary() even when text matching fails.
"""
import pytest
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _make_state_with_formal_by_id():
    """Create a state with 3 arguments and formal results linked by arg_id."""
    state = UnifiedAnalysisState("Full text for testing formal verification tracking.")

    a1 = state.add_argument("The economy is growing due to increased exports")
    a2 = state.add_argument("Immigration has no effect on wages")
    a3 = state.add_argument("Climate change requires immediate policy action")

    # PL result linked to arg_1
    state.add_propositional_analysis_result(
        formulas=["Exports(x) → Growth(x)"],
        satisfiable=True,
        model={"Exports": True, "Growth": True},
        arg_id=a1,
    )

    # FOL result linked to arg_2
    state.add_fol_analysis_result(
        formulas=["∀x. Immigration(x) → ¬WageEffect(x)"],
        consistent=True,
        inferences=["¬WageEffect(john)"],
        confidence=0.85,
        arg_id=a2,
    )

    # NL-to-logic translation linked to arg_3
    state.add_nl_to_logic_translation(
        original_text="Completely different text",
        formula="requires(climate_change, policy_action)",
        logic_type="FOL",
        is_valid=True,
        arg_id=a3,
    )

    return state, [a1, a2, a3]


class TestFormalVerificationIDTracking:
    """Test arg_id-based linking for formal verification enrichment."""

    def test_all_3_formal_matched_by_id(self):
        state, args = _make_state_with_formal_by_id()
        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] == 3
        assert summary["with_formal_verification"] == 3

    def test_profile_gets_pl_result_by_id(self):
        state, args = _make_state_with_formal_by_id()
        profile = state.get_argument_profile(args[0])
        formal_types = {r.get("logic_type") or "PL" for r in profile.formal_results}
        # PL result is present (no logic_type field, but has satisfiable)
        assert any("satisfiable" in r for r in profile.formal_results)

    def test_profile_gets_fol_result_by_id(self):
        state, args = _make_state_with_formal_by_id()
        profile = state.get_argument_profile(args[1])
        assert any("consistent" in r for r in profile.formal_results)

    def test_profile_gets_nl_translation_by_id(self):
        state, args = _make_state_with_formal_by_id()
        profile = state.get_argument_profile(args[2])
        assert any(r.get("logic_type") == "FOL" for r in profile.formal_results)

    def test_mixed_id_and_text_matching(self):
        """Both ID-linked and text-matched formal results counted."""
        state = UnifiedAnalysisState("text")
        a1 = state.add_argument("The economy is growing")
        a2 = state.add_argument("Immigration has effects")

        # arg_1: linked by ID (text doesn't match)
        state.add_nl_to_logic_translation(
            "Different text entirely",
            "p → q",
            "PL",
            is_valid=True,
            arg_id=a1,
        )
        # arg_2: linked by text match (no arg_id)
        state.add_nl_to_logic_translation(
            "Immigration has effects",
            "r ∧ s",
            "FOL",
            is_valid=True,
        )

        summary = state.get_enrichment_summary()
        assert summary["with_formal_verification"] == 2

    def test_nl_translation_without_arg_id_uses_text(self):
        state = UnifiedAnalysisState("text")
        state.add_argument("Climate change is real")
        state.add_nl_to_logic_translation(
            "Climate change is real",
            "climate_change_real(x)",
            "FOL",
            is_valid=True,
        )
        summary = state.get_enrichment_summary()
        assert summary["with_formal_verification"] == 1

    def test_pl_result_without_arg_id_not_counted(self):
        """PL results without arg_id and without text match are not counted."""
        state = UnifiedAnalysisState("text")
        state.add_argument("Some argument")
        state.add_propositional_analysis_result(
            formulas=["p → q"],
            satisfiable=True,
        )
        summary = state.get_enrichment_summary()
        # No text match possible (PL results have no original_text)
        assert summary["with_formal_verification"] == 0

    def test_empty_state(self):
        state = UnifiedAnalysisState("text")
        summary = state.get_enrichment_summary()
        assert summary["with_formal_verification"] == 0
        assert summary["total_arguments"] == 0
