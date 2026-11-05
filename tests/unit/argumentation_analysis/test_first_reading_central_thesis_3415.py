"""#3415 — the first reading names the thesis and the mechanism first.

Cycle 1 measured it: 9/10 readings ran and read the document whole, but 0 of
the 10 M1 items fall on a passage a move retained — the question chose local
gestures (a claim, a concession), not the central thesis and the mechanism
that carries it; on one long document the zero-shot's central point sits at
about character 40 000 of 47 644 and no move is near. And one malformed answer
character (a ',' delimiter) cost the whole reading.

Three asks, each with its born-red witness, plus the byte-identical control:

1. the question names the central thesis and its mechanism FIRST, each with a
   verbatim quote and its position — witnessed on a synthetic long document
   (> 30 000 characters, opaque filler) whose mechanism is stated once, LATE
   (past the midpoint);
2. a malformed object costs its own move, never the reading: every object
   that reads on its own is kept, the lost ones are counted and stated;
3. the thesis and the mechanism reach Act II and Act III under their own
   names, with their quote.

Offline: a recording fake model answers the single call, the documents are
synthetic, nothing depends on the corpus, a key, or the network. Born-red
discipline: the symbols #3415 creates (``slot``, ``malformed_moves``, the
slots in the question) are measured inside the tests, so a run on the
pre-fix tree reports each witness's own failure. The slot-less control keeps
the pre-#3415 wording byte-identical — the pinned wording itself is guarded
by ``test_first_reading_acts_3395``, which this change must leave green.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# --- the synthetic long document (opaque filler, no corpus content) ---------

_FILLER_PARA = (
    "Le paragraphe de contexte developpe un point peripherique : des chiffres "
    "d'expose, une remarque de methode, rien qui porte la demonstration "
    "centrale du document. "
)

_THESIS = (
    "La these tenue par le document est que la reforme protege ses "
    "commanditaires plutot que les usagers."
)

_MECHANISM = (
    "Le mecanisme qui la porte tient en une phrase : la garantie offerte "
    "repose entierement sur la delegation du risque aux petits porteurs."
)

_LOCAL_1 = "des chiffres d'expose"
_LOCAL_2 = "une remarque de methode"


def _long_document() -> str:
    """A document whose thesis sits early-ish and whose mechanism is stated
    ONCE, LATE — the measured shape (the central point at 40 000 of 47 644)."""
    head = _FILLER_PARA * 100
    middle = _FILLER_PARA * 100
    tail = _FILLER_PARA * 40
    return f"{head}\n\n{_THESIS}\n\n{middle}\n\n{_MECHANISM}\n\n{tail}"


def reading():
    """The module under test, imported late on purpose (born-red discipline)."""
    from argumentation_analysis.agents.core import reading as module

    return module


class _FakeModel:
    """Answers once, records the prompt, so the call itself is measurable."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def _state(text: str) -> SimpleNamespace:
    return SimpleNamespace(raw_text=text)


def _slots_answer() -> str:
    """The answer the question now asks for: thesis and mechanism first."""
    return json.dumps(
        {
            "thesis": {
                "reading": "la reforme protege ses commanditaires",
                "quote": _THESIS,
            },
            "mechanism": {
                "reading": "le risque est delegue aux petits porteurs",
                "quote": _MECHANISM,
            },
            "moves": [
                {"kind": "claim", "reading": "un chiffre", "quote": _LOCAL_1},
                {"kind": "concession", "reading": "une remarque", "quote": _LOCAL_2},
            ],
        },
        ensure_ascii=False,
    )


def _malformed_answer() -> str:
    """A well-shaped answer with ONE unreadable move object (trailing comma).

    The document-level parse rejects the whole text; per-object salvage must
    keep the two slots and the two good moves, and count exactly one lost.
    """
    return (
        '{"thesis": '
        + json.dumps(
            {"reading": "la reforme protege ses commanditaires", "quote": _THESIS},
            ensure_ascii=False,
        )
        + ', "mechanism": '
        + json.dumps(
            {"reading": "le risque est delegue", "quote": _MECHANISM},
            ensure_ascii=False,
        )
        + ', "moves": ['
        + json.dumps(
            {"kind": "claim", "reading": "un chiffre", "quote": _LOCAL_1},
            ensure_ascii=False,
        )
        + ', {"kind": "threat", "reading": "phrase perdue", "quote": "citation perdue",}'
        + ", "
        + json.dumps(
            {"kind": "concession", "reading": "une remarque", "quote": _LOCAL_2},
            ensure_ascii=False,
        )
        + "]}"
    )


def _mechanism_corrupted_answer() -> str:
    """The bad character sits INSIDE the mechanism object (R1144).

    The mechanism is lost and counted; the thesis keeps its slot. A bare-span
    salvage cannot tell the two apart — both arrive as anonymous moves.
    """
    return (
        '{"thesis": '
        + json.dumps(
            {"reading": "la reforme protege ses commanditaires", "quote": _THESIS},
            ensure_ascii=False,
        )
        + ', "mechanism": {"reading": "le risque est delegue", "quote": "'
        + _MECHANISM
        + '",}, "moves": ['
        + json.dumps(
            {"kind": "claim", "reading": "un chiffre", "quote": _LOCAL_1},
            ensure_ascii=False,
        )
        + ", "
        + json.dumps(
            {"kind": "concession", "reading": "une remarque", "quote": _LOCAL_2},
            ensure_ascii=False,
        )
        + "]}"
    )


# ---------------------------------------------------------------------------
# Ask 1 — the question names the thesis and the mechanism first
# ---------------------------------------------------------------------------


class TestTheQuestionNamesTheThesisAndMechanismFirst:
    def test_the_fixture_is_the_measured_shape(self) -> None:
        doc = _long_document()
        assert len(doc) > 30_000
        # The mechanism is stated once, late — past the midpoint.
        assert doc.count(_MECHANISM) == 1
        assert doc.index(_MECHANISM) > len(doc) // 2

    async def test_the_prompt_asks_for_the_two_slots(self) -> None:
        model = _FakeModel(_slots_answer())
        await reading().build_first_reading(_state(_long_document()), model)
        prompt = model.prompts[0]
        assert "CENTRAL THESIS" in prompt
        assert "MECHANISM" in prompt
        # The schema carries the two slots, and a local move comes after.
        assert '"thesis"' in prompt and '"mechanism"' in prompt
        assert prompt.index("CENTRAL THESIS") < prompt.index("moves")

    async def test_the_reading_keeps_the_late_mechanism(self) -> None:
        doc = _long_document()
        result = await reading().build_first_reading(
            _state(doc), _FakeModel(_slots_answer())
        )
        assert result.status == "ok"
        slots = {m.slot: m for m in result.moves if m.slot}
        assert set(slots) == {"thesis", "mechanism"}
        # The kinds stay in the closed vocabulary the render prints.
        assert slots["thesis"].kind == "thesis"
        assert slots["mechanism"].kind == "device"
        # The mechanism's quote is positioned past the midpoint of the
        # document — the passage cycle 1's moves never approached.
        mech = slots["mechanism"]
        assert mech.offset is not None
        assert mech.offset > len(doc) // 2
        # The slots come first; the local moves survive after them.
        assert [m.slot for m in result.moves[:2]] == ["thesis", "mechanism"]
        assert len(result.moves) == 4


# ---------------------------------------------------------------------------
# Ask 2 — one bad object costs its own move, never the reading
# ---------------------------------------------------------------------------


class TestOneBadObjectCostsItsOwnMove:
    async def test_the_readable_objects_survive_and_the_lost_one_is_counted(
        self,
    ) -> None:
        doc = _long_document()
        result = await reading().build_first_reading(
            _state(doc), _FakeModel(_malformed_answer())
        )
        assert result.status == "ok"
        # The whole-answer parse fails (a trailing comma inside one object):
        # per-object salvage keeps the two slots and the two good moves.
        assert len(result.moves) == 4
        quotes = {m.quote for m in result.moves}
        assert _THESIS in quotes and _MECHANISM in quotes
        assert _LOCAL_1 in quotes and _LOCAL_2 in quotes
        # R1144 — the salvage keeps the KEYS: the two slots come back under
        # their own names and kinds, ahead of the local moves (a comparison
        # of quotes alone cannot see this — it was the measured blind spot).
        assert [m.slot for m in result.moves[:2]] == ["thesis", "mechanism"]
        assert [m.kind for m in result.moves[:2]] == ["thesis", "device"]
        # Exactly one object was unreadable — stated, never hidden.
        assert result.malformed_moves == 1
        assert "citation perdue" not in quotes
        payload = result.to_state()
        assert payload["malformed_moves"] == 1
        # The note names the slots — never « autre : » for the thesis or the
        # mechanism (the reader-visible face of the same defect).
        note = reading().first_reading_note(SimpleNamespace(defining_moves=payload))
        assert "thèse centrale" in note and "mécanisme" in note
        # Recovered moves are not an error (the writers' shared guard would
        # drop the whole invoke on an error key).
        assert "error" not in payload

    async def test_the_mechanism_is_lost_and_the_thesis_keeps_its_slot(
        self,
    ) -> None:
        """R1144 — a bad character inside the mechanism costs the mechanism
        only: it is counted, the thesis keeps its slot, the moves survive."""
        result = await reading().build_first_reading(
            _state(_long_document()), _FakeModel(_mechanism_corrupted_answer())
        )
        assert result.status == "ok"
        assert result.malformed_moves == 1
        assert [m.slot for m in result.moves] == ["thesis", "", ""]
        assert [m.kind for m in result.moves] == ["thesis", "claim", "concession"]
        quotes = {m.quote for m in result.moves}
        assert _THESIS in quotes and _LOCAL_1 in quotes and _LOCAL_2 in quotes
        assert _MECHANISM not in quotes

    async def test_an_answer_nothing_can_read_is_still_a_parse_error(self) -> None:
        result = await reading().build_first_reading(
            _state(_long_document()), _FakeModel("not json at all")
        )
        assert result.status == "parse_error"
        assert result.moves == []


# ---------------------------------------------------------------------------
# Ask 3 — the thesis and the mechanism reach the Acts
# ---------------------------------------------------------------------------

_ACT_FILLER = "filler text for the witness, no corpus content."


def _state_with_slots() -> UnifiedAnalysisState:
    """A production-shaped state whose reading recorded the two slots."""
    state = UnifiedAnalysisState(_ACT_FILLER)
    state.defining_moves = {
        "moves": [
            {
                "kind": "thesis",
                "reading": "La these protege les commanditaires.",
                "quote": _THESIS,
                "offset": 12,
                "basis": "first_reading",
                "slot": "thesis",
            },
            {
                "kind": "device",
                "reading": "Le risque est delegue aux petits porteurs.",
                "quote": _MECHANISM,
                "offset": 48,
                "basis": "first_reading",
                "slot": "mechanism",
            },
        ],
        "dropped_quotes": 0,
        "status": "ok",
        "read_scope": {"whole_document": True, "offset": 0, "window": len(_ACT_FILLER)},
        "basis": "first_reading",
    }
    return state


class TestTheSlotsReachTheActs:
    def test_act2_carries_the_mechanism_under_its_name(self) -> None:
        prompt = build_act2_prompt(build_act2_evidence(_state_with_slots()))
        assert "mécanisme" in prompt
        assert _MECHANISM in prompt
        assert "thèse centrale" in prompt
        assert _THESIS in prompt

    def test_act3_carries_the_mechanism_under_its_name(self) -> None:
        prompt = build_act3_prompt(build_act3_evidence(_state_with_slots()))
        assert "mécanisme" in prompt
        assert _MECHANISM in prompt


# ---------------------------------------------------------------------------
# The control — a slot-less record renders the pre-#3415 passage
# ---------------------------------------------------------------------------


def _slotless_record() -> dict:
    return {
        "moves": [
            {
                "kind": "claim",
                "reading": "Un chiffre d'expose.",
                "quote": _LOCAL_1,
                "offset": 7,
                "basis": "first_reading",
            }
        ],
        "dropped_quotes": 0,
        "status": "ok",
        "read_scope": {"whole_document": True, "offset": 0, "window": 40},
        "basis": "first_reading",
    }


class TestTheSlotlessControlIsByteIdentical:
    def test_no_new_token_no_new_line(self) -> None:
        state = SimpleNamespace(defining_moves=_slotless_record())
        note = reading().first_reading_note(state)
        # None of #3415's tokens appear for a record that carries none of
        # its keys; the pre-#3415 wording is pinned by the 3395 acts suite,
        # which this change must leave green (it ran: 40 passed).
        for token in ("thèse centrale", "mécanisme", "objet(s) illisible(s)"):
            assert token not in note
        assert "affirmation :" in note  # the local move prints as before
