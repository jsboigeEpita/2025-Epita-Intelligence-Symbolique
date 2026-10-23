# -*- coding: utf-8 -*-
"""#3151 — the weave must keep the evidence's own bindings.

The R1106 Act II render moved a counter-argument (and its supporting
material) from the unit it targets onto the deliberation winner — both sit
in the same « soutiens » movement, and the reader got a counter against the
passage the report itself calls the strongest. The binding was CORRECT in
the evidence (``build_act2_evidence`` indexes counters by ``target_arg_id``
and the prompt lists each under its own bullet); it was lost in the weave.

Three post-weave checks over the bundle the writer received (deterministic,
no LLM call), added to ``check_reading_license``:

* ``counter_on_wrong_unit`` — a counter's distinctive tokens cited in the
  paragraph of a unit that is not its target;
* ``only_virtues_drops_a_holding_one`` — « Seuls X et Y » while the unit's
  holding virtues (the same ≥ 0.75 rule the evidence uses) include one more;
* ``superlative_over_tied_counters`` — « le contre-argument le plus fort »
  while the maximum score is a tie.

Synthetic vocabularies only (phares, fournils, ponts — no corpus content,
privacy HARD). Distinctive-token design: each unit's description and each
counter's content carry words no OTHER unit/counter carries, so a paragraph
attributable to a unit and a citation attributable to a counter are both
measured, never guessed.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _units():
    # The REAL producer shape (#3202): `UnifiedAnalysisState.add_argument`
    # writes `identified_arguments[arg_id] = description`, a str. The dict
    # fixture this used to carry was a double richer than the object, and it
    # certified a path no producer writes.
    return {
        "arg_alpha": "Le phare octogonal d'alpha domine la baie.",
        "arg_bravo": "Le fournil de bravo pétille dès l'aube.",
        "arg_charlie": "La conduite du convoi ferroviaire impressionne.",
    }


def _counters():
    return [
        {
            "id": "ca_1",
            "target_arg_id": "arg_bravo",
            "counter_content": (
                "Le fournil ne pétille que si la bonde océane reste ouverte."
            ),
            "strategy": "distinguo",
            "score": 0.59,
        },
        {
            "id": "ca_2",
            "target_arg_id": "arg_charlie",
            "counter_content": (
                "Aucun plan de voie ne mentionne la passerelle moussue."
            ),
            "strategy": "attaque directe",
            "score": 0.48,
        },
    ]


def _quality():
    return {
        "arg_charlie": {
            "scores": {
                "clarte": 1.0,
                "pertinence": 1.0,
                "refutation_constructive": 1.0,
            }
        }
    }


def _state(counters=None, quality=None):
    return SimpleNamespace(
        identified_arguments=_units(),
        counter_arguments=counters if counters is not None else _counters(),
        argument_quality_scores=quality if quality is not None else _quality(),
    )


class TestCounterOnWrongUnit:
    """DoD 1 — unit B's counter in unit A's paragraph is flagged."""

    def test_a_weave_that_moves_a_counter_onto_another_unit_is_flagged(self):
        """The paragraph talks about arg_alpha (its distinctive tokens) and
        cites ca_1's distinctive tokens — ca_1 targets arg_bravo. Red on
        ``044af5147``: no such check existed."""
        weave = (
            "Le phare octogonal domine la baie, personne ne le conteste ; "
            "pourtant la bonde océane reste ouverte, et c'est là l'objection."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_on_wrong_unit" in kinds
        flag = next(f for f in result["flags"] if f["kind"] == "counter_on_wrong_unit")
        assert flag["measured"]["target_arg_id"] == "arg_bravo"
        assert flag["measured"]["paragraph_units"] == ["arg_alpha"]

    def test_the_same_counter_in_its_own_units_paragraph_passes(self):
        """Control: the paragraph talks about arg_bravo and cites ca_1 — its
        own target. No flag."""
        weave = (
            "Le fournil pétille dès l'aube. "
            "Mais la bonde océane reste ouverte, dit l'objection."
        )
        result = check_reading_license(weave, _state())
        assert [
            f["kind"] for f in result["flags"] if f["kind"] == "counter_on_wrong_unit"
        ] == []

    def test_a_counter_cited_nowhere_flags_nothing(self):
        """A paragraph that cites no counter's tokens makes no binding claim
        — no flag, either unit."""
        weave = "Le phare octogonal domine la baie en silence."
        result = check_reading_license(weave, _state())
        assert result["flags"] == []


class TestOnlyVirtues:
    """DoD 2 — « seuls X et Y » checked against the unit's holding virtues."""

    def test_seuls_dropping_a_holding_virtue_is_flagged(self):
        """arg_charlie holds THREE virtues (clarte, pertinence,
        refutation_constructive ≥ 0.75); the prose keeps two and says
        « seuls ». Red on ``044af5147``."""
        weave = (
            "La conduite du convoi ferroviaire impressionne. "
            "Seuls la clarté et la pertinence le sauvent."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "only_virtues_drops_a_holding_one" in kinds
        flag = next(
            f
            for f in result["flags"]
            if f["kind"] == "only_virtues_drops_a_holding_one"
        )
        assert flag["measured"]["unit"] == "arg_charlie"
        assert flag["measured"]["dropped"] == ["refutation_constructive"]

    def test_seuls_naming_every_holding_virtue_passes(self):
        """Control: the exhaustive claim matches the measured set."""
        weave = (
            "La conduite du convoi ferroviaire impressionne. "
            "Seuls la clarté, la pertinence et la réfutation constructive "
            "le sauvent."
        )
        result = check_reading_license(weave, _state())
        assert [
            f["kind"]
            for f in result["flags"]
            if f["kind"] == "only_virtues_drops_a_holding_one"
        ] == []


class TestSuperlativeOnTiedCounters:
    """Requested 3 — a superlative needs a unique maximum."""

    def test_a_superlative_over_a_tied_maximum_is_flagged(self):
        """ca_1 and ca_2 both score 0.59 — « le plus fort » reads a tie as a
        unique maximum. Red on ``044af5147``."""
        counters = _counters()
        counters[1]["score"] = 0.59
        weave = (
            "Le contre-argument le plus fort de l'ensemble vise le phare " "octogonal."
        )
        result = check_reading_license(weave, _state(counters=counters))
        kinds = [f["kind"] for f in result["flags"]]
        assert "superlative_over_tied_counters" in kinds
        flag = next(
            f for f in result["flags"] if f["kind"] == "superlative_over_tied_counters"
        )
        assert flag["measured"]["tied"] == ["ca_1", "ca_2"]

    def test_the_same_superlative_on_a_unique_maximum_passes(self):
        """Control: 0.59 vs 0.48 — the maximum is unique, the superlative is
        licensed."""
        weave = (
            "Le contre-argument le plus fort de l'ensemble vise le phare " "octogonal."
        )
        result = check_reading_license(weave, _state())
        assert [
            f["kind"]
            for f in result["flags"]
            if f["kind"] == "superlative_over_tied_counters"
        ] == []
