"""#3623 — a turn's speaker tag belongs to the NEXT sentence, not the previous.

Measured defect (recorded doc_C states, every cycle c11–c20): a piece of 20
characters or fewer that has the FORM of a speaker tag (theatre/transcript
convention, ``NOM.`` or ``NOM:``) was joined BACKWARD into the sentence
before it by #2982's no-drop join. A unit then ends with the name of the
party who answers it — the reversed attribution #3572 traced through 14
state cells at c17.

The fix is by FORM, as a class: no word list from the corpus (dataset privacy
rule 7), no new length rule — the ``<= 20`` branch is the existing
``_MIN_SENTENCE_CHARS`` join threshold, and the tag body's ``{1,40}`` is the
existing #3584 gate bound.

One shared definition (``speaker_tag_form`` in ``core.shared_state``) serves
two readers: this splitter (a bare tag opens the next turn) and #3584's form
gate (a unit that is nothing but a tag holds no proposition).

Synthetic names only. Deterministic: no JVM, no LLM, no corpus.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import non_propositional_form
from argumentation_analysis.plugins.text_to_kb_plugin import (
    _heuristic_extract_arguments,
    _split_sentences,
    _split_sentences_with_offsets,
)

# The issue's synthetic witness: two turns, each opened by its speaker tag.
_TWO_TURNS = (
    "ALPHA. This first line is long enough to stand alone. "
    "BETA. This second line answers it at some length."
)

# A text with no speaker tag: the split must be byte for byte what it was
# before this change (pinned from main).
_NO_TAG = (
    "Dr. Smith opened the session. Yes. "
    "The committee then voted on the motion at length."
)
_NO_TAG_MAIN_OUTPUT = [
    "Dr. Smith opened the session. Yes.",
    "The committee then voted on the motion at length.",
]


def _normalized(text: str) -> str:
    return " ".join(text.split())


class TestTheTagJoinsForward:
    def test_the_tag_no_longer_closes_the_previous_turn(self) -> None:
        """The witness. On main the middle sentence is « This first line …
        alone. BETA. » — the tag of the next speaker closes the first
        speaker's line. After the fix the tag opens the second turn."""
        sentences = _split_sentences(_TWO_TURNS)
        assert sentences == [
            "ALPHA. This first line is long enough to stand alone.",
            "BETA. This second line answers it at some length.",
        ]

    def test_the_moved_tag_sentence_starts_at_the_tag(self) -> None:
        """#2973 — a sentence's offset is the offset of its first character,
        so a moved tag's sentence starts AT the tag."""
        text = "  " + _TWO_TURNS
        sentences = _split_sentences_with_offsets(text)
        assert len(sentences) == 2
        second, second_at = sentences[1]
        assert second_at == text.index("BETA.")
        for sentence, offset in sentences:
            assert text[offset : offset + len(sentence)] == sentence

    def test_every_character_survives_whitespace_normalised(self) -> None:
        """#2982 — the no-drop guarantee holds with tags in the text."""
        assert _normalized(" ".join(_split_sentences(_TWO_TURNS))) == _normalized(
            _TWO_TURNS
        )

    def test_a_text_without_a_tag_splits_as_before(self) -> None:
        """Ask 3 — no tag, byte for byte the same split as main."""
        assert _split_sentences(_NO_TAG) == _NO_TAG_MAIN_OUTPUT

    def test_a_colon_tag_never_joins_backward(self) -> None:
        """The colon terminator, opening the piece (« NOM: reply »), is the
        same class: it opens a turn even when the piece is short."""
        text = "A previous statement is developed at length here. BETA: Go."
        sentences = _split_sentences(text)
        assert sentences == [
            "A previous statement is developed at length here.",
            "BETA: Go.",
        ]


class TestTheSharedFormPredicate:
    def test_the_two_terminators_are_one_definition(self) -> None:
        # Imported here (not at module level): the symbol is NEW in #3623, and
        # a module-level ImportError would turn the whole file into a
        # collection ERROR that masks the other witnesses' néo-rouge.
        from argumentation_analysis.core.shared_state import speaker_tag_form

        assert speaker_tag_form("ALPHA.") == "tag_only"
        assert speaker_tag_form("ALPHA:") == "tag_only"
        assert speaker_tag_form("ALPHA: a reply follows") == "tag_prefix"
        assert speaker_tag_form("Alpha.") == ""  # mixed case is not the form
        assert speaker_tag_form("Yes.") == ""  # lowercase is not the form
        assert speaker_tag_form("") == ""


class TestTheGateAdmitsThePeriodForm:
    def test_a_period_tag_alone_holds_no_proposition(self) -> None:
        assert non_propositional_form("ALPHA.") == "speaker_tag_only"

    def test_the_colon_cases_are_unchanged(self) -> None:
        assert non_propositional_form("ALPHA:") == "speaker_tag_only"
        assert non_propositional_form("ALPHA: a reply follows") == ""
        assert non_propositional_form("ALPHA: [a stage direction]") == (
            "speaker_tag_only"
        )


class TestNoUnitEndsOnATag:
    def test_a_tag_opens_the_next_unit_instead_of_closing_this_one(self) -> None:
        """A marker sentence right after a tag used to flush a unit that
        ENDED on the tag (the measured class). Now the tag rides the next
        unit's opening."""
        text = (
            "ALPHA. The first statement is developed at length here. "
            "BETA. Therefore the second statement is developed at length too."
        )
        units = [a.text for a in _heuristic_extract_arguments(text)]
        assert units == [
            "ALPHA. The first statement is developed at length here.",
            "BETA. Therefore the second statement is developed at length too.",
        ]

    def test_a_tag_with_no_turn_after_it_forms_its_own_unit(self) -> None:
        """A chunk may end on a tag (the reply starts the next chunk). The
        tag survives as its own unit — #2982 forbids dropping it — and
        #3584's gate refuses that unit as non-propositional, so it never
        closes the previous unit and never enters the population."""
        text = "ALPHA. The first statement is developed at length here. BETA."
        units = [a.text for a in _heuristic_extract_arguments(text)]
        assert units == [
            "ALPHA. The first statement is developed at length here.",
            "BETA.",
        ]
        assert non_propositional_form(units[-1]) == "speaker_tag_only"
        assert non_propositional_form(units[0]) == ""
