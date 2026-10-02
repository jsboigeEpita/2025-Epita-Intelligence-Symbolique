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
    "state_text_length",
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

    ``span`` is the (start, end) FRACTION of the source text covered by the
    selected positioned units — ``None`` when the strategy has no text
    length (population bands) or no selected unit carries an offset. It is
    what makes a head-bound selection SAY head-bound: bands over text
    positions can saturate on a thin spread, the span cannot (review of
    #2887: a population anchored in the first 3,000 characters of a 56k text
    rendered « 8/8 bandes » — bands built over the population itself recompute
    the checked field from what it checks).

    ``largest_uncovered_stretch`` (#2896 a) is the largest FRACTION of the
    source text no selected unit covers — the gaps between consecutive
    selected offsets, the text's start and end included. It is the number
    that can FAIL: « 3/3 bands » stayed true on the paid run while a 0.41
    stretch (0.01 → 0.42) held 15 located units nobody read. ``None`` under
    the same conditions as ``span``.
    """

    selected: Tuple[SelectableUnit, ...]
    k: int
    n_total: int
    bands_covered: int
    bands_total: int
    span: Optional[Tuple[float, float]] = None
    largest_uncovered_stretch: Optional[float] = None


def _text_band(offset: int, text_length: int, band_count: int) -> int:
    """The fixed-width text band of ``offset`` — clamped, never out of range."""
    width = text_length / band_count
    return min(int(offset // width), band_count - 1) if width else 0


def _spread_indices(m: int, q: int) -> List[int]:
    """#2896 (b) — ``q`` evenly spaced INTERIOR positions over a band's
    ``m`` offset-sorted units: ``(k+1)·m/(q+1)`` for ``k = 0..q-1``,
    clamped, deduped.

    Interior quantiles, not the edges: a band's edges adjoin its
    neighbours' picks, so an edge pick spends a slot re-covering ground
    the next band already reads and leaves the band's own middle
    uncovered (``q=2`` at 0 %/100 % of the band ≈ the head-bias this
    replaces). Identity when the grant holds the whole band; a single
    grant takes the band's middle — a lone head pick is the head-bias
    this replaces. ``m > q`` makes the step exceed 1, so positions are
    strictly increasing and the dedup never fires in that range.
    """
    if q <= 0 or m <= 0:
        return []
    if q >= m:
        return list(range(m))
    seen: Dict[int, None] = {}  # dict-as-ordered-set
    for k in range(1, q + 1):
        seen[min(round(k * m / (q + 1)), m - 1)] = None
    return list(seen)


def _largest_uncovered_stretch(
    selected_offsets: Sequence[int], text_length: Optional[int]
) -> Optional[float]:
    """#2896 (a) — the largest text fraction no selected unit covers.

    Edges count: the gap from the text's start to the first selected
    offset, the gaps between consecutive selected offsets, and the gap
    from the last to the text's end. ``None`` without a text length or
    without a positioned pick (the same honesty conditions as ``span`` —
    an invented fraction would defeat the metric that exists to fail).
    """
    if not text_length or not selected_offsets:
        return None
    offsets = sorted(selected_offsets)
    edges = [offsets[0]]
    edges += [b - a for a, b in zip(offsets, offsets[1:])]
    edges.append(text_length - offsets[-1])
    return max(edges) / text_length


def stratified_position(
    units: Sequence[SelectableUnit],
    n: int,
    band_count: Optional[int] = None,
    text_length: Optional[int] = None,
) -> SelectionResult:
    """≥1 unit per position band, then fill; returned in text order, stated.

    Two band geometries, one round-robin:

    * ``text_length`` given (the recorded path, #2887 review): bands are
      fixed-width bands of ``[0, text_length]`` — thirds by default — so
      ``bands_covered < bands_total`` is REACHABLE: a head-only population
      covers one third whatever its size, and ``span`` carries the exact
      (start, end) fraction of the text the selected units occupy.
    * ``text_length`` None (stateless fallbacks): bands are equal-count over
      the offset-sorted positioned population, as in slice A — a band denotes
      a position range of this document. No span: without the text length a
      fraction of it would be invented.

    Within a band the picks are SPREAD over the band's extent (#2896 b):
    the round-robin's grant allocation runs first (counts only), then each
    band's ``q`` grants go to its evenly spaced interior quantile positions
    (``_spread_indices``) — the paid run showed head-of-band picks leaving a
    0.41 stretch nobody reads while the band carried located units
    throughout. ``k`` and the bands are unchanged; only the inner order
    moved. Absent-offset units fill what remains, last, in insertion order.
    The returned selection is ALWAYS in TEXT order (offset ascending,
    absent last), whatever the interleaving picked — downstream phases read
    the document's order, not the extraction clock's.
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

    if text_length is not None and text_length > 0:
        bands = band_count if band_count is not None else 3
        band_of = {
            i: _text_band(p[0].offset or 0, text_length, bands)
            for i, p in enumerate(positioned)
        }
        band_lists: List[List[int]] = [[] for _ in range(bands)]
        for i in range(len(positioned)):
            band_lists[band_of[i]].append(i)
    else:
        bands = band_count if band_count is not None else min(n, len(positioned))
        # Equal-count split, remainder to the earliest bands.
        base, extra = divmod(len(positioned), bands) if bands else (0, 0)
        band_lists = []
        cursor = 0
        for b in range(bands):
            size = base + (1 if b < extra else 0)
            band_lists.append(list(range(cursor, cursor + size)))
            cursor += size

    if n >= len(units):
        # The budget holds the whole population: selection is the identity,
        # still in text order, and every populated band is covered by
        # construction.
        all_ordered = tuple(u for u, _ in positioned) + tuple(u for u, _ in absent)
        covered = len({b for b, bl in enumerate(band_lists) if bl}) if bands else 0
        sel_offsets = [off for u, _ in positioned if (off := u.offset) is not None]
        span = (
            (min(sel_offsets) / text_length, max(sel_offsets) / text_length)
            if text_length and sel_offsets
            else None
        )
        return SelectionResult(
            all_ordered,
            len(units),
            len(units),
            covered,
            bands,
            span,
            _largest_uncovered_stretch(sel_offsets, text_length),
        )

    # #2896 (b) — pass 1: the round-robin's grant allocation, counts only
    # (identical walk to the pre-spread picker, so each band's share and
    # the absent-fill budget are unchanged); pass 2: each band's grants go
    # to its spread positions instead of its head.
    grants: List[int] = [0] * len(band_lists)
    remaining = n
    round_idx = 0
    while remaining > 0 and round_idx < max((len(bl) for bl in band_lists), default=0):
        for b, bl in enumerate(band_lists):
            if remaining <= 0:
                break
            if round_idx < len(bl):
                grants[b] += 1
                remaining -= 1
        round_idx += 1
    picked: List[int] = []  # indices into `positioned`
    chosen: Dict[int, bool] = {}
    for b, bl in enumerate(band_lists):
        for j in _spread_indices(len(bl), grants[b]):
            idx = bl[j]
            picked.append(idx)
            chosen[idx] = True
    # Leftover budget → absent-offset units, stable insertion order.
    absent_picked = 0
    while len(picked) + absent_picked < n and absent_picked < len(absent):
        absent_picked += 1

    selected_positioned = [positioned[i][0] for i in picked if i < len(positioned)]
    selected_absent = [absent[j][0] for j in range(absent_picked)]
    covered = len(
        {b for b, bl in enumerate(band_lists) if any(i in chosen for i in bl)}
    )
    # Text order ALWAYS (review nit): the round-robin interleaves bands,
    # the document does not.
    selected_positioned.sort(key=lambda u: u.offset or 0)
    ordered = tuple(selected_positioned) + tuple(selected_absent)
    sel_offsets = [off for u in selected_positioned if (off := u.offset) is not None]
    span = (
        (min(sel_offsets) / text_length, max(sel_offsets) / text_length)
        if text_length and sel_offsets
        else None
    )
    return SelectionResult(
        ordered,
        len(ordered),
        len(units),
        covered,
        bands,
        span,
        _largest_uncovered_stretch(sel_offsets, text_length),
    )


def select_for_budget(
    units: Sequence[SelectableUnit],
    n: int,
    strategy: str = "stratified_position",
    band_count: Optional[int] = None,
    text_length: Optional[int] = None,
) -> SelectionResult:
    """The dispatch point every budget-bounded population goes through.

    One strategy today (``stratified_position``). An unknown name is a loud
    error, not a silent fallback to the head (#1019). ``text_length`` routes
    the strategy to fixed text bands and yields the coverage span — pass it
    wherever the source text length is known (every state-backed call site).
    """
    if strategy != "stratified_position":
        raise ValueError(
            f"select_for_budget: unknown strategy {strategy!r} — the only "
            "implemented strategy is 'stratified_position'"
        )
    return stratified_position(units, n, band_count=band_count, text_length=text_length)


def state_text_length(state: Any) -> Optional[int]:
    """``len(state.raw_text)`` when the state carries the source text, else
    ``None`` — the ONE way call sites hand the text length to the selector,
    so recorded coverage is always in text terms (#2887 review)."""
    raw = getattr(state, "raw_text", None)
    return len(raw) if isinstance(raw, str) and raw else None


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
        if not isinstance(provenance, dict):
            # A side-table that is not a mapping is a named absence for every
            # unit — never a crash in the selector, never a fabricated
            # position (measured: a MagicMock state reached this line and
            # sorted MagicMocks).
            provenance = {}
        units: List[SelectableUnit] = []
        for arg_id, text in identified.items():
            prov = provenance.get(arg_id, {})
            if not isinstance(prov, dict):
                prov = {}
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
