"""#2982 — the heuristic splitter dropped words from the units it extracts.

`text_to_kb_plugin`'s producer split after every period (abbreviations
included) and then discarded every piece of 20 characters or fewer. A claim
attributed to someone lost its attribution: ``He knows that Mr. Smith was
abroad`` reads ``Smith was abroad`` in the unit, and the speaker's ``He knows
that`` is gone. Measured on doc_A (06/10 saved state): 24 of 33 units were
missing a fragment of 3 to 18 characters against the source, 18 of them a
fragment ending on an abbreviation.

Since #2974 the restitution writers receive cited units **whole**, as source
text — a unit that is not the source text is a quotation missing words.

The fix: no split after a common abbreviation, and never a drop — a short
piece JOINS its neighbour. The second rule is the guarantee; the abbreviation
list is a convenience (a missed abbreviation merges two sentences, it never
loses text).

Privacy: invented filler, no corpus sentence. Deterministic: no JVM, no LLM.
"""

from __future__ import annotations

from argumentation_analysis.plugins.text_to_kb_plugin import (
    _heuristic_extract_arguments,
)

# The issue's synthetic example: the period after ``Mr.`` is not a sentence end.
_ABBREVIATED = "He knows that Mr. Smith was abroad at the time."


def _normalized(text: str) -> str:
    return " ".join(text.split())


class TestNoWordIsLost:
    def test_the_attribution_survives_the_abbreviation(self) -> None:
        """On main this unit read « Smith was abroad at the time. » — the
        speaker's « He knows that » was dropped (17 characters, under the
        filter). The unit must carry it."""
        args = _heuristic_extract_arguments(_ABBREVIATED)
        assert len(args) == 1
        assert "He knows that" in args[0].text
        assert "Smith was abroad" in args[0].text

    def test_a_short_standalone_piece_joins_a_neighbour(self) -> None:
        """Positive control: a genuinely short piece between two long ones is
        KEPT — attached to a neighbour, never dropped."""
        text = (
            "The first claim is developed at length in this paragraph. "
            "Yes. "
            "The second claim is developed at length in this paragraph too."
        )
        args = _heuristic_extract_arguments(text)
        assert args, "the text must yield at least one unit"
        joined = _normalized(" ".join(a.text for a in args))
        assert "Yes." in joined

    def test_every_character_survives_whitespace_normalised(self) -> None:
        """The property worth holding: the concatenation of the sentences,
        whitespace-normalised, is the text — in order, nothing dropped."""
        from argumentation_analysis.plugins.text_to_kb_plugin import (
            _split_sentences,
        )

        text = (
            "Dr. Smith opened the session. He knows that Mr. Jones was away. "
            "Yes. The committee then voted on the motion at length."
        )
        rejoined = _normalized(" ".join(_split_sentences(text)))
        assert rejoined == _normalized(text)


class TestTheSplitRespectsAbbreviations:
    def test_an_abbreviation_does_not_end_a_sentence(self) -> None:
        from argumentation_analysis.plugins.text_to_kb_plugin import (
            _split_sentences,
        )

        sentences = _split_sentences("He knows that Mr. Smith was abroad at the time.")
        assert len(sentences) == 1
        assert "He knows that" in sentences[0]
        assert "Smith was abroad" in sentences[0]

    def test_a_real_period_still_ends_a_sentence(self) -> None:
        """The positive control on the other side: two real sentences stay
        two sentences."""
        from argumentation_analysis.plugins.text_to_kb_plugin import (
            _split_sentences,
        )

        sentences = _split_sentences(
            "The committee convened in the main hall this morning. "
            "It voted on the motion after a long debate."
        )
        assert len(sentences) == 2
