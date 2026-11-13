"""#3415 ask 4 — a failed citation no longer costs the thesis.

The paid probe of 2026-11-05 measured it on the longest panel document: the
mechanism survived the citation rule 3/3, the thesis 1/3 — and a thesis whose
citation failed fell WITH its reading, under an anonymous « 1 geste écarté ».
The centre of the document was the one gesture the reader could not afford to
lose, and the record could not even say WHICH gesture it had lost.

Three born-red witnesses, one per face of the repair, plus the byte-identical
control:

1. RELocated — the model inserted a word, so the quote fails the citation
   rule, but the document carries a run of consecutive words long enough and
   covering enough of the quote. The move keeps its reading and takes the
   DOCUMENT's characters as its quote (``anchor="relocated"``): the model's
   words never reach a guillemet.
2. UNANCHORED — a paraphrase the document shares almost nothing with. The
   reading survives (it is what Act II and Act III need), the quote is empty,
   and the note prints no guillemets (``anchor="unanchored"``).
3. NAMED — a slot that produced nothing at all is recorded in
   ``dropped_slots`` with its reason, and the note names it: « thèse centrale :
   aucun geste retenu (lecture vide) » — a fact where the count was anonymous.

The control: a clean reading keeps the pre-#3415 record and note BYTE-IDENTICAL
— measured, not hoped: the fixture was run against the frozen pre-change module
and the working one, and the pinned literals below are that measurement.

Offline: a recording fake model answers the single call, the document is
synthetic with opaque content, nothing depends on the corpus, a key or the
network. No second model call is made anywhere (the anchor is a deterministic
word scan), and ``normalised_quote_in`` is untouched.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

# --- the synthetic document (opaque filler, no corpus content) --------------

_FILLER = (
    "Le contexte developpe un point peripherique : des chiffres d'expose, une "
    "remarque de methode, rien qui porte la demonstration centrale. "
)

_DOC_THESIS = (
    "La reforme protege ses commanditaires plutot que les usagers qui la "
    "financent sans en profiter."
)

_DOC_MECHANISM = (
    "Le mecanisme tient en une phrase : la garantie offerte repose "
    "entierement sur la delegation du risque aux petits porteurs."
)

_LOCAL_1 = "des chiffres d'expose"


def _document() -> str:
    """A document whose thesis and mechanism sit far from its head."""
    head = _FILLER * 40
    middle = _FILLER * 40
    tail = _FILLER * 10
    return f"{head}\n\n{_DOC_THESIS}\n\n{middle}\n\n{_DOC_MECHANISM}\n\n{tail}"


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


def _answer(thesis: object) -> str:
    """One answer differing only in its THESIS entry — the slot under test."""
    return json.dumps(
        {
            "thesis": thesis,
            "mechanism": {
                "reading": "le risque est delegue aux petits porteurs",
                "quote": _DOC_MECHANISM,
            },
            "moves": [
                {"kind": "claim", "reading": "un chiffre", "quote": _LOCAL_1},
            ],
        },
        ensure_ascii=False,
    )


def _clean_thesis() -> dict:
    return {
        "reading": "la reforme protege ses commanditaires",
        "quote": _DOC_THESIS,
    }


def _inserted_word_thesis() -> dict:
    """The model copied the span and INSERTED one word: the citation rule
    refuses the quote (it is not a substring), while the document still
    carries a 10-word run of it — the anchor's exact case."""
    return {
        "reading": "la reforme protege ses commanditaires",
        "quote": _DOC_THESIS.replace("commanditaires ", "commanditaires vraiment "),
    }


def _paraphrased_thesis() -> dict:
    """A paraphrase sharing (almost) no word run with the document."""
    return {
        "reading": "le texte soutient que la loi avantage ses auteurs",
        "quote": "ce texte soutient que la loi avantage ceux qui l'ecrivent et leurs amis",
    }


async def _build(answer: str):
    module = reading()
    return await module.build_first_reading(_state(_document()), _FakeModel(answer))


def _slots(result) -> dict:
    return {move.slot: move for move in result.moves if move.slot}


# ---------------------------------------------------------------------------
# Witness 1 — the failed citation relocates on the document's own words
# ---------------------------------------------------------------------------


class TestAFailedCitationRelocatesOnTheDocument:
    async def test_the_thesis_keeps_its_reading_with_the_documents_words(self) -> None:
        module = reading()
        doc = _document()
        result = await _build(_answer(_inserted_word_thesis()))
        assert result.status == "ok"
        slots = _slots(result)
        # The thesis SURVIVED — on the frozen tree this dict has no "thesis".
        thesis = slots["thesis"]
        assert thesis.kind == "thesis"
        assert thesis.anchor == module.ANCHOR_RELOCATED
        # The anchor took the LONGEST shared run (10 words), and the inserted
        # word — the model's own — is gone from what the record quotes.
        assert (
            thesis.quote == "plutot que les usagers qui la financent sans en profiter."
        )
        assert "vraiment" not in thesis.quote
        # The quote is the DOCUMENT's characters, at its own offset: the span
        # re-reads from the text it claims to come from.
        assert thesis.offset is not None
        assert doc[thesis.offset : thesis.offset + len(thesis.quote)] == thesis.quote
        # ... and the citation rule accepts it as given — the anchor returns
        # passages, not approximations, so nothing here relaxed the rule.
        assert module.first_reading.quote_occurs_in(doc, thesis.quote)
        # A slot recovered is not a slot dropped.
        assert result.dropped_quotes == 0
        assert "dropped_slots" not in result.to_state()

    def test_the_scan_refuses_an_overlap_below_the_declared_floors(self) -> None:
        """The two floors are declared, and a short shared run anchors
        nothing: 4 shared words under an 8-word floor is a coincidence of
        vocabulary, and the passage it would point at is not the model's."""
        module = reading()
        doc = "la reforme protege ses commanditaires vraiment ailleurs."
        # 4 consecutive shared words ("la reforme protege ses" is 4) — the
        # quote also shares "commanditaires" after the insert.
        quote = "la reforme protege ses enormes commanditaires"
        assert module.anchor_quote_in(doc, quote) is None

    def test_the_scan_finds_the_longest_run_above_the_floors(self) -> None:
        """A 12-word quote whose last 11 words the document carries: the run
        clears both floors (8 words, 6 = half of 12), and the passage is the
        document's own characters at their own offset."""
        module = reading()
        doc = (
            "debut la reforme protege ses commanditaires plutot que les "
            "usagers sans detour vraiment fin."
        )
        quote = (
            "enormes la reforme protege ses commanditaires plutot que les "
            "usagers sans detour"
        )
        anchored = module.anchor_quote_in(doc, quote)
        assert anchored is not None
        passage, start = anchored
        assert passage == (
            "la reforme protege ses commanditaires plutot que les usagers sans detour"
        )
        assert doc[start : start + len(passage)] == passage


# ---------------------------------------------------------------------------
# Witness 2 — the paraphrase keeps the reading, loses the guillemets
# ---------------------------------------------------------------------------


class TestAParaphrasedThesisKeepsItsReading:
    async def test_the_reading_survives_without_the_models_words(self) -> None:
        module = reading()
        result = await _build(_answer(_paraphrased_thesis()))
        assert result.status == "ok"
        slots = _slots(result)
        thesis = slots["thesis"]
        assert thesis.anchor == module.ANCHOR_UNANCHORED
        assert thesis.reading == "le texte soutient que la loi avantage ses auteurs"
        assert thesis.quote == ""
        assert thesis.offset is None
        assert result.dropped_quotes == 0

    async def test_the_record_carries_the_anchor_state(self) -> None:
        result = await _build(_answer(_paraphrased_thesis()))
        payload = result.to_state()
        assert payload["moves"][0] == {
            "kind": "thesis",
            "reading": "le texte soutient que la loi avantage ses auteurs",
            "quote": "",
            "offset": None,
            "basis": "first_reading",
            "slot": "thesis",
            "anchor": "unanchored",
        }

    async def test_the_note_prints_no_guillemets_over_the_models_words(self) -> None:
        module = reading()
        payload = (await _build(_answer(_paraphrased_thesis()))).to_state()
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        thesis_line = next(
            line for line in note.splitlines() if "thèse centrale" in line
        )
        # The reading reaches the writer — that is the point of #3395 — but
        # nothing between « » does: the model's words are not the document's.
        assert "le texte soutient que la loi avantage ses auteurs" in thesis_line
        assert "«" not in thesis_line and "»" not in thesis_line
        assert "citation non ancrée" in thesis_line

    async def test_the_unanchored_thesis_still_reaches_act_ii(self) -> None:
        module = reading()
        payload = (await _build(_answer(_paraphrased_thesis()))).to_state()
        state = SimpleNamespace(defining_moves=payload)
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "le texte soutient que la loi avantage ses auteurs" in prompt
        assert "citation non ancrée" in prompt


# ---------------------------------------------------------------------------
# Witness 3 — the lost slot is named, with its reason
# ---------------------------------------------------------------------------


class TestTheLostSlotIsNamed:
    async def test_a_slot_with_no_reading_is_named(self) -> None:
        module = reading()
        payload = (
            await _build(_answer({"reading": "", "quote": _DOC_THESIS}))
        ).to_state()
        assert payload["dropped_slots"] == [{"slot": "thesis", "reason": "no_reading"}]
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        assert "thèse centrale : aucun geste retenu (lecture vide)" in note

    async def test_a_slot_that_is_not_an_object_is_named(self) -> None:
        module = reading()
        payload = (await _build(_answer("une phrase, pas un objet"))).to_state()
        assert payload["dropped_slots"] == [
            {"slot": "thesis", "reason": "not_an_object"}
        ]
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        assert "thèse centrale : aucun geste retenu (réponse illisible)" in note

    async def test_the_mechanism_is_named_the_same_way(self) -> None:
        """Both slots are named — the mechanism is not a second-class slot."""
        module = reading()
        answer = json.dumps(
            {
                "thesis": _clean_thesis(),
                "mechanism": {"reading": "", "quote": _DOC_MECHANISM},
                "moves": [
                    {"kind": "claim", "reading": "un chiffre", "quote": _LOCAL_1},
                ],
            },
            ensure_ascii=False,
        )
        payload = (await _build(answer)).to_state()
        assert payload["dropped_slots"] == [
            {"slot": "mechanism", "reason": "no_reading"}
        ]
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        assert "mécanisme : aucun geste retenu (lecture vide)" in note


# ---------------------------------------------------------------------------
# The control — a clean reading keeps the pre-#3415 shape, byte-identical
# ---------------------------------------------------------------------------

#: The measured record of a clean reading (every quote verbatim). The fixture
#: was run against the FROZEN pre-ask-4 module and the working one: both
#: produce exactly this payload — the anchor leaves the ordinary path alone.
#: #3511(b) — this document carries two bare stretches, so the second pass
#: runs and records itself (the record is intended state, not drift: the
#: echoed quotes land outside their stretch and are counted, none kept —
#: the three moves are byte-identical).
_CONTROL_RECORD = {
    "moves": [
        {
            "kind": "thesis",
            "reading": "la reforme protege ses commanditaires",
            "quote": _DOC_THESIS,
            "offset": 5442,
            "basis": "first_reading",
            "slot": "thesis",
        },
        {
            "kind": "device",
            "reading": "le risque est delegue aux petits porteurs",
            "quote": _DOC_MECHANISM,
            "offset": 10981,
            "basis": "first_reading",
            "slot": "mechanism",
        },
        {
            "kind": "claim",
            "reading": "un chiffre",
            "quote": _LOCAL_1,
            "offset": 46,
            "basis": "first_reading",
        },
    ],
    "dropped_quotes": 0,
    "status": "ok",
    "read_scope": {
        "offset": 0,
        "window": 12465,
        "status": "selected",
        "text_length": 12465,
        "whole_document": True,
    },
    "basis": "first_reading",
    "second_pass": {
        "gap": 3116,
        "call_bound": 2,
        "stretches": [
            {"offset": 5537, "length": 5444, "read": True},
            {"offset": 67, "length": 5375, "read": True},
        ],
        "calls": 2,
        "moves_kept": 0,
        "dropped_quotes": 2,
        "malformed": 0,
        "failed_calls": 0,
    },
}

_CONTROL_NOTE = (
    "LECTURE PREMIÈRE — un seul lecteur, sur le texte entier, avant les "
    "instruments. Ce sont des GESTES DU TEXTE, pas un verdict d'instrument : "
    "ne les présente jamais comme un sophisme ni comme une note.\n"
    "  Portée : document entier lu une fois.\n"
    # #3431 — the order is stated (the record beneath stores the slots
    # first) and the position prints in the reader's terms, never as the
    # raw character offset this control carried before.
    "  Ordre : celui du document, du premier geste au dernier.\n"
    "  - affirmation : un chiffre — « des chiffres d'expose », "
    "vers le début du texte (0 %)\n"
    "  - thèse centrale : la reforme protege ses commanditaires — "
    f"« {_DOC_THESIS} », vers le milieu du texte (44 %)\n"
    "  - mécanisme : le risque est delegue aux petits porteurs — "
    f"« {_DOC_MECHANISM} », vers la fin du texte (88 %)\n"
    # #3511(b) — the pass that read the bare stretches states itself; the
    # bound (2) did not bite (both stretches read).
    "  Passe seconde : 2 tranche(s) relue(s) après la lecture d'ensemble."
)


class TestTheCleanReadingIsByteIdentical:
    async def test_the_state_and_the_note_are_unchanged(self) -> None:
        module = reading()
        result = await _build(_answer(_clean_thesis()))
        assert result.status == "ok"
        payload = result.to_state()
        # Measured identical on the frozen tree: no anchor key, no
        # dropped_slots key, same counts, same offsets, same order.
        assert payload == _CONTROL_RECORD
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        assert note == _CONTROL_NOTE

    async def test_no_anchor_token_appears_on_the_clean_path(self) -> None:
        """The control's other face: not even a word of the new vocabulary
        reaches the note when every quote passed the rule as given."""
        module = reading()
        payload = (await _build(_answer(_clean_thesis()))).to_state()
        note = module.first_reading_note(SimpleNamespace(defining_moves=payload))
        for token in ("réancrée", "citation non ancrée", "aucun geste retenu"):
            assert token not in note
