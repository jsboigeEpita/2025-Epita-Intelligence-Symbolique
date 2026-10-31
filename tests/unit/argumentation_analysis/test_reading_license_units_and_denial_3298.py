# -*- coding: utf-8 -*-
"""#3298 — the licence reads units where the sentence names them, and French
« et non » as the denial it is.

Two false positives, one grounded synthesis (R1125a, one-document pass):

1. ``fallacy_name_without_record`` fired on a sentence that was RIGHT. It
   named its five units explicitly (``arg_16`` … ``arg_63``, all recorded) —
   but the check ignored explicit ids, and bound ``arg_47`` instead through
   the word ``identified``, which came from INSIDE the ``[artifact:…]``
   anchors. Two causes: anchor interiors fed the tokenizer, and an explicit
   ``arg_N`` named no unit. After #3307 the prose no longer prints bare keys
   at all — the unit is named through the anchor
   (``[artifact:identified_fallacies.fallacy_16]`` → its
   ``target_argument_id``), so the licence must read that channel too.

2. ``breadth_as_robustness`` fired on a sentence that DENIED the inference:
   « L'étendue des extensions mesure ici la rareté des arêtes et non la
   solidité du discours. » The contrastive « et non » / « mais non » was
   invisible to ``_NEGATION`` — the French counterpart of #3287's English
   ``not``.

Born red on ``b5f515b86``: the binding witnesses fail because explicit ids
and anchors name nothing (and anchor tokens bind the wrong unit), the
denial witnesses fail because « et non » is not a negation. The controls —
description-only naming, affirmative claim, other-clause negation — pass on
BOTH sides. Everything offline: ``SimpleNamespace`` states, the real
``check_reading_license``, no kernel, no network, zero spend. Synthetic
vocabularies only (notaire, fournil, tarification — no corpus content).
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _state() -> SimpleNamespace:
    """The R1125a shape in miniature.

    Seven units whose descriptions share no word with each other (so a
    distinctive token names exactly one unit); five carry a fallacy record,
    ``arg_47`` does not — its description alone contains the English word
    ``identified`` that the anchors' interiors carry too, which is the whole
    false bind. ``arg_51`` is the description-only and anchor-named control.
    """
    return SimpleNamespace(
        identified_arguments={
            "arg_16": "La dérision vise le notaire provincial.",
            "arg_23": "L'attaque vise le fournil municipal.",
            "arg_37": "Le renvoi au guichet doré détourne l'échange.",
            "arg_44": "Le procès d'incohérence s'appuie sur la vigie.",
            "arg_63": "La culpabilité par association circule au port.",
            "arg_47": "The identified pathway remains unmeasured.",
            "arg_51": "La tarification des abonnements nocturnes.",
        },
        identified_fallacies={
            "fallacy_3": {"fallacy_type": "dérision", "target_argument_id": "arg_16"},
            "fallacy_7": {
                "fallacy_type": "attaque personnelle",
                "target_argument_id": "arg_23",
            },
            "fallacy_16": {
                "fallacy_type": "whataboutisme",
                "target_argument_id": "arg_37",
            },
            "fallacy_9": {
                "fallacy_type": "procès en incohérence",
                "target_argument_id": "arg_44",
            },
            "fallacy_12": {
                "fallacy_type": "culpabilité par association",
                "target_argument_id": "arg_63",
            },
        },
    )


def _sparse_state() -> SimpleNamespace:
    """One sparse Dung frame (density 0.25 < 1.0) — the #3287 reproduction
    shape, for the denial witnesses."""
    return SimpleNamespace(
        dung_frameworks={
            "dung_4": {"arguments": ["a", "b", "c", "d"], "attacks": [["a", "b"]]}
        }
    )


def _kinds(text: str, state: SimpleNamespace) -> list:
    return [f["kind"] for f in check_reading_license(text, state)["flags"]]


# -- the measured sentence, defect 1 ----------------------------------------


R1125A_UNITS_SENTENCE = (
    "Ils prennent la forme de la dérision sur arg_16 "
    "[artifact:identified_fallacies.fallacy_3], de l'attaque personnelle sur "
    "arg_23 [artifact:identified_fallacies.fallacy_7], du whataboutisme sur "
    "arg_37 [artifact:identified_fallacies.fallacy_16], du procès en "
    "incohérence sur arg_44 [artifact:identified_fallacies.fallacy_9] et de "
    "la culpabilité par association sur arg_63 "
    "[artifact:identified_fallacies.fallacy_12]."
)


class TestTheUnitsTheSentenceNames:
    """DoD — unit binding: anchor tokens never bind, explicit ids and
    anchors do."""

    def test_the_measured_sentence_flags_nothing(self):
        """Born red on ``b5f515b86``: ``['fallacy_name_without_record']``
        with ``units == ['arg_47']`` — bound through ``identified`` inside
        the anchors, while the five explicit ids went unread."""
        assert _kinds(R1125A_UNITS_SENTENCE, _state()) == []

    def test_anchor_tokens_alone_no_longer_bind_a_unit(self):
        """The smallest reproduction: the fallacy name, an anchor, and
        nothing else. Old: ``arg_47`` bound through ``identified`` (anchor
        interior) → flagged. Now: the anchor names ``arg_44`` (its record's
        target, recorded) and the anchor's characters bind nothing."""
        sentence = (
            "Un whataboutisme apparaît également "
            "[artifact:identified_fallacies.fallacy_9]."
        )
        assert _kinds(sentence, _state()) == []

    def test_an_explicit_id_without_a_record_still_flags(self):
        """DoD control — naming ``arg_51`` in the prose binds it: no record
        sits on it, so the fallacy name IS unbacked. Old: the explicit id
        named nothing, the sentence shares no description token, and the
        false negative passed for clean."""
        sentence = "Le discours culmine en un homme de paille sur arg_51."
        kinds = _kinds(sentence, _state())
        assert kinds == ["fallacy_name_without_record"]
        flags = check_reading_license(sentence, _state())["flags"]
        assert flags[0]["measured"]["units"] == ["arg_51"]

    def test_a_unit_named_only_by_its_description_still_binds(self):
        """DoD control — the description path is untouched: naming arg_51 by
        its description's distinctive tokens binds it (and flags, no
        record). Passes on both sides of the fix."""
        sentence = (
            "La généralisation hâtive touche la tarification des abonnements "
            "nocturnes."
        )
        kinds = _kinds(sentence, _state())
        assert kinds == ["fallacy_name_without_record"]
        flags = check_reading_license(sentence, _state())["flags"]
        assert flags[0]["measured"]["units"] == ["arg_51"]

    def test_a_unit_anchor_names_its_unit(self):
        """The #3307 channel: the prose prints no bare key, the unit lives
        in the citation. ``[artifact:identified_arguments.arg_51]`` names
        arg_51 exactly as an explicit id did — unbacked name, flagged. Old:
        anchors named nothing, the false negative passed for clean."""
        sentence = (
            "Le whataboutisme revient ici [artifact:identified_arguments.arg_51]."
        )
        kinds = _kinds(sentence, _state())
        assert kinds == ["fallacy_name_without_record"]
        flags = check_reading_license(sentence, _state())["flags"]
        assert flags[0]["measured"]["units"] == ["arg_51"]


# -- the measured sentence, defect 2 ----------------------------------------


R1125A_DENIAL_SENTENCE = (
    "L'étendue des extensions mesure ici la rareté des arêtes et non la "
    "solidité du discours [artifact:dung_frameworks.dung_4]."
)


class TestFrenchContrastiveDenial:
    """DoD — « et non » / « mais non » before the marker, same clause,
    licenses; the affirmative claim and another clause's negation do
    not (#3288 scope rules)."""

    def test_the_measured_sentence_is_not_a_robustness_claim(self):
        """Born red on ``b5f515b86``: ``['breadth_as_robustness']`` — the
        denial « et non la solidité » was invisible to ``_NEGATION``."""
        assert _kinds(R1125A_DENIAL_SENTENCE, _sparse_state()) == []

    def test_mais_non_licenses_the_same_way(self):
        sentence = (
            "L'étendue des extensions mesure ici la rareté des arêtes mais "
            "non la solidité du discours."
        )
        assert _kinds(sentence, _sparse_state()) == []

    def test_pas_still_licenses_the_issue_probe(self):
        """The issue's own probe: the same sentence with « pas » never
        flagged. Control on both sides."""
        sentence = (
            "L'étendue des extensions mesure ici la rareté des arêtes, pas "
            "la solidité du discours."
        )
        assert _kinds(sentence, _sparse_state()) == []

    def test_the_affirmative_sentence_still_flags(self):
        """DoD control — the assertion is still caught, on both sides."""
        sentence = "L'étendue des extensions montre la solidité du discours."
        assert _kinds(sentence, _sparse_state()) == ["breadth_as_robustness"]

    def test_a_negation_in_another_clause_does_not_license(self):
        """DoD control, the #3288 scope: the « et non » denies the monetary
        reading, sixty characters away from the claim it would need to
        deny. The 32-character window is the scope rule — unwidened here.
        Flags on both sides."""
        sentence = (
            "L'analyse écarte la piste monétariste et non la piste "
            "keynésienne, puis l'étendue des extensions mesure la solidité "
            "du discours."
        )
        assert _kinds(sentence, _sparse_state()) == ["breadth_as_robustness"]
