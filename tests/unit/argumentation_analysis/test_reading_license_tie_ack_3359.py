"""#3359 — a superlative that ACKNOWLEDGES the tie is not a false maximum.

`superlative_over_tied_counters` fired on every superlative about
counter-arguments while the maximum was shared. R1134a's render was CONFORME
and flagged anyway: « le contre-argument le plus fort, à égalité avec un autre
contre-argument » states the very tie the flag accuses it of hiding.

Born red on the parent commit: the equality sentence produced the flag.

Fixtures are local and synthetic (phares, fournils, ponts — no corpus content,
privacy HARD), in the producer's own shape: `identified_arguments[arg_id]` is
the description string (#3202) and each counter carries its `target_arg_id`.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _units():
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


def _state(tied=True):
    counters = _counters()
    if tied:
        counters[1]["score"] = 0.59  # ca_1 and ca_2 both hold the maximum
    return SimpleNamespace(
        identified_arguments=_units(),
        counter_arguments=counters,
        argument_quality_scores={
            "arg_charlie": {
                "scores": {
                    "clarte": 1.0,
                    "pertinence": 1.0,
                    "refutation_constructive": 1.0,
                }
            }
        },
    )


def _kinds(weave, tied=True):
    result = check_reading_license(weave, _state(tied=tied))
    return [f["kind"] for f in result["flags"]]


class TestTheEqualityMarkerExempts:
    def test_the_r1134a_sentence_is_not_flagged(self):
        weave = (
            "Le contre-argument le plus fort, à égalité avec un autre "
            "contre-argument, vise le phare octogonal."
        )
        assert "superlative_over_tied_counters" not in _kinds(weave)

    def test_the_english_spelling_is_exempt_too(self):
        weave = (
            "The highest-scoring counter-argument is tied with another "
            "counter-argument on the lighthouse."
        )
        assert "superlative_over_tied_counters" not in _kinds(weave)

    def test_citing_every_holder_states_the_tie_by_enumeration(self):
        # The parent flags this spelling (measured), so the witness is not
        # vacuous: both holders are named, which states the tie by
        # enumeration even without an equality idiom.
        weave = (
            "Le contre-argument le plus fort (ca_1 et ca_2) vise le phare " "octogonal."
        )
        assert "superlative_over_tied_counters" not in _kinds(weave)


def _eleven_counters():
    """A realistic width: the passes carry 37-41 counters (#3359 R1135).

    Eleven is the smallest population that contains ``ca_10`` — the id whose
    characters ``ca_1`` sits inside. ca_1 and ca_2 hold the shared maximum.
    """
    topics = [
        "la bonde océane",
        "la passerelle moussue",
        "le fanal de quart",
        "la cale sèche",
        "le treuil hydraulique",
        "la bitte d'amarrage",
        "le guindeau",
        "la membrure cintrée",
        "le vaigrage",
        "l'étrave",
        "le tableau arrière",
    ]
    counters = []
    for index, topic in enumerate(topics, start=1):
        counters.append(
            {
                "id": f"ca_{index}",
                "target_arg_id": "arg_bravo",
                "counter_content": f"Aucune mesure ne mentionne {topic}.",
                "strategy": "attaque directe",
                # ca_1 and ca_2 tie at the top; the rest sit below.
                "score": 0.59 if index <= 2 else 0.5 - index / 100.0,
            }
        )
    return counters


class TestHolderCitationIsATokenNotASubstring:
    """R1135 — `ca_1` is not cited when the sentence writes `ca_10`.

    The exemption used `holder in sentence`, a raw substring test: on a render
    with ten or more counters, citing ``ca_10`` and ``ca_2`` satisfied
    ``ca_1`` — so the enumerating condition claimed the sentence named every
    holder of a tied maximum it in fact hid.
    """

    def _weave_flags(self, weave):
        state = SimpleNamespace(
            identified_arguments=_units(),
            counter_arguments=_eleven_counters(),
            argument_quality_scores={},
        )
        result = check_reading_license(weave, state, max_flags=200)
        return [
            f for f in result["flags"] if f["kind"] == "superlative_over_tied_counters"
        ]

    def test_citing_ca_10_and_ca_2_does_not_cite_ca_1(self):
        weave = (
            "Le contre-argument le plus fort (ca_10 et ca_2) vise le phare "
            "octogonal."
        )
        assert self._weave_flags(weave), (
            "ca_1 is inside the characters of ca_10 — a substring test reads the "
            "sentence as naming every holder and hides the flag"
        )

    def test_naming_both_holders_as_tokens_still_exempts(self):
        """Control: the exemption must survive the repair on a real enumeration."""
        weave = (
            "Le contre-argument le plus fort (ca_1 et ca_2) vise le phare " "octogonal."
        )
        assert not self._weave_flags(weave)

    def test_the_fixture_does_raise_the_flag_when_nobody_is_named(self):
        """Positive control: on this population the guard DOES fire, so the
        test above measures the substring exemption and not a silent guard."""
        weave = "Le contre-argument le plus fort de l'ensemble vise le phare octogonal."
        assert self._weave_flags(weave)


class TestTheFlagStillCatchesAHiddenTie:
    """The exemption reads the sentence; it is not a hole in the rule."""

    def test_a_tie_without_the_marker_is_still_flagged(self):
        weave = "Le contre-argument le plus fort de l'ensemble vise le phare octogonal."
        assert "superlative_over_tied_counters" in _kinds(weave)

    def test_citing_one_holder_and_no_equality_leaves_the_flag(self):
        weave = "Le contre-argument le plus fort (ca_1) vise le phare octogonal."
        assert "superlative_over_tied_counters" in _kinds(weave)

    def test_the_exemption_does_not_invent_a_tie(self):
        """Control: 0.59 vs 0.48 — no tie exists, nothing to acknowledge."""
        weave = (
            "Le contre-argument le plus fort, à égalité avec un autre "
            "contre-argument, vise le phare octogonal."
        )
        assert "superlative_over_tied_counters" not in _kinds(weave, tied=False)
