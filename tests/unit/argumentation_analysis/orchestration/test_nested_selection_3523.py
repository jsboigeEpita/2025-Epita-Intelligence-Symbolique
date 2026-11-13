"""#3523 — the per-argument selection is NESTED, and the ceiling is 45.

The defect. ``_pick_by_targets`` re-spaced its even target grid
``j/(q+1)`` whenever a band's grant count ``q`` grew: at ``q = 1`` the
single target sits at 1/2, at ``q = 2`` the two targets move to 1/3 and
2/3 — a unit taken at ``q`` can lose its target at ``q + 1``. Measured
on the recorded c6 states, one document kept 2 of 5 judge passages at
budget 45 and 1 of 5 at 60. The miniature below is a band of 100 whose
units sit at 30/50/70: ``q = 1`` takes 50 (the only target), ``q = 2``
re-spaces to 100/3 and 200/3 and takes 30 and 70 — 50 is dropped.

The fix. The targets are consumed in NESTED-INSERTION order
(``_nested_target_fractions``: 1/2, 1/4, 3/4, 1/8, 3/8, ...), so the
``q``-run's sequence is replayed verbatim when one more grant arrives
and only the new target picks a unit. At the dyadic levels (q = 1, 3,
7, 15, 31) the target SET equals the old even grid — every budget the
panel probes (3 per band, 15 per band at 45) keeps the old targets, and
only the assignment order moves.

Deterministic, no LLM, invented ids only.
"""

import random

from argumentation_analysis.core.reading_window import (
    PER_ARGUMENT_CEILING,
    per_argument_unit_budget,
)
from argumentation_analysis.orchestration import selection as selection_mod
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    _nested_target_fractions,
    select_for_budget,
)

_TEXT = 300  # three bands of 100


def _issue_population():
    """The issue's miniature: one band's units at 30/50/70, one unit in
    each other band so the round-robin reaches band 0's second grant at
    k=4."""
    return [
        SelectableUnit(unit_id="arg_30", text="unit at 30", offset=30),
        SelectableUnit(unit_id="arg_50", text="unit at 50", offset=50),
        SelectableUnit(unit_id="arg_70", text="unit at 70", offset=70),
        SelectableUnit(unit_id="arg_150", text="unit at 150", offset=150),
        SelectableUnit(unit_id="arg_250", text="unit at 250", offset=250),
    ]


def _ids(population, k, **kwargs):
    return {u.unit_id for u in select_for_budget(population, k, **kwargs).selected}


class TestTheRaiseNeverDropsAPickedUnit:
    def test_the_issue_miniature_keeps_the_unit_the_old_grid_dropped(self):
        """Born red: under the re-spaced grid, k=3 picks arg_50 and k=4
        replaces it with arg_30 + arg_70. The nested order must keep it."""
        s3 = _ids(_issue_population(), 3, text_length=_TEXT)
        s4 = _ids(_issue_population(), 4, text_length=_TEXT)
        assert "arg_50" in s3, "the single 1/2 target must take the unit at 50"
        assert s3 <= s4, f"k=4 dropped {sorted(s3 - s4)} — selection is not nested"

    def test_every_k_on_a_pseudo_random_population(self):
        """The property, not one example: on a dense population with
        absent units mixed in, every k keeps every unit k-1 picked."""
        rng = random.Random(3523)
        population = [
            SelectableUnit(
                unit_id=f"arg_{i}",
                text=f"unit {i} " + "x" * rng.randint(0, 40),
                offset=rng.randint(0, 59_999),
            )
            for i in range(60)
        ] + [
            SelectableUnit(unit_id=f"absent_{i}", text=f"absent {i}") for i in range(4)
        ]
        previous = set()
        for k in range(1, len(population) + 1):
            current = _ids(population, k, text_length=60_000)
            assert previous <= current, (
                f"k={k} dropped {sorted(previous - current)} — a budget raise "
                "withdrew an examined unit"
            )
            previous = current

    def test_every_k_with_priority_spans(self):
        """The preference swap must not undo the nesting: a priority unit
        an earlier k had to give up for cannot vanish at k+1 simply because
        the base pick set moved."""
        rng = random.Random(3524)
        population = [
            SelectableUnit(
                unit_id=f"arg_{i}",
                text=f"unit {i}",
                offset=rng.randint(0, 59_999),
            )
            for i in range(50)
        ]
        spans = [(2_000, 2_400), (30_000, 30_500), (57_000, 57_400)]
        previous = set()
        for k in range(1, len(population) + 1):
            current = _ids(population, k, text_length=60_000, priority_spans=spans)
            assert (
                previous <= current
            ), f"k={k} dropped {sorted(previous - current)} with priority spans"
            previous = current


class TestTheNewGrantPicksTheNewTargetsUnit:
    def test_one_more_grant_adds_exactly_one_unit_and_it_is_the_new_targets(self):
        """The strong statement: at k=3 -> k=4 only band 0's q moves (1 -> 2),
        so the delta is exactly the nearest untaken unit to the newly
        inserted fraction 1/4 of [0, 100] — the unit at 30."""
        population = [
            SelectableUnit(unit_id=f"arg_{off}", text=f"unit at {off}", offset=off)
            for off in (10, 30, 50, 70, 90, 110, 150, 190, 210, 250, 290)
        ]
        s3 = _ids(population, 3, text_length=_TEXT)
        s4 = _ids(population, 4, text_length=_TEXT)
        assert s4 - s3 == {
            "arg_30"
        }, "the delta of one grant must be the new target's nearest unit"
        assert s3 <= s4


class TestTheTargetsAreTheEvenGridAtTheDyadicLevels:
    def test_the_fractions_are_a_prefix_sequence(self):
        for q in (0, 1, 2, 5, 14, 29):
            assert _nested_target_fractions(q) == _nested_target_fractions(q + 1)[:q]

    def test_the_panel_probe_levels_keep_the_old_even_grid(self):
        """q = 3 (three grants per band, the k=9 probes) and q = 15 (the
        budget-45 replay) must target the same positions as j/(q+1)."""
        for q in (1, 3, 7, 15, 31):
            assert sorted(_nested_target_fractions(q)) == [
                j / (q + 1) for j in range(1, q + 1)
            ], f"q={q} no longer targets the old even grid"


class TestTheCeilingIs45:
    def test_the_declared_ceiling_is_45(self):
        assert PER_ARGUMENT_CEILING == 45

    def test_the_longest_panel_document_is_rationed_to_45(self):
        # 179,139 chars ask 60 units at two per 6,016-char chunk.
        assert per_argument_unit_budget(179_139) == 45

    def test_documents_under_the_old_ceiling_are_unchanged(self):
        assert per_argument_unit_budget(320) == 10
        assert per_argument_unit_budget(56_430) == 20


class TestTheNestingIsLoadBearing:
    def test_restoring_the_respaced_grid_brings_the_drop_back(self, monkeypatch):
        """Mutation control kept as a witness: the OLD grid, reinstated,
        must make the nesting test above fail — otherwise the property is
        not what the nested order buys."""
        monkeypatch.setattr(
            selection_mod,
            "_nested_target_fractions",
            lambda q: [j / (q + 1) for j in range(1, q + 1)],
        )
        s3 = _ids(_issue_population(), 3, text_length=_TEXT)
        s4 = _ids(_issue_population(), 4, text_length=_TEXT)
        assert not s3 <= s4, "the re-spaced grid must drop a unit at q+1"
        assert "arg_50" in s3 and "arg_50" not in s4
