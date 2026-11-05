"""#3394 — a figure reaches the reader with its scale, its direction or its count.

Cycle 0's panel renders (10 documents) handed the non-specialist reader:

* verdict counts without their bar — « k/8 arguments évalués » on 9 of 9
  renders, never saying 8 of what nor which threshold applies;
* bare scores — « score producteur 0.56 », « qualité 3.0 », « évaluation
  globale 1,28 », « score brut 0,58 »;
* vote support as a word with no count — « une large majorité des méthodes
  de vote », « à l'unanimité des méthodes qui ont tranché »;
* taxonomy labels without their definition — « sophisme métonymique »,
  « substitut de preuve », bare to the reader.

The producers fix it (#3394): one formatter prints a score with its scale
and direction, the vote band carries its count from governance's own
record, the verdict clause names its bar, and a label carries the
taxonomy's one-line definition on its first mention. The writers receive
the formatted string — no vocabulary rule is added to any prompt.

Fixtures are synthetic (opaque ids, the vendored taxonomy's own public
reference rows). Born red on main: the formatters, the bar, the counted
band and the definition note do not exist there.
"""

from __future__ import annotations

import re

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    QualityStrength,
    _VERDICT_BASE_RE,
    build_act3_evidence,
    build_act3_prompt,
    discourse_virtue_reader_sentence,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    quality_ranking_line,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.cited_units import (
    qualitative_support_band,
)
from argumentation_analysis.reporting.restitution.figure_scales import (
    score_with_scale,
    sum_on_its_maximum,
    vote_count_phrase,
)
from argumentation_analysis.core.fallacy_attribution import taxonomy_definition_note
from argumentation_analysis.utils.taxonomy_loader import (
    _capped,
    taxonomy_definition,
)

# The vendored taxonomy's own root row (public reference data, path "0"):
# text_fr « Argument fallacieux », desc_fr the one-line definition below.
_ROOT_LABEL = "Argument fallacieux"
_ROOT_DESC = "Votre discours vise à tromper votre auditoire."


class TestScoreCarriesItsScale:
    """Ask 1 — « score producteur 0.56 », bare, was scale-free decoration."""

    def test_a_score_prints_scale_and_direction(self):
        assert score_with_scale(0.56, 1.0) == "0,56 sur 1,00 — plus haut = meilleur"

    def test_lower_is_better_prints_its_direction(self):
        rendered = score_with_scale(0.4, 1.0, higher_is_better=False)
        assert rendered == "0,40 sur 1,00 — plus bas = meilleur"

    def test_decimal_places_follow_the_caller(self):
        assert (
            score_with_scale(1.0, 1.0, decimals=1)
            == "1,0 sur 1,0 — plus haut = meilleur"
        )

    def test_unmeasured_prints_nothing(self):
        assert score_with_scale(None, 1.0) == ""
        assert score_with_scale(0.5, None) == ""
        assert score_with_scale(float("nan"), 1.0) == ""

    def test_the_strengths_line_hands_the_writer_the_formatted_score(self):
        state = SimpleNamespace(
            identified_arguments={
                f"arg_{i}": f"Une revendication synthetique numero {i}."
                for i in range(1, 9)
            },
            identified_fallacies={},
            argument_quality_scores={
                f"arg_{i}": {"scores": {"pertinence": 1.0}} for i in range(1, 9)
            },
            counter_arguments=[],
        )
        prompt = build_act3_prompt(build_act3_evidence(state))
        start = prompt.find("[CE QUI TIENT — forces (qualité)]")
        assert start != -1
        slot = prompt[start : prompt.find("[", start + 1)]
        assert "score 1,0 sur 1,0 — plus haut = meilleur" in slot, (
            "the writer must receive the score WITH its scale and direction, "
            "never the bare number (#3394 ask 1)"
        )
        assert "vertu atteinte sur 8 des 8 arguments évalués" in slot


class TestTheVerdictCountNamesItsBar:
    """Ask 1 — « 7/8 arguments évalués » never said 8 of what, nor the bar."""

    def test_the_grafted_verdict_states_the_bar(self):
        sentence = discourse_virtue_reader_sentence(
            [
                QualityStrength(
                    virtue="pertinence",
                    score=1.0,
                    args_at_top=7,
                    args_evaluated=8,
                    units_total=89,
                )
            ]
        )
        assert "barre : 3/4 des arguments évalués" in sentence, (
            "the count names the threshold that admits a virtue to the "
            "discourse statement (#3394)"
        )
        assert "7/8 arguments évalués" in sentence

    def test_the_woven_removal_still_anchors_on_the_base(self):
        # The graft's base must stay contiguous in its historical shape:
        # ``_VERDICT_BASE_RE`` removes woven restatements by that anchor.
        sentence = discourse_virtue_reader_sentence(
            [
                QualityStrength(
                    virtue="pertinence",
                    score=1.0,
                    args_at_top=7,
                    args_evaluated=8,
                    units_total=89,
                )
            ]
        )
        assert _VERDICT_BASE_RE.search(sentence), (
            "the bar clause must not break the woven-restatement removal "
            "(#3335's anchor rides the exact « k/m arguments évalués » shape)"
        )


class TestAVotePrintsItsCount:
    """Ask 2 — « une large majorité des méthodes de vote » carried no number.

    R1145 tranche (#3394): the population is the SCRUTINS — the noun is
    « scrutins » and the two consensus protocols are named apart, never
    counted in the fraction.
    """

    def test_the_count_comes_from_the_record(self):
        assert vote_count_phrase(9, 10) == "9 des 10 scrutins"

    def test_no_count_without_a_population(self):
        assert vote_count_phrase(None, 10) is None
        assert vote_count_phrase(9, None) is None
        assert vote_count_phrase(0, 10) is None

    def test_the_band_carries_its_count(self):
        band = qualitative_support_band(9, 10)
        assert band == "par une large majorité des scrutins (9 des 10 scrutins)"

    def test_unanimity_carries_its_count(self):
        band = qualitative_support_band(10, 10)
        assert band == "à l'unanimité des scrutins qui ont décidé (10 des 10 scrutins)"

    def test_the_protocols_are_named_apart_from_the_fraction(self):
        """#3394 (tranche R1145) — « 9 des 10 scrutins, plus deux protocoles
        de consensus »: the protocols run and are recorded, but they are not
        scrutins and never enter the vote's denominator."""
        band = qualitative_support_band(9, 10, n_consensus_protocols=2)
        assert band == (
            "par une large majorité des scrutins (9 des 10 scrutins), "
            "plus deux protocoles de consensus"
        )
        assert "12" not in band, "the protocols must not inflate the population"
        # Honest absence: a record that carries no protocol gets no clause.
        assert qualitative_support_band(9, 10, n_consensus_protocols=0) == (
            "par une large majorité des scrutins (9 des 10 scrutins)"
        )
        assert qualitative_support_band(9, 10) == (
            "par une large majorité des scrutins (9 des 10 scrutins)"
        )
        # One protocol that decided (the other failed) says « un ».
        assert qualitative_support_band(9, 10, n_consensus_protocols=1) == (
            "par une large majorité des scrutins (9 des 10 scrutins), "
            "plus un protocole de consensus"
        )

    def test_no_band_without_a_measured_support(self):
        assert qualitative_support_band(None, 10) is None
        assert qualitative_support_band(9, 0) is None


class TestALabelCarriesItsDefinition:
    """Ask 3 — « sophisme métonymique » reached the reader bare."""

    def test_the_taxonomy_resolves_a_name_to_its_definition(self):
        assert taxonomy_definition(_ROOT_LABEL, None) == _ROOT_DESC

    def test_the_taxonomy_resolves_a_dotted_path(self):
        assert taxonomy_definition("", "0") == _ROOT_DESC

    def test_an_unresolvable_label_stays_bare(self):
        # A definition looked up, never borrowed: a wrong-node definition
        # would be invention, not lookup (anti-#1019).
        assert taxonomy_definition("sophisme inexistant de test", None) == ""

    def test_a_partial_name_is_not_a_lookup(self):
        # Substring matching could designate a sibling node — excluded by
        # construction.
        assert taxonomy_definition("Argument fallac", None) == ""

    def test_the_note_reads_the_entry_record(self):
        # R1143: the root definition is second person, so the note also names
        # the addressee the taxonomy speaks to.
        assert taxonomy_definition_note({"type": _ROOT_LABEL}) == (
            "définition (la taxonomie s'adresse à qui commet le sophisme) : "
            f"{_ROOT_DESC}"
        )

    def test_the_note_prints_nothing_when_the_node_does_not_resolve(self):
        assert taxonomy_definition_note({"type": "sophisme inexistant de test"}) == ""

    def test_a_definition_is_one_line_and_capped(self):
        long_text = "mot " * 100
        capped = _capped(long_text)
        assert len(capped) <= 241  # cap + ellipsis
        assert capped.endswith("…")
        assert "\n" not in capped


class TestTheDefinitionRidesTheFirstMention:
    """Ask 3, wiring — the weak-point line carries the definition once."""

    @staticmethod
    def _state_with_fallacies(n: int) -> SimpleNamespace:
        return SimpleNamespace(
            identified_arguments={
                "arg_1": "Une revendication synthetique numero 1.",
                "arg_2": "Une revendication synthetique numero 2.",
            },
            identified_fallacies={
                f"fallacy_{i}": {
                    "type": _ROOT_LABEL,
                    "family": "Erreur de raisonnement",
                    "target_argument_id": f"arg_{(i % 2) + 1}",
                    "justification": f"justification synthetique numero {i}",
                }
                for i in range(1, n + 1)
            },
            argument_quality_scores={},
            counter_arguments=[],
        )

    @staticmethod
    def _weaknesses_slot(prompt: str) -> str:
        start = prompt.find("[CE QUI NE TIENT PAS — faiblesses localisées]")
        assert start != -1, "weaknesses slot missing from the Act III prompt"
        # The item lines themselves open with a bracket (``- [fallacy] …``),
        # so the section ends at the next SECTION header (\n\n[), not at the
        # next bracket of any kind.
        end = prompt.find("\n\n[", start + 1)
        return prompt[start : end if end != -1 else len(prompt)]

    def test_the_first_mention_carries_the_definition(self):
        prompt = build_act3_prompt(build_act3_evidence(self._state_with_fallacies(1)))
        slot = self._weaknesses_slot(prompt)
        assert (
            "définition (la taxonomie s'adresse à qui commet le sophisme) : "
            f"{_ROOT_DESC}" in slot
        ), (
            "a taxonomy label reaching the reader carries the taxonomy's "
            "one-line definition on its first mention (#3394 ask 3), and the "
            "note names the addressee when the definition is second person "
            "(R1143)"
        )

    def test_the_definition_is_said_once_per_label(self):
        prompt = build_act3_prompt(build_act3_evidence(self._state_with_fallacies(3)))
        slot = self._weaknesses_slot(prompt)
        assert slot.count("définition") == 1, (
            "the definition rides the FIRST mention; a repeat on every line "
            "would bury the document-grounded detail"
        )
        assert slot.count(_ROOT_LABEL) >= 3


# --- Ask 1, residual surfaces: the ranking and the severity spectrum ----------


def _quality(*entries: tuple) -> dict:
    """Production shape: ``overall`` never travels without its ``scores``
    map (``add_quality_score`` writes the pair). ``n`` is the count of
    evaluated virtues — the sum's own ceiling (#1942)."""
    return {
        arg_id: {
            "overall": overall,
            "scores": {f"vertu_{i}": 1.0 for i in range(n)},
        }
        for arg_id, overall, n in entries
    }


class TestASumPrintsOnItsOwnMaximum:
    """Ask 1 — « évaluation globale 1,28 » was a sum without its ceiling."""

    def test_the_issue_example_shape(self):
        assert sum_on_its_maximum(1.28, 5) == "1,28 sur 5"

    def test_the_maximum_prints_as_a_count_not_a_float(self):
        assert sum_on_its_maximum(5.0, 6).endswith(" sur 6")

    def test_unmeasurable_ceiling_prints_nothing(self):
        assert sum_on_its_maximum(5.0, None) == ""
        assert sum_on_its_maximum(5.0, 0) == ""
        assert sum_on_its_maximum(None, 6) == ""
        assert sum_on_its_maximum(float("nan"), 6) == ""


class TestTheRankingCarriesItsScale:
    """Ask 1 — « qualité 3.0 » was the ranking's bare ``(3.0)``."""

    def test_each_listed_score_names_its_own_ceiling(self):
        line = quality_ranking_line(
            _quality(("arg_1", 5.0, 6), ("arg_2", 4.0, 2), ("arg_3", 3.0, 6)), 9
        )
        assert "arg_1 (5,00 sur 6)" in line, line
        assert "arg_2 (4,00 sur 2)" in line, line
        # two units on different ceilings: the reader sees which is which
        assert "sur 6" in line and "sur 2" in line

    def test_the_line_names_the_convention_and_the_direction_once(self):
        line = quality_ranking_line(_quality(("arg_1", 5.0, 6)), 9)
        assert "chaque score est une somme de vertus" in line, line
        assert "plus haut = meilleur" in line, line

    def test_the_winner_clause_carries_its_scale(self):
        # R1142 — the rank compares PARTS: 4-on-2 (part 2,00) outranks
        # 5-on-6 (part 0,83), the order the cycle-0 measurement table shows
        # on 9/10 documents. The scale clause rides each figure as before.
        line = quality_ranking_line(
            _quality(("arg_1", 5.0, 6), ("arg_2", 4.0, 2), ("arg_3", 3.0, 6)),
            9,
            "arg_1",
        )
        assert "est 2ᵉ de ce classement (5,00 sur 6)" in line, line
        assert "arg_2 (4,00 sur 2) est en tête" in line, line

    def test_the_overflow_group_carries_a_scale(self):
        # Under the part order the six 3.0-on-2 units (part 1,50) all
        # outrank 5.0-on-6 (part 0,83) and 4.0-on-2 (part 2,00) heads them:
        # three ride the listing, the boundary tie counts the other four.
        entries = [("arg_1", 5.0, 6), ("arg_2", 4.0, 2)]
        entries += [(f"arg_{i}", 3.0, 2) for i in range(3, 9)]
        line = quality_ranking_line(_quality(*entries), 9)
        assert "et 4 autres à 3,00 sur 2" in line, line

    def test_an_entry_without_a_ceiling_prints_no_number(self):
        # ``add_quality_score`` pairs the two; a state holding a bare sum has
        # an unmeasurable scale — the id rides, the bare number does not.
        quality = _quality(("arg_1", 5.0, 6), ("arg_2", 4.0, 2))
        quality["arg_bare"] = {"overall": 4.5}
        line = quality_ranking_line(quality, 9)
        assert "arg_bare" in line, line
        assert "arg_bare (" not in line, line


class TestSeverityCarriesItsScale:
    """Ask 1 — Act I's expected spectrum printed « (sévérité 0.8) » bare."""

    def test_the_general_spectrum_names_scale_and_direction(self):
        state = SimpleNamespace(
            source_metadata={},
            stakes_and_stakeholders={
                "stakes": [],
                "stakeholders": [],
                "rhetorical_register": "",
                "discursive_arena": "",
            },
            identified_arguments={},
        )
        evidence = build_act1_evidence(state)
        assert evidence.spectrum_general, "no genre → the general branch"
        prompt = build_act1_prompt(evidence)
        assert "sur 1,0 — plus haut = plus grave" in prompt, (
            "the severity weight reaches the writer on its [0, 1] scale, "
            "with the direction a non-specialist can read (#3394 ask 1)"
        )
        assert not re.search(
            r"sévérité \d\.\d\)", prompt
        ), "the bare dot-decimal severity shape is gone"
