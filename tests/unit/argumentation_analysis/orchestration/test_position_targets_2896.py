"""#2896 (b) retouch (R1053) — position targets, not rank quantiles.

The coordinator's zero-LLM dry run on the paid-run population measured
the rank spread following unit DENSITY: tier 1 holds 25 located units
dense in its first 5 %, so rank quantiles kept spending every pick there
and the thesis passage (arg_16, offset fraction 0.107) was never taken
at any k. Position quantiles over the same population take it (k=6 and
k=8), and the largest uncovered stretch measures 0.342/0.288/0.285
(rank) vs 0.224/0.193/0.174 (position) at k=6/8/10.

This witness builds the density defect in miniature — tier 1 dense at
its head with ONE isolated unit past the cluster (the thesis analogue),
tiers 2-3 evenly held — and asserts the selector reads by POSITION:

1. the isolated unit IS selected: under the rank rule its index sits
   past every interior quantile of the 21-unit tier, so it was never
   taken (the miniature of "the thesis is never taken");
2. the largest uncovered stretch clears a bound the rank rule fails on
   the SAME population (both values measured on this population are
   written below: rank 0.339 — red at birth — position 0.265).

Deterministic, no LLM, invented ids only.
"""

from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    select_for_budget,
)

_TEXT = 30_000  # thirds of 10_000

# Tier 1: 20 units dense at the head (100..955, step 45) + the isolated
# thesis analogue at 8900 — dense head, sparse tail, the measured shape.
_DENSE = [100 + j * 45 for j in range(20)]
_ISO = 8_900


def _population():
    offsets = (
        _DENSE
        + [_ISO]
        + [11_000, 15_000, 19_000]  # tier 2, evenly held
        + [21_000, 25_000, 29_000]  # tier 3, evenly held
    )
    return [
        SelectableUnit(unit_id=f"arg_{i + 1}", text=f"unit at {off}", offset=off)
        for i, off in enumerate(offsets)
    ]


def _iso_id():
    # the isolated unit's id: it follows the 20 dense units
    return f"arg_{len(_DENSE) + 1}"


def test_the_isolated_unit_is_taken_at_position_targets():
    """The thesis analogue: rank quantiles of a 21-unit tier dense at its
    head land at indices ~5/10/16 (all inside the dense cluster); the
    position targets 2500/5000/7500 send the 5000-target to the isolated
    unit (|8900-5000| = 3900 < |910-5000| = 4090)."""
    result = select_for_budget(_population(), 9, text_length=_TEXT)
    picked_ids = {u.unit_id for u in result.selected}
    assert _iso_id() in picked_ids, (
        f"the isolated unit {_iso_id()} (offset {_ISO}) was not taken — "
        "the spread followed unit density, not text position (R1053)"
    )


def test_stretch_beats_the_rank_rule_on_the_same_population():
    """Largest uncovered stretch, measured on THIS population:

    * rank quantiles (the pre-retouch rule): picks 325/550/820 in tier 1
      → the 820 → 11000 gap dominates: 10180/30000 = 0.339;
    * position targets: picks 910/955/8900 in tier 1 → the largest gap is
      955 → 8900: 7945/30000 = 0.265.

    The bound 0.30 sits between the two — red under rank, green under
    position, for the same population and the same budget."""
    result = select_for_budget(_population(), 9, text_length=_TEXT)
    stretch = result.largest_uncovered_stretch
    assert stretch is not None, "a positioned selection over a known text length must carry the stretch"
    assert stretch <= 0.30, (
        f"largest_uncovered_stretch = {stretch:.3f} — the rank rule's "
        "0.339 (measured on this population at birth); the position rule "
        "measures 0.265"
    )
