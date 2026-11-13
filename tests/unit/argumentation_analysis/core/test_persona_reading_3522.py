"""#3522 — the personas' read: whole when it fits, windowed, never starved.

Cycle 6 measured the defect on the recorded panel states: the personas read
LESS as the first reading named MORE. Three mechanisms, all in
``reading_window.persona_reading``:

1. a merged passage was cut at its head (``text[start:end][:allowance]``), so
   moves merging into one span produced one passage of 1 200 characters;
2. the anchors header took half the call, and with #3516's 23-36 entries the
   passages were left with ~2 950 characters where c5 read ~3 600;
3. a document that fits one call was still read as passages, never whole.

These witnesses are synthetic and free: no LLM, no network, no corpus.
"""

from __future__ import annotations

import re

import pytest

from argumentation_analysis.core.reading_window import (
    PERSONA_PASSAGE_SHARE,
    STATUS_ANCHORED_ON_MOVES,
    STATUS_HEAD_FALLBACK_NO_MOVES,
    STATUS_WHOLE_DOCUMENT,
    WHOLE_TEXT_CALL_CAPACITY,
    persona_reading,
)

_PROSE = "une phrase de contexte, avec des virgules; et une autre clause. "


def _text(chars: int) -> str:
    return (_PROSE * (chars // len(_PROSE) + 1))[:chars]


def _spread_moves(text, count, reading="lecture détaillée du mouvement"):
    step = max(1, (len(text) - 400) // max(1, count - 1)) if count > 1 else 0
    return [
        {
            "kind": "claim",
            "reading": reading[:100],
            "quote": "",
            "offset": min(len(text) - 1, 100 + i * step),
        }
        for i in range(count)
    ]


class TestWholeReadWhenItFits:
    @pytest.mark.parametrize("length,count", [(5_049, 33), (2_201, 14)])
    def test_a_document_that_fits_one_call_is_read_whole(self, length, count):
        """The panel's two short documents fit one call. c6 read them to
        1 225 characters once the moves merged into a single span."""
        text = _text(length)
        excerpt, selection, extra = persona_reading(text, _spread_moves(text, count))

        assert selection.status == STATUS_WHOLE_DOCUMENT
        assert extra["chars_read"] == len(text) == length
        assert text in excerpt, "the whole document, not a passage of it"
        assert len(excerpt) <= WHOLE_TEXT_CALL_CAPACITY

    def test_a_short_document_with_no_position_is_read_whole_too(self):
        """Fitting one call wins over the opening-window fallback: the
        fallback exists for documents that do NOT fit, and reading the whole
        text invents no position."""
        text = _text(5_000)
        moves = [{"kind": "thesis", "reading": "thèse", "quote": "", "offset": None}]

        excerpt, selection, _ = persona_reading(text, moves)

        assert selection.status == STATUS_WHOLE_DOCUMENT
        assert text in excerpt

    def test_above_the_capacity_without_positions_still_names_the_fallback(self):
        """The fallback keeps its meaning: it is what survives when the
        document exceeds the call. No whole read is claimed where none
        happened."""
        text = _text(20_000)

        excerpt, selection, extra = persona_reading(text, [])

        assert selection.status == STATUS_HEAD_FALLBACK_NO_MOVES
        assert excerpt == text[:3000]
        assert extra["moves_read"] == 0

    def test_the_whole_read_status_is_recorded_with_the_document_length(self):
        text = _text(2_201)
        _, selection, _ = persona_reading(text, _spread_moves(text, 14))

        assert selection.offset == 0
        assert selection.window == len(text)

    @pytest.mark.parametrize("capacity", [1_000, WHOLE_TEXT_CALL_CAPACITY])
    def test_the_whole_read_stops_exactly_where_one_call_ends(self, capacity):
        """The whole-document arm puts the text in the excerpt unsliced, so
        its own guard is the only thing holding the prompt under one call.
        The unbounded-prompt census (#2908) registers the site on that guard:
        this is the guard's witness, one character either side of it."""
        fits = _text(capacity - 2)
        excerpt, selection, _ = persona_reading(
            fits, _spread_moves(fits, 12), capacity=capacity
        )
        assert selection.status == STATUS_WHOLE_DOCUMENT
        assert fits in excerpt
        assert len(excerpt) <= capacity

        over = _text(capacity - 1)
        excerpt, selection, _ = persona_reading(
            over, _spread_moves(over, 12), capacity=capacity
        )
        assert selection.status != STATUS_WHOLE_DOCUMENT
        assert over not in excerpt


class TestNoHeadCut:
    def _tokenised(self, length: int, tokens):
        """Prose with unique tokens placed at the given offsets."""
        chars = list(_text(length))
        for token, position in tokens:
            chars[position : position + len(token)] = token
        return "".join(chars)

    def test_a_passage_carries_every_anchor_that_merged_into_it(self):
        """Ten moves 100 characters apart merge into ONE span whose first
        1 200 characters stop before the last moves. The head cut lost them;
        the windowed read carries each anchor's own quote."""
        tokens = [
            (f"JETON{index:02d}QUOTE", 1_000 + index * 100) for index in range(10)
        ]
        text = self._tokenised(20_000, tokens)
        moves = [
            {
                "kind": "claim",
                "reading": f"m{index}",
                "quote": token,
                "offset": position,
            }
            for index, (token, position) in enumerate(tokens)
        ]

        excerpt, selection, extra = persona_reading(text, moves, capacity=2_000)

        assert selection.status == STATUS_ANCHORED_ON_MOVES
        for token, _ in tokens:
            assert token in excerpt, f"the head cut dropped {token}"
        assert extra["moves_read"] == len(tokens)
        assert len(excerpt) <= 2_000

    def test_a_short_merged_span_is_still_read_whole(self):
        """No windowing when the span already fits its allowance: the
        passage keeps its contiguous text."""
        text = _text(20_000)
        moves = [
            {"kind": "claim", "reading": "m", "quote": "", "offset": 1_000},
            {"kind": "claim", "reading": "m", "quote": "", "offset": 1_100},
        ]

        excerpt, selection, _ = persona_reading(text, moves, capacity=4_000)

        assert selection.status == STATUS_ANCHORED_ON_MOVES
        # The two padded spans merge into [700, 1_400): 1_000 and 1_100 each
        # take PERSONA_PASSAGE_PAD (300) on both sides.
        assert text[700:1_400] in excerpt, "the merged span is contiguous"
        assert " … " not in excerpt, "a span that fits is never windowed"

    def test_the_windows_do_not_depend_on_the_order_the_moves_arrive_in(self):
        """``defining_moves`` hands the moves in document order, and the
        windowing merged neighbouring windows assuming it. Replayed on a
        recorded panel state with the moves reversed, one document's read
        fell from 3 693 to 2 492 characters and its quotes found from 16 to
        9: a window that starts before the previous one swallowed it. The
        read is a function of the moves, not of the order they were listed
        in."""
        tokens = [
            (f"JETON{index:02d}QUOTE", 1_000 + index * 100) for index in range(10)
        ]
        text = self._tokenised(20_000, tokens)
        moves = [
            {
                "kind": "claim",
                "reading": f"m{index}",
                "quote": token,
                "offset": position,
            }
            for index, (token, position) in enumerate(tokens)
        ]

        excerpt, _, extra = persona_reading(text, list(reversed(moves)), capacity=2_000)

        for token, _ in tokens:
            assert token in excerpt, f"listing order dropped {token}"
        assert extra["moves_read"] == len(tokens)


class TestHeaderDoesNotStarvePassages:
    def test_the_long_documents_keep_at_least_the_c5_share(self):
        """30 moves with the c6-style long readings: the header truncated at
        half the call used to leave ~3 000 characters of text. The bar is
        the c5 share, measured, not asserted."""
        text = _text(60_000)
        moves = _spread_moves(text, 30, reading="lecture détaillée du mouvement " * 4)

        excerpt, selection, extra = persona_reading(text, moves)

        assert selection.status == STATUS_ANCHORED_ON_MOVES
        assert extra["chars_read"] >= PERSONA_PASSAGE_SHARE
        assert len(excerpt) <= WHOLE_TEXT_CALL_CAPACITY

    def test_the_header_is_fitted_by_whole_lines(self):
        """A header cut mid-line prints half a reading as if it were a
        move's label. The fitting keeps whole lines; the count says how many
        moves travelled."""
        text = _text(60_000)
        moves = _spread_moves(text, 30, reading="lecture détaillée du mouvement " * 4)

        excerpt, _, extra = persona_reading(text, moves)

        header = excerpt.split("\n\n", 1)[0]
        for line in header.splitlines():
            assert line.startswith("- ["), "every header line is an anchor line"
            assert line.endswith("…") is False, "no half-line is presented as whole"
        assert extra["moves_read"] > 0

    def _long_document_with_late_roles(self):
        text = _text(60_000)
        moves = _spread_moves(text, 30, reading="lecture détaillée du mouvement " * 4)
        moves[20].update(kind="thesis", slot="thesis")
        moves[24].update(slot="mechanism")
        moves[27].update(slot="pillar")
        moves[29].update(slot="pillar")
        return text, moves

    def test_the_roles_travel_before_the_local_moves(self):
        """Fitted under what the passages leave, the header cannot name every
        move of a long document. Fitted in document order it kept the first
        lines: replayed on the recorded panel states, the five long documents
        had 9 of their 43 role-bearing moves labelled, where the half-call
        header labelled 21 — the thesis and the mechanism sit late in a text
        and fell off first. The roles are what make the passages readable as
        a whole (#3442): they are fitted first (33 of 43 on the same states),
        the local moves take what is left."""
        text, moves = self._long_document_with_late_roles()

        excerpt, selection, _ = persona_reading(text, moves)

        assert selection.status == STATUS_ANCHORED_ON_MOVES
        header = excerpt.split("\n\n", 1)[0]
        assert "- [thèse centrale] position" in header
        assert "- [mécanisme] position" in header
        assert header.count("- [pilier de la thèse (claim)] position") == 2
        assert len(header.splitlines()) > 4, "local moves take the room left"

    def test_the_header_keeps_document_order_whatever_was_fitted_first(self):
        """Priority decides WHICH lines travel, never where they sit: the
        header stays a map of the text, positions ascending."""
        text, moves = self._long_document_with_late_roles()

        excerpt, _, _ = persona_reading(text, moves)

        header = excerpt.split("\n\n", 1)[0]
        positions = [
            int(match.group(1))
            for match in (
                re.search(r"position (\d+)", line) for line in header.splitlines()
            )
            if match
        ]
        assert len(positions) == len(header.splitlines())
        assert positions == sorted(positions)

    def test_an_unplaced_role_is_named_too(self):
        """A role whose quote the locator could not place sorts last in
        ``defining_moves``. It carries no passage, so the header is the only
        place the persona can learn the document has that thesis."""
        text, moves = self._long_document_with_late_roles()
        moves.append(
            {
                "kind": "thesis",
                "slot": "thesis",
                "reading": "thèse non localisée",
                "quote": "",
                "offset": None,
            }
        )

        excerpt, _, _ = persona_reading(text, moves)

        header = excerpt.split("\n\n", 1)[0]
        assert "- [thèse centrale] position non localisée : thèse non" in header
