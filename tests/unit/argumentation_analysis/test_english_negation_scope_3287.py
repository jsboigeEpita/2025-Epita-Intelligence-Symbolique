"""#3287 — the negation test reads English, and does not read across a clause.

The R1124 one-document render carried a sentence that explicitly denies the
inference the ``breadth_as_robustness`` check exists to catch:

    The framework itself warns that this breadth reflects sparse attack
    coverage, not a robust discourse.

The check flagged it anyway, because ``_NEGATION`` (``reading_license.py:108``)
declared only French tokens (``ne``, ``n'``, ``pas``, ``jamais``, ``sans``,
``aucun*``). The English denial was invisible.

The obvious repair — add ``not`` to that pattern — is the one this file exists
to forbid: a 32-character window will happily carry a negation belonging to a
DIFFERENT claim ("This is not sparse coverage, and a robust discourse is what
it shows" asserts robustness). So the English side is read only when it sits
ADJACENT to the robustness marker: no punctuation between the two. The scope
control below is the anti-masque — it goes red if the English tokens are ever
folded into the broad ``_NEGATION`` window.

Everything here is offline: a ``SimpleNamespace`` carrying one Dung frame, the
real ``check_reading_license``, no kernel, no network, zero spend.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _sparse_state() -> SimpleNamespace:
    """The reproduction the issue names: two arguments, zero attacks."""
    return SimpleNamespace(
        dung_frameworks={"frame": {"arguments": ["a", "b"], "attacks": []}}
    )


def _kinds(text: str) -> list:
    return [
        flag["kind"] for flag in check_reading_license(text, _sparse_state())["flags"]
    ]


# -- the exact sentence from the paid render -------------------------------

R1124_SENTENCE = (
    "The framework itself warns that this breadth reflects sparse attack "
    "coverage, not a robust discourse."
)


class TestTheMeasuredFalsePositiveIsGone:
    def test_the_r1124_sentence_is_not_a_robustness_claim(self):
        # Born red on 2e2a1c3cf: ["breadth_as_robustness"].
        assert _kinds(R1124_SENTENCE) == []

    @pytest.mark.parametrize(
        "text",
        [
            "This breadth does not establish a robust discourse.",
            "This breadth isn't a robust discourse.",
            "The framework warns this breadth is never a robust discourse.",
            "This breadth is hardly a robust discourse.",
            "The breadth is far from a robust discourse.",
        ],
    )
    def test_other_english_denials_are_not_claims(self, text):
        assert _kinds(text) == []


# -- the controls that must keep working -----------------------------------


class TestAffirmativeControlsStillFlag:
    def test_affirmative_english_is_still_flagged(self):
        assert _kinds("This breadth shows a robust discourse.") == [
            "breadth_as_robustness"
        ]

    def test_affirmative_french_is_still_flagged(self):
        assert _kinds(
            "L'extension grounded couvre les deux arguments et le propos est robuste."
        ) == ["breadth_as_robustness"]

    def test_a_qualified_french_denial_is_still_unflagged(self):
        assert (
            _kinds(
                "L'extension grounded couvre tout, mais elle n'est pas robuste "
                "face à une attaque supplémentaire."
            )
            == []
        )


class TestScopeIsRespected:
    def test_a_negation_in_another_clause_does_not_license_the_claim(self):
        """The control the issue asks for: 'not' negates sparsity, not robustness.

        This sentence asserts robustness, so it must stay flagged. It goes red
        the moment the English tokens are read through the broad 32-character
        window instead of the adjacent-prefix test: the window holds ``not``,
        the claim does not.
        """
        assert _kinds(
            "This breadth is not sparse; a robust discourse is what it shows."
        ) == ["breadth_as_robustness"]

    def test_a_coordination_break_does_not_license_the_claim(self):
        """'not sparse but robust' asserts both halves."""
        assert _kinds("This breadth is not sparse but a robust discourse.") == [
            "breadth_as_robustness"
        ]

    def test_a_negation_after_the_marker_does_not_license_it(self):
        assert _kinds("This breadth shows a robust discourse, not a weakness.") == [
            "breadth_as_robustness"
        ]

    def test_not_only_asserts_what_follows(self):
        """'not only broad but robust' asserts both terms."""
        assert _kinds("The breadth is not only broad but robust discourse.") == [
            "breadth_as_robustness"
        ]

    def test_a_denial_buried_far_inside_the_same_clause_does_not_license_it(self):
        """The window is the existing scope rule; it is not widened here."""
        assert _kinds(
            "The analysis does not support any reading under which this breadth "
            "would count as a robust discourse."
        ) == ["breadth_as_robustness"]
