# -*- coding: utf-8 -*-
"""#3158 — a counter-argument's factual claim stays the counter-argument's.

Act II restated, in the report's own voice, a *prior trend* that no source in
the state asserts: ``fallacy_15`` (post hoc) only says other factors are not
ruled out, while the trend is asserted by ``ca_31`` — an LLM-generated
counter-argument that cites no source. The prompt handed it over as a bare
line ``Contre-argument (…) : …`` with no rule saying whose claim it is, so the
writer adopted an unverified external fact as the refutation. The reader
cannot tell it from a checked fact.

The fix is producer-side, because only that is deterministic: the line that
carries a factual claim carries its provenance, and the writer is bound to
keep the attribution. A **render check** backs it — a paragraph that restates
that claim with no attribution is flagged.

* witness — the rebuilt prompt carries the claim with its tag; the check
  flags an unattributed restatement.
* control — a counter-argument that only reframes the question asserts
  nothing about the world: no tag, and restating it earns no flag.
* mutation — removing the tag makes the witness red.

Synthetic vocabulary only (phares, bonde océane, cloche du port — no corpus
content, privacy HARD): the *shape* is doc_B's, the words are not.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

#: The claim the counter makes about the world. It asserts a prior empirical
#: trend through an external authority (« les études ») — exactly the form
#: that was adopted as a checked fact.
_CLAIM = (
    "Les études montrent que la poussée des marées dépend d'autres facteurs "
    "que la cloche du port, et non du tintement qu'on lui prête."
)

#: A counter-argument that only reframes the question. It asserts nothing
#: about the world: there is no fact to attribute.
_REFRAMING = (
    "Autrement dit, la question est de savoir si le locuteur visait vraiment "
    "la cloche du port, ou seulement l'heure qu'elle annonce."
)

#: The doc_B instance the issue was filed for: an ENGLISH counter whose claim
#: is a dated trend. The predicate returned False on it — the vocabulary was
#: French-only and carried no year or trend marker.
_ENGLISH_DATED_TREND = (
    "The 2019 staffing deal shows that labour costs have been falling since "
    "the harbour opened, well beyond the toll change."
)

#: The same trend with no year in the sentence: the direction over time is
#: the fact, and a vocabulary that only read years would miss it.
_ENGLISH_TREND_NO_YEAR = (
    "Labour costs have been falling since the harbour opened, well beyond "
    "the toll change."
)

#: The reframing control, in English — the generator writes both languages.
_ENGLISH_REFRAMING = (
    "In other words, the question is whether the speaker meant the harbour "
    "bell, or only the hour it announces."
)

TAG = "affirmation factuelle NON SOURCÉE"


def _state(counter_content: str = _CLAIM):
    # Real producer shapes (measured on the paid states): `add_argument` writes
    # the description STRING itself, and `add_fallacy` writes the target under
    # `target_argument_id`. Counters are the ones keyed by `target_arg_id`.
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        identified_arguments={
            "arg_1": "La cloche du port annonce la poussée des marées."
        },
        identified_fallacies={
            "fallacy_15": {
                "id": "fallacy_15",
                "type": "post hoc",
                "family": "causalité",
                "justification": (
                    "Rien n'exclut que d'autres facteurs expliquent la "
                    "coïncidence observée."
                ),
                "target_argument_id": "arg_1",
            }
        },
        counter_arguments=[
            {
                "id": "ca_31",
                "target_arg_id": "arg_1",
                "strategy": "Alternative causal explanation",
                "counter_content": counter_content,
                "score": 0.485,
            }
        ],
        argument_quality_scores=None,
    )


def _prompt(counter_content: str = _CLAIM) -> str:
    return build_act2_prompt(build_act2_evidence(_state(counter_content)))


def _counter_line(prompt: str) -> str:
    lines = [ln for ln in prompt.splitlines() if "Contre-argument" in ln]
    assert len(lines) == 1, lines
    return lines[0]


class TestThePromptCarriesTheProvenance:
    def test_the_factual_claim_arrives_with_its_provenance_tag(self):
        """Born red on main: the line was ``Contre-argument (stratégie) : …``
        — the writer had no way to know the claim was a generator's."""
        line = _counter_line(_prompt())
        assert TAG in line
        # the tag rides on the claim's own line, not somewhere else in the
        # prompt where the writer could miss the binding
        assert "poussée des marées" in line

    def test_a_reframing_counter_carries_no_tag(self):
        """Control — a counter that asserts nothing about the world needs no
        provenance: there is no fact for the report to adopt."""
        assert TAG not in _counter_line(_prompt(_REFRAMING))

    def test_an_english_dated_trend_is_tagged_too(self):
        """Witness (born red, rework): ca_31 on the doc_B state is an English
        dated trend — French-only vocabulary left the very instance the issue
        was filed for untagged."""
        assert TAG in _counter_line(_prompt(_ENGLISH_DATED_TREND))

    def test_an_english_trend_without_a_year_is_tagged(self):
        """The direction over time is the fact: a vocabulary that only read
        years would tag the dated form and miss this one."""
        assert TAG in _counter_line(_prompt(_ENGLISH_TREND_NO_YEAR))

    def test_an_english_reframing_carries_no_tag(self):
        """Control, other language — the generator writes English or French
        depending on the run; a reframing asserts nothing in either."""
        assert TAG not in _counter_line(_prompt(_ENGLISH_REFRAMING))


class TestTheCheckFlagsTheChangeOfVoice:
    def test_an_unattributed_restatement_is_flagged(self):
        """The defect sentence: the trend, in the report's own voice, used as
        the refutation. Nothing in it names whose claim it is."""
        weave = (
            "La cloche du port n'explique pas la poussée des marées : les "
            "études montrent que d'autres facteurs en décident."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_claim_in_own_voice" in kinds
        flag = next(
            f for f in result["flags"] if f["kind"] == "counter_claim_in_own_voice"
        )
        assert flag["measured"]["counters"] == ["ca_31"]

    def test_an_attributed_restatement_is_not_flagged(self):
        """Control — the same claim, attributed. This is the sentence the
        consigne asks for; it must stay green."""
        weave = (
            "La cloche du port n'explique pas la poussée des marées : un "
            "contre-argument objecte que les études montrent que d'autres "
            "facteurs en décident."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_claim_in_own_voice" not in kinds

    def test_a_reframing_counter_restated_earns_no_flag(self):
        """Control — the reframing asserts nothing, so its restatement is not
        an adopted fact and cannot be flagged as one."""
        weave = (
            "La cloche du port n'explique pas la poussée des marées ; "
            "autrement dit, la question est de savoir si le locuteur visait "
            "vraiment la cloche du port."
        )
        result = check_reading_license(weave, _state(_REFRAMING))
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_claim_in_own_voice" not in kinds

    def test_a_pronoun_attribution_counts(self):
        """Control — « . Selon lui, les études … »: the pronoun carries the
        attribution into the second sentence."""
        weave = (
            "Un contre-argument objecte à cette lecture. Selon lui, les "
            "études montrent que d'autres facteurs décident de la poussée "
            "des marées."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_claim_in_own_voice" not in kinds

    def test_an_attribution_in_the_previous_sentence_still_counts(self):
        """Control — the objection is named, then the claim follows in a
        sentence with no marker of its own (« Un contre-argument objecte à
        cette lecture. Les études montrent que … »). The attribution is one
        sentence away, which the consigne's own phrasing invites; flagging it
        would punish the writer for following the rule."""
        weave = (
            "Un contre-argument objecte à cette lecture. Les études montrent "
            "que d'autres facteurs décident de la poussée des marées."
        )
        result = check_reading_license(weave, _state())
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_claim_in_own_voice" not in kinds


# --- second instance: the debate channel (issue comment) -------------------

_DILEMMA_UNIT = "Le dilemme des résolutions impose un choix binaire, sans issue."
_DILEMMA_WEAVE = "Le dilemme des résolutions se retourne : c'est un faux dilemme."


def _act3_state(*, with_record: bool):
    state = _state()
    state.identified_arguments = {"arg_69": _DILEMMA_UNIT}
    state.identified_fallacies = (
        {
            "fallacy_1": {
                "id": "fallacy_1",
                "type": "post hoc",
                "family": "causalité",
                "justification": "Aucune autre cause n'est écartée.",
                "target_argument_id": "arg_69",
            }
        }
        if with_record
        else {}
    )
    state.debate_transcripts = [
        {
            "topic": "t",
            "exchanges": [
                {
                    "point": "le dilemme des résolutions impose un choix binaire",
                    "rebuttal": "The dilemma is also false, because both horns fail.",
                }
            ],
        }
    ]
    return state


class TestTheDebateChannel:
    def test_a_debate_reply_arrives_with_its_provenance_tag(self):
        """Born red on main: the DÉBAT line delivered the reply's verdict as
        plain matter, and Act III restated « c'est un faux dilemme » as its own
        finding on a unit no detector had recorded anything for."""
        prompt = build_act3_prompt(build_act3_evidence(_act3_state(with_record=False)))
        line = next(ln for ln in prompt.splitlines() if "DÉBAT (échange" in ln)
        assert "réplique produite par un agent de débat" in line
        assert "jamais vérifiée" in line
        # on the reply's own line, where the rule it serves applies
        assert "both horns fail" in line

    def test_a_fallacy_name_needs_a_record_on_the_unit(self):
        """Born red: no check existed. The name, in the report's own voice, on
        a unit whose record carries a different fallacy."""
        result = check_reading_license(_DILEMMA_WEAVE, _act3_state(with_record=False))
        kinds = [f["kind"] for f in result["flags"]]
        assert "fallacy_name_without_record" in kinds
        flag = next(
            f for f in result["flags"] if f["kind"] == "fallacy_name_without_record"
        )
        assert flag["measured"]["name"].lower() == "faux dilemme"
        assert flag["measured"]["units"] == ["arg_69"]

    def test_a_fallacy_name_on_a_recorded_unit_passes(self):
        """Control — the unit carries a fallacy record, so naming a class on it
        is not an invention. No flag."""
        result = check_reading_license(_DILEMMA_WEAVE, _act3_state(with_record=True))
        kinds = [f["kind"] for f in result["flags"]]
        assert "fallacy_name_without_record" not in kinds

    def test_a_negated_fallacy_name_is_no_claim(self):
        """Control — « Rien n'indique un faux dilemme » asserts nothing."""
        weave = "Rien n'indique un faux dilemme dans le dilemme des résolutions."
        result = check_reading_license(weave, _act3_state(with_record=False))
        kinds = [f["kind"] for f in result["flags"]]
        assert "fallacy_name_without_record" not in kinds

    def test_a_name_attributed_to_the_debate_is_not_the_reports(self):
        """Control — the name is the reply's, and the report says so."""
        weave = (
            "Dans le débat, la réplique objecte qu'il s'agit d'un faux dilemme "
            "sur le dilemme des résolutions."
        )
        result = check_reading_license(weave, _act3_state(with_record=False))
        kinds = [f["kind"] for f in result["flags"]]
        assert "fallacy_name_without_record" not in kinds
