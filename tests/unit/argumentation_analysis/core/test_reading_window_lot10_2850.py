"""#2850 lot 10 — the whole text, in k calls (dispatch R1144).

The measured gap this lot closes: on the v1 panel the pipeline read a
fraction of each document (fact extraction 5-18 %, personas 1-6 %,
per-argument 10 of 97-412 units on the long half). The dispatch's four
rules, pinned here on the pure mechanism:

1. the whole text is read in ``k = ceil(L / capacity)`` contiguous calls —
   the chunks TILE the document, and a document under one capacity is a
   single call, byte-identical to today's;
2. the per-argument budget grows with the text, ``k(L)``, with a DECLARED
   ceiling and today's flat 10 as the floor;
3. the personas read the document through the first reading's positions,
   each passage within one call's capacity — the opening window survives
   only when that reading gave no usable position, and the record says so;
4. the capacity is one named constant derived from lot 9's own arithmetic,
   never a second literal.

Synthetic opaque text only; no LLM, no network.
"""

from __future__ import annotations

import math

import pytest

from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    PER_ARGUMENT_CEILING,
    PER_ARGUMENT_FLOOR,
    STATUS_ANCHORED_ON_MOVES,
    STATUS_HEAD_FALLBACK_NO_MOVES,
    WHOLE_TEXT_CALL_CAPACITY,
    chunked_reading_offsets,
    one_call_extraction_capacity,
    per_argument_unit_budget,
    persona_reading,
)

_PROSE = "une phrase de contexte, avec des virgules; et une autre clause. "


def _text(chars: int) -> str:
    return (_PROSE * (chars // len(_PROSE) + 1))[:chars]


class TestCapacity:
    def test_capacity_is_lot_nines_arithmetic_not_a_second_literal(self):
        """The whole lot reads at ONE capacity: lot 9's
        ``one_call_extraction_capacity`` at the production knob. A literal
        here would drift the moment the knob moves."""
        assert WHOLE_TEXT_CALL_CAPACITY == one_call_extraction_capacity(8192)
        assert WHOLE_TEXT_CALL_CAPACITY > 0

    def test_a_non_positive_capacity_fails_loud(self):
        with pytest.raises(ValueError):
            chunked_reading_offsets(1000, 0)
        with pytest.raises(ValueError):
            persona_reading("texte", [], capacity=0)


class TestChunkedOffsets:
    @pytest.mark.parametrize("length", [0, 320, 5_049, 13_927, 179_139])
    def test_the_chunks_tile_the_document(self, length):
        """k = ceil(L / capacity), contiguous, and their union IS [0, L):
        no gap can hide a passage, no overlap re-reads one."""
        offsets = chunked_reading_offsets(length, WHOLE_TEXT_CALL_CAPACITY)
        assert len(offsets) == max(1, math.ceil(length / WHOLE_TEXT_CALL_CAPACITY))
        assert offsets[0] == 0
        spans = [(o, min(o + WHOLE_TEXT_CALL_CAPACITY, length)) for o in offsets]
        cursor = 0
        for start, end in spans:
            if length == 0:
                continue
            assert start == cursor, "the chunks must be contiguous"
            cursor = end
        if length:
            assert cursor == length, "the last chunk must reach the end"

    def test_below_one_capacity_is_the_single_call_of_today(self):
        length = WHOLE_TEXT_CALL_CAPACITY - 1
        assert chunked_reading_offsets(length, WHOLE_TEXT_CALL_CAPACITY) == [0]

    def test_the_selector_offset_stays_skipped(self):
        """#1737 — the head the selector dropped (a table of contents) is not
        re-read by tiling from 0."""
        offsets = chunked_reading_offsets(20_000, 6_016, start=1_200)
        assert offsets[0] == 1_200
        assert offsets[-1] + 6_016 >= 20_000

    def test_a_tail_only_document_is_still_reached(self):
        """The tail third is the measured loss: on 20k chars, k = 4 and the
        last offset is past 18k."""
        offsets = chunked_reading_offsets(20_000, 6_016)
        assert len(offsets) == 4
        assert offsets[-1] > 18_000


class TestPerArgumentBudget:
    def test_the_floor_is_todays_flat_ten(self):
        assert per_argument_unit_budget(320) == PER_ARGUMENT_FLOOR
        assert per_argument_unit_budget(WHOLE_TEXT_CALL_CAPACITY) == 10

    @pytest.mark.parametrize(
        "length,expected",
        [
            (13_927, 10),  # k=3 -> 6, floored at 10
            (47_644, 16),  # k=8 -> 16
            (56_430, 20),  # k=10 -> 20
            (179_139, 45),  # k=30 -> 60, ceilinged at 45 (#3523)
        ],
    )
    def test_k_grows_with_the_text_under_a_declared_ceiling(self, length, expected):
        assert per_argument_unit_budget(length) == expected

    def test_the_ceiling_is_declared_and_never_exceeded(self):
        # #3523 — 30 -> 45 on the c6 same-side replay (12/33 at 1.58x; the
        # added units at chance past 45). The pin stays: the value moves on a
        # measured panel, never as a repair side effect.
        assert PER_ARGUMENT_CEILING == 45
        assert per_argument_unit_budget(10_000_000) == PER_ARGUMENT_CEILING


class TestPersonaReading:
    def _moves(self):
        return [
            {
                "kind": "thesis",
                "reading": "la thèse centrale",
                "quote": "la thèse centrale",
                "offset": 40,
            },
            {
                "kind": "device",
                "reading": "le mécanisme",
                "quote": "un mécanisme",
                "offset": 60_000,
            },
        ]

    def test_the_passages_are_anchored_on_the_moves_not_the_opening(self):
        """The measured case: the mechanism sits at 60k in an 80k document —
        the opening window never reached it. The anchored excerpt carries the
        thesis block, the move positions, and text from BOTH positions."""
        text = _text(80_000)
        moves = [
            {"kind": "thesis", "reading": "thèse", "quote": text[40:60], "offset": 40},
            {
                "kind": "device",
                "reading": "mécanisme",
                "quote": text[60_000:60_030],
                "offset": 60_000,
            },
        ]
        excerpt, selection, extra = persona_reading(text, moves)

        assert selection.status == STATUS_ANCHORED_ON_MOVES
        assert "thèse" in excerpt and "mécanisme" in excerpt
        assert "position 40" in excerpt and "position 60000" in excerpt
        assert text[60_000:60_030] in excerpt, "the tail passage must be read"
        assert len(excerpt) <= WHOLE_TEXT_CALL_CAPACITY
        assert extra["chars_read"] > 0 and extra["windows"] >= 2
        assert extra["moves_total"] == 2

    def test_a_narrow_budget_reports_fewer_moves_rather_than_lying(self):
        """When many positions do not fit one call, the excerpt stays under
        the capacity and the record says how many passages it carried."""
        text = _text(30_000)
        moves = [
            {"kind": "claim", "reading": f"m{i}", "quote": "", "offset": i * 1_500}
            for i in range(20)
        ]
        excerpt, selection, extra = persona_reading(text, moves, capacity=2_000)
        assert len(excerpt) <= 2_000
        assert selection.status == STATUS_ANCHORED_ON_MOVES
        assert extra["windows"] < extra["moves_total"]
        assert extra["windows"] >= 1

    def test_no_usable_position_falls_back_to_the_opening_window_and_says_so(self):
        """The dispatch: the opening window survives ONLY when the first
        reading failed, and the record says it is a fallback."""
        text = _text(20_000)
        excerpt, selection, extra = persona_reading(text, [])
        assert excerpt == text[:LLM_EXTRACTION_WINDOW]
        assert selection.status == STATUS_HEAD_FALLBACK_NO_MOVES
        assert selection.offset == 0
        assert selection.window == LLM_EXTRACTION_WINDOW
        assert extra["moves_total"] == 0 and extra["moves_read"] == 0

    def test_unpositioned_moves_are_reported_as_such_not_invented(self):
        # #3522 — a document ABOVE one call keeps the intent this witness
        # has always pinned: no position to anchor on means the opening
        # window, never a guessed one. (Below one call the document is now
        # read whole — ``test_persona_reading_3522`` pins that branch.)
        text = _text(20_000)
        moves = [{"kind": "thesis", "reading": "thèse", "quote": "", "offset": None}]
        excerpt, selection, _ = persona_reading(text, moves)
        # No position to anchor on → the fallback window, never a guessed one.
        assert selection.status == STATUS_HEAD_FALLBACK_NO_MOVES
        assert excerpt == text[:LLM_EXTRACTION_WINDOW]

    def test_a_pillar_prints_its_role_not_just_its_kind(self):
        """#3442 — the first reading now records pillars (``slot="pillar"``),
        and they flow to the personas through ``defining_moves``. The header
        must say the passage carries the thesis: a bare ``claim`` label would
        read as one more local move, the exact confusion #3442's note guard
        names. The kind stays, in parentheses."""
        text = _text(10_000)
        moves = [
            {
                "kind": "thesis",
                "slot": "thesis",
                "reading": "la thèse",
                "quote": text[100:120],
                "offset": 100,
            },
            {
                "kind": "device",
                "slot": "mechanism",
                "reading": "le mécanisme",
                "quote": text[200:220],
                "offset": 200,
            },
            {
                "kind": "claim",
                "slot": "pillar",
                "reading": "le passage qui porte la thèse",
                "quote": text[8_000:8_030],
                "offset": 8_000,
            },
            {
                "kind": "concession",
                "reading": "un geste local",
                "quote": text[300:320],
                "offset": 300,
            },
        ]
        excerpt, selection, _ = persona_reading(text, moves)
        assert selection.status == STATUS_ANCHORED_ON_MOVES
        assert "[thèse centrale] position 100" in excerpt
        assert "[mécanisme] position 200" in excerpt
        assert "[pilier de la thèse (claim)] position 8000" in excerpt
        # A local move keeps its bare kind — the role label is for slots only.
        assert "[concession] position 300" in excerpt
        # The pillar's passage is read like any anchored move's.
        assert text[8_000:8_030] in excerpt
