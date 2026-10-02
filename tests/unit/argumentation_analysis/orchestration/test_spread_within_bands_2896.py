# -*- coding: utf-8 -*-
"""#2896 (b): within-band picks are spread, not each band's head.

The #2850 paid run measured it: the quality phase (k=8) picked
0.00/0.00/0.01 | 0.42/0.47/0.50 | 0.71/0.72 — every band's slots went to
its first units in offset order, leaving a 0.41 stretch nobody reads (15
located units of band 1 lie beyond 0.05 and are never picked). The spread
fix picks evenly spaced interior quantiles of each band's extent instead;
k and the bands are unchanged.
"""

import re

from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    select_for_budget,
)

_TEXT = 30_000
_STEP = 640


def _units():
    """45 units, evenly spread within each third (mirrors the dump's
    population: located units throughout each band, so the head-pick —
    not the population — is what leaves the gap)."""
    units = []
    n = 0
    for band_start in (0, 10_000, 20_000):
        for j in range(15):
            n += 1
            offset = band_start + j * _STEP
            units.append(
                SelectableUnit(
                    unit_id=f"arg_{n}",
                    text=f"Unit {n} claims something specific about point {n}.",
                    producer="test",
                    offset=offset,
                )
            )
    return units


def _largest_gap(selected):
    """Largest uncovered stretch, start and end included (the #2896 (a)
    definition, computed here independently of the fix)."""
    offsets = sorted(u.offset for u in selected if u.offset is not None)
    if not offsets:
        return None
    edges = [offsets[0] - 0]
    edges += [b - a for a, b in zip(offsets, offsets[1:])]
    edges.append(_TEXT - offsets[-1])
    return max(edges) / _TEXT


def test_band_picks_are_spread_not_the_head():
    """(b) witness: with head-picks the largest stretch is 0.312 (gap
    band1→band2); the spread brings it to 0.205. Bound 0.25 separates
    them with margin both sides."""
    selection = select_for_budget(_units(), 8, text_length=_TEXT)
    assert selection.k == 8
    assert selection.bands_covered == 3

    gap = _largest_gap(selection.selected)
    assert gap is not None
    assert gap <= 0.25, (
        f"largest uncovered stretch {gap:.3f} > 0.25 — within-band picks "
        "still cluster at the band heads"
    )


def test_selection_result_carries_the_stretch():
    """(a) witness: the SelectionResult records the largest uncovered
    stretch (start and end included) so analysis_coverage can carry it."""
    selection = select_for_budget(_units(), 8, text_length=_TEXT)
    recorded = getattr(selection, "largest_uncovered_stretch", None)
    assert recorded is not None, "SelectionResult has no largest_uncovered_stretch"
    assert abs(recorded - _largest_gap(selection.selected)) < 1e-9
