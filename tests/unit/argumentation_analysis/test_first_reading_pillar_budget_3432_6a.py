"""#3432 demande 6(a) — a long document's five pillars all reach the lenses.

The first reading reads the whole document, but a flat ``MAX_PILLARS = 3``
cuts the answer to three supports whatever the document's length. The panel's
severe M1-on-thesis mostly falls outside those spans. This fixture supplies
FIVE distinct, verbatim supports over more than 40 000 characters: the model
has found them, so dropping the last two is the producer's budget, not a
failure of the fake model.

The repair follows ``per_argument_unit_budget``: a length-dependent budget,
with today's three as its floor and a declared ceiling. ``MAX_MOVES`` and the
citation rule stay untouched. A short document's prompt and state remain
byte-for-byte identical to the flat-three implementation.

Synthetic text and opaque ids only. Born red on main: only three of the five
pillars reach ``defining_move_spans`` and the note.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.reading import (
    build_first_reading,
    defining_move_spans,
    first_reading_note,
)

_FILLER = (
    "Le paragraphe de contexte expose une observation peripherique, sans "
    "apporter de premisse a la demonstration centrale du document. "
)
_THESIS = (
    "La these centrale du document est que la reforme preserve les "
    "avantages de ses promoteurs plutot que l'acces des usagers."
)
_MECHANISM = (
    "Le mecanisme de la these est la delegation du risque collectif aux "
    "usagers qui ne participent pas a sa definition."
)
_PILLARS = (
    "Le registre de la seance montre que les usagers n'ont pas ete consultes.",
    "Une note anterieure etablit que le meme dispositif a ete refuse auparavant.",
    "Le tableau des participations indique que les promoteurs decident seuls.",
    "Le rapport financier affecte la totalite du risque aux petits porteurs.",
    "Une annexe compare deux decisions contraires prises sur des faits identiques.",
)
_LOCAL = "une observation peripherique"


def _long_document() -> str:
    """Five unique supports, spread from the opening to the end of 44k+ chars."""
    parts = [_FILLER * 30, _THESIS]
    for pillar in _PILLARS:
        parts.extend((_FILLER * 60, pillar))
    parts.extend((_FILLER * 20, _MECHANISM, _FILLER * 5))
    document = "\n\n".join(parts)
    assert len(document) > 40_000
    return document


def _answer() -> str:
    return json.dumps(
        {
            "thesis": {
                "reading": "la reforme preserve les promoteurs",
                "quote": _THESIS,
            },
            "mechanism": {"reading": "le risque est delegue", "quote": _MECHANISM},
            "pillars": [
                {
                    "kind": "claim",
                    "reading": f"support documentaire {i}",
                    "quote": quote,
                }
                for i, quote in enumerate(_PILLARS)
            ],
            "moves": [
                {"kind": "claim", "reading": "une remarque locale", "quote": _LOCAL}
            ],
        },
        ensure_ascii=False,
    )


class _FakeModel:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


async def test_five_long_document_pillars_reach_spans_and_note() -> None:
    """The dispatch's witness, red on the flat-three producer."""
    document = _long_document()
    result = await build_first_reading(
        SimpleNamespace(raw_text=document), _FakeModel(_answer())
    )
    assert result.status == "ok"
    pillars = [move for move in result.moves if move.slot == "pillar"]
    assert [move.quote for move in pillars] == list(_PILLARS)

    spans = defining_move_spans(SimpleNamespace(defining_moves=result.to_state()))
    note = first_reading_note(SimpleNamespace(defining_moves=result.to_state()))
    for quote in _PILLARS:
        start = document.index(quote)
        assert (start, start + len(quote)) in spans
        assert quote in note


async def test_the_model_is_told_the_length_dependent_budget() -> None:
    """Raising a parser slice without asking for the supports would not repair recall."""
    from argumentation_analysis.agents.core import reading as module

    model = _FakeModel(_answer())
    await module.build_first_reading(SimpleNamespace(raw_text=_long_document()), model)
    budget = module.pillar_budget(len(_long_document()))
    assert budget >= 5
    assert f"At most {budget} pillars" in model.prompts[0]


def test_the_budget_has_the_per_argument_shape_and_named_bounds() -> None:
    from argumentation_analysis.agents.core.reading import pillar_budget
    from argumentation_analysis.core import reading_window as window

    assert window.PILLAR_FLOOR == 3
    assert pillar_budget(1_000) == window.PILLAR_FLOOR
    assert pillar_budget(len(_long_document())) >= 5
    assert pillar_budget(10_000_000) == window.PILLAR_CEILING
    assert window.PILLAR_CEILING <= 8


async def test_a_short_document_keeps_the_flat_three_state_and_prompt() -> None:
    """The floor, not a new field or a changed prompt, preserves the control."""
    from argumentation_analysis.agents.core import reading as module
    from argumentation_analysis.agents.core.reading.first_reading import (
        FIRST_READING_PROMPT,
    )

    short_document = f"{_THESIS}\n\n{_PILLARS[0]}\n\n{_MECHANISM}\n\n{_LOCAL}"
    answer = json.dumps(
        {
            "thesis": {"reading": "la these", "quote": _THESIS},
            "mechanism": {"reading": "le mecanisme", "quote": _MECHANISM},
            "pillars": [
                {"kind": "claim", "reading": "le seul support", "quote": _PILLARS[0]}
            ],
            "moves": [{"kind": "claim", "reading": "une remarque", "quote": _LOCAL}],
        },
        ensure_ascii=False,
    )
    model = _FakeModel(answer)
    result = await module.build_first_reading(
        SimpleNamespace(raw_text=short_document), model
    )
    assert module.pillar_budget(len(short_document)) == module.MAX_PILLARS == 3
    assert "At most 3 pillars" in model.prompts[0]
    assert model.prompts == [
        FIRST_READING_PROMPT.format(
            max_moves=module.MAX_MOVES,
            max_pillars=module.MAX_PILLARS,
            excerpt=short_document,
        )
    ]
    assert result.to_state() == {
        "moves": [
            {
                "kind": "thesis",
                "reading": "la these",
                "quote": _THESIS,
                "offset": short_document.index(_THESIS),
                "basis": module.FIRST_READING_BASIS,
                "slot": "thesis",
            },
            {
                "kind": "device",
                "reading": "le mecanisme",
                "quote": _MECHANISM,
                "offset": short_document.index(_MECHANISM),
                "basis": module.FIRST_READING_BASIS,
                "slot": "mechanism",
            },
            {
                "kind": "claim",
                "reading": "le seul support",
                "quote": _PILLARS[0],
                "offset": short_document.index(_PILLARS[0]),
                "basis": module.FIRST_READING_BASIS,
                "slot": "pillar",
            },
            {
                "kind": "claim",
                "reading": "une remarque",
                "quote": _LOCAL,
                "offset": short_document.index(_LOCAL),
                "basis": module.FIRST_READING_BASIS,
            },
        ],
        "dropped_quotes": 0,
        "status": "ok",
        "read_scope": {
            "offset": 0,
            "window": len(short_document),
            "status": "selected",
            "text_length": len(short_document),
            "whole_document": True,
        },
        "basis": module.FIRST_READING_BASIS,
    }


async def test_malformed_sibling_keeps_the_same_length_bound() -> None:
    """The JSON salvage must not quietly restore the flat-three limit."""
    malformed = _answer().replace(
        '"reading": "une remarque locale"',
        '"reading": "une remarque locale",',
    )
    result = await build_first_reading(
        SimpleNamespace(raw_text=_long_document()), _FakeModel(malformed)
    )
    assert result.status == "ok"
    assert result.malformed_moves >= 1
    assert [move.quote for move in result.moves if move.slot == "pillar"] == list(
        _PILLARS
    )


def test_the_anti_pendulum_bounds_stay_put() -> None:
    from argumentation_analysis.agents.core.reading import MAX_MOVES
    from argumentation_analysis.agents.core.reading.first_reading import (
        quote_occurs_in,
    )

    assert MAX_MOVES == 12
    assert quote_occurs_in(_PILLARS[0], _PILLARS[0])
    assert not quote_occurs_in(_PILLARS[0], _PILLARS[0] + " affirmation inventee")
