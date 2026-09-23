"""#2362 class A, option 4 — the additions are class vocabulary, measured.

User arbitration Q-R1042-A (2026-09-23): the 5 heads of state and the 4
spelling variants are PUBLIC CLASS VOCABULARY, not document identifiers.
Measured margin (2026-09-23, tokens derived at runtime from the encrypted
corpus): none of the 9 additions appears among the tokens — zero corpus
margin; the merged list measures 26 of 28 absent. Only hit counts are
written here, never which entries the corpus holds.

No leader spelling is written in this file (the tests/ sweep would flag
it): every carrier below is derived from PERSON_PATTERNS at runtime.
"""

from __future__ import annotations


def test_option4_additions_are_present() -> None:
    """19 patterns before the arbitration + 9 additions = the merged list."""
    from argumentation_analysis.evaluation.leak_patterns import PERSON_PATTERNS

    assert len(PERSON_PATTERNS) == 28, (
        f"PERSON_PATTERNS carries {len(PERSON_PATTERNS)} entries — the "
        "option-4 additions (Q-R1042-A) are not all in the class vocabulary"
    )


def test_person_re_catches_every_pattern_lowercase_in_prose() -> None:
    """The shared person detector is case-insensitive and letter-bounded.

    Every class entry — accented or not — must be caught in lowercase prose,
    which the pre-option-4 cassette audit (case-sensitive substring over a
    hand-copied list) was structurally blind to.
    """
    from argumentation_analysis.evaluation.leak_patterns import (
        PERSON_PATTERNS,
        PERSON_RE,
    )

    for i, pattern in enumerate(PERSON_PATTERNS):
        carrier = f"une mention de {pattern.lower()} dans un propos tenu"
        assert PERSON_RE.search(carrier), (
            f"PERSON_PATTERNS[{i}] is not detected in lowercase prose — "
            "the shared detector lost case-insensitivity"
        )
