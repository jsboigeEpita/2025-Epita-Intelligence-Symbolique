"""#3518 — the inventory supplies a unit where the extraction cut none.

The first reading names every argument with a verbatim, located anchor
(#3516). The per-argument pass could only examine a unit the EXTRACTION
produced: where the reading named an argument in a stretch no unit covers,
the move reached no lens whatever the budget — ``k_eff`` already held every
overlapping unit, and there was none. On the R1165 witness, 33 of 167
positioned moves (20 %) sat in such a stretch, hiding 9 of the 21 named
central passages; the simulation (each such move entering the population as
a unit) took the free replay from 12/39 to 20/39 passages examined, past
the ≥ 18/39 bar of #3511.

The repair: the move SUPPLIES the unit — ``text``/``source_quote`` are the
anchor, ``offset`` the move's, ``producer`` the first reading, the id the
move's index (``reading_N`` — the index the residue records). ONE producer
(``anchored_units_for_named_moves``), deterministic from the state, wired at
the per-argument population and re-derived by every writer that must
resolve the ids: the fallacy target guard, the coverage review's rows (so
``coverage_family_by_unit`` can key them, #3510), the tier-2 binding and
the winner writer. The other ``merged_population_units`` consumers are
censused in the PR body, unwired.

Anti-pendulum: ``k`` is not raised (the budget already reserved room for
every named move — #3516's ``max(k(L), named)``); the extraction is not
re-run (the anchors are already verbatim and located); only the selector's
own predicate decides "nothing overlaps".

Synthetic document, opaque ids, no corpus content. Born red on main.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from argumentation_analysis.agents.core.reading.coverage_review import (
    coverage_family_by_unit,
    unit_id_at_offset,
)
from argumentation_analysis.orchestration.selection import (
    anchored_units_for_named_moves,
    merged_population_units,
    named_move_residue,
)
from argumentation_analysis.orchestration.state_writers import (
    resolve_fallacy_target_arg_id,
)

_HEAD_PASSAGE = (
    "La premiere phrase du document expose la position initiale de "
    "l'auteur sur la question, longue enough pour l'analysabilite."
)
_GAP_QUOTE = (
    "un passage central du document que l'extraction n'a jamais decoupe "
    "en unite analysable"
)
_OVERLAP_QUOTE = "la position initiale de l'auteur"

_DOC = (
    _HEAD_PASSAGE
    + ". "
    + ("Du remplissage neutre pour ecarter les unites les unes des autres. " * 40)
    + _GAP_QUOTE
    + ". "
    + ("Encore du remplissage neutre jusqu'a la fin du document. " * 20)
)


class _CoverageState:
    """Duck-typed state: raw text, population, provenance, reading, coverage
    book — the ``record_analysis_coverage`` contract the real state carries
    (base fields + ``extra_fields`` merge, #3326) and the ``add_trace_entry``
    no-op the winner-reading writer calls."""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.identified_arguments: Dict[str, str] = {}
        self.argument_provenance: Dict[str, Dict[str, Any]] = {}
        self.defining_moves: Dict[str, Any] = {"moves": [], "status": "ok"}
        self.analysis_coverage: Dict[str, Any] = {}
        self.coverage_review: Dict[str, Any] = {}

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
            "span": span,
            "largest_uncovered_stretch": largest_uncovered_stretch,
            "unit_ids": list(unit_ids or []),
        }
        entry.update(extra_fields or {})
        self.analysis_coverage[str(phase)] = entry

    def add_trace_entry(self, *args, **kwargs):  # noqa: ANN002, ANN003 — no-op
        return None


def _state_with_gap() -> _CoverageState:
    """One extracted unit at the head; the reading names two moves — one the
    head unit covers, one in a stretch no unit touches (defining_moves sorts
    by offset: head move index 0, gap move index 1 → ``reading_1``)."""
    state = _CoverageState(_DOC)
    head_offset = _DOC.index(_HEAD_PASSAGE)
    gap_offset = _DOC.index(_GAP_QUOTE)
    state.identified_arguments["arg_1"] = _HEAD_PASSAGE
    state.argument_provenance["arg_1"] = {
        "producer": "llm_extract",
        "offset": head_offset,
        "source_quote": _HEAD_PASSAGE,
    }
    state.defining_moves["moves"] = [
        {
            "kind": "claim",
            "reading": "la position de depart",
            "quote": _OVERLAP_QUOTE,
            "offset": _DOC.index(_OVERLAP_QUOTE),
        },
        {
            "kind": "pillar",
            "reading": "le passage que rien ne couvre",
            "quote": _GAP_QUOTE,
            "offset": gap_offset,
        },
    ]
    return state


def _selected_pairs(state: _CoverageState):
    from argumentation_analysis.orchestration.invoke_callables import (
        _extract_arguments_for_parallel,
    )

    return _extract_arguments_for_parallel(_DOC, {"_state_object": state})


class TestTheGapMoveIsExamined:
    def test_the_gap_move_is_selected_examined_and_recorded(self):
        """The dispatch's witness: named in a stretch with no extracted
        unit → selected, examined, and recorded as examined in the residue.
        Born red on main: no unit overlapped the move, so nothing could be
        selected there and the residue filed ``no_overlapping_unit``."""
        state = _state_with_gap()
        pairs = _selected_pairs(state)
        ids = [unit_id for unit_id, _text in pairs]
        assert "reading_1" in ids
        # the anchored unit's text IS the anchor — the descent reads the
        # passage, and its window (#3376) centres on it via source_quote
        anchored = anchored_units_for_named_moves(state, merged_population_units(state))
        assert any(
            u.unit_id == "reading_1"
            and u.source_quote == _GAP_QUOTE
            and u.text == _GAP_QUOTE
            and u.producer == "first_reading"
            for u in anchored
        )
        record = state.analysis_coverage["fallacy_per_argument"]
        assert "reading_1" in record["unit_ids"]
        # the residue: the gap move (index 1) is EXAMINED, and no
        # ``no_overlapping_unit`` entry remains for it
        assert 1 in record["named_moves_examined"]
        reasons = {
            (e.get("index"), e.get("reason")) for e in record["named_unexamined"]
        }
        assert (1, "no_overlapping_unit") not in reasons

    def test_the_residue_names_the_reason_when_injection_is_dropped(self):
        """The same state through the residue producer, on the MERGED
        population alone, still files the gap move as ``no_overlapping_unit``
        — the mutation control's ground truth (what main does)."""
        state = _state_with_gap()
        merged = merged_population_units(state)
        residue = named_move_residue(state, [], merged)
        reasons = {
            (e.get("index"), e.get("reason")) for e in residue["named_unexamined"]
        }
        assert (1, "no_overlapping_unit") in reasons


class TestNoDuplicatesNoInvention:
    def test_an_overlapped_move_creates_no_extra_unit(self):
        """A move an extracted unit already overlaps adds nothing: the head
        move gets no ``reading_0`` unit."""
        state = _state_with_gap()
        anchored = anchored_units_for_named_moves(state, merged_population_units(state))
        assert [u.unit_id for u in anchored] == ["reading_1"]

    def test_one_unit_per_passage(self):
        """Two gap moves over the SAME stretch: the first anchors, the second
        is examined through it — never a second unit for one passage."""
        state = _state_with_gap()
        gap_offset = _DOC.index(_GAP_QUOTE)
        state.defining_moves["moves"].append(
            {
                "kind": "claim",
                "reading": "un second nommage du meme passage",
                "quote": _GAP_QUOTE[10:],
                "offset": gap_offset + 10,
            }
        )
        anchored = anchored_units_for_named_moves(state, merged_population_units(state))
        assert [u.unit_id for u in anchored] == ["reading_1"]

    def test_no_gap_moves_means_byte_identical_population(self):
        """A state whose every named move overlaps a unit: the producer
        returns nothing and the selection path keeps the merged population's
        pairs alone — the byte-identity control."""
        state = _CoverageState(_DOC)
        head_offset = _DOC.index(_HEAD_PASSAGE)
        state.identified_arguments["arg_1"] = _HEAD_PASSAGE
        state.argument_provenance["arg_1"] = {
            "producer": "llm_extract",
            "offset": head_offset,
            "source_quote": _HEAD_PASSAGE,
        }
        state.defining_moves["moves"] = [
            {
                "kind": "claim",
                "reading": "la position de depart",
                "quote": _OVERLAP_QUOTE,
                "offset": _DOC.index(_OVERLAP_QUOTE),
            }
        ]
        assert (
            anchored_units_for_named_moves(state, merged_population_units(state)) == []
        )
        pairs = _selected_pairs(state)
        assert [unit_id for unit_id, _ in pairs] == ["arg_1"]
        record = state.analysis_coverage["fallacy_per_argument"]
        assert not any(str(i).startswith("reading_") for i in record["unit_ids"])

    def test_a_state_without_reading_names_nothing(self):
        state = _CoverageState(_DOC)
        state.identified_arguments["arg_1"] = _HEAD_PASSAGE
        state.argument_provenance["arg_1"] = {"producer": "llm_extract"}
        assert (
            anchored_units_for_named_moves(state, merged_population_units(state)) == []
        )


class TestTheWritersResolveTheNewIds:
    def test_the_fallacy_writer_resolves_a_finding_on_the_new_unit(self):
        """Born red on main: the membership guard read identified_arguments
        alone and a finding grounded on ``reading_1`` resolved to None — the
        finding lost in silence (#1019)."""
        state = _state_with_gap()
        assert (
            resolve_fallacy_target_arg_id(state, {"source_arg_id": "reading_1"})
            == "reading_1"
        )
        # the sentinel rule keeps excluding the wide-net stamp
        assert (
            resolve_fallacy_target_arg_id(state, {"source_arg_id": "whole_text"})
            is None
        )
        # an id nothing carries still resolves to nothing
        assert (
            resolve_fallacy_target_arg_id(state, {"source_arg_id": "reading_9"}) is None
        )

    def test_the_review_maps_a_passage_on_the_anchored_unit(self):
        """The review's rows carry the anchored unit: a passage at that
        offset maps to ``reading_1`` (and the examined filter can see what
        the descent examined), instead of mapping to no unit."""
        from argumentation_analysis.agents.core.reading.coverage_review import (
            _unit_rows,
        )

        state = _state_with_gap()
        rows = _unit_rows(state)
        ids = {row["unit_id"] for row in rows}
        assert "reading_1" in ids
        gap_offset = _DOC.index(_GAP_QUOTE)
        assert unit_id_at_offset(rows, gap_offset + 5) == "reading_1"

    def test_a_retained_finding_on_the_anchored_unit_reaches_its_move(self):
        """Born red on main: the tier-2 binding read the merged population
        alone, so a finding keyed ``reading_1`` never reached its move."""
        from argumentation_analysis.orchestration.selection import (
            named_moves_with_retained_finding,
        )

        state = _state_with_gap()
        state.coverage_review = {
            "status": "ok",
            "items": [
                {
                    "unit_id": "reading_1",
                    "routed": {
                        "finding": {"fallacies": [{"family": "appels a l'autorite"}]}
                    },
                }
            ],
        }
        assert coverage_family_by_unit(state).get("reading_1") == "appels a l'autorite"
        assert named_moves_with_retained_finding(state) == frozenset({1})

    def test_the_winner_writer_keeps_the_anchored_unit(self):
        """Born red on main: ``by_id`` read the merged population alone, so a
        winner walk on ``reading_1`` produced a record whose geometry
        measured nothing (no resolved unit) — the walk's coverage line was
        hollow."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_fallacy_winner_reading_to_state,
        )

        state = _state_with_gap()
        _write_fallacy_winner_reading_to_state(
            {"fallacies": [], "examined_ids": ["reading_1"]}, state, {}
        )
        record = state.analysis_coverage["fallacy_per_argument"]
        assert "reading_1" in record["unit_ids"]
        assert record["added_by"].get("reading_1") == "vote_winner_reading"
        # the geometry MEASURED the resolved unit: the span (a fraction of
        # the text) covers the anchored passage — not the empty (0, 0) a
        # dropped id would leave
        gap_offset = _DOC.index(_GAP_QUOTE)
        assert record["span"][0] == pytest.approx(gap_offset / len(_DOC), abs=1e-6)
        assert record["span"][1] > gap_offset / len(_DOC)
        assert record["bands_covered"] >= 1
        # and the recomputed residue sees the walk: the gap move is examined
        assert 1 in record["named_moves_examined"]
