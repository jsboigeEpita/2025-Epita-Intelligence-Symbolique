"""#3511 — the first reading's inventory scales, every named move is
examined, the note stays a page.

Born-red witnesses for the dispatch's asks:

* **The inventory bound** — ``inventory_budget(L)``: 2 per capacity-chunk,
  floored at the render cap (12), ceilinged at 30. The PROMPT states the
  computed bound and the parse enforces the bound it stated — never the
  render cap (#3511's core split: ``MAX_MOVES`` is what the NOTE shows).
* **Every named move reaches the examined set** — the selector buys
  ``max(k(L), named)`` (``examined_unit_budget``) and records the residue
  (« nommé, non examiné » with its reason), never a silent truncation.
  The chain witnesses run parse → state → selector on synthetic documents,
  so BOTH mutations redden them: restoring the flat ``MAX_MOVES`` on the
  inventory (long document: 18 named fall to 12), and reverting the budget
  to k(L) alone (floor band: 12 named, 10 bought, 2 unexamined with a
  ``budget`` reason).
* **The note stays a page** — at most 12 move lines; over the cap the page
  is chosen (slots, then what the examination reached, then a spread) and
  the count line « N gestes nommés, M montrés ici » says what is hidden.

Synthetic documents only: markers and filler, no corpus content (privacy —
a fixture is a tracked file).
"""

import json

from argumentation_analysis.agents.core.reading.first_reading import (
    MAX_MOVES,
    build_first_reading,
    build_first_reading_prompt,
    examined_unit_budget,
    first_reading_note,
)
from argumentation_analysis.core.reading_window import (
    INVENTORY_CEILING,
    INVENTORY_FLOOR,
    PER_ARGUMENT_CEILING,
    WHOLE_TEXT_CALL_CAPACITY,
    inventory_budget,
    per_argument_unit_budget,
)

# --- the fixtures: synthetic long documents, no corpus content ---------------


def _synth_document(parts: int, part_len: int = 5300) -> str:
    """A synthetic document: one unique marker per part, filler around it.

    ``parts * part_len`` characters, marker ``marqueur-numero-XX`` at each
    part's head — quotes the citation rule can verify at known offsets.
    """
    filler = "la phrase continue sans rien affirmer de neuf par ici. " * 400
    chunks = []
    for i in range(parts):
        marker = f"marqueur-numero-{i:02d}"
        chunk = f"{marker} {filler}"
        chunks.append(chunk[:part_len].ljust(part_len))
    return "".join(chunks)


def _fake_llm_answer(n_moves: int, text: str) -> str:
    """A clean JSON answer: thesis, mechanism, and ``n_moves`` local moves.

    The two slots quote markers 00 and 01; the local moves quote markers
    02… so no quote collides with a slot (dedup would eat the collision —
    the counts must measure the BOUND, not the dedup).
    """
    assert 2 + n_moves <= 100
    moves = []
    for i in range(n_moves):
        quote = f"marqueur-numero-{i + 2:02d}"
        assert quote in text
        moves.append({"kind": "claim", "reading": f"geste numero {i}", "quote": quote})
    return json.dumps(
        {
            "thesis": {
                "reading": "la these centrale du document synthetique",
                "quote": "marqueur-numero-00",
            },
            "mechanism": {
                "reading": "le mecanisme qui la porte",
                "quote": "marqueur-numero-01",
            },
            "pillars": [],
            "moves": moves,
        }
    )


def _fake_llm(answer: str):
    async def _call(prompt: str) -> str:
        return answer

    return _call


class _CoverageState:
    """A duck-typed state: raw text, population, provenance, coverage book.

    The same ``record_analysis_coverage`` contract the real state carries
    (base fields + ``extra_fields`` merge, #3326) — the selector's residue
    rides the additive surface.
    """

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.identified_arguments: dict = {}
        self.argument_provenance: dict = {}
        self.defining_moves: dict = {"moves": [], "status": "no_llm"}
        self.analysis_coverage: dict = {}

    def record_analysis_coverage(
        self,
        phase,
        k,
        n_total,
        bands_covered,
        bands_total,
        span=None,
        largest_uncovered_stretch=None,
        unit_ids=None,
        extra_fields=None,
    ):
        entry = {
            "k": int(k),
            "N": int(n_total),
            "bands_covered": int(bands_covered),
            "bands_total": int(bands_total),
        }
        if unit_ids is not None:
            entry["unit_ids"] = [str(u) for u in unit_ids]
        if span is not None:
            entry["span_start"], entry["span_end"] = float(span[0]), float(span[1])
        if largest_uncovered_stretch is not None:
            entry["largest_uncovered_stretch"] = float(largest_uncovered_stretch)
        if extra_fields:
            entry.update(extra_fields)
        self.analysis_coverage[phase] = entry


def _units_at_markers(state: _CoverageState, marker_ids):
    """One unit per given marker: 400 chars starting AT the marker, so a
    move quoting that marker has its span inside the unit's span (the
    overlap the witness measures). Covers the slots' markers too — named
    moves include the slots."""
    for i in marker_ids:
        marker = f"marqueur-numero-{i:02d}"
        offset = state.raw_text.index(marker)
        text = state.raw_text[offset : offset + 400]
        arg_id = f"arg_{i + 1}"
        state.identified_arguments[arg_id] = text
        state.argument_provenance[arg_id] = {
            "producer": "fixture",
            "offset": offset,
            "source_quote": text[:50],
        }
    return state


# --- ask 1: the inventory budget ----------------------------------------------


class TestInventoryBudget:
    def test_floor_is_the_render_cap_and_ceiling_the_family(self):
        assert INVENTORY_FLOOR == MAX_MOVES == 12
        assert INVENTORY_CEILING == PER_ARGUMENT_CEILING == 30

    def test_short_document_stays_at_the_floor(self):
        assert inventory_budget(200) == 12
        assert inventory_budget(WHOLE_TEXT_CALL_CAPACITY) == 12

    def test_long_document_scales_two_per_chunk_then_ceils(self):
        # 4 chunks -> 8 -> floored 12 ; 10 chunks -> 20 ; 60 chunks -> 120 -> 30
        assert inventory_budget(4 * WHOLE_TEXT_CALL_CAPACITY) == 12
        assert inventory_budget(10 * WHOLE_TEXT_CALL_CAPACITY) == 20
        assert inventory_budget(60 * WHOLE_TEXT_CALL_CAPACITY) == 30

    def test_prompt_states_the_computed_bound_not_the_render_cap(self):
        long_doc = _synth_document(30)
        assert inventory_budget(len(long_doc)) == 30
        prompt = build_first_reading_prompt(long_doc)
        assert "At most 30 entries in total" in prompt
        short_doc = _synth_document(1, part_len=4000)
        assert inventory_budget(len(short_doc)) == 12
        assert "At most 12 entries in total" in build_first_reading_prompt(short_doc)


# --- ask 2 + 3: the chain — parse keeps the inventory, selector buys k_eff ----


class TestEveryNamedMoveIsExamined:
    async def _run_chain(self, state: _CoverageState, n_moves: int):
        from argumentation_analysis.orchestration.invoke_callables import (
            _extract_arguments_for_parallel,
        )

        answer = _fake_llm_answer(n_moves, state.raw_text)
        result = await build_first_reading(state, _fake_llm(answer))
        assert result.status == "ok"
        state.defining_moves = result.to_state()
        extracted = _extract_arguments_for_parallel(
            state.raw_text, {"_state_object": state}
        )
        return result, extracted, state.analysis_coverage["fallacy_per_argument"]

    async def test_long_document_names_18_and_all_are_examined(self):
        """The DoD chain on a long document: the parse keeps 18 named moves
        (inventory 30 > the former flat 12), the selector buys k_eff and
        every named move reaches the examined set. Reddens when the flat
        MAX_MOVES is restored on the inventory (12 local kept, not 18)."""
        doc = _synth_document(30)
        state = _units_at_markers(_CoverageState(doc), range(20))
        result, extracted, coverage = await self._run_chain(state, 18)

        assert len(result.moves) == 20  # 2 slots + 18 local moves, all kept
        assert len(extracted) == 20
        assert coverage["named_moves_total"] == 20
        assert coverage["named_moves_examined"] == list(range(20))
        assert coverage["named_unexamined"] == []

    async def test_floor_band_buys_the_named_not_kl(self):
        """A 16k document: k(L) floors at 10, the inventory floor is 12
        TOTAL entries (the slots inside it — 2 slots + 10 local moves kept
        of 14 offered). The pass buys the 12 named, above k(L)=10, and
        every named move is examined with no budget residue. Reddens when
        the budget reverts to k(L) alone (10 bought, 2 named unexamined
        with a ``budget`` reason)."""
        doc = _synth_document(16, part_len=1000)
        assert per_argument_unit_budget(len(doc)) == 10
        assert inventory_budget(len(doc)) == 12
        state = _units_at_markers(_CoverageState(doc), range(12))
        result, extracted, coverage = await self._run_chain(state, 14)

        # 12 TOTAL entries kept (2 slots + 10 locals; the floor cut 4
        # offered locals) — the bound is on the whole inventory.
        assert len(result.moves) == 12
        assert coverage["k"] == 12
        assert coverage["named_moves_total"] == 12
        assert coverage["named_moves_examined"] == list(range(12))
        assert coverage["named_unexamined"] == []

    def test_residue_reasons_are_closed_and_true(self):
        """Direct residue check: an unpositioned move and a move over a
        document stretch no unit covers are NAMED with their reason —
        « nommé, non examiné », never a silent truncation."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _named_move_residue,
        )

        doc = _synth_document(4, part_len=1000)
        state = _CoverageState(doc)
        moves = [
            {
                "kind": "claim",
                "reading": "situe",
                "quote": "marqueur-numero-00",
                "offset": doc.index("marqueur-numero-00"),
            },
            {
                "kind": "claim",
                "reading": "non situe",
                "quote": "phrase absente",
                "offset": None,
            },
        ]
        state.defining_moves = {"moves": moves, "status": "ok"}
        residue = _named_move_residue(
            state,
            selected_units=[],
            population_units=[
                type("U", (), {"offset": 0, "text": doc[:400]})(),
            ],
        )
        assert residue["named_moves_total"] == 2
        reasons = {r["index"]: r["reason"] for r in residue["named_unexamined"]}
        # move 0: no selected unit -> its overlapping unit is population only
        assert reasons[0] == "budget"
        # move 1: no offset -> unpositioned
        assert reasons[1] == "unpositioned"


# --- ask 4: the note stays a page ---------------------------------------------


def _note_state(n_moves: int, unexamined=None):
    doc = _synth_document(max(4, n_moves), part_len=5400)
    moves = []
    for i in range(n_moves):
        quote = f"marqueur-numero-{i:02d}"
        offset = doc.index(quote)
        moves.append(
            {
                "kind": "claim",
                "reading": f"geste {i}",
                "quote": quote,
                "offset": offset,
            }
        )
    state = _CoverageState(doc)
    state.defining_moves = {
        "moves": moves,
        "status": "ok",
        "dropped_quotes": 0,
        "malformed_moves": 0,
        "read_scope": {
            "offset": 0,
            "window": len(doc),
            "status": "selected",
            "text_length": len(doc),
            "whole_document": True,
        },
    }
    if unexamined is not None:
        state.analysis_coverage["fallacy_per_argument"] = {
            "named_unexamined": [{"index": i, "reason": "budget"} for i in unexamined]
        }
    return state, moves


class TestTheNoteStaysAPage:
    def test_under_the_cap_the_render_is_unchanged(self):
        state, moves = _note_state(8)
        note = first_reading_note(state)
        assert "Ordre : celui du document, du premier geste au dernier." in note
        assert "nommés" not in note  # no count line when nothing is hidden
        assert note.count("\n  - ") == 8

    def test_over_the_cap_twelve_lines_and_the_count(self):
        state, moves = _note_state(20)
        note = first_reading_note(state)
        move_lines = [ln for ln in note.splitlines() if ln.startswith("  - ")]
        assert len(move_lines) == MAX_MOVES == 12
        assert "20 gestes nommés, 12 montrés ici" in note
        assert "échantillonné, pas exhaustif" in note
        assert "Ordre : thèse, mécanisme et piliers d'abord" in note

    def test_slots_show_first_when_truncating(self):
        state, moves = _note_state(16)
        # mark three moves as slots at late positions
        for i in (5, 9, 13):
            moves[i]["slot"] = (
                "thesis" if i == 5 else ("mechanism" if i == 9 else "pillar")
            )
            moves[i]["kind"] = "thesis" if i == 5 else ("device" if i == 9 else "claim")
        note = first_reading_note(state)
        move_lines = [ln for ln in note.splitlines() if ln.startswith("  - ")]
        assert len(move_lines) == 12
        assert move_lines[0].startswith("  - thèse centrale")
        assert move_lines[1].startswith("  - mécanisme")
        assert move_lines[2].startswith("  - pilier de la thèse")

    def test_examined_moves_outrank_the_spread(self):
        """With a measured residue, the reached moves take the page before
        the positional sample of the unreached ones."""
        state, moves = _note_state(
            16, unexamined=[1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14]
        )
        note = first_reading_note(state)
        move_lines = [ln for ln in note.splitlines() if ln.startswith("  - ")]
        assert len(move_lines) == 12
        # reached = 0, 5, 10, 15 -> they all show (tier 2, document order)
        for reached in (0, 5, 10, 15):
            assert f"geste {reached} —" in note
        # the spread fills the rest from the UNREACHED pool
        unreached_shown = sum(
            1
            for i in (1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14)
            if f"geste {i} —" in note
        )
        assert unreached_shown == 8  # 12 lines - 4 reached

    def test_no_coverage_record_means_no_examined_claim(self):
        """unexamined unknown (no selection recorded): the note shows the
        slots and a spread — it claims no examination it cannot read."""
        state, moves = _note_state(16)
        for i in (0, 5, 10):
            moves[i]["slot"] = "pillar"
        note = first_reading_note(state)
        assert "16 gestes nommés, 12 montrés ici" in note
        move_lines = [ln for ln in note.splitlines() if ln.startswith("  - ")]
        assert len(move_lines) == 12
        assert move_lines[0].startswith("  - pilier de la thèse")


# --- the budget seam: a function of the state ---------------------------------


class TestExaminedUnitBudget:
    def test_short_doc_no_moves_is_kl(self):
        state = _CoverageState("court texte " * 100)
        assert examined_unit_budget(state) == 10  # k(L) floor

    def test_named_raises_the_budget_above_kl(self):
        doc = _synth_document(4, part_len=1000)  # k(L) = 10
        state = _CoverageState(doc)
        state.defining_moves = {
            "moves": [
                {
                    "kind": "claim",
                    "reading": "g",
                    "quote": "marqueur-numero-00",
                    "offset": 0,
                }
            ]
            * 12,
            "status": "ok",
        }
        assert examined_unit_budget(state) == 12

    def test_kl_above_named_wins(self):
        doc = _synth_document(30)  # k(L) = 30
        state = _CoverageState(doc)
        state.defining_moves = {
            "moves": [
                {
                    "kind": "claim",
                    "reading": "g",
                    "quote": "marqueur-numero-00",
                    "offset": 0,
                }
            ]
            * 5,
            "status": "ok",
        }
        assert examined_unit_budget(state) == 30

    def test_no_text_is_none(self):
        assert examined_unit_budget(_CoverageState("")) is None


# --- ask 5: the call's own completion cap -------------------------------------


class _FakeMsg:
    content = "{}"


class _FakeChoice:
    message = _FakeMsg()


class _FakeResponse:
    choices = [_FakeChoice()]


class TestFirstReadingCompletionCap:
    def _patch(self, monkeypatch, captured):
        from argumentation_analysis.orchestration import invoke_callables as ic

        async def fake_guarded(client, **kwargs):
            captured.update(kwargs)
            return _FakeResponse()

        monkeypatch.setattr(ic, "_get_openai_client", lambda: (object(), "model-x"))
        monkeypatch.setattr(
            ic,
            "_resolve_llm_route",
            lambda: (None, "https://api.openai.com/v1", "model-x"),
        )
        monkeypatch.setattr(ic, "_guarded_chat_completion", fake_guarded)
        return ic

    async def test_the_reading_call_carries_its_own_named_cap(self, monkeypatch):
        """Through the INVOKE SITE (the seam the run actually calls), not
        the builder: the first reading's one call carries its own
        ``max_completion_tokens`` — the site wiring is the measured thing."""
        captured: dict = {}
        ic = self._patch(monkeypatch, captured)
        state = _CoverageState(_synth_document(4, part_len=1000))
        payload = await ic._invoke_first_reading(
            state.raw_text, {"_state_object": state}
        )
        # its OWN cap, named apart from the extraction capacity constant
        assert ic._FIRST_READING_MAX_TOKENS == 8192
        assert captured.get("max_completion_tokens") == 8192
        # the call went through the persona seam (the fake answer "{}" is a
        # parse_error — the witness measures the KWARGS, not the answer)
        assert payload.get("status") == "parse_error"

    async def test_other_personas_send_no_cap(self, monkeypatch):
        captured: dict = {}
        ic = self._patch(monkeypatch, captured)
        llm, _ = ic._build_persona_callable("historian")
        await llm("prompt")
        assert "max_completion_tokens" not in captured
        assert "max_tokens" not in captured
