"""#3511 (R1164 rework) — the zero-shot's own question, an inventory bound
that does not ration, an examination that follows the inventory.

Born-red witnesses for the R1164 dispatch, measured against the first
#3516 head: with the bound raised to 30/20/20/16/12/12 the reading still
named only 17/16/15/12/10/10 entries — the bound did not bind — and the
"gestures by kind" overlapped 4 of 39 central passages against 5.6 for
random anchors (chance level). The probe that asked the zero-shot's own
question exhaustively named 29-73 arguments and overlapped 26/39.

* **The question (A)** — step 3 asks for EVERY argument, exhaustively,
  wherever it sits, each with ONE verbatim anchor of 8 to 40 words; the
  measured-at-chance "gestures by kind" sentence is gone.
* **The bound (B)** — floor 12 (the render cap, the pinned pair), ceiling
  80 (the probe's observed maximum + ~10 %), NO density per chunk: the
  model named 29 arguments on ~5k characters, it does not ration by
  length. The prompt states the computed bound (#3480's lesson).
* **The examination follows the inventory (C)** — ``k_eff =
  min(N, max(k(L), named))`` (``examined_unit_budget``): the named raise
  the pass, the pass never outnames the inventory.
* **The residue survives both writers (review §1)** — one producer
  (``selection.named_move_residue``), called by the per-argument selection
  AND the #3326 winner reading on the MERGED selection: a second coverage
  write rebuilt the entry and erased the record on 5 of the 6 long
  documents in c5.
* **One overlap rule (review §2)** — the residue decides "examined" with
  the selector's own predicate (``_unit_overlaps_spans`` over
  ``_population_starts``), never a paraphrase extent (which ran ~2.6×
  past the passage and counted 5 moves the selector does not reach).
* **Tier 2 discriminates again (review §3)** — the moves the examination
  reached AND a lens retained a finding on (the #3510 predicate,
  ``coverage_family_by_unit``, reused), spread-sampled, never the head.
* **The note stays a page** — at most 12 move lines; the count line
  « N gestes nommés, M montrés ici » says what is hidden.

Synthetic documents only: markers and filler, no corpus content (privacy —
a fixture is a tracked file).
"""

import json

from argumentation_analysis.agents.core.reading.first_reading import (
    MAX_MOVES,
    _shown_move_indices,
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
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    merged_population_units,
    named_move_residue,
    named_moves_with_retained_finding,
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
    (base fields + ``extra_fields`` merge, #3326 — the entry is REBUILT,
    which is the defect review §1 measures), plus the ``add_trace_entry``
    no-op the winner-reading writer calls.
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

    def add_trace_entry(self, **_kwargs):
        return None


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


# --- ask B: the inventory bound ------------------------------------------------


class TestInventoryBudget:
    def test_floor_is_the_render_cap_and_ceiling_the_probe(self):
        """The floor is the pinned pair with the render cap; the ceiling is
        the probe's own measure (73 named + ~10 %), no longer the
        per-argument family's — the examination now FOLLOWS the inventory,
        so the old tie would ration the inventory by the pass again."""
        assert INVENTORY_FLOOR == MAX_MOVES == 12
        assert INVENTORY_CEILING == 80
        assert INVENTORY_CEILING != PER_ARGUMENT_CEILING

    def test_no_density_the_bound_does_not_scale(self):
        """The probe named 29 arguments on ~5k characters: the zero-shot
        does not ration by length, and neither does the bound. Reddens if
        a per-chunk density comes back (short document 12, long 30)."""
        assert inventory_budget(200) == 80
        assert inventory_budget(WHOLE_TEXT_CALL_CAPACITY) == 80
        assert inventory_budget(60 * WHOLE_TEXT_CALL_CAPACITY) == 80

    def test_prompt_states_the_computed_bound_not_the_render_cap(self):
        long_doc = _synth_document(30)
        assert inventory_budget(len(long_doc)) == 80
        assert "At most 80 entries in total" in build_first_reading_prompt(long_doc)
        short_doc = _synth_document(1, part_len=4000)
        assert "At most 80 entries in total" in build_first_reading_prompt(short_doc)
        assert "At most 12 entries" not in build_first_reading_prompt(short_doc)


# --- ask A: the question is the zero-shot's ------------------------------------


class TestTheQuestionIsTheZeroShots:
    def test_step3_asks_the_exhaustive_question_with_a_verbatim_anchor(self):
        """R1164 decision A: every argument, exhaustively, wherever it
        sits, each with ONE verbatim anchor of 8 to 40 words — the probe's
        own question, measured at 26/39 against 4/39 for gestures by kind.
        Reddens if the measured-at-chance sentence comes back."""
        prompt = build_first_reading_prompt(_synth_document(4, part_len=1000))
        assert "EVERY argument" in prompt
        assert "exhaustively" in prompt
        assert "verbatim anchor" in prompt
        assert "8 to 40 words" in prompt
        # the measured-at-chance vocabulary is gone
        assert "BY ITS KIND" not in prompt
        assert "rebuttal" not in prompt


# --- ask C + the chain: parse keeps the inventory, selector buys k_eff ---------


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
        (the bound is 80, the former flat 12 is gone), the selector buys
        k_eff and every named move reaches the examined set. Reddens when a
        flat cap is restored on the inventory (12 local kept, not 18)."""
        doc = _synth_document(30)
        state = _units_at_markers(_CoverageState(doc), range(20))
        result, extracted, coverage = await self._run_chain(state, 18)

        assert len(result.moves) == 20  # 2 slots + 18 local moves, all kept
        assert len(extracted) == 20
        assert coverage["named_moves_total"] == 20
        assert coverage["named_moves_examined"] == list(range(20))
        assert coverage["named_unexamined"] == []

    async def test_named_raise_the_pass_above_kl(self):
        """A 16k document: k(L) floors at 10 and the reading names 16 (2
        slots + 14 locals — under the 80 bound, all kept). The pass buys
        the 16 named, above k(L)=10, and every named move is examined.
        Reddens when the budget reverts to k(L) alone (10 bought, 6 named
        unexamined with a ``budget`` reason)."""
        doc = _synth_document(16, part_len=1000)
        assert per_argument_unit_budget(len(doc)) == 10
        state = _units_at_markers(_CoverageState(doc), range(16))
        result, extracted, coverage = await self._run_chain(state, 14)

        assert len(result.moves) == 16
        assert coverage["k"] == 16
        assert coverage["named_moves_total"] == 16
        assert coverage["named_moves_examined"] == list(range(16))
        assert coverage["named_unexamined"] == []

    def test_residue_reasons_are_closed_and_true(self):
        """Direct residue check over the selector's OWN rule: the three
        closed reasons, each on a geometry that produces it — ``budget``
        (a population unit owns the passage, the selection did not buy
        it), ``no_overlapping_unit`` (every unit starts after the move's
        span — nobody owns it) and ``unpositioned`` (no located quote).
        The moves are written in ``defining_moves`` order: positioned by
        ascending offset, unpositioned last."""
        doc = _synth_document(4, part_len=1000)
        state = _CoverageState(doc)
        state.defining_moves = {
            "moves": [
                {  # span (0, 17): the only unit starts at 1500, AFTER the
                    # span — no unit owns it, the pass had nothing to buy
                    "kind": "claim",
                    "reading": "sans unite",
                    "quote": "marqueur-numero-00",
                    "offset": 0,
                },
                {  # span (2000, 2017): the unit at 1500 is the nearest
                    # start at or before it — it owns the passage
                    "kind": "claim",
                    "reading": "couvert par la population",
                    "quote": "marqueur-numero-02",
                    "offset": 2000,
                },
                {  # no offset: no span, no overlap, nothing to examine
                    "kind": "claim",
                    "reading": "non situe",
                    "quote": "phrase absente",
                    "offset": None,
                },
            ],
            "status": "ok",
        }
        population = [
            SelectableUnit(
                unit_id="arg_1",
                text=doc[1500:1900],
                producer="fixture",
                offset=1500,
            )
        ]
        residue = named_move_residue(
            state, selected_units=[], population_units=population
        )
        assert residue["named_moves_total"] == 3
        assert residue["named_moves_examined"] == []
        reasons = {r["index"]: r["reason"] for r in residue["named_unexamined"]}
        assert reasons == {
            0: "no_overlapping_unit",
            1: "budget",
            2: "unpositioned",
        }

    def test_the_residues_overlap_rule_is_the_selectors_own(self):
        """R1164 review §2 (born-red): a unit without a source quote whose
        PARAPHRASE runs over the move's span does not examine it — the
        nearest unit start at or before the span owns the passage, exactly
        as ``_prefer_priority`` decides. The paraphrase rule measured 73
        moves examined on 82 where the selector's own rule reaches 68."""
        doc = _synth_document(4, part_len=1000)
        offset = doc.index("marqueur-numero-03")  # span (3000, 3017)
        # its paraphrase (3500 chars from 0) runs over the move's span…
        long_paraphrase = SelectableUnit(
            unit_id="arg_A", text=doc[:3500], producer="fixture", offset=0
        )
        # …but the nearest start at or before the span (2900) is another
        # unit's — THAT one owns the passage, and it is not selected.
        owner = SelectableUnit(
            unit_id="arg_C", text=doc[2900:2950], producer="fixture", offset=2900
        )
        state = _CoverageState(doc)
        state.defining_moves = {
            "moves": [
                {
                    "kind": "claim",
                    "reading": "g",
                    "quote": "marqueur-numero-03",
                    "offset": offset,
                }
            ],
            "status": "ok",
        }
        residue = named_move_residue(
            state,
            selected_units=[long_paraphrase],
            population_units=[long_paraphrase, owner],
        )
        assert residue["named_moves_examined"] == []
        assert residue["named_unexamined"][0]["reason"] == "budget"


# --- review §1: the residue survives the winner reading's second write ---------


class TestTheResidueSurvivesTheWinnerWriter:
    def test_the_winner_reading_recomputes_the_residue_over_the_merge(self):
        """R1164 review §1 (born-red, blocking): the #3326 writer re-records
        ``fallacy_per_argument`` on the union of unit ids — a write whose
        ``extra_fields`` held ``added_by`` alone rebuilt the entry and
        ERASED the named-moves record (measured: gone on 5 of the 6 long
        documents in c5). Here the winner reading adds a unit that reaches
        one unexamined move: the keys survive, and that move now counts as
        examined — only the recompute over the MERGED selection can say
        it."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fallacy_winner_reading_to_state,
        )

        doc = _synth_document(6, part_len=1000)
        state = _units_at_markers(_CoverageState(doc), range(3))
        state.defining_moves = {
            "moves": [
                {
                    "kind": "claim",
                    "reading": f"geste {i}",
                    "quote": f"marqueur-numero-{i:02d}",
                    "offset": doc.index(f"marqueur-numero-{i:02d}"),
                }
                for i in range(3)
            ],
            "status": "ok",
        }
        units = merged_population_units(state)
        # the per-argument pass selected the units of markers 0 and 1:
        # the move at marker 2 is named, its unit exists, not bought.
        state.record_analysis_coverage(
            "fallacy_per_argument",
            2,
            3,
            1,
            1,
            unit_ids=["arg_1", "arg_2"],
            extra_fields=named_move_residue(state, units[:2], units),
        )
        before = state.analysis_coverage["fallacy_per_argument"]
        assert before["named_moves_total"] == 3
        assert [r["reason"] for r in before["named_unexamined"]] == ["budget"]

        _write_fallacy_winner_reading_to_state(
            {"examined_ids": ["arg_3"], "fallacies": []}, state, {}
        )
        after = state.analysis_coverage["fallacy_per_argument"]
        assert after["unit_ids"] == ["arg_1", "arg_2", "arg_3"]
        assert after["added_by"] == {"arg_3": "vote_winner_reading"}
        # the record survived the second write, on the merged selection
        assert after["named_moves_total"] == 3
        assert after["named_moves_examined"] == [0, 1, 2]
        assert after["named_unexamined"] == []


# --- ask 4: the note stays a page ----------------------------------------------


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


def _finding_state(finding_indices):
    """A note state where the coverage review's walk retained a fallacy on
    the units of the given moves (the #3510 predicate, through the real
    reader ``named_moves_with_retained_finding``) and the examination
    reached every named move."""
    state, moves = _note_state(20, unexamined=[])
    _units_at_markers(state, finding_indices)
    state.coverage_review = {
        "status": "ok",
        "items": [
            {
                "unit_id": f"arg_{i + 1}",
                "routed": {"finding": {"fallacies": [{"family": "appel a la peur"}]}},
            }
            for i in finding_indices
        ],
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

    def test_tier2_holds_the_reached_moves_a_lens_retained_a_finding_on(self):
        """R1164 review §3 (born-red): 20 moves, all reached, findings on 3
        of them at 10, 50 and 90 % of the document — the page shows exactly
        those 3 ahead of the spread. Reddens when tier 2 fills from the
        document's head instead (the 90 % finding would not show)."""
        state, moves = _finding_state((2, 10, 18))
        assert named_moves_with_retained_finding(state) == frozenset({2, 10, 18})
        note = first_reading_note(state)
        move_lines = [ln for ln in note.splitlines() if ln.startswith("  - ")]
        assert len(move_lines) == 12
        for found in (2, 10, 18):
            assert f"geste {found} —" in note
        # the spread carries the rest — not a finding, it is tier 3's to
        # choose, and 12 lines cannot hold all 17 of them
        shown = sum(1 for i in range(20) if f"geste {i} —" in note)
        assert shown == 12

    def test_tier2_spreads_when_findings_exceed_the_room(self):
        """R1164 review §3, variant: findings on 6 moves with room for 2 —
        the pair is a SPREAD over the findings, never the first two."""
        moves = [{"kind": "claim"} for _ in range(20)]
        for i in range(10):  # 10 slots leave room = 2
            moves[i]["slot"] = (
                "thesis" if i == 0 else ("mechanism" if i == 1 else "pillar")
            )
        findings = frozenset({11, 13, 15, 17, 18, 19})
        shown = _shown_move_indices(moves, frozenset(), findings)
        assert len(shown) == MAX_MOVES == 12
        # the two tier-2 lines: findings[0] and findings[3] by position
        assert set(shown[10:]) == {11, 17}

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

    def test_forty_named_with_kl_twenty_is_forty(self):
        """R1164 DoD: 40 named, k(L) = 20 — the budget follows the named
        (the replay configuration that measured 20/39 passages examined)."""
        doc = _synth_document(12, part_len=5000)  # 60k chars -> k(L) = 20
        assert per_argument_unit_budget(len(doc)) == 20
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
            * 40,
            "status": "ok",
        }
        assert examined_unit_budget(state) == 40

    def test_the_pass_never_outnames_the_inventory(self):
        """R1164 DoD: with N = 25 the budget is 25 even though 40 are
        named — the ``min`` against the inventory bound. Reddens when the
        seam reverts to ``max(k(L), named)`` alone."""
        doc = _synth_document(12, part_len=5000)
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
            * 40,
            "status": "ok",
        }
        assert examined_unit_budget(state, bound=25) == 25

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
