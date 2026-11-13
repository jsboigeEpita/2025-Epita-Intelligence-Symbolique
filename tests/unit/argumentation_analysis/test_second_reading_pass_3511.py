"""#3511(b) — the second reading pass over the bare stretches.

The coordinator decision of 13/11 (issue #3511): after the whole-document
reading, a stretch no anchored move covers, longer than a gap derived from
the document itself, gets its own reading call; the moves join the inventory
with a second-pass marker; a document with no bare stretch issues no second
call and keeps a byte-identical inventory.

The free witnesses the decision asks for, on synthetic texts and a scripted
LLM (no network, no paid call):

* an argument PLANTED in a stretch no first-pass move anchors is absent from
  the inventory before and present after, with its second-pass marker;
* the MUTATION: with the pass disabled (the stretch finder neutered), that
  witness is red again;
* the CONTROL: a short text — one capacity chunk — issues no second call.

Then the rule's own units: the gap is the document's, the bound is the
chunk count, the bite is recorded and stated in the note, the citation rule
and the locator are the same as the first pass's, and the examined budget
stays under the per-argument ceiling (#3523).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from argumentation_analysis.agents.core.reading import first_reading as fr
from argumentation_analysis.agents.core.reading.first_reading import (
    DefiningMove,
    FirstReading,
    _second_reading_pass,
    bare_stretch_spans,
    build_first_reading,
    examined_unit_budget,
    first_reading_note,
    second_pass_call_bound,
)
from argumentation_analysis.core.reading_window import (
    WHOLE_TEXT_CALL_CAPACITY,
)

_FILLER = (
    "Remplissage neutre du corpus synthetique pour la geometrie des ancres "
    "de la premiere lecture. "
)


def _marker(i: int) -> str:
    """A unique, verbatim, quotable sentence — one per planted argument."""
    return (
        f"Le marqueur unique numero {i} porte une affirmation distincte "
        "du reste du texte et n apparait qu une seule fois."
    )


def _filler(length: int) -> str:
    return _FILLER * (length // len(_FILLER) + 1)


def _parts_document(
    n_parts: int, part_len: int, planted_at: float | None = None
) -> str:
    """Markers at the head of each equal part; ``planted_at`` adds one extra
    marker at that fraction — the argument the first pass will NOT name."""
    parts = [_marker(i) + " " + _filler(part_len) for i in range(n_parts)]
    doc = "".join(parts)
    if planted_at is not None:
        at = int(len(doc) * planted_at)
        doc = doc[:at] + _marker(999) + " " + doc[at:]
    return doc


def _answer(moves: List[Dict[str, Any]], thesis: str | None = None) -> str:
    payload: Dict[str, Any] = {"moves": moves}
    if thesis is not None:
        payload["thesis"] = {"reading": thesis, "quote": _marker(0)}
    return json.dumps(payload, ensure_ascii=False)


_THESIS_READING = "la these centrale du document synthetique"


class _ScriptedLLM:
    """Answers in order, records every prompt — the call count is a fact."""

    def __init__(self, answers: List[str]):
        self.answers = list(answers)
        self.prompts: List[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        assert self.answers, "scripted LLM ran out of answers"
        return self.answers.pop(0)


class _RaisingLLM:
    """A provider that fails on every call."""

    async def __call__(self, prompt: str) -> str:
        raise RuntimeError("provider down")


class _State:
    """The smallest state build_first_reading reads: the raw text."""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text


def _head_only_answer() -> str:
    """A whole-document draw that anchors the head: the thesis, one move."""
    return _answer(
        [{"kind": "claim", "reading": "geste d ouverture", "quote": _marker(0)}],
        thesis=_THESIS_READING,
    )


# --- the decision's three witnesses ------------------------------------------


@pytest.mark.parametrize("planted_at", [0.35, 0.6, 0.85])
async def test_a_planted_argument_in_a_bare_stretch_joins_the_inventory(planted_at):
    """The decision's first witness: absent before, present after, marked —
    wherever the hole sits (the geometry is positional, not a head/tail
    special case)."""
    doc = _parts_document(3, 5100, planted_at=planted_at)
    llm = _ScriptedLLM(
        [
            _head_only_answer(),  # the whole-document draw: head anchor only
            _answer(
                [
                    {
                        "kind": "claim",
                        "reading": "l argument plante dans la tranche nue",
                        "quote": _marker(999),
                    }
                ]
            ),
        ]
    )
    result = await build_first_reading(_State(doc), llm)

    # The pass ran: the whole-document call plus exactly one stretch call
    # (one anchor leaves one bare stretch).
    assert len(llm.prompts) == 2
    assert result.second_pass["calls"] == 1
    # The stretch prompt carried the thesis READING as context, never its
    # verbatim quote (an echo would have to be dropped by containment).
    assert _THESIS_READING in llm.prompts[1]
    assert _marker(0) not in llm.prompts[1]
    # The planted argument — verbatim, located, marked second-pass.
    planted = [m for m in result.moves if m.reading.startswith("l argument")]
    assert planted, "the bare-stretch argument did not join the inventory"
    assert planted[0].reading_pass == fr.SECOND_PASS_MARKER
    offset = planted[0].offset
    assert isinstance(offset, int) and 0 <= offset < len(doc)
    # It came from a stretch the pass actually read.
    read = [s for s in result.second_pass["stretches"] if s["read"]]
    assert any(s["offset"] <= offset < s["offset"] + s["length"] for s in read)
    # The payload carries the marker under its own key.
    payload = result.to_state()
    assert payload["second_pass"]["calls"] == 1
    assert any(m.get("pass") == fr.SECOND_PASS_MARKER for m in payload["moves"])


async def test_mutation_with_the_pass_disabled_the_planted_argument_is_absent():
    """The decision's mutation witness: neuter the stretch finder, the
    planted argument is gone again — the pass, and only the pass, carried
    it. The same scripted second answer would have named it."""
    doc = _parts_document(3, 5100, planted_at=0.75)
    llm = _ScriptedLLM(
        [
            _head_only_answer(),
            _answer([{"kind": "claim", "reading": "plante", "quote": _marker(999)}]),
        ]
    )
    original = fr.bare_stretch_spans
    fr.bare_stretch_spans = lambda raw, moves: ([], 0)
    try:
        result = await build_first_reading(_State(doc), llm)
    finally:
        fr.bare_stretch_spans = original
    assert len(llm.prompts) == 1
    assert not result.second_pass
    assert not [m for m in result.moves if m.reading == "plante"]


async def test_a_short_text_issues_no_second_call():
    """The decision's control: one capacity chunk, one reading, no second
    call — even with a long bare tail the first pass left behind."""
    doc = _parts_document(1, 4000, planted_at=0.9)
    assert len(doc) <= WHOLE_TEXT_CALL_CAPACITY
    llm = _ScriptedLLM([_head_only_answer()])
    result = await build_first_reading(_State(doc), llm)
    assert len(llm.prompts) == 1
    payload = result.to_state()
    assert "second_pass" not in payload
    assert not [m for m in result.moves if m.quote == _marker(999)]


# --- the rule: the gap is the document's own ---------------------------------


def test_nothing_anchored_is_no_stretch():
    """k = 0: the gap is the whole document and no span exceeds it —
    re-asking the same failed read is the measured non-repair (R1166)."""
    doc = _parts_document(2, 3000)
    bare, gap = bare_stretch_spans(doc, [])
    assert bare == []
    assert gap == len(doc)


def test_overlapping_quotes_are_one_anchor_group():
    doc = "a" * 300 + _marker(1) + "b" * 200
    at = doc.index(_marker(1))
    moves = [
        {"offset": at, "quote": _marker(1)[:20]},
        {"offset": at + 10, "quote": _marker(1)[10:40]},
    ]
    bare, gap = bare_stretch_spans(doc, moves)
    # One merged group: the gap is over ONE anchor group, not two quotes,
    # and neither edge segment (300 and ~270 chars) exceeds it (~305).
    assert gap == len(doc) // 2
    assert bare == []


def test_the_longest_stretch_is_first_and_ties_go_to_the_earlier():
    left, mid, right = "x" * 100, "y" * 900, "z" * 900
    doc = left + _marker(1) + mid + _marker(2) + right
    at1, at2 = doc.index(_marker(1)), doc.index(_marker(2))
    moves = [
        {"offset": at1, "quote": _marker(1)},
        {"offset": at2, "quote": _marker(2)},
    ]
    bare, gap = bare_stretch_spans(doc, moves)
    assert gap == len(doc) // 3
    lengths = [e - s for s, e in bare]
    assert lengths == sorted(lengths, reverse=True)
    # The two 900-char stretches qualify (gap 706), tie broken by position;
    # the 100-char head does not.
    assert bare == [(at1 + len(_marker(1)), at2), (at2 + len(_marker(2)), len(doc))]


def test_the_call_bound_is_one_per_chunk_beyond_the_first():
    assert second_pass_call_bound(WHOLE_TEXT_CALL_CAPACITY) == 0
    assert second_pass_call_bound(WHOLE_TEXT_CALL_CAPACITY + 1) == 1
    assert second_pass_call_bound(3 * WHOLE_TEXT_CALL_CAPACITY + 10) == 3


# --- the bound bites: recorded on the state, stated in the note ---------------


def _four_anchor_document() -> str:
    """Four anchors, three ~4,100-char stretches and one ~3,400 tail: with
    k=4 the gap is L/5 (~3,287), so FOUR stretches qualify while the real
    call bound is 2 — the bound bites by geometry, no patching needed. One
    extra marker is planted in the MIDDLE of the second stretch (the
    longest): the argument a stretch call can legitimately name — the
    anchors themselves never sit inside a stretch."""
    f1, f2, f3, f4 = (_filler(4100), _filler(4100), _filler(4100), _filler(3400))
    mid = len(f2) // 2
    f2 = f2[:mid] + _marker(999) + " " + f2[mid:]
    return _marker(0) + f1 + _marker(1) + f2 + _marker(2) + f3 + _marker(3) + f4


def _anchored(doc: str, indices: List[int]) -> FirstReading:
    result = FirstReading(status="ok")
    result.moves = [
        DefiningMove(
            kind="claim",
            reading=f"g{i}",
            quote=_marker(i),
            offset=doc.index(_marker(i)),
        )
        for i in indices
    ]
    return result


async def test_the_bound_bites_and_both_the_record_and_the_note_say_so():
    doc = _four_anchor_document()
    bare, gap = bare_stretch_spans(
        doc, [m.to_dict() for m in _anchored(doc, [0, 1, 2, 3]).moves]
    )
    # Four anchor groups -> the gap is L/5 (~3,287): all four segments
    # (4,249, 4,136, 4,136, 3,478) exceed it, while the document spends at
    # most 2 second-pass calls — the bite is the geometry's own.
    assert len(bare) == 4
    assert all(e - s > gap for s, e in bare), "a non-bare stretch was counted"
    assert second_pass_call_bound(len(doc)) == 2

    result = _anchored(doc, [0, 1, 2, 3])
    llm = _ScriptedLLM([_answer([]), _answer([])])  # the read stretches answer nothing
    await _second_reading_pass(result, doc, llm, 80)

    record = result.second_pass
    assert record["calls"] == 2
    assert record["call_bound"] == 2
    unread = [s for s in record["stretches"] if not s["read"]]
    assert len(unread) == 2, "the bite left no unread stretch to record"

    state = SimpleNamespace(
        raw_text=doc,
        defining_moves={
            "status": "ok",
            "read_scope": {"whole_document": True},
            "moves": [m.to_dict() for m in result.moves],
            "second_pass": record,
        },
    )
    note = first_reading_note(state)
    assert "Passe seconde" in note
    assert "2 tranche(s) relue(s)" in note
    assert "2 tranche(s) nue(s) au-delà de la borne d'appels (2)" in note


async def test_a_failed_stretch_call_costs_its_stretch_not_the_reading():
    """Provider failure on a stretch: counted, and the first pass's
    inventory stands untouched. R1167 finding 3: an attempt that raised is
    not a re-read — ``calls`` counts the stretches actually read (0 here),
    the failed ones say their own count, and the note states the failure
    instead of printing « relue(s) » over a dead provider."""
    doc = _four_anchor_document()
    result = _anchored(doc, [0, 1, 2, 3])
    before = [m.to_dict() for m in result.moves]
    await _second_reading_pass(result, doc, _RaisingLLM(), 80)
    assert result.second_pass["failed_calls"] == 2
    assert result.second_pass["calls"] == 0
    assert [m.to_dict() for m in result.moves] == before
    state = SimpleNamespace(
        raw_text=doc,
        defining_moves={
            "status": "ok",
            "read_scope": {"whole_document": True},
            "moves": [m.to_dict() for m in result.moves],
            "second_pass": result.second_pass,
        },
    )
    note = first_reading_note(state)
    assert "Passe seconde : 0 tranche(s) relue(s)" in note
    assert "2 appel(s) en échec" in note


# --- the same citation rule, the same locator, whole-document offsets ---------


async def test_a_quote_the_document_does_not_carry_is_dropped_and_counted():
    doc = _four_anchor_document()
    result = _anchored(doc, [0, 1, 2, 3])
    llm = _ScriptedLLM(
        [
            _answer(
                [
                    {
                        "kind": "claim",
                        "reading": "citation inventee",
                        "quote": "Cette phrase n existe dans aucun document.",
                    }
                ]
            )
        ]
        * 2
    )
    await _second_reading_pass(result, doc, llm, 80)
    assert result.second_pass["dropped_quotes"] >= 1
    assert not [m for m in result.moves if m.reading == "citation inventee"]


async def test_a_quote_outside_its_stretch_is_not_kept():
    """The stretch call may echo the thesis context; the containment rule
    drops the echo — the anchor must land inside the stretch it was asked
    about."""
    doc = _four_anchor_document()
    result = _anchored(doc, [0, 1, 2, 3])
    llm = _ScriptedLLM(
        [_answer([{"kind": "claim", "reading": "echo", "quote": _marker(0)}])] * 2
    )
    await _second_reading_pass(result, doc, llm, 80)
    assert not [m for m in result.moves if m.reading == "echo"]


async def test_a_quote_repeated_within_a_stretch_answer_is_kept_once():
    doc = _four_anchor_document()
    result = _anchored(doc, [0, 1, 2, 3])
    # The planted marker sits in the SECOND stretch — the longest, so the
    # first call. Quoted twice in that answer, it is one move: the second is
    # a dropped duplicate, counted.
    llm = _ScriptedLLM(
        [
            _answer(
                [
                    {"kind": "claim", "reading": "a", "quote": _marker(999)},
                    {"kind": "claim", "reading": "b", "quote": _marker(999)},
                ]
            ),
            _answer([]),
        ]
    )
    await _second_reading_pass(result, doc, llm, 80)
    kept = [m for m in result.moves if m.quote == _marker(999)]
    assert len(kept) == 1
    assert kept[0].reading == "a"


async def test_the_inventory_bound_still_caps_the_total():
    doc = _four_anchor_document()
    result = _anchored(doc, [0, 1, 2, 3])
    llm = _ScriptedLLM(
        [
            _answer([{"kind": "claim", "reading": "a", "quote": _marker(999)}]),
            _answer([]),
        ]
    )
    await _second_reading_pass(
        result, doc, llm, len(result.moves)
    )  # inventory already full
    assert result.second_pass.get("inventory_capped", 0) >= 1
    assert len(result.moves) == 4, "a move joined a full inventory"


# --- byte-identical when nothing is bare --------------------------------------


def _even_document(k: int = 5, step: int = 900) -> str:
    """Evenly anchored by construction: every segment is ``step`` chars and
    the gap is ``step + (k * quote_len) // (k + 1)`` — above every segment,
    so no stretch is bare."""
    return "".join(_filler(step) + _marker(i) for i in range(k)) + _filler(step)


async def test_an_evenly_anchored_document_keeps_a_byte_identical_inventory():
    doc = _even_document()
    result = _anchored(doc, [0, 1, 2, 3, 4])
    bare, _gap = bare_stretch_spans(doc, [m.to_dict() for m in result.moves])
    assert bare == [], "the even document must have no bare stretch"
    llm = _ScriptedLLM([])
    await _second_reading_pass(result, doc, llm, 80)
    assert not result.second_pass
    payload = json.dumps(result.to_state(), sort_keys=True)

    result2 = _anchored(doc, [0, 1, 2, 3, 4])
    original = fr.bare_stretch_spans
    fr.bare_stretch_spans = lambda raw, moves: ([], 0)
    try:
        await _second_reading_pass(result2, doc, llm, 80)
    finally:
        fr.bare_stretch_spans = original
    assert json.dumps(result2.to_state(), sort_keys=True) == payload


# --- the examined budget stays under the ceiling (#3523) ----------------------


def _budget_state(doc: str, named: int) -> SimpleNamespace:
    return SimpleNamespace(
        raw_text=doc,
        defining_moves={
            "status": "ok",
            "moves": [
                {"kind": "claim", "reading": "g", "quote": _marker(0), "offset": 0}
            ]
            * named,
        },
    )


def test_named_past_the_ceiling_is_capped_at_it():
    """The second pass can push the named count past k(L)'s ceiling; the
    EXAMINED count — the pass's real cost, ~0.019 $ per unit (#3523) —
    stays under it. What the cap excludes lands in the recorded residue."""
    doc = _parts_document(10, 5100)  # k(L) well above the floor, below 45
    assert examined_unit_budget(_budget_state(doc, 60)) == 45


def test_under_the_ceiling_the_formula_is_unchanged():
    doc = _parts_document(10, 5100)
    # named 40, k(L) 18: the pre-(b) pins' case, unchanged by the cap term.
    assert examined_unit_budget(_budget_state(doc, 40)) == 40


# --- R1167 revision: the writer, the slice locator, the share, the priority ---


def test_the_writer_carries_the_second_pass_and_only_when_it_ran():
    """R1167 finding 1, the blocking one. The writer is the ONLY path from
    the phase output into ``state.defining_moves``; its closed key list
    dropped the record, so the « Passe seconde » line never printed in
    production even though the PR body said it did. A payload WITH a record
    gives a state that carries it; a payload without one keeps the
    byte-identical pre-(b) shape."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_first_reading_to_state,
    )

    payload_with = {
        "moves": [{"kind": "claim", "reading": "g", "quote": "q", "offset": 3}],
        "dropped_quotes": 0,
        "status": "ok",
        "read_scope": {"whole_document": True},
        "second_pass": {
            "calls": 1,
            "stretches": [{"offset": 9, "length": 99, "read": True}],
        },
    }
    # The real state declares its fields — the writer only writes on an
    # attribute the state already carries (``hasattr``), so the witness
    # mirrors that shape instead of a bare namespace.
    state = SimpleNamespace(defining_moves=None)
    _write_first_reading_to_state(payload_with, state, {})
    assert state.defining_moves["second_pass"]["calls"] == 1
    assert "Passe seconde : 1 tranche(s) relue(s)" in first_reading_note(state)

    payload_without = {k: v for k, v in payload_with.items() if k != "second_pass"}
    state2 = SimpleNamespace(defining_moves=None)
    _write_first_reading_to_state(payload_without, state2, {})
    assert "second_pass" not in state2.defining_moves
    assert "Passe seconde" not in first_reading_note(state2)


async def test_a_quote_the_document_also_carries_earlier_is_kept_at_its_stretch():
    """R1167 finding 2's own repro: the same phrase anchored at ~100 and
    present again inside a bare stretch. The old document-first locator
    returned the FIRST occurrence, the containment test rejected it, and the
    pass lost the argument it was sent to find — ``moves_kept: 0,
    dropped_quotes: 1``. The slice locator keeps the stretch's own
    occurrence, at a whole-document offset."""
    doc = _marker(999) + " " + _four_anchor_document()  # the words ALSO sit at 0
    result = _anchored(doc, [0, 1, 2, 3])
    llm = _ScriptedLLM(
        [
            _answer(
                [
                    {
                        "kind": "claim",
                        "reading": "l occurrence de la tranche",
                        "quote": _marker(999),
                    }
                ]
            ),
            _answer([]),
        ]
    )
    await _second_reading_pass(result, doc, llm, 80)
    kept = [m for m in result.moves if m.reading == "l occurrence de la tranche"]
    assert kept, "the stretch's own occurrence was dropped"
    offset = kept[0].offset
    stretch = next(s for s in result.second_pass["stretches"] if s["read"])
    assert stretch["offset"] <= offset < stretch["offset"] + stretch["length"]
    assert offset > 0, "located at the document's first occurrence, not the stretch's"
    assert result.second_pass["dropped_quotes"] == 0


def _shared_document(per_stretch: int = 4) -> str:
    """Four anchors; the two longest stretches (the two the bound reads)
    each carry ``per_stretch`` planted markers of their own."""
    f1, f2, f3, f4 = (_filler(4600), _filler(4100), _filler(4100), _filler(3300))

    def plant(filler: str, base: int, count: int) -> str:
        step = len(filler) // (count + 1)
        for i in range(count):
            at = step * (i + 1)
            filler = filler[:at] + _marker(base + i) + " " + filler[at:]
        return filler

    f1 = plant(f1, 900, per_stretch)
    f2 = plant(f2, 950, per_stretch)
    return _marker(0) + f1 + _marker(1) + f2 + _marker(2) + f3 + _marker(3) + f4


async def test_the_inventory_share_is_not_first_come_first_served():
    """R1167's mechanism read in the records: the ceiling was served in
    stretch-arrival order, the first stretches filled the inventory and the
    tail's findings reached it only as a count. Each stretch the pass reads
    now takes a SHARE of the slots still open — with 4 slots and 2 stretches,
    2 each — and what a stretch loses to its share is counted ON it."""
    doc = _shared_document(4)
    result = _anchored(doc, [0, 1, 2, 3])

    def offered(base: int) -> List[Dict[str, Any]]:
        return [
            {
                "kind": "claim",
                "reading": f"premier {base + i}",
                "quote": _marker(base + i),
            }
            for i in range(4)
        ]

    llm = _ScriptedLLM([_answer(offered(900)), _answer(offered(950))])
    # 4 first-pass moves; the inventory leaves room for exactly 4 more.
    await _second_reading_pass(result, doc, llm, 8)

    record = result.second_pass
    assert record["calls"] == 2
    read = [s for s in record["stretches"] if s["read"]]
    assert len(read) == 2
    # Two slots each: NO stretch took the four the old order would have let
    # the first one take, and each stretch's loss is counted on it.
    assert sorted(s.get("inventory_lost", 0) for s in read) == [2, 2]
    assert record["inventory_capped"] == 4
    assert record["moves_kept"] == 4
    for stretch in read:
        kept_here = [
            m
            for m in result.moves
            if m.reading_pass == fr.SECOND_PASS_MARKER
            and stretch["offset"]
            <= (m.offset or -1)
            < stretch["offset"] + stretch["length"]
        ]
        assert len(kept_here) == 2, "one stretch monopolised the inventory"


def test_the_selection_keeps_the_first_pass_priority_when_the_pass_adds_moves():
    """R1167's bar item 3, the free witness the coordinator asked for: on a
    synthetic document, the selection keeps the first pass's priorities when
    the pass adds moves. The pass's moves join the inventory and the
    population (their anchored units exist), but the selector's reserved
    seats belong to the whole-document reading's centres — a full inventory
    of priority spans measured as no priority at all."""
    from argumentation_analysis.agents.core.reading import (
        defining_move_spans,
        first_pass_move_spans,
    )
    from argumentation_analysis.orchestration.invoke_callables import (
        _selection_priority_spans,
    )
    from argumentation_analysis.orchestration.selection import (
        SelectableUnit,
        select_for_budget,
    )

    def unit(i: int) -> SelectableUnit:
        text = f"unite synthetique numero {i} du document temoin"
        return SelectableUnit(
            unit_id=f"unit_{i}",
            text=text,
            producer="extraction",
            offset=i * 100,
            source_quote=text,
        )

    population = [unit(i) for i in range(10)]
    spans_of = {i: (i * 100, i * 100 + len(unit(i).text)) for i in range(10)}
    # First-pass centres at units 1 and 8; the pass adds 3, 4 and 6.

    def move(i: int, pas: str) -> Dict[str, Any]:
        return {
            "kind": "claim",
            "reading": f"g{i}",
            "quote": unit(i).text,
            "offset": i * 100,
            **({"pass": pas} if pas else {}),
        }

    state = SimpleNamespace(
        raw_text="x" * 1000,
        defining_moves={
            "status": "ok",
            "moves": [
                move(1, ""),
                move(8, ""),
                move(3, "second"),
                move(4, "second"),
                move(6, "second"),
            ],
        },
    )

    # The split is real: all five spans exist, the selector hints at two.
    assert sorted(defining_move_spans(state)) == sorted(
        [spans_of[1], spans_of[3], spans_of[4], spans_of[6], spans_of[8]]
    )
    assert sorted(first_pass_move_spans(state)) == [spans_of[1], spans_of[8]]
    assert _selection_priority_spans(state) == [spans_of[1], spans_of[8]]

    # A pass-free state keeps the same hint — byte-identical selection.
    state_first_only = SimpleNamespace(
        raw_text="x" * 1000,
        defining_moves={"status": "ok", "moves": [move(1, ""), move(8, "")]},
    )
    assert _selection_priority_spans(state_first_only) == _selection_priority_spans(
        state
    )

    # Through the seam, at a budget that cannot take everything: the two
    # first-pass units hold the reserved seats whatever else the band rule
    # reaches. The pass's units compete through the ordinary rule, they do
    # not displace the centres.
    selection = select_for_budget(
        population,
        3,
        text_length=1000,
        priority_spans=_selection_priority_spans(state),
    )
    chosen = {u.unit_id for u in selection.selected}
    assert {"unit_1", "unit_8"} <= chosen
    assert selection.priority_taken == 2
