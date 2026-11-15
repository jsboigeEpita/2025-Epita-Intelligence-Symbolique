"""#2850 slice A — unit tests for the ONE selector.

The selector is the coverage repair's core gesture; these tests pin its
contract: stratified bands (≥1 selected unit per band), stable within-band
order, named-absence units never seeding a band, text-order return, and a
budget that never grows. All deterministic, no LLM.
"""

from typing import Any, Dict, List, Optional
from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    _positioned_spans,
    merged_population_units,
    rests_on_unit_ids,
    select_for_budget,
)


def _spread(n: int, span: int = 60000) -> List[SelectableUnit]:
    """n units evenly spread over `span`, in scrambled insertion order."""
    step = span // max(n, 1)
    units = [
        SelectableUnit(unit_id=f"arg_{i+1}", text=f"unit {i}", offset=i * step)
        for i in range(n)
    ]
    # Reverse so insertion order ≠ text order — stratification must not
    # depend on the population arriving sorted.
    return units[::-1]


class TestStratifiedPosition:
    def test_every_band_gets_one_unit(self):
        units = _spread(9)
        result = select_for_budget(units, 3)
        assert result.k == 3
        assert result.bands_total == 3
        assert result.bands_covered == 3
        offsets = [u.offset for u in result.selected]
        # One unit from each third of the POPULATION'S offset range (bands
        # are equal-count, so boundaries derive from the actual offsets, not
        # from a nominal span) — the father defect's counter-gesture: the
        # tail is reached, not just the head.
        lo = min(u.offset for u in units)
        hi = max(u.offset for u in units)
        span = max(hi - lo, 1)
        thirds = {min(2, (o - lo) * 3 // span) for o in offsets}
        assert thirds == {0, 1, 2}

    def test_selection_spans_the_tail(self):
        # The non-vacuity instrument: on a head-shaped world (main's
        # behaviour) the first 10 of 30 units all sit in the first third.
        units = _spread(30)
        result = select_for_budget(units, 10)
        assert result.k == 10
        max_offset = max(u.offset or 0 for u in result.selected)
        assert max_offset > 40000, "no selected unit reaches the last third"

    def test_result_is_in_text_order(self):
        units = _spread(6)
        result = select_for_budget(units, 6)
        offsets = [u.offset for u in result.selected]
        assert offsets == sorted(offsets)

    def test_budget_is_never_raised(self):
        units = _spread(20)
        result = select_for_budget(units, 5)
        assert result.k == 5
        assert result.n_total == 20

    def test_named_absence_never_seeds_a_band(self):
        positioned = _spread(6)
        absent = [SelectableUnit(unit_id="arg_abs", text="no position", offset=None)]
        result = select_for_budget(positioned + absent, 3)
        ids = [u.unit_id for u in result.selected]
        assert "arg_abs" not in ids, "absent units fill leftover budget, never a band"
        assert result.bands_covered == 3

    def test_named_absence_fills_leftover_budget(self):
        positioned = _spread(3)
        absent = [
            SelectableUnit(unit_id=f"abs_{i}", text="x", offset=None) for i in range(3)
        ]
        result = select_for_budget(positioned + absent, 5)
        ids = [u.unit_id for u in result.selected]
        assert "abs_0" in ids and "abs_1" in ids
        assert ids[-1].startswith("abs_") or ids[-2].startswith("abs_")

    def test_budget_holds_everything_is_the_identity(self):
        units = _spread(4)
        result = select_for_budget(units, 10)
        assert result.k == 4 == result.n_total
        assert set(u.unit_id for u in result.selected) == set(u.unit_id for u in units)

    def test_zero_budget_selects_nothing(self):
        result = select_for_budget(_spread(4), 0)
        assert result.selected == ()
        assert result.k == 0 and result.n_total == 4

    def test_empty_population(self):
        result = select_for_budget([], 5)
        assert result.selected == ()
        assert result.n_total == 0

    def test_all_absent_population(self):
        units = [
            SelectableUnit(unit_id=f"a{i}", text="x", offset=None) for i in range(4)
        ]
        result = select_for_budget(units, 2)
        assert [u.unit_id for u in result.selected] == ["a0", "a1"]
        assert result.bands_covered == 0 and result.bands_total == 0

    def test_unknown_strategy_is_loud(self):
        with pytest.raises(ValueError, match="unknown strategy"):
            select_for_budget(_spread(3), 2, strategy="salience")


class TestMergedPopulation:
    def _state(self) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState("alpha beta gamma delta")
        state.add_argument(
            "claim one", producer="llm_extract", source_quote="beta gamma"
        )
        state.add_argument("beta gamma delta", producer="kb_heuristic")
        state.add_argument("unlocatable claim", producer="llm_extract")
        return state

    def test_both_producers_one_list(self):
        units = merged_population_units(self._state())
        assert [u.producer for u in units] == [
            "llm_extract",
            "kb_heuristic",
            "llm_extract",
        ]

    def test_offsets_come_from_provenance(self):
        units = merged_population_units(self._state())
        by_id = {u.unit_id: u for u in units}
        assert by_id["arg_1"].offset == 6  # "beta gamma"
        assert by_id["arg_2"].offset == 6  # own text, found
        assert by_id["arg_3"].offset is None  # named absence carried through

    def test_quote_rides_along(self):
        units = merged_population_units(self._state())
        assert units[0].source_quote == "beta gamma"
        assert units[1].source_quote == ""

    def test_fallback_mints_positional_ids(self):
        args = [{"text": "a", "source_quote": "q"}, "plain"]
        units = merged_population_units(None, fallback_args=args)
        assert [u.unit_id for u in units] == ["arg_1", "arg_2"]
        assert all(u.offset is None for u in units)

    def test_no_state_no_fallback_is_empty(self):
        assert merged_population_units(None) == []


class TestCoverageFigure:
    def test_bands_covered_counts_only_selected(
        self,
    ):
        units = _spread(9)
        result = select_for_budget(units, 2)
        assert result.bands_covered == 2
        assert result.bands_total == 2

    def test_k_counts_absent_units_without_covering_a_band(self):
        positioned = _spread(3)
        absent = [SelectableUnit(unit_id="abs", text="x", offset=None)]
        result = select_for_budget(positioned + absent, 4)
        assert result.k == 4
        assert result.bands_covered == 3  # only positioned bands


class TestTextBandsAndSpan2887:
    """Review of #2887 — recorded coverage speaks in TEXT terms.

    Population bands (slice A's default) recompute the checked field from
    what it checks: a head-only population of 10 units renders « 8/8 bandes »
    while occupying 0.00–0.05 of the text. With ``text_length``, bands are
    fixed thirds of ``[0, L]`` — reachable-partial — and ``span`` carries the
    exact fraction of the text the selected units occupy.
    """

    def _head_only(self):
        # 10 units all inside the first 3,000 chars of a 56,430-char text —
        # the review's measured situation.
        return [
            SelectableUnit(unit_id=f"a{i}", text=f"t{i}", offset=100 + i * 280)
            for i in range(10)
        ]

    def test_head_only_covers_one_third_and_says_so(self):
        sel = select_for_budget(self._head_only(), 8, text_length=56430)
        assert sel.bands_total == 3
        assert (
            sel.bands_covered == 1
        ), "a head-only population covers ONE text third — never 8/8"
        assert sel.span is not None and sel.span[1] < 1 / 3

    def test_the_paired_population_geometry_is_the_tautology(self):
        """The control of the control: the SAME population, no text length,
        saturates its own bands — this is the measured defect the review
        names, pinned so the two geometries cannot be conflated again."""
        sel = select_for_budget(self._head_only(), 8)
        assert sel.bands_covered == sel.bands_total == 8

    def test_span_is_the_fraction_of_the_text(self):
        units = [
            SelectableUnit(unit_id="a", text="ta", offset=1200),
            SelectableUnit(unit_id="b", text="tb", offset=50000),
        ]
        sel = select_for_budget(units, 2, text_length=60000)
        # #3393 — the extent ends where the last unit ENDS (offset + text
        # length), never at its start: the panel measured Act I saying
        # 0.00–0.73 next to the bounds' own 0.00–1.00 for the same units.
        assert sel.span == (1200 / 60000, 50002 / 60000)

    def test_return_is_text_order_even_when_bands_interleave(self):
        """The review nit: round-robin interleaves bands, the returned
        selection must not — always offset-ascending, absent last."""
        units = [
            SelectableUnit(unit_id=f"a{i}", text=f"t{i}", offset=o)
            for i, o in enumerate(range(0, 48000, 6000))
        ]
        sel = select_for_budget(units, 8, band_count=3, text_length=48000)
        offsets = [u.offset for u in sel.selected if u.offset is not None]
        assert offsets == sorted(offsets), (
            "the returned selection reads in the document's order, not the "
            "round-robin's"
        )

    def test_no_text_length_keeps_population_bands_and_no_span(self):
        units = [
            SelectableUnit(unit_id=f"a{i}", text=f"t{i}", offset=i * 100)
            for i in range(6)
        ]
        sel = select_for_budget(units, 4)
        assert sel.span is None
        assert sel.bands_total == 4  # the slice-A population geometry

    def test_identity_selection_carries_the_span_too(self):
        units = [
            SelectableUnit(unit_id="a", text="ta", offset=100),
            SelectableUnit(unit_id="b", text="tb", offset=20000),
        ]
        sel = select_for_budget(units, 5, text_length=40000)
        assert sel.k == 2
        # #3393 — end of the extent = end of the last unit (20000 + len("tb")).
        assert sel.span == (100 / 40000, 20002 / 40000)
        assert sel.bands_covered == 2 and sel.bands_total == 3


class TestTheSpanIsThePassageNotTheParaphrase3502:
    """#3502, born red on the pre-fix head — the extent rule reaches selection.

    A unit that carries a source quote is covered by its PASSAGE, not by the
    extractor's paraphrase (``text``): on the coordinator's panel measure the
    paraphrase runs ×2.6 past the located passage in the median, so the
    coverage extent overstated its end. Under the one extent rule
    (``shared_state.unit_extent``, #3502) the span ends where the quote ends,
    and the space between quote end and paraphrase end belongs to whatever
    the document puts there — a second unit, not this one's overrun.
    """

    def test_a_quoted_units_span_ends_at_the_quote(self):
        paraphrase = "La reformulation de l'extracteur depasse le passage " * 12
        units = [
            SelectableUnit(
                unit_id="a", text=paraphrase, offset=0, source_quote="court passage"
            ),
            SelectableUnit(unit_id="b", text="tb", offset=len("court passage")),
        ]
        spans = _positioned_spans(units, 60000)
        # quote len 13 ("court passage") — NOT len(paraphrase): a second unit
        # starts right after the quote and holds that space in its own right.
        assert spans == [(0, 13), (13, 15)]

    def test_the_coverage_figure_no_longer_counts_the_overrun(self):
        """The measured effect on the panel was the figure: the span fraction
        said the selection read further into the text than the passages it
        located. Same population, through the selector."""
        paraphrase = "La reformulation de l'extracteur depasse le passage " * 12
        units = [
            SelectableUnit(
                unit_id="a", text=paraphrase, offset=0, source_quote="court passage"
            ),
            SelectableUnit(unit_id="b", text="tb", offset=len("court passage")),
        ]
        sel = select_for_budget(units, 5, text_length=60000)
        assert sel.span == (0 / 60000, 15 / 60000)


class TestRestsOnUnitIds3511:
    """#3511 — the model-free rule naming the unit a claim RESTS ON.

    The measured fact: a move sits on an evidence passage 1 time in 23
    (against 8 in 28 for claims) — the evidence lies BESIDE the move. The
    rule (the coordinator's candidate (b), picked from the 23 judged
    occurrences: it names a unit intersecting the judged passage's unit 7
    times in 9, against 5 in 9 for "just the unit before") names, per
    positioned move, the nearest positioned unit that starts before it in
    the SAME blank-line paragraph, CARRIES a quotation mark or a figure,
    and does not already overlap a move. All deterministic, no LLM.
    """

    @staticmethod
    def _state(raw: str, moves: List[Dict[str, Any]]) -> SimpleNamespace:
        return SimpleNamespace(raw_text=raw, defining_moves={"moves": moves})

    def test_the_nearest_carrying_unit_before_the_move_in_its_paragraph_wins(self):
        raw = (
            "first paragraph stands alone.\n\n"
            "evidence 3 opens then the claim ends.\n\n"
            "a last paragraph."
        )
        claim_at = raw.index("the claim")
        moves = [{"offset": claim_at, "quote": "the claim"}]
        # Quoted extents: the rule reads positions, and a point unit at the
        # move's start would be the move's own unit (nearest-before, #3395).
        population = [
            SelectableUnit(
                unit_id="other_par",
                text="x",
                offset=0,
                source_quote="first paragraph",
            ),
            SelectableUnit(
                unit_id="rests_on",
                text="x",
                offset=raw.index("evidence"),
                source_quote="evidence 3",
            ),
        ]
        named = rests_on_unit_ids(self._state(raw, moves), population)
        assert named == frozenset({"rests_on"})

    def test_a_non_carrying_unit_is_skipped_for_an_earlier_carrier(self):
        """The carrier test is what candidate (b) adds over "just the unit
        before": a plain sentence between the evidence and the move is not
        the unit the claim draws from."""
        raw = "said 7 things. plain words follow. the claim ends."
        claim_at = raw.index("the claim")
        moves = [{"offset": claim_at, "quote": "the claim"}]
        population = [
            SelectableUnit(
                unit_id="carrier",
                text="x",
                offset=raw.index("said"),
                source_quote="said 7 things",
            ),
            SelectableUnit(
                unit_id="plain",
                text="x",
                offset=raw.index("plain"),
                source_quote="plain words follow",
            ),
        ]
        named = rests_on_unit_ids(self._state(raw, moves), population)
        assert named == frozenset({"carrier"})

    def test_an_apostrophe_alone_is_not_a_carrier(self):
        """French elision (`l'assemblée`, `d'une`) is everywhere and is not
        evidence: measured on c13–c15, counting `'` and `’` as carriers lets
        74–76 % of the positioned units through (59–61 % without), while the
        judged outcome is the same 7/9 rows and 2/14 false positives with or
        without them. Born red on the first head of this PR, where the
        apostrophe still counted."""
        raw = "said 7 things. l'assemblée suit. the claim ends."
        claim_at = raw.index("the claim")
        moves = [{"offset": claim_at, "quote": "the claim"}]
        population = [
            SelectableUnit(
                unit_id="carrier",
                text="x",
                offset=raw.index("said"),
                source_quote="said 7 things",
            ),
            SelectableUnit(
                unit_id="elision",
                text="x",
                offset=raw.index("l'assemblée"),
                source_quote="l'assemblée suit",
            ),
        ]
        named = rests_on_unit_ids(self._state(raw, moves), population)
        assert named == frozenset({"carrier"})

    def test_a_unit_whose_extent_reaches_the_move_stays_priority_not_rests_on(self):
        raw = "one.\n\nearly 2 evidence so the claim follows.\n\nlast."
        claim_at = raw.index("the claim")
        moves = [{"offset": claim_at, "quote": "the claim"}]
        ev = raw.index("evidence")
        reaches = SelectableUnit(
            unit_id="reaches",
            text="x",
            offset=ev,
            source_quote=raw[ev : claim_at + 3],
        )
        before = SelectableUnit(
            unit_id="before",
            text="x",
            offset=raw.index("early"),
            source_quote="early 2",
        )
        named = rests_on_unit_ids(self._state(raw, moves), [reaches, before])
        # ``reaches`` overlaps the move: #3395 already gives it a seat, the
        # rule must skip to the next preceding carrier instead of
        # double-naming.
        assert named == frozenset({"before"})

    def test_a_move_first_in_its_paragraph_names_nothing(self):
        raw = "first 1.\n\nclaim opens its own paragraph.\n\nlast 3."
        claim_at = raw.index("claim")
        moves = [{"offset": claim_at, "quote": "claim"}]
        population = [
            SelectableUnit(unit_id="p1", text="x", offset=0, source_quote="first 1"),
            SelectableUnit(
                unit_id="p3", text="x", offset=raw.index("last"), source_quote="last 3"
            ),
        ]
        assert rests_on_unit_ids(self._state(raw, moves), population) == frozenset()

    def test_a_text_without_blank_lines_is_one_paragraph(self):
        """Measured on the panel: one long document carries no newline at all,
        so the paragraph rule must degenerate to nearest-preceding-carrier,
        defined and deterministic, never a crash."""
        raw = "alpha beta gamma. delta epsilon 4. the claim ends the text."
        claim_at = raw.index("the claim")
        moves = [{"offset": claim_at, "quote": "the claim"}]
        population = [
            SelectableUnit(unit_id="a", text="x", offset=0, source_quote="alpha beta"),
            SelectableUnit(
                unit_id="b",
                text="x",
                offset=raw.index("delta"),
                source_quote="delta epsilon 4",
            ),
        ]
        assert rests_on_unit_ids(self._state(raw, moves), population) == frozenset(
            {"b"}
        )

    def test_two_moves_sharing_their_rests_on_unit_name_it_once(self):
        raw = "intro.\n\nevidence 5 opens one claim then a second claim ends.\n\nlast."
        first_at = raw.index("one claim")
        second_at = raw.index("second claim")
        moves = [
            {"offset": first_at, "quote": "one claim"},
            {"offset": second_at, "quote": "second claim"},
        ]
        population = [
            SelectableUnit(
                unit_id="shared",
                text="x",
                offset=raw.index("evidence"),
                source_quote="evidence 5 opens",
            )
        ]
        assert rests_on_unit_ids(self._state(raw, moves), population) == frozenset(
            {"shared"}
        )

    def test_no_moves_names_nothing(self):
        raw = "a claim with no reading behind it."
        population = [SelectableUnit(unit_id="u", text="x", offset=0)]
        assert rests_on_unit_ids(self._state(raw, []), population) == frozenset()


class TestIdPrioritySeats3511:
    """#3511 — ``priority_unit_ids``: a seat beside the move's, same budget.

    The flag is OFF in production (no call site passes ids); these pin the
    behaviour the replay measures through, and the nesting contract #3523
    proved for spans under the same union.
    """

    def test_the_id_union_swaps_exactly_one_seat_and_keeps_the_budget(self):
        units = _spread(20)
        spans = [(30000, 30100)]
        base = select_for_budget(units, 6, text_length=60000, priority_spans=spans)
        on_span = [u for u in units if 29500 <= (u.offset or 0) <= 30500]
        outsider = next(
            u
            for u in units
            if u not in base.selected and u not in on_span and (u.offset or 0) < 2000
        )
        variant = select_for_budget(
            units,
            6,
            text_length=60000,
            priority_spans=spans,
            priority_unit_ids={outsider.unit_id},
        )
        base_ids = [u.unit_id for u in base.selected]
        variant_ids = [u.unit_id for u in variant.selected]
        assert outsider.unit_id in variant_ids
        assert len(variant_ids) == len(base_ids) == 6
        assert set(variant_ids) - set(base_ids) == {outsider.unit_id}
        assert variant.priority_taken == base.priority_taken + 1

    def test_the_union_never_takes_a_seat_from_a_priority_unit(self):
        units = _spread(20)
        spans = [(30000, 30100)]
        ids = {u.unit_id for u in units if (u.offset or 0) >= 50000}
        variant = select_for_budget(
            units, 6, text_length=60000, priority_spans=spans, priority_unit_ids=ids
        )
        variant_ids = set(u.unit_id for u in variant.selected)
        # Every span-overlapping unit that the base selection had stays.
        base = select_for_budget(units, 6, text_length=60000, priority_spans=spans)
        for u in base.selected:
            if 29500 <= (u.offset or 0) <= 30500:
                assert u.unit_id in variant_ids

    def test_the_id_union_keeps_the_nesting_contract(self):
        units = _spread(24)
        spans = [(20000, 20100), (40000, 40100)]
        ids = {f"arg_{i}" for i in range(1, 25, 3)}
        previous: set = set()
        for k in range(1, 15):
            sel = select_for_budget(
                units,
                k,
                text_length=60000,
                priority_spans=spans,
                priority_unit_ids=ids,
            )
            current = {u.unit_id for u in sel.selected}
            assert previous <= current, f"budget {k} dropped a unit of {k - 1}"
            previous = current

    def test_ids_without_spans_is_defined_and_deterministic(self):
        """Degenerate but defined: no span to measure distance from, the
        index tie decides — never the ValueError of an empty ``min``."""
        units = _spread(10)
        first = select_for_budget(
            units, 4, text_length=60000, priority_unit_ids={"arg_3"}
        )
        second = select_for_budget(
            units, 4, text_length=60000, priority_unit_ids={"arg_3"}
        )
        first_ids = [u.unit_id for u in first.selected]
        assert first_ids == [u.unit_id for u in second.selected]
        assert "arg_3" in first_ids
