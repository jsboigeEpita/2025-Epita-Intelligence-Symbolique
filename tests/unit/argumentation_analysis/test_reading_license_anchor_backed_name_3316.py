# -*- coding: utf-8 -*-
"""#3316 — a fallacy name cited with its own record anchor is backed; the
check stops reading units the sentence never names.

The flag ``fallacy_name_without_record`` fired on a sentence that names a
fallacy **with its own record anchor**, because ANOTHER word of the same
sentence bound a record-less unit through the description channel. The
coordinator's census: the remaining false positive of #3313's class (R1127c)
binds a unit through the token ``speaker``; after #3307 the prose prints no
bare key, so description tokens are a larger share of how the check binds
units, and coincidences of this kind become more likely, not less.

Measured before the candidate was kept (stored states, zero LLM calls):
candidate A — the anchor backs the name — removes **4 distinct false
positives** of the 31 the flag raises on this seat's 496 texts (among them
the ``speaker`` and ``opponent`` bindings of the R1127 pass state), and
loses **zero true positives**: in every removed flag the unbacked units
were bound only through description-token coincidences, never through an
explicit id or an anchor. Candidate B — subtracting taxonomy vocabulary
before description binding — removes **nothing** on this corpus: the
binding tokens are ordinary English words (carries, reasons, opponent,
speaker, claims), not label vocabulary. A also reads what the sentence
asserts, which is why it is the one kept.

One measured trap the helper encodes: a clause boundary never sits INSIDE
an anchor — the anchor's own dots (``identified_fallacies`` **.**
``fallacy_2``) are not punctuation. A plain ``[.,;:!?]`` search cut the
span at the record key's dot, and the backing anchor became invisible —
that bug is why the first measurement of candidate A removed nothing.

Born red on ``10f54722f`` (main + #3318): the two shape witnesses flag; the
controls — no anchor, dangling anchor, anchor in another clause — pass on
BOTH sides. Everything offline: ``SimpleNamespace`` states, the real
``check_reading_license``, no kernel, no network, zero spend. Synthetic
vocabularies only.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _state() -> SimpleNamespace:
    """Six units whose descriptions share no word with each other (so a
    distinctive token names exactly one unit); five carry a fallacy record.
    ``arg_53`` and ``arg_6`` carry none — their descriptions alone contain
    the English words ``speaker`` and ``opponent`` that the report's prose
    carries too, which is the whole false bind."""
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


# -- the measured shapes (R1127c speaker binding; ad hominem opponent) --------

R1127C_SPEAKER_SENTENCE = (
    "The tu quoque against the corruption charge "
    "[artifact:identified_fallacies.fallacy_1] and the whataboutism against "
    "the admission question [artifact:identified_fallacies.fallacy_2] both "
    "shift the burden onto Speaker_B."
)

OPPONENT_SENTENCE = (
    "The ad hominem against arg_45 [artifact:identified_fallacies.fallacy_11] "
    "is scored as weak reasoning and depends on discrediting its opponent."
)


class TestTheAnchorBacksTheName:
    """DoD — a name followed, within its clause, by a fallacy anchor whose
    record exists is backed: the check does not look for other units in the
    sentence. No anchor, a dangling anchor, or an anchor in another clause
    back nothing."""

    def test_the_r1127c_shape_flags_nothing(self):
        """Born red: on the pre-fix module the sentence flags
        ``fallacy_name_without_record`` with ``units == ['arg_53']`` — bound
        through ``speaker`` while the name's own anchor (fallacy_2, record
        existing) sits right after it."""
        assert _flags(R1127C_SPEAKER_SENTENCE, _state()) == []

    def test_the_opponent_binding_flags_nothing(self):
        """The second measured shape: the name backed by fallacy_11, arg_6
        bound through ``opponent``. Born red the same way."""
        assert _flags(OPPONENT_SENTENCE, _state()) == []

    def test_a_name_without_an_anchor_still_flags(self):
        """DoD control — no anchor, an unbacked unit named explicitly: the
        name is NOT backed, the flag is real. Green on both sides."""
        flags = _flags("L'ad hominem frappe ici arg_6.", _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_a_dangling_anchor_backs_nothing(self):
        """DoD control — an anchor whose record does NOT exist is not a
        backing: the flag stays. Green on both sides."""
        flags = _flags(
            "L'ad hominem [artifact:identified_fallacies.fallacy_99] "
            "frappe ici arg_6.",
            _state(),
        )
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]

    def test_an_anchor_in_another_clause_backs_nothing(self):
        """DoD control — the comma ends the name's clause before the anchor:
        no backing, and the description-bound unbacked unit still flags.
        Green on both sides."""
        sentence = (
            "L'ad hominem est allégué, et le registre "
            "[artifact:identified_fallacies.fallacy_11] concerne une autre "
            "unité que son opponent."
        )
        flags = _flags(sentence, _state())
        assert [f["measured"]["units"] for f in flags] == [["arg_6"]]
