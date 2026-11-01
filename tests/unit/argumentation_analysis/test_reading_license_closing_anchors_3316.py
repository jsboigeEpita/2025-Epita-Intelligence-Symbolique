# -*- coding: utf-8 -*-
"""#3316 leg 2 — a fallacy name separated from its record anchors by a
qualifying clause is backed by the anchors that close the sentence.

The residual the coordinator's replay kept (R1129a, ``arg_52``): the name is
followed by a comma, then by « attribuées à la parole rapportée de
l'adversaire, non à … », then by the anchors that cite its records. Leg 1
backed a name by an anchor **within its clause**, so the comma put both
anchors out of reach and the flag stood.

Two candidates were measured first on this seat's stored states (187 states,
496 texts, zero LLM calls):

- **widen ``_ATTRIBUTION_MARKERS`` to the reported-speech attribution**
  (``attribu\\w+ à``, ``parole rapportée``): removes **0** flags on this
  seat's fallacy surface, but moves **8** flags on ``counter_claim_in_own_voice``
  — the rule #3158 shares that marker set with. It was not kept: a shared
  surface moved without a carrier to justify it.
- **let the anchors that close the sentence back the name**: removes **0**
  here too (the residual lives on the coordinator's saved paid states, not on
  this seat) and moves **nothing else**. Kept.

The risk the coordinator named — ``(b)`` reopens the borrowing that the
clause stop prevents — is fenced four ways (see
``_backed_by_closing_anchors``): the run must CLOSE the sentence, every
anchor in it must be a record-bearing fallacy anchor, the prose outside
anchors must name no explicit ``arg_N``, and no later fallacy name may
follow the matched one (that is the neighbour-borrowing case, and the
control asserts it still flags).

Born red on ``198d7dd9a``: the residual witness flags; every control passes
on BOTH sides. ``SimpleNamespace`` states, the real ``check_reading_license``,
no kernel, no network, zero spend. Synthetic vocabularies only.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _state() -> SimpleNamespace:
    """Six units whose descriptions share no word with each other (so a
    distinctive token names exactly one unit); five carry a fallacy record.
    ``arg_6`` carries none — its description alone contains the English word
    ``opponent`` that the report's prose carries too, which is the whole
    false bind."""
    return SimpleNamespace(
        identified_arguments={
            "arg_13": "La passerelle desservait le comptoir douanier.",
            "arg_53": "The speaker concedes the admission question.",
            "arg_85": "Le séquestre amortit la crique saisonnière.",
            "arg_6": "The opponent funds the weekly gazette.",
            "arg_45": "La vigie du quai signale le chaland.",
            "arg_118": "L'arbitre du quai clôt la grieche.",
        },
        identified_fallacies={
            "fallacy_1": {"fallacy_type": "tu quoque", "target_argument_id": "arg_13"},
            "fallacy_2": {
                "fallacy_type": "whataboutisme",
                "target_argument_id": "arg_85",
            },
            "fallacy_11": {
                "fallacy_type": "ad hominem",
                "target_argument_id": "arg_45",
            },
            "fallacy_14": {
                "fallacy_type": "ad hominem",
                "target_argument_id": "arg_118",
            },
            "fallacy_15": {
                "fallacy_type": "bad reasons",
                "target_argument_id": "arg_118",
            },
        },
    )


def _flags(text: str, state: SimpleNamespace) -> list:
    return [
        f
        for f in check_reading_license(text, state)["flags"]
        if f["kind"] == "fallacy_name_without_record"
    ]


#: The residual shape, synthetic vocabulary: the name, a comma, the
#: attribution qualifier, then the two anchors that cite its records — the
#: run that closes the sentence. ``arg_6`` (no record) is bound by the word
#: ``opponent``; ``l'arbitre du quai`` names ``arg_118``, which HAS a record.
R1129A_RESIDUAL = (
    "La métaphore et la fausse analogie, mais attribuées à la parole "
    "rapportée de l'opponent, non à l'arbitre du quai "
    "[artifact:identified_fallacies.fallacy_11] "
    "[artifact:identified_fallacies.fallacy_14]."
)

#: The same sentence with its anchors removed: the flag it must keep.
R1129A_WITHOUT_ANCHORS = (
    "La métaphore et la fausse analogie, mais attribuées à la parole "
    "rapportée de l'opponent, non à l'arbitre du quai."
)


class TestTheClosingAnchorsBackTheName:
    """DoD box 1 — the residual shape stops flagging once the anchors that
    close the sentence are read as the name's backing."""

    def test_the_r1129a_residual_shape_flags_nothing(self):
        """Born red: on the pre-fix module this sentence flags
        ``fallacy_name_without_record`` with ``units == ['arg_6']`` — the
        name's clause ends at the comma, both anchors sit outside it."""
        assert _flags(R1129A_RESIDUAL, _state()) == []

    def test_the_same_sentence_without_its_anchors_still_flags(self):
        """The positive control: removing only the anchors brings the flag
        back, so it is the anchors — not the wording — that backed the name.
        Green on both sides."""
        flags = _flags(R1129A_WITHOUT_ANCHORS, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]


class TestTheBorrowingFenceHolds:
    """DoD box 2 — what the widening must NOT license. Every case below is
    green on both sides: the pre-fix module flags it through the clause stop,
    the post-fix module still flags it."""

    def test_a_later_name_cannot_borrow_the_closing_anchor(self):
        """The coordinator's control: « name with an anchor, then a name
        without ». Here the second name owns the closing anchor, so the
        first one must not be backed by it."""
        sentence = (
            "La fausse analogie pèse sur l'opponent, et l'ad hominem est cité "
            "[artifact:identified_fallacies.fallacy_11]."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_a_dangling_closing_anchor_backs_nothing(self):
        """A record that does not exist is not a backing (leg 1's rule, kept
        at sentence level)."""
        sentence = (
            "La fausse analogie pèse sur l'opponent "
            "[artifact:identified_fallacies.fallacy_99]."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_an_explicit_unit_id_keeps_the_flag(self):
        """The sentence already names its unit in prose: the anchors are not
        what identifies it, so they back nothing. The comma keeps the anchor
        out of the name's clause — without it the leg-1 rule would back the
        name and this control would test nothing."""
        sentence = (
            "La fausse analogie pèse sur arg_6, citée "
            "[artifact:identified_fallacies.fallacy_11]."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_a_mixed_anchor_run_backs_nothing(self):
        """A unit anchor among the closing run makes it ambiguous: said
        nothing rather than guessed. The comma keeps the run out of the
        name's clause, so the sentence-level reading is what is under test."""
        sentence = (
            "La fausse analogie pèse sur l'opponent, citée "
            "[artifact:identified_arguments.arg_45] "
            "[artifact:identified_fallacies.fallacy_11]."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_anchors_that_do_not_close_the_sentence_back_nothing(self):
        """The widening reads the run that ENDS the sentence. Anchors with
        prose after them stay what leg 1 said they were: out of the clause,
        backing nothing."""
        sentence = (
            "La fausse analogie pèse sur l'opponent, citée "
            "[artifact:identified_fallacies.fallacy_11] depuis longtemps."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]
