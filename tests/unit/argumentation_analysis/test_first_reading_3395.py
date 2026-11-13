"""#3395 — witnesses: the first reading, its consumers, and its labels.

The v1 panel's M1 gap: on 8 of 10 documents the same-model zero-shot carries
the document's defining move and no line of the render does. The pipeline's
answer is a PRODUCER — one whole-document read that writes the moves, with
verified verbatim quotes — and two production consumers: the per-argument unit
selection (the units overlapping a move are examined first) and the writers
(the moves are carried, or their absence is stated).

Every test here is offline: a recording fake model answers the single call, and
the documents are synthetic, so nothing depends on the corpus, a key, or the
network.

Born-red discipline: the symbols this issue CREATES are imported INSIDE the test
that measures them, so a run on the pre-fix tree reports each witness's own
failure (an absent module, an unknown keyword, a missing line) instead of one
collection error that would prove nothing.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    select_for_budget,
)

# A synthetic document whose moves are spaced far enough apart that a quote is
# unambiguous, and whose sentences carry the punctuation the window selector
# looks for (a real document, not a blob).
DOC = (
    "Le rapport commence par une concession : la mesure a coûté cher à la "
    "région. Puis il affirme que l'effort en valait la peine, sur la foi d'un "
    "chiffre unique. Enfin il interpelle l'auditoire et l'invite à choisir "
    "son camp."
)
CONCESSION = "la mesure a coûté cher à la région"
CLAIM = "l'effort en valait la peine"
DEVICE = "l'invite à choisir son camp"


def reading():
    """The module under test, imported late on purpose (see the docstring)."""
    from argumentation_analysis.agents.core import reading as module

    return module


def _state(text: str = DOC) -> SimpleNamespace:
    """A state carrying the text — the producer's only requirement."""
    return SimpleNamespace(raw_text=text)


class _FakeModel:
    """Answers once, records the prompt, so the call itself is measurable."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def _answer(*moves: tuple[str, str, str]) -> str:
    return json.dumps(
        {
            "moves": [
                {"kind": kind, "reading": reading_text, "quote": quote}
                for kind, reading_text, quote in moves
            ]
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# 1. One call, on the whole document when it fits.
# ---------------------------------------------------------------------------


async def test_the_whole_document_is_read_in_one_call():
    """THE witness: one call, the document whole, and the scope says so.

    Before the fix there was no such call at all — the render's only whole-text
    knowledge came from the zero-shot arm outside the pipeline.
    """
    model = _FakeModel(_answer(("concession", "Il concède le coût.", CONCESSION)))
    result = await reading().build_first_reading(_state(), model)

    assert len(model.prompts) == 1, "the first reading is ONE call"
    assert CONCESSION in model.prompts[0], "the prompt carries the document"
    assert result.status == "ok"
    assert result.read_scope["whole_document"] is True
    assert result.read_scope["offset"] == 0


async def test_a_document_past_thirty_thousand_characters_is_read_whole():
    """R1142 — the bound is the zero-shot arm's own cut: NO cut (#2841 rule 4).

    30 000 left four panel documents unread (47 644 to 179 139 characters) —
    exactly the long documents where M1 is worst. The first reading reads
    what the comparison reads: the whole text reaches the prompt and the
    scope says so. A document past the model's context fails loud
    (``llm_error``, persisted by the writer) rather than reading a window
    the comparison cannot use.
    """
    long_doc = DOC * 400
    assert len(long_doc) > 30000, "the witness must be past the old bound"
    model = _FakeModel(_answer(("thesis", "Il pose sa thèse.", CONCESSION)))
    result = await reading().build_first_reading(_state(long_doc), model)

    # #3511(b) — the whole read is ONE call; later calls, when there are
    # any, are the second pass reading BARE STRETCHES — strict substrings,
    # never the whole document again.
    assert long_doc in model.prompts[0], "the WHOLE text reaches the prompt"
    assert all(long_doc not in p for p in model.prompts[1:])
    assert result.read_scope["whole_document"] is True
    assert result.read_scope["window"] == len(long_doc)


# ---------------------------------------------------------------------------
# 1b. The seam the witnesses above double: a REAL production state (R1143).
# ---------------------------------------------------------------------------


async def test_a_real_state_is_read_whole_and_its_window_is_recorded(monkeypatch):
    """R1143 — every spectacular run of cycle 1 failed this phase on
    « 'UnifiedAnalysisState' object is not callable »: the no-cut branch
    called the state as if it were its recorder. The witnesses above pass a
    bare namespace, which never reached that call. This one goes through the
    production surface — the invoke callable, a ``UnifiedAnalysisState``, the
    writer — with only the model faked.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.orchestration import invoke_callables
    from argumentation_analysis.orchestration.state_writers import (
        _write_first_reading_to_state,
    )

    long_doc = DOC * 400
    state = UnifiedAnalysisState(long_doc)
    model = _FakeModel(_answer(("concession", "Il concède le coût.", CONCESSION)))
    monkeypatch.setattr(
        invoke_callables,
        "_build_persona_callable",
        # #3511 — the site passes the reading's own completion cap; the stub
        # accepts the production signature and ignores it.
        lambda name, **kwargs: (model, None),
    )

    payload = await invoke_callables._invoke_first_reading(
        long_doc, {"_state_object": state}
    )
    _write_first_reading_to_state(payload, state, {})

    # R1167 — pinned to the measured count, not a floor: the whole-document
    # draw plus the ONE bare stretch this document leaves (the fake model
    # answers the same payload for both calls; the stretch's CONCESSION is
    # the document's second occurrence, a different passage).
    assert len(model.prompts) == 2, "the model is called"
    assert long_doc in model.prompts[0], "the WHOLE text reaches the prompt"
    # #3511(b) — after the whole read, only bare stretches are re-read.
    assert all(long_doc not in p for p in model.prompts[1:])
    record = state.defining_moves
    assert record["status"] == "ok", record
    assert record["read_scope"]["whole_document"] is True
    # One move per PASSAGE (R1167 finding 2): the same words occur at 41 and
    # at 262 — two passages, two moves, the second marked with its pass.
    assert [(m["quote"], m.get("pass", "")) for m in record["moves"]] == [
        (CONCESSION, ""),
        (CONCESSION, "second"),
    ]
    assert len({m["offset"] for m in record["moves"]}) == 2
    # R1167 finding 1 (the blocking one), through the writer this test
    # already exercises: the second pass's record REACHES the state — the
    # writer is the only path from the phase output into defining_moves —
    # and the note, which reads the state, prints the line.
    assert record["second_pass"]["calls"] == 1
    assert record["second_pass"]["moves_kept"] == 1
    from argumentation_analysis.agents.core.reading import first_reading_note

    assert "Passe seconde : 1 tranche(s) relue(s)" in first_reading_note(state)
    window = state.reading_window_status["first_reading"]
    assert window["offset"] == 0
    assert window["window"] == len(long_doc), "the recorded window is the text"


async def test_no_model_is_an_honest_empty_read():
    result = await reading().build_first_reading(_state(), None)
    assert result.status == "no_llm"
    assert result.moves == []


async def test_an_unparseable_answer_is_a_parse_error_not_an_empty_finding():
    result = await reading().build_first_reading(_state(), _FakeModel("je ne sais pas"))
    assert result.status == "parse_error"
    assert result.error


# ---------------------------------------------------------------------------
# 2. The quote is checked against the text; a failure is counted, never kept.
# ---------------------------------------------------------------------------


async def test_a_quote_the_document_does_not_carry_is_dropped_and_counted():
    """THE witness of the verification: a move whose quote the document does
    not carry is dropped, and the count travels — a silently discarded move is
    the defect this producer repairs."""
    model = _FakeModel(
        _answer(
            ("concession", "Il concède le coût.", CONCESSION),
            ("thesis", "Il défend la réforme.", "la réforme transformera tout"),
            ("threat", "Il menace.", "loi"),  # under the citation floor
        )
    )
    result = await reading().build_first_reading(_state(), model)

    assert [m.quote for m in result.moves] == [CONCESSION]
    assert (
        result.dropped_quotes == 2
    ), "the invented quote and the two-word keyword are both counted"


async def test_a_move_carries_the_position_of_its_quote():
    model = _FakeModel(_answer(("claim", "Il affirme le résultat.", CLAIM)))
    result = await reading().build_first_reading(_state(), model)

    assert result.moves[0].offset == DOC.index(CLAIM)


async def test_the_same_quote_named_twice_is_one_move():
    model = _FakeModel(
        _answer(
            ("concession", "Il concède le coût.", CONCESSION),
            ("concession", "Il le redit.", CONCESSION),
        )
    )
    result = await reading().build_first_reading(_state(), model)

    assert len(result.moves) == 1
    assert result.dropped_quotes == 1


async def test_the_moves_are_bounded():
    # #3511 (R1164) — the bound the parse enforces is the INVENTORY (80,
    # the probe's own measure), no longer the render cap: the record keeps
    # what the model was told it may name, the note chooses what it shows.
    from argumentation_analysis.core.reading_window import inventory_budget

    doc = " ".join(
        f"Phrase numéro {i} du document, avec ses virgules." for i in range(90)
    )
    assert inventory_budget(len(doc)) == 80
    moves = [
        ("claim", f"Lecture {i}.", f"Phrase numéro {i} du document") for i in range(85)
    ]
    result = await reading().build_first_reading(
        _state(doc), _FakeModel(_answer(*moves))
    )

    assert len(result.moves) == 80


# ---------------------------------------------------------------------------
# 3. The kind vocabulary is closed, and absence is stated as absence.
# ---------------------------------------------------------------------------


def test_the_kind_vocabulary_is_closed():
    kind = reading().move_kind
    assert kind("THESIS") == "thesis"
    assert kind("thèse") == "thesis"  # the model answers in French
    assert kind("procédé central") == "device"
    assert kind("") == "other"
    assert kind("quelque chose") == "other"
    assert kind(None) == "other"


# ---------------------------------------------------------------------------
# 4. The record: the state carries the moves, labelled.
# ---------------------------------------------------------------------------


async def test_the_state_carries_the_moves_and_their_label():
    from argumentation_analysis.orchestration.state_writers import (
        _write_first_reading_to_state,
    )

    model = _FakeModel(
        _answer(
            ("concession", "Il concède le coût.", CONCESSION),
            ("device", "Il invite à choisir un camp.", DEVICE),
        )
    )
    result = await reading().build_first_reading(_state(), model)

    # Every production state carries the field (``UnifiedAnalysisState``
    # initialises it); the writer fills it rather than creating it, like its
    # two sibling persona writers (#3377).
    state = SimpleNamespace(defining_moves={})
    _write_first_reading_to_state(result.to_state(), state, {})

    record = state.defining_moves
    assert record["basis"] == reading().FIRST_READING_BASIS
    assert record["status"] == "ok"
    assert [m["quote"] for m in record["moves"]] == [CONCESSION, DEVICE]
    assert record["read_scope"]["whole_document"] is True


def test_the_spans_come_from_the_positioned_moves_only():
    state = SimpleNamespace(
        defining_moves={
            "moves": [
                {"kind": "thesis", "reading": "r", "quote": "abcdefgh", "offset": 10},
                {"kind": "claim", "reading": "r", "quote": "abcdefgh", "offset": None},
            ],
            "status": "ok",
        }
    )
    assert reading().defining_move_spans(state) == [(10, 18)]
    assert len(reading().defining_moves(state)) == 2, "an unpositioned move is read"


def test_a_failed_reading_reaches_the_state_through_the_writer():
    """R1142 — the failure branch must REACH the state. The writer used to
    skip every error-carrying payload, so a read that ran and failed left the
    ``no_llm`` default and the note's « lecture en échec » branch never fired
    in production. Same father as the two #3377 persona writers."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_first_reading_to_state,
    )

    failed = reading().FirstReading(status="llm_error", error="TimeoutError: 30s")
    state = SimpleNamespace(defining_moves={"status": "no_llm"})
    _write_first_reading_to_state(failed.to_state(), state, {})

    assert state.defining_moves["status"] == "llm_error", "the failure is persisted"
    assert state.defining_moves["error"] == "TimeoutError: 30s"


def test_a_payload_that_is_not_a_dict_is_still_skipped():
    """The control of the R1142 rewrite: only a payload that carries nothing
    persistable (not a dict) leaves the state's default alone."""
    from argumentation_analysis.orchestration.state_writers import (
        _write_first_reading_to_state,
    )

    state = SimpleNamespace(defining_moves={"status": "no_llm"})
    _write_first_reading_to_state("boom", state, {})

    assert state.defining_moves == {"status": "no_llm"}


# ---------------------------------------------------------------------------
# 5. Consumer A — the per-argument selection prefers the units that matter.
# ---------------------------------------------------------------------------


def _units(count: int = 40, step: int = 1000) -> list[SelectableUnit]:
    return [
        SelectableUnit(unit_id=f"u{i}", text=f"unité {i}", offset=i * step)
        for i in range(count)
    ]


def test_the_selection_is_untouched_without_a_first_reading():
    """The control: no spans → the stratified pass, byte-identical, and the
    count says zero rather than guessing one."""
    units = _units()
    base = select_for_budget(units, 10, text_length=40000)
    same = select_for_budget(units, 10, text_length=40000, priority_spans=None)

    assert [u.unit_id for u in same.selected] == [u.unit_id for u in base.selected]
    assert base.priority_taken == 0
    assert same.priority_taken == 0


def test_a_unit_that_overlaps_a_move_is_examined_first():
    """THE consumer witness: take a unit the stratified pass did NOT select,
    declare it covered by a move, and it must enter the ten."""
    units = _units()
    base = select_for_budget(units, 10, text_length=40000)
    selected_ids = {u.unit_id for u in base.selected}
    missing = next(u for u in reversed(units) if u.unit_id not in selected_ids)
    assert missing.unit_id not in selected_ids, "the witness must start absent"

    got = select_for_budget(
        units,
        10,
        text_length=40000,
        priority_spans=[(missing.offset - 5, missing.offset + 5)],
    )

    assert missing.unit_id in {u.unit_id for u in got.selected}
    assert got.k == base.k == 10, "the budget is unchanged"
    # R1142 — 2, not 1: a span built at a unit's seam (start ± 5) catches
    # the unit itself (its point lies inside) AND the passage opener (the
    # nearest start at or before the span's start — here the unit 1 000
    # characters earlier). Two clauses of the overlap rule, both legitimate
    # on this synthetic span.
    assert got.priority_taken == 2
    assert len(got.selected) == len(base.selected)


def test_two_moves_keep_both_their_units():
    units = _units()
    base = select_for_budget(units, 10, text_length=40000)
    selected_ids = {u.unit_id for u in base.selected}
    missing = [u for u in reversed(units) if u.unit_id not in selected_ids][:2]

    got = select_for_budget(
        units,
        10,
        text_length=40000,
        priority_spans=[(u.offset - 5, u.offset + 5) for u in missing],
    )

    got_ids = {u.unit_id for u in got.selected}
    assert {u.unit_id for u in missing} <= got_ids
    # R1142 — 3, not 2: the two seam spans catch their two units plus one
    # passage opener (the nearest-start clause, see the single-span witness).
    assert got.priority_taken == 3


def test_a_unit_whose_passage_contains_the_quote_is_examined_first():
    """R1142 — the coordinator's witness: a unit whose KNOWN extent (its
    ``source_quote``) contains the move's quote. The unit starts BEFORE the
    quote, so the old "the unit's start falls inside the quote" test never
    preferred it — and on the cycle-0 states only 18-40 % of quotes contain
    a unit start, which left consumer A inert on four moves out of five on
    the long documents."""
    units = _units()
    base = select_for_budget(units, 10, text_length=40000)
    selected_ids = {u.unit_id for u in base.selected}
    missing = next(u for u in reversed(units) if u.unit_id not in selected_ids)

    containing = replace(missing, source_quote="p" * 300)
    units = [containing if u.unit_id == missing.unit_id else u for u in units]
    # The move's quote lies strictly INSIDE the unit's passage.
    got = select_for_budget(
        units,
        10,
        text_length=40000,
        priority_spans=[(missing.offset + 50, missing.offset + 100)],
    )

    assert missing.unit_id in {u.unit_id for u in got.selected}
    assert got.priority_taken == 1


def test_the_nearest_unit_before_the_quote_is_the_passage():
    """R1142 — extent UNKNOWN (the median ``source_quote`` length is 0 on
    half the panel documents): the named rule prefers the unit whose start is
    the NEAREST at or before the quote's start — the passage the quote lies
    in — and not an earlier unit that merely precedes it."""
    units = _units()
    base = select_for_budget(units, 10, text_length=40000)
    selected_ids = {u.unit_id for u in base.selected}
    absent = [u for u in reversed(units) if u.unit_id not in selected_ids][:2]
    nearest, earlier = absent[0], absent[1]  # descending offsets

    got = select_for_budget(
        units,
        10,
        text_length=40000,
        priority_spans=[(nearest.offset + 500, nearest.offset + 600)],
    )
    got_ids = {u.unit_id for u in got.selected}

    assert nearest.unit_id in got_ids, "the passage the quote lies in is preferred"
    assert earlier.unit_id not in got_ids, "an earlier start does not own the passage"


def test_a_budget_that_holds_everything_counts_its_moves():
    units = _units(count=5)
    got = select_for_budget(units, 10, text_length=5000, priority_spans=[(2995, 3005)])
    # R1142 — 2, not 1: the unit at 3 000 (its point lies in the span) and
    # the unit at 2 000 (the nearest start at or before the span's start —
    # the passage the quote lies in).
    assert got.priority_taken == 2
    assert got.k == 5


def test_the_selection_stays_in_text_order():
    units = _units()
    got = select_for_budget(units, 10, text_length=40000, priority_spans=[(3995, 4005)])
    offsets = [u.offset for u in got.selected]
    assert offsets == sorted(offsets)


# ---------------------------------------------------------------------------
# 6. Consumer B — the writers carry the moves, or state their absence.
# ---------------------------------------------------------------------------


def _state_with_moves(moves: list[dict], status: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(
        defining_moves={
            "moves": moves,
            "dropped_quotes": 1,
            "status": status,
            "error": "",
            "read_scope": {
                "offset": 0,
                "window": 30000,
                "status": "short_input",
                "text_length": len(DOC),
                "whole_document": status == "ok",
            },
            "basis": "first_reading",
        }
    )


def test_the_note_labels_the_moves_as_a_first_reading():
    state = _state_with_moves(
        [
            {
                "kind": "concession",
                "reading": "Il concède le coût.",
                "quote": CONCESSION,
                "offset": DOC.index(CONCESSION),
                "basis": "first_reading",
            }
        ]
    )
    note = reading().first_reading_note(state)

    assert "LECTURE PREMIÈRE" in note
    assert "document entier lu une fois" in note
    assert CONCESSION in note
    assert "pas un verdict" in note
    assert "1 geste(s) écarté(s)" in note


def test_a_missing_reading_is_stated_as_missing():
    absent = reading().first_reading_note(_state_with_moves([], status="no_llm"))
    assert "non enregistrée" in absent

    empty = reading().first_reading_note(_state_with_moves([], status="ok"))
    assert "aucun geste" in empty


def test_the_ok_note_without_moves_follows_the_scope():
    """R1142 — « lu en entier » is a measured claim: when
    ``read_scope.whole_document`` is False, the ok-without-moves note states
    the window it read, never a whole reading it did not do."""
    state = SimpleNamespace(
        defining_moves={
            "moves": [],
            "dropped_quotes": 0,
            "status": "ok",
            "error": "",
            "read_scope": {
                "offset": 1200,
                "window": 3000,
                "status": "selected",
                "text_length": 9000,
                "whole_document": False,
            },
            "basis": "first_reading",
        }
    )
    note = reading().first_reading_note(state)

    assert "lu en entier" not in note
    assert "3000" in note and "1200" in note, "the note states the window it read"


def test_the_note_prints_the_kind_in_french():
    """R1142 — the note is French prose (#3393, the reader's vocabulary): the
    kind prints as its French label, while the STATE keeps the English key of
    the closed vocabulary (the export boundary and the tests read the key)."""
    state = _state_with_moves(
        [
            {
                "kind": "thesis",
                "reading": "Il pose sa thèse.",
                "quote": CLAIM,
                "offset": DOC.index(CLAIM),
                "basis": "first_reading",
            }
        ]
    )
    note = reading().first_reading_note(state)

    assert "thèse" in note
    assert "- thesis" not in note
    assert (
        state.defining_moves["moves"][0]["kind"] == "thesis"
    ), "the state keeps the English key"


def test_the_synthesis_briefing_carries_the_moves():
    """The writer's consumer: the moves reach the synthesis as their own
    labelled section, quote included — not as a bare flag."""
    state = _state_with_moves(
        [
            {
                "kind": "concession",
                "reading": "Il concède le coût.",
                "quote": CONCESSION,
                "offset": DOC.index(CONCESSION),
                "basis": "first_reading",
            }
        ]
    )
    briefing = DeepSynthesisAgent.build_artifact_briefing(state)

    assert "[artifact:defining_moves.0]" in briefing
    assert CONCESSION in briefing
    assert "LECTURE PREMIÈRE" in briefing


def test_the_synthesis_briefing_states_an_absent_reading():
    state = _state_with_moves([], status="no_llm")
    briefing = DeepSynthesisAgent.build_artifact_briefing(state)

    assert "[artifact:defining_moves.status]" in briefing
    assert "non enregistrée" in briefing


# ---------------------------------------------------------------------------
# 7. The export boundary drops the wording, keeps the record.
# ---------------------------------------------------------------------------


def test_the_export_boundary_drops_the_moves_wording():
    from argumentation_analysis.evaluation.sanitize_state import sanitize_state

    payload = {
        "raw_text": "le document entier ici",
        "defining_moves": _state_with_moves(
            [
                {
                    "kind": "concession",
                    "reading": "Il concède le coût.",
                    "quote": CONCESSION,
                    "offset": DOC.index(CONCESSION),
                    "basis": "first_reading",
                }
            ]
        ).defining_moves,
    }
    dumped = json.dumps(sanitize_state(payload), ensure_ascii=False)

    assert CONCESSION not in dumped, "a verbatim span never crosses the boundary"
    # The boundary keeps the RECORD (the same counts-only summary the two
    # persona reads get, #3377): how many moves, never what they said.
    assert '"moves_count": 1' in dumped


# ---------------------------------------------------------------------------
# 8. The wiring: a production phase, and the dependency that orders its reader.
# ---------------------------------------------------------------------------


def test_the_standard_workflow_declares_the_producer_and_its_reader():
    """#1842's demand rule: a capability with no production phase is silence.
    The first reading must be a phase, and the per-argument pass must declare
    that it reads what that phase writes."""
    from argumentation_analysis.orchestration.workflows import build_standard_workflow

    workflow = build_standard_workflow()
    phases = {phase.name: phase for phase in workflow.phases}

    assert "first_reading" in phases
    assert phases["first_reading"].capability == "first_reading"
    assert "first_reading" in phases["hierarchical_fallacy"].depends_on


def test_the_spectacular_workflow_declares_the_producer_and_its_reader():
    """R1142 — the panel runs SPECTACULAR (``run_corpus_batch.py``'s default,
    and every cycle-0 fiche says so): a producer wired only into standard
    measures nothing there. Worse, every spectacular state carries the field,
    so without the phase the synthesis briefing would print the ``no_llm``
    absence note — the exact inverse of the M1 gap this producer repairs."""
    from argumentation_analysis.orchestration.workflows import (
        build_spectacular_workflow,
    )

    phases = {phase.name: phase for phase in build_spectacular_workflow().phases}

    assert "first_reading" in phases
    assert phases["first_reading"].capability == "first_reading"
    assert "first_reading" in phases["hierarchical_fallacy"].depends_on
