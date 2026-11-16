"""#3625 — a paragraph break is a turn-boundary candidate.

The character before a paragraph break can hide the next turn's speaker tag:
an interruption dash (``--``) or a closing bracket after a stage direction
(``).``) is not a sentence terminator, so ``_SENTENCE_SPLIT``'s
one-character lookbehind never fires there — the dash-ended line, the
paragraph break and the tag stay ONE piece, the tag never becomes a piece of
its own, and #3623's forward join never sees it. The unit's text still ends
with the answering party's name.

Synthetic names only (ALPHA, BETA, M. Dupont) — no corpus text.
"""

import re


def _split(text):
    from argumentation_analysis.plugins.text_to_kb_plugin import _split_sentences

    return _split_sentences(text)


def _split_offsets(text):
    from argumentation_analysis.plugins.text_to_kb_plugin import (
        _split_sentences_with_offsets,
    )

    return _split_sentences_with_offsets(text)


_WITNESS_DASH = (
    "ALPHA. I did not mean it, dear friend--\n\n\n\n"
    "BETA. This line answers the interruption at full length."
)
_WITNESS_BRACKET = (
    "(A stage direction closes it.)\n \n"
    "BETA. This line answers the stage direction at full length."
)
_NO_TAG_BREAK = (
    "ALPHA. One turn ends abruptly--\n\n"
    "Plain prose continues without any tag at sufficient length."
)
_ABBREVIATION_BREAK = "He stops--\n\nM. Dupont replies to him at full length here."
_COLON_BREAK = (
    "ALPHA. A turn ends here--\n\n"
    "BETA: The coloned reply follows the break at full length."
)


class TestParagraphTagCut:
    def test_witness_dash_two_turns(self):
        """The issue's witness: the dash-held tag opens the NEXT turn."""
        sentences = _split(_WITNESS_DASH)
        assert len(sentences) == 2
        assert "BETA" not in sentences[0]
        assert sentences[0].rstrip().endswith("--")
        assert sentences[1].startswith("BETA.")

    def test_witness_bracket_shape(self):
        """Same shape with a closing bracket and a spaced blank line."""
        sentences = _split(_WITNESS_BRACKET)
        assert len(sentences) == 2
        assert "BETA" not in sentences[0]
        assert sentences[1].startswith("BETA.")

    def test_moved_tag_sentence_starts_at_tag(self):
        """#2973 — the joined reply starts AT the tag, not at the dash."""
        sentences = _split_offsets(_WITNESS_DASH)
        reply = next(s for s in sentences if s[0].startswith("BETA."))
        assert reply[1] == _WITNESS_DASH.index("BETA.")

    def test_characters_survive(self):
        """#2982 — every non-whitespace character survives into some piece."""

        def _chars(text):
            return re.sub(r"\s+", "", text)

        for witness in (_WITNESS_DASH, _WITNESS_BRACKET, _COLON_BREAK):
            joined = "".join(_split(witness))
            assert _chars(joined) == _chars(witness)

    def test_no_tag_break_splits_byte_for_byte(self):
        """A break with NO tag after it cuts nothing, dash or not."""
        # On main as on the branch, the dash-ended paragraph without a tag
        # stays ONE piece: the sentence split never fires (no terminator),
        # and the paragraph rule adds no cut of its own — the internal
        # paragraph break survives inside the sentence, byte for byte.
        assert _split(_NO_TAG_BREAK) == [_NO_TAG_BREAK]

    def test_abbreviation_paragraph_is_not_a_turn(self):
        """``M.`` opens a name, not a turn: no cut, byte for byte as today."""
        assert _split(_ABBREVIATION_BREAK) == [_ABBREVIATION_BREAK]

    def test_colon_tag_after_break(self):
        """The colon form opens the next turn too."""
        sentences = _split(_COLON_BREAK)
        assert len(sentences) == 2
        assert sentences[1].startswith("BETA:")
