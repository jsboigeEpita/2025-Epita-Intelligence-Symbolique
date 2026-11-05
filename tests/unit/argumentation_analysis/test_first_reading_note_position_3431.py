"""#3431 — the note's position speaks to the reader, and the order says itself.

Panel cycle 2 measured 4 M2 items where the judge read a peroration call as
the speech's opening. The note handed the writer a raw character offset
(« [texte, position 54448] » of a 58 052-character document) that names
nothing without the document in hand, and never said its lines follow the
document's order — while the record beneath them stores the thesis and
mechanism slots first (#3420).

The asks, witnessed here on a synthetic document whose thesis sits at 94 %:

1. the position prints as the share of the text and its part, in the
   reader's vocabulary — no raw offset reaches a writer (the offset stays
   in the state, where the selection reads it);
2. the note prints the moves in document order AND SAYS SO;
3. a thesis at 90 %+ is placed in the end part and its line is not first.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.reading.first_reading import (
    first_reading_note,
)

_TEXT_LENGTH = 100_000


def _record(moves: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(
        defining_moves={
            "moves": moves,
            "dropped_quotes": 0,
            "status": "ok",
            "read_scope": {
                "offset": 0,
                "window": _TEXT_LENGTH,
                "status": "short_input",
                "text_length": _TEXT_LENGTH,
                "whole_document": True,
            },
            "basis": "first_reading",
        }
    )


# The slots-first storage order of the record (#3420): the thesis and the
# mechanism are stored BEFORE the local move, exactly as the measured state
# carried them — the note must not inherit that order.
_SLOTS_FIRST_MOVES = [
    {
        "kind": "thesis",
        "reading": "Il appelle a la revolte fiscale.",
        "quote": "la revolte fiscale est le seul recours",
        "offset": 94_000,
        "basis": "first_reading",
        "slot": "thesis",
    },
    {
        "kind": "device",
        "reading": "Le risque est delegue.",
        "quote": "le risque est delegue aux petits porteurs",
        "offset": 93_000,
        "basis": "first_reading",
        "slot": "mechanism",
    },
    {
        "kind": "claim",
        "reading": "Un chiffre d'expose.",
        "quote": "des chiffres d'expose",
        "offset": 3_000,
        "basis": "first_reading",
    },
]


class TestTheLateThesisReadsAsLate:
    """The measured defect: a thesis at 94 % printed so a writer read it as
    the opening call of the speech."""

    def test_the_position_is_the_share_and_its_part(self) -> None:
        note = first_reading_note(_record(_SLOTS_FIRST_MOVES))
        thesis_lines = [ln for ln in note.splitlines() if "revolte fiscale" in ln]
        assert len(thesis_lines) == 1
        thesis_line = thesis_lines[0]
        assert "vers la fin du texte (94 %)" in thesis_line

    def test_no_raw_offset_reaches_the_writer(self) -> None:
        note = first_reading_note(_record(_SLOTS_FIRST_MOVES))
        for raw in ("position 94000", "position 93000", "position 3000"):
            assert (
                raw not in note
            ), f"a raw character offset reached the writer: {raw!r}"

    def test_the_thesis_line_is_not_first(self) -> None:
        note = first_reading_note(_record(_SLOTS_FIRST_MOVES))
        move_lines = [ln for ln in note.splitlines() if ln.strip().startswith("- ")]
        assert len(move_lines) == 3
        # Document order: the 3 % local claim opens, the 94 % thesis closes.
        assert "chiffres d'expose" in move_lines[0]
        assert "revolte fiscale" in move_lines[-1]

    def test_the_order_is_stated(self) -> None:
        note = first_reading_note(_record(_SLOTS_FIRST_MOVES))
        assert "Ordre : celui du document" in note

    def test_the_state_keeps_the_offsets(self) -> None:
        """Ask 1's other half: the offset is removed from the WRITER's text,
        not from the state — the selection and the census still read it."""
        state = _record(_SLOTS_FIRST_MOVES)
        first_reading_note(state)
        moves = state.defining_moves["moves"]
        assert [m["offset"] for m in moves] == [94_000, 93_000, 3_000]


class TestTheBands:
    """The reader's vocabulary, on the share alone."""

    def test_a_peroration_is_named_as_one(self) -> None:
        moves = [
            {
                "kind": "claim",
                "reading": "L'appel final.",
                "quote": "l'appel final du discours",
                "offset": 98_000,
                "basis": "first_reading",
            }
        ]
        note = first_reading_note(_record(moves))
        assert "dans la péroraison (98 %)" in note

    def test_an_unpositioned_move_prints_no_position(self) -> None:
        moves = [
            {
                "kind": "claim",
                "reading": "Un fait.",
                "quote": "un fait du discours",
                "basis": "first_reading",
            }
        ]
        note = first_reading_note(_record(moves))
        assert "%" not in note
        assert "position" not in note

    def test_a_record_without_a_length_prints_no_share(self) -> None:
        state = _record(_SLOTS_FIRST_MOVES)
        state.defining_moves["read_scope"] = {"whole_document": True}
        note = first_reading_note(state)
        assert "%" not in note, "no text_length, no share: a bare quote, never a guess"
