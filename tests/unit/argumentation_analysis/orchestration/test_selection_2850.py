"""#2850 slice A — unit tests for the ONE selector.

The selector is the coverage repair's core gesture; these tests pin its
contract: stratified bands (≥1 selected unit per band), stable within-band
order, named-absence units never seeding a band, text-order return, and a
budget that never grows. All deterministic, no LLM.
"""

from typing import List, Optional

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    merged_population_units,
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
