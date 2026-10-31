# -*- coding: utf-8 -*-
"""#3318 — the bare comma-contrastive denial « X, non Y » is a denial.

``breadth_as_robustness`` fired on the sentence that REFUSES the inference,
on every paid pass that used the bare comma form — the coordinator's census
(R1127a/b/c, R1129a): « …mesure la rareté des arêtes, non la solidité du
discours. » #3298 taught ``_NEGATION`` « et non » / « mais non » / « ou
non »; the comma form, which the writers use far more, was still read as an
affirmation — every ``breadth_as_robustness`` flag on the five most recent
paid passes was a false positive accusing the writer of the very inference
the sentence refuses.

Measured before the pattern was kept (stored states, zero LLM calls): 501
raw « , non » occurrences against 0 « non seulement » and 0 « non sans »;
five distinct sentences sit in a negation window of a marker and all five
are denials; replaying the whole licence on the 496 texts with and without
the candidate moves no flag in either direction (722 = 722).

One measured divergence from the issue's DoD, witnessed here as it behaves:
the control « non sans solidité » does NOT flag on main either — a window
carrying « sans » is already licensed by ``_NEGATION``'s own ``sans`` token
(pre-existing, unchanged by this fix). The candidate's lookahead keeps « non
sans » out so it cannot license anything beyond what ``sans`` already does,
and the witness pins that behaviour on both sides.

Born red on ``d4c5558bd``: the two denial witnesses fail (the comma form is
not a negation); the controls pass on BOTH sides. Everything offline:
``SimpleNamespace`` states, the real ``check_reading_license``, no kernel,
no network, zero spend. Model prose only.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _sparse_state() -> SimpleNamespace:
    """One sparse Dung frame (density 0.25 < 1.0) — the #3287/#3298
    reproduction shape, for the denial witnesses."""
    return SimpleNamespace(
        dung_frameworks={
            "dung_4": {"arguments": ["a", "b", "c", "d"], "attacks": [["a", "b"]]}
        }
    )


def _kinds(text: str, state: SimpleNamespace) -> list:
    return [f["kind"] for f in check_reading_license(text, state)["flags"]]


# -- the measured sentences (R1127a and R1129a shapes) ------------------------


class TestCommaContrastiveDenial:
    """DoD — « , non » before the marker, same clause, licenses; the
    affirmative claim, the non-denial « non » forms and another clause's
    « , non » do not."""

    def test_the_measured_comma_denial_is_not_a_robustness_claim(self):
        """Born red on ``d4c5558bd``: ``['breadth_as_robustness']`` — the
        denial « , non la solidité » was invisible to ``_NEGATION``."""
        sentence = (
            "L'étendue des extensions mesure ici la rareté des arêtes, non "
            "la solidité du discours."
        )
        assert _kinds(sentence, _sparse_state()) == []

    def test_the_arcs_variant_licenses_the_same_way(self):
        """The R1129a wording — same denial, one word apart."""
        sentence = (
            "L'étendue des extensions mesure ici la rareté des arcs, non "
            "la solidité de l'argumentation."
        )
        assert _kinds(sentence, _sparse_state()) == []

    def test_non_seulement_still_flags(self):
        """DoD control — « non seulement » asserts what follows (#3287's
        ``not only``): it must not license the marker it rides. Flags on
        both sides of the fix."""
        sentence = (
            "L'étendue des extensions atteste, non seulement la solidité "
            "du discours, mais sa portée."
        )
        assert _kinds(sentence, _sparse_state()) == ["breadth_as_robustness"]

    def test_non_sans_stays_licensed_by_the_preexisting_sans(self):
        """DoD control, measured divergence — the issue asks that « non
        sans solidité » still flags; it does not flag on MAIN either,
        because ``sans`` alone already licenses a window carrying it
        (``_NEGATION``'s own token, pre-existing). Witnessed as it behaves,
        on both sides: the comma candidate adds nothing here — the
        lookahead keeps « non sans » out of the new alternative."""
        sentence = (
            "L'étendue des extensions couvre peu d'attaques, restant non "
            "sans solidité."
        )
        assert _kinds(sentence, _sparse_state()) == []

    def test_the_affirmative_sentence_still_flags(self):
        """DoD control — the assertion is still caught, on both sides."""
        sentence = "L'étendue des extensions montre la solidité du discours."
        assert _kinds(sentence, _sparse_state()) == ["breadth_as_robustness"]

    def test_a_comma_non_in_another_clause_does_not_license(self):
        """DoD control, the #3288 scope — the « , non » denies the coverage
        reading; the claim it would need to deny sits another clause away,
        outside the unchanged 32-character window. Flags on both sides."""
        sentence = (
            "L'étendue des extensions mesure la rareté des arêtes, non la "
            "couverture des attaques, et c'est bien la solidité du discours "
            "qui s'en déduit."
        )
        assert _kinds(sentence, _sparse_state()) == ["breadth_as_robustness"]
