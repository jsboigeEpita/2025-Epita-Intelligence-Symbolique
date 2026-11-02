"""#3357 — the briefing's quality line states the #289 penalty it applied.

The state stores ``overall`` fallacy-adjusted (#289) beside the evaluator's
penalty record (#3133). The line used to print only the adjusted sum, so a
unit measured 4.5 and penalised to 1.8 reached the writer as
``overall=1.8000000000000003``: the penalty invisible, and no way to tell that
score from a unit that simply scored 1.8.

Born red on the parent commit: ``_quality_line`` did not exist, and the line
carried the unpenalised arithmetic residue.
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

PENALISED_LINE = (
    "overall=1.8 (mesure 4.5, -60% pour 2 sophismes ; score penalise, "
    "non comparable aux scores sans penalite)"
)


def _briefing_lines(quality):
    state = SimpleNamespace(argument_quality_scores=quality)
    brief = DeepSynthesisAgent.build_artifact_briefing(state)
    return {
        line.split("]")[0].split(".")[-1]: line.split("] ", 1)[1]
        for line in brief.splitlines()
        if line.startswith("[artifact:argument_quality_scores.")
    }


def _penalised(overall=1.8000000000000003, original=4.5, factor=0.4, count=2):
    return {
        "scores": {f"v{i}": 0.5 for i in range(9)},
        "overall": overall,
        "fallacy_penalty": {
            "applied": True,
            "fallacies": [f"fallacy_{i}" for i in range(count)],
            "penalty_factor": factor,
            "original_score": original,
        },
    }


class TestPenalisedScoreIsPairedWithItsMeasure:
    def test_the_arg_37_form_states_both_judgements(self):
        lines = _briefing_lines({"arg_37": _penalised()})
        assert lines["arg_37"] == PENALISED_LINE

    def test_the_float_noise_of_the_adjusted_sum_never_prints(self):
        lines = _briefing_lines({"arg_37": _penalised()})
        assert "1.8000000000000003" not in lines["arg_37"]
        assert "1.8" in lines["arg_37"]

    def test_the_penalty_is_not_comparable_with_an_unpenalised_score(self):
        lines = _briefing_lines({"arg_37": _penalised()})
        assert "non comparable aux scores sans penalite" in lines["arg_37"]

    def test_a_single_fallacy_is_not_pluralised(self):
        lines = _briefing_lines({"arg_01": _penalised(count=1)})
        assert "pour 1 sophisme " in lines["arg_01"] + " "
        assert "1 sophismes" not in lines["arg_01"]

    def test_a_penalty_without_numbers_still_pairs_the_rule(self):
        entry = {
            "scores": {"v0": 0.5},
            "overall": 0.5,
            "fallacy_penalty": {"applied": True},
        }
        lines = _briefing_lines({"arg_02": entry})
        assert lines["arg_02"] == (
            "overall=0.5 (score penalise, non comparable aux scores sans penalite)"
        )


class TestUnpenalisedLineIsUntouched:
    """The issue's control: a unit with no applied penalty renders as before."""

    @pytest.mark.parametrize(
        "overall,expected", [(4.5, "overall=4.5"), (3, "overall=3")]
    )
    def test_the_line_is_byte_identical(self, overall, expected):
        lines = _briefing_lines({"arg_38": {"scores": {"a": 1.0}, "overall": overall}})
        assert lines["arg_38"] == expected

    def test_a_recorded_but_unapplied_penalty_changes_nothing(self):
        entry = {
            "scores": {"a": 1.0},
            "overall": 4.5,
            "fallacy_penalty": {
                "applied": False,
                "fallacies": ["f"],
                "penalty_factor": 0.4,
                "original_score": 4.5,
            },
        }
        lines = _briefing_lines({"arg_39": entry})
        assert lines["arg_39"] == "overall=4.5"

    def test_a_bare_number_entry_is_still_rendered(self):
        lines = _briefing_lines({"arg_40": 2.25})
        assert lines["arg_40"] == "overall=2.25"


class TestTheActsReadingIsUnchanged:
    """#3357 touches the briefing only: the #3123 licence still reads `overall`."""

    def test_the_penalised_fraction_still_reads_the_adjusted_sum(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            quality_fraction,
        )

        entry = _penalised()
        assert quality_fraction(entry) == pytest.approx(1.8 / 9, abs=0.01)
