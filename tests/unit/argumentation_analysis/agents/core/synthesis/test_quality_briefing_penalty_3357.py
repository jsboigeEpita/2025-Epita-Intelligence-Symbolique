"""#3357 — the briefing's quality line states the #289 penalty it applied.

The state stores ``overall`` fallacy-adjusted (#289) beside the evaluator's
penalty record (#3133). The line used to print only the adjusted sum, so a
unit measured 4.5 and penalised to 1.8 reached the writer as
``overall=1.8000000000000003``: the penalty invisible, and no way to tell that
score from a unit that simply scored 1.8.

Born red on the parent commit: ``_quality_line`` did not exist, and the line
carried the unpenalised arithmetic residue.

R1135 rework — the fixtures are built with the PRODUCER's convention, not an
invented one. ``invoke_callables.py``::

    penalty = min(0.3 * len(fallacy_targets[i]), 0.6)
    result["note_finale"] = max(0, original - original * penalty)
    result["fallacy_penalty"] = {..., "penalty_factor": penalty, ...}

so ``penalty_factor`` is the RATE REMOVED: one fallacy is 0.3, two are 0.6,
and the cap holds at 0.6 beyond that. The first version of this file stored
the remaining ratio (0.4 for 4.5 → 1.8), a shape the producer never writes —
which is why the witness stayed green on a line that printed −40 % where the
record means −60 %. ``test_the_fixture_follows_the_producer_relation`` pins
the relation so a wrong-convention fixture fails instead of passing.
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

PENALISED_LINE = (
    "overall=1,80 sur 9 après pénalité (4,50 avant) (-60% pour 2 "
    "sophismes ; score penalise, non comparable aux scores sans penalite)"
)


def _briefing_lines(quality):
    state = SimpleNamespace(argument_quality_scores=quality)
    brief = DeepSynthesisAgent.build_artifact_briefing(state)
    return {
        line.split("]")[0].split(".")[-1]: line.split("] ", 1)[1]
        for line in brief.splitlines()
        if line.startswith("[artifact:argument_quality_scores.")
    }


def _producer_rate(count: int) -> float:
    """The rate the producer subtracts for ``count`` fallacies (#289)."""
    return min(0.3 * count, 0.6)


def _penalised(original=4.5, count=2):
    """The record ``invoke_callables.py`` writes — formula included."""
    rate = _producer_rate(count)
    return {
        "scores": {f"v{i}": 0.5 for i in range(9)},
        # the producer's own arithmetic: note = original - original * rate
        "overall": original - original * rate,
        "fallacy_penalty": {
            "applied": True,
            "fallacies": [f"fallacy_{i}" for i in range(count)],
            "penalty_factor": rate,
            "original_score": original,
        },
    }


class TestTheFixtureUsesTheProducerConvention:
    def test_the_fixture_follows_the_producer_relation(self):
        """Pin the relation the record satisfies: a fixture storing the
        remaining ratio as ``penalty_factor`` cannot pass this."""
        for count in (1, 2, 3, 4):
            entry = _penalised(count=count)
            penalty = entry["fallacy_penalty"]
            assert penalty["penalty_factor"] == pytest.approx(min(0.3 * count, 0.6))
            assert entry["overall"] == pytest.approx(
                penalty["original_score"] * (1 - penalty["penalty_factor"])
            )

    def test_the_cap_holds_past_two_fallacies(self):
        assert _penalised(count=4)["fallacy_penalty"]["penalty_factor"] == 0.6


class TestPenalisedScoreIsPairedWithItsMeasure:
    def test_the_arg_37_form_states_both_judgements(self):
        lines = _briefing_lines({"arg_37": _penalised()})
        assert lines["arg_37"] == PENALISED_LINE

    def test_the_float_noise_of_the_adjusted_sum_never_prints(self):
        lines = _briefing_lines({"arg_37": _penalised()})
        assert "1.8000000000000003" not in lines["arg_37"]
        assert "1,80 sur 9" in lines["arg_37"]

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
            "overall=0,50 sur 1 après pénalité "
            "(score penalise, non comparable aux scores sans penalite)"
        )


class TestTheReductionIsTheRateRemoved:
    """R1135 — the printed reduction is ``penalty × 100``, the producer's rate.

    The first version printed its complement (``(1 - penalty) × 100``): −40 %
    for a real −60 %. These shapes are the producer's: 1 fallacy → 0.3,
    2 → 0.6, and the cap holds at 0.6.
    """

    @pytest.mark.parametrize("count,expected", [(1, "-30%"), (2, "-60%"), (4, "-60%")])
    def test_the_rate_removed_is_what_prints(self, count, expected):
        lines = _briefing_lines({f"arg_{count}": _penalised(count=count)})
        assert expected in lines[f"arg_{count}"]
        # the complement the first version printed (40 % for a 60 % rate)
        assert "-40%" not in lines[f"arg_{count}"]


class TestUnpenalisedLineRidesItsScale:
    """#3394 ask 1 (R1143) superseded the R1135 byte-stability of the
    UNPENALISED branch: the bare ``overall=…`` was the bare-number defect.
    The line carries its ceiling when ``scores`` measures one; the control
    for byte-stability moved to the entry WITHOUT a scores map."""

    @pytest.mark.parametrize(
        "overall,expected",
        [
            (4.5, "overall=4,50 sur 1"),
            (3, "overall=3,00 sur 1"),
            # the scale prints through the #3394 formatter — two decimals,
            # French comma (the R1135 "keeps its third decimal" note is
            # superseded with the bare spelling itself)
            (4.567, "overall=4,57 sur 1"),
        ],
    )
    def test_the_line_is_byte_identical(self, overall, expected):
        lines = _briefing_lines({"arg_38": {"scores": {"a": 1.0}, "overall": overall}})
        assert lines["arg_38"] == expected

    def test_an_entry_without_scores_keeps_the_bare_spelling(self):
        # The control the DoD names: nothing measurable to scale, nothing
        # penalised — byte-for-byte the pre-#3394 line.
        lines = _briefing_lines({"arg_41": {"overall": 4.5}})
        assert lines["arg_41"] == "overall=4.5"

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
        assert lines["arg_39"] == "overall=4,50 sur 1"

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
