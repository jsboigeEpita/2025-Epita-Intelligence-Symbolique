"""#2850 slice A — ONE selector for every budget-bounded population.

The father defect, one sentence: a head window, or the first N items in
insertion order, stands for the document. This module is the ONE selection
gesture the coverage repair applies wherever a population meets a budget.

A unit is any addressable item carrying an offset in the source text — an
extracted argument (either producer) or a text segment. Selection is
stratified over the offset range: at least one unit per position band, then
fill. The within-band order is the stable insertion order — stated, because
no upstream signal exists at every selection point (measured: quality scores
exist only after quality runs, fallacy hits only after the fallacy pass; a
salience variant can come later, per phase, where a signal already exists
upstream).

The budget is real and unchanged: ``select_for_budget`` picks N units where
the call site used to take the first N — it never raises the cap
(anti-pendulum: a bigger head is still a head).

Units whose offset is a named absence claim no position: they never seed a
band and only fill leftover budget after positioned units, in stable order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "SelectableUnit",
    "SelectionResult",
    "select_for_budget",
    "stratified_position",
    "merged_population_units",
]


@dataclass(frozen=True)
class SelectableUnit:
    """One addressable population item, at its text position when known."""

    unit_id: str
    text: str
    producer: str = ""
    offset: Optional[int] = None
    source_quote: str = ""


@dataclass(frozen=True)
class SelectionResult:
    """The selection plus the coverage figure the state renders once.

    ``bands_covered`` counts the bands holding at least one SELECTED unit;
    ``bands_total`` is the band count the strategy used. Units without an
    offset count in ``k``/``n_total`` but never in ``bands_covered`` — the
    rendered sentence lends them no position.
    """

    selected: Tuple[SelectableUnit, ...]
    k: int
    n_total: int
    bands_covered: int
    bands_total: int


def stratified_position(
    units: Sequence[SelectableUnit], n: int, band_count: Optional[int] = None
) -> SelectionResult:
    """≥1 unit per position band, then fill; stable within band, stated.

    Bands are equal-count over the offset-sorted positioned population, so a
    band denotes a position RANGE of this document, not a fixed character
    constant. Round 1 takes the first unit of each band (stable order within
    band = insertion order); each further round takes the next unit of each
    band; absent-offset units fill what remains, last, in insertion order.
    The returned selection is in TEXT order (offset ascending, absent last):
    downstream phases read the document's order, not the extraction clock's.
    """
    if n <= 0:
        return SelectionResult((), 0, len(units), 0, 0)
    if not units:
        return SelectionResult((), 0, 0, 0, 0)

    indexed = list(enumerate(units))
    positioned = sorted(
        ((u, i) for i, u in indexed if u.offset is not None),
        key=lambda pair: (pair[0].offset or 0, pair[1]),
    )
    absent = [(u, i) for i, u in indexed if u.offset is None]

    if n >= len(units):
        # The budget holds the whole population: selection is the identity,
        # still in text order, and every band is covered by construction.
        all_ordered = tuple(u for u, _ in positioned) + tuple(u for u, _ in absent)
        bands = min(n, len(positioned)) if positioned else 0
        return SelectionResult(all_ordered, len(units), len(units), bands, bands)

    bands = band_count if band_count is not None else min(n, len(positioned))
    # Equal-count split, remainder to the earliest bands.
    base, extra = divmod(len(positioned), bands) if bands else (0, 0)
    band_lists: List[List[int]] = []
    cursor = 0
    for b in range(bands):
        size = base + (1 if b < extra else 0)
        band_lists.append(list(range(cursor, cursor + size)))
        cursor += size

    picked: List[int] = []  # indices into `positioned`
    chosen: Dict[int, bool] = {}
    round_idx = 0
    while len(picked) < n and round_idx < max(
        (len(bl) for bl in band_lists), default=0
    ):
        for bl in band_lists:
            if len(picked) >= n:
                break
            if round_idx < len(bl):
                idx = bl[round_idx]
                picked.append(idx)
                chosen[idx] = True
        round_idx += 1
    # Leftover budget → absent-offset units, stable insertion order.
    absent_picked = 0
    while len(picked) + absent_picked < n and absent_picked < len(absent):
        absent_picked += 1

    selected_positioned = [positioned[i][0] for i in picked if i < len(positioned)]
    selected_absent = [absent[j][0] for j in range(absent_picked)]
    covered = len(
        {b for b, bl in enumerate(band_lists) if any(i in chosen for i in bl)}
    )
    ordered = tuple(selected_positioned) + tuple(selected_absent)
    return SelectionResult(ordered, len(ordered), len(units), covered, bands)


def select_for_budget(
    units: Sequence[SelectableUnit], n: int, strategy: str = "stratified_position"
) -> SelectionResult:
    """The dispatch point every budget-bounded population goes through.

    One strategy today (``stratified_position``). An unknown name is a loud
    error, not a silent fallback to the head (#1019).
    """
    if strategy != "stratified_position":
        raise ValueError(
            f"select_for_budget: unknown strategy {strategy!r} — the only "
            "implemented strategy is 'stratified_position'"
        )
    return stratified_position(units, n)


def merged_population_units(
    state: Any, fallback_args: Optional[Sequence[Any]] = None
) -> List[SelectableUnit]:
    """The ONE population: every unit in ``identified_arguments``, either
    producer, with its provenance offset where one was recorded.

    #2850's two-producers-under-one-key defect meant downstream phases read
    whichever producer their context happened to carry — the extract output
    (llm_extract alone) on the quality/JTMS/PL-FOL paths. This builder reads
    the merged state population. ``fallback_args`` (the extract phase's own
    output) only serves a context with no state object: there the units mint
    positional ids, as before, and carry no offsets — the named absence.
    """
    identified = getattr(state, "identified_arguments", None)
    if isinstance(identified, dict) and identified:
        provenance = getattr(state, "argument_provenance", {}) or {}
        units: List[SelectableUnit] = []
        for arg_id, text in identified.items():
            prov = provenance.get(arg_id, {})
            units.append(
                SelectableUnit(
                    unit_id=str(arg_id),
                    text=str(text),
                    producer=str(prov.get("producer", "")),
                    offset=prov.get("offset"),
                    source_quote=str(prov.get("source_quote", "")),
                )
            )
        return units
    if fallback_args:
        return [
            SelectableUnit(
                unit_id=f"arg_{i + 1}",
                text=str(a.get("text", a) if isinstance(a, dict) else a),
                producer="llm_extract" if isinstance(a, dict) else "",
                source_quote=(
                    str(a.get("source_quote", "")) if isinstance(a, dict) else ""
                ),
            )
            for i, a in enumerate(fallback_args)
        ]
    return []
