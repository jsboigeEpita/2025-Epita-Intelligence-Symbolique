"""#3432 — the first reading names the PILLARS the thesis rests on.

Cycle 2 of the panel (#3374) measured that the render states the central thesis
on 9/10 documents but does not examine it: 25 severe M1-on-thesis items remain,
and on 7 documents the zero-shot names what the thesis rests on — the two or
three passages of evidence or reasoning that carry it — where no line of the
render does. The pillars sit far from the thesis passage; the per-argument
selection (#3395) prefers the units overlapping a defining move, so they were
rarely read at all.

The repair is a third slot in the reading, never a raised ``MAX_MOVES``: each
pillar carries a verbatim quote, the citation rule (#3427's anchor) applies to
it like to every slot, and being a move its span joins ``defining_move_spans``
so the selector examines it first.

Witnesses here, all synthetic and offline (a recording fake model answers the
single call; no corpus, no key, no network, no JVM):

* the fixture is the measured shape — the pillars sit thousands of characters
  away from the thesis;
* the question asks for the pillars, before the other moves;
* the producer records them under ``slot="pillar"`` with the document's own
  characters, and the note names them « pilier de la thèse »;
* their spans reach ``defining_move_spans`` — the selection hint — which is
  what makes the lenses read them;
* the bound is declared (``MAX_PILLARS``) and the model is told it;
* a pillar whose quote fails the citation rule keeps its reading through the
  anchor, exactly like the thesis and the mechanism;
* a pillar with no reading is NAMED in ``dropped_slots`` rather than counted.

Born red on the pre-#3432 tree: the module has no ``pillars`` slot, no
``MAX_PILLARS`` and the note has no « pilier » label.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

# --- the synthetic document (opaque filler, no corpus content) --------------

_FILLER = (
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

# Two pillars, stated FAR from the thesis — the measured shape. The second one
# is deliberately the longest: it must survive the citation rule as given.
_PILLAR_1 = (
    "Le compte rendu de la seance du conseil montre que le vote sur la "
    "garantie a ete emporte par les seuls suffrages des commanditaires "
    "present, les usagers n'ayant pas ete convoques."
)

_PILLAR_2 = (
    "Une note de service anterieure etablit que le meme dispositif avait "
    "deja ete refuse aux menages modestes pour un motif de solvabilite, "
    "puis accorde aux societes de portage sans nouvel examen."
)

_LOCAL = "des chiffres d'expose"


def _document() -> str:
    """Thesis early, mechanism late, the two pillars far from both."""
    return (
        f"{_FILLER * 40}\n\n"
        f"{_THESIS}\n\n"
        f"{_FILLER * 40}\n\n"
        f"{_PILLAR_1}\n\n"
        f"{_FILLER * 40}\n\n"
        f"{_PILLAR_2}\n\n"
        f"{_FILLER * 10}\n\n"
        f"{_MECHANISM}\n\n"
        f"{_FILLER * 5}"
    )


def reading():
    """The module under test, imported late on purpose (born-red discipline)."""
    from argumentation_analysis.agents.core import reading as module

    return module


class _FakeModel:
    """Answers once and records the prompt, so the call itself is measurable."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def _state(text: str) -> SimpleNamespace:
    return SimpleNamespace(raw_text=text)


def _answer(pillars=None, moves=None) -> str:
    """The answer the question now asks for: thesis, mechanism, PILLARS, moves."""
    if pillars is None:
        pillars = [
            {
                "kind": "claim",
                "reading": "le vote emporte par les seuls commanditaires",
                "quote": _PILLAR_1,
            },
            {
                "kind": "claim",
                "reading": "un refus anterieur pour les menages modestes",
                "quote": _PILLAR_2,
            },
        ]
    if moves is None:
        moves = [{"kind": "claim", "reading": "un chiffre", "quote": _LOCAL}]
    return json.dumps(
        {
            "thesis": {
                "reading": "la reforme protege ses commanditaires",
                "quote": _THESIS,
            },
            "mechanism": {"reading": "le risque est delegue", "quote": _MECHANISM},
            "pillars": pillars,
            "moves": moves,
        },
        ensure_ascii=False,
    )


async def _read(answer: str = "") -> tuple[object, str]:
    doc = _document()
    result = await reading().build_first_reading(
        _state(doc), _FakeModel(answer or _answer())
    )
    return result, doc


# ---------------------------------------------------------------------------
# The fixture is the measured shape
# ---------------------------------------------------------------------------


class TestTheFixtureIsTheMeasuredShape:
    def test_the_pillars_sit_far_from_the_thesis(self) -> None:
        doc = _document()
        thesis_at = doc.index(_THESIS)
        for pillar in (_PILLAR_1, _PILLAR_2):
            assert doc.count(pillar) == 1
            assert doc.index(pillar) - thesis_at > 5_000

    def test_the_pillars_are_not_restatements_of_the_thesis(self) -> None:
        # A pillar shares no sentence with the thesis: the slot would be
        # useless if it only re-quoted the thesis further along.
        doc = _document()
        for pillar in (_PILLAR_1, _PILLAR_2):
            assert pillar != _THESIS
            assert pillar not in _THESIS and _THESIS not in pillar
            assert len(pillar.split()) >= 12
            assert doc.count(pillar) == 1


# ---------------------------------------------------------------------------
# Ask 1 — the question asks for the pillars
# ---------------------------------------------------------------------------


class TestTheQuestionAsksForThePillars:
    async def test_the_prompt_names_the_pillars(self) -> None:
        model = _FakeModel(_answer())
        await reading().build_first_reading(_state(_document()), model)
        prompt = model.prompts[0]
        assert "PILLARS" in prompt
        assert '"pillars"' in prompt
        # The schema asks for a quote and a kind, like every other entry.
        assert (
            '"kind": "claim|concession|device|audience|threat|dilemma|other"' in prompt
        )

    async def test_the_pillars_come_before_the_other_moves(self) -> None:
        model = _FakeModel(_answer())
        await reading().build_first_reading(_state(_document()), model)
        prompt = model.prompts[0]
        assert (
            prompt.index("PILLARS")
            < prompt.index('"pillars"')
            < prompt.index('"moves"')
        )

    async def test_the_bound_is_declared_and_told_to_the_model(self) -> None:
        module = reading()
        assert module.MAX_PILLARS == 3
        model = _FakeModel(_answer())
        document = _document()
        await module.build_first_reading(_state(document), model)
        budget = module.pillar_budget(len(document))
        assert budget >= module.MAX_PILLARS
        assert f"At most {budget} pillars" in model.prompts[0]

    def test_the_volume_bound_is_not_the_repair(self) -> None:
        """The issue's anti-pendulum: the pillars are named, not caught by
        volume — ``MAX_MOVES`` is untouched."""
        assert reading().MAX_MOVES == 12


# ---------------------------------------------------------------------------
# Ask 1 — the producer records them, with the document's own characters
# ---------------------------------------------------------------------------


class TestTheProducerRecordsThePillars:
    async def test_each_pillar_is_a_move_under_its_slot(self) -> None:
        result, doc = await _read()
        assert result.status == "ok"
        pillars = [m for m in result.moves if m.slot == "pillar"]
        assert len(pillars) == 2
        quotes = {m.quote for m in pillars}
        assert quotes == {_PILLAR_1, _PILLAR_2}
        # The characters are the DOCUMENT's: positions address it exactly.
        for move in pillars:
            assert move.offset is not None
            assert doc[move.offset : move.offset + len(move.quote)] == move.quote
            assert move.kind in reading().MOVE_KINDS
            assert not move.anchor  # passed the citation rule as given

    async def test_the_pillars_come_before_the_local_moves(self) -> None:
        result, _ = await _read()
        slots = [m.slot for m in result.moves]
        local_at = slots.index("")
        assert slots[0] == "thesis" and slots[1] == "mechanism"
        assert slots.count("pillar") == 2
        # The pillars keep their place ahead of every local move, whatever
        # their position in the document.
        assert max(i for i, s in enumerate(slots) if s == "pillar") < local_at

    async def test_an_unknown_pillar_kind_stays_in_the_closed_vocabulary(self) -> None:
        answer = _answer(
            pillars=[
                {"kind": "pilier", "reading": "un vote emporte", "quote": _PILLAR_1},
                {"reading": "un refus anterieur", "quote": _PILLAR_2},
            ]
        )
        result, _ = await _read(answer)
        pillars = [m for m in result.moves if m.slot == "pillar"]
        assert len(pillars) == 2
        # « pilier » is not in the closed vocabulary; a pillar stays a claim
        # rather than arriving as « autre », and a kind-less pillar too.
        assert {m.kind for m in pillars} == {"claim"}

    async def test_the_bound_is_enforced(self) -> None:
        # Five DISTINCT passages the answer offers as pillars — distinct so
        # the dedupe cannot be what holds the count down.
        distinct = (
            _PILLAR_1,
            _PILLAR_2,
            "des chiffres d'expose",
            "une remarque de methode",
            "la delegation du risque aux petits porteurs",
        )
        for passage in distinct:
            assert passage in _document()
        many = [
            {"kind": "claim", "reading": f"pilier {i}", "quote": passage}
            for i, passage in enumerate(distinct)
        ]
        result, _ = await _read(_answer(pillars=many))
        pillars = [m for m in result.moves if m.slot == "pillar"]
        budget = reading().pillar_budget(len(_document()))
        assert len(pillars) == budget
        # The kept ones are the first pillars the length-aware budget allows.
        assert [m.quote for m in pillars] == list(distinct[:budget])


# ---------------------------------------------------------------------------
# Ask 1 — the spans reach the selection
# ---------------------------------------------------------------------------


class TestThePillarsReachTheSelection:
    async def test_the_pillar_spans_join_defining_move_spans(self) -> None:
        module = reading()
        result, doc = await _read()
        state = SimpleNamespace(defining_moves=result.to_state())
        spans = module.defining_move_spans(state)
        for pillar in (_PILLAR_1, _PILLAR_2):
            start = doc.index(pillar)
            assert (start, start + len(pillar)) in spans

    async def test_the_state_records_the_slot_and_the_position(self) -> None:
        result, doc = await _read()
        record = result.to_state()
        pillars = [m for m in record["moves"] if m.get("slot") == "pillar"]
        assert len(pillars) == 2
        for pillar in pillars:
            assert pillar["offset"] == doc.index(pillar["quote"])
            assert pillar["basis"] == reading().FIRST_READING_BASIS


# ---------------------------------------------------------------------------
# The reader meets them
# ---------------------------------------------------------------------------


class TestTheNoteNamesThePillars:
    async def test_the_note_speaks_the_readers_words(self) -> None:
        module = reading()
        result, _ = await _read()
        note = module.first_reading_note(
            SimpleNamespace(defining_moves=result.to_state())
        )
        assert "pilier de la thèse" in note
        # Both quotes are printed, each with its label.
        assert note.count("pilier de la thèse") == 2
        assert _PILLAR_1 in note and _PILLAR_2 in note

    async def test_a_pillar_is_never_presented_as_a_verdict(self) -> None:
        module = reading()
        result, _ = await _read()
        note = module.first_reading_note(
            SimpleNamespace(defining_moves=result.to_state())
        )
        assert "pas un verdict d'instrument" in note


# ---------------------------------------------------------------------------
# The citation rule applies to the pillars like to every other slot
# ---------------------------------------------------------------------------


class TestTheCitationRuleAppliesToThePillars:
    async def test_a_failed_pillar_quote_is_re_anchored_not_lost(self) -> None:
        doc = _document()
        # One word changed: the citation rule refuses it, the anchor floors
        # (8 consecutive words, half the quote) are still cleared.
        altered = _PILLAR_1.replace("convoques", "invites")
        assert altered not in doc
        result = await reading().build_first_reading(
            _state(doc),
            _FakeModel(
                _answer(
                    pillars=[
                        {
                            "kind": "claim",
                            "reading": "un vote emporte",
                            "quote": altered,
                        }
                    ]
                )
            ),
        )
        pillars = [m for m in result.moves if m.slot == "pillar"]
        assert len(pillars) == 1
        move = pillars[0]
        assert move.anchor == reading().ANCHOR_RELOCATED
        # The printed characters are the DOCUMENT's, never the model's.
        assert move.quote != altered
        assert move.quote in doc
        assert move.offset is not None

    async def test_a_pillar_with_no_reading_is_named_not_counted(self) -> None:
        result = await reading().build_first_reading(
            _state(_document()),
            _FakeModel(_answer(pillars=[{"quote": _PILLAR_1}])),
        )
        named = [d for d in result.dropped_slots if d.get("slot") == "pillar"]
        assert named, "the lost pillar must be named"
        assert named[0].get("reason") == "no_reading"
        assert not [m for m in result.moves if m.slot == "pillar"]

    async def test_a_pillar_quote_absent_from_the_document_never_prints_the_models_words(
        self,
    ) -> None:
        invented = (
            "Un passage entierement invente par le modele et qui ne figure "
            "nulle part dans le document analyse par le pipeline."
        )
        result = await reading().build_first_reading(
            _state(_document()),
            _FakeModel(
                _answer(
                    pillars=[
                        {
                            "kind": "claim",
                            "reading": "un pilier invente",
                            "quote": invented,
                        }
                    ]
                )
            ),
        )
        pillars = [m for m in result.moves if m.slot == "pillar"]
        assert len(pillars) == 1
        assert pillars[0].quote != invented
        assert pillars[0].anchor in (
            reading().ANCHOR_UNANCHORED,
            reading().ANCHOR_RELOCATED,
        )


# ---------------------------------------------------------------------------
# One bad character elsewhere does not cost the pillars their slot
# ---------------------------------------------------------------------------


class TestTheSalvageRoutesThePillarsBackToTheirSlot:
    async def test_a_malformed_move_keeps_the_pillars_named(self) -> None:
        answer = _answer()
        # Break ONE object in the moves list (trailing comma), leaving the
        # pillars array intact.
        answer = answer.replace(
            '"moves": [{"kind": "claim", "reading": "un chiffre", "quote": "des chiffres d\'expose"}]',
            '"moves": [{"kind": "claim", "reading": "perdu", "quote": "citation perdue",}]',
        )
        result = await reading().build_first_reading(
            _state(_document()), _FakeModel(answer)
        )
        pillars = [m for m in result.moves if m.slot == "pillar"]
        assert len(pillars) == 2, "the pillars must survive a malformed sibling"
        assert result.malformed_moves >= 1
