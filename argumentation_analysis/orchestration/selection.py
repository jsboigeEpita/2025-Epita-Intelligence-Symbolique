"""#2850 slice A — ONE selector for every budget-bounded population.

The father defect, one sentence: a head window, or the first N items in
insertion order, stands for the document. This module is the ONE selection
gesture the coverage repair applies wherever a population meets a budget.

A unit is any addressable item carrying an offset in the source text — an
extracted argument (either producer) or a text segment. Selection is
stratified over the offset range: at least one unit per position band, then
fill. Within a band the picks sit at evenly spaced interior POSITION
targets (R1053): a target lands where the text needs reading and takes the
nearest unit to it — rank quantiles were measured following unit DENSITY
instead (a tier dense in its first 5 % spent every pick there, and the
central thesis passage was never taken at any budget).

The budget is real and unchanged: ``select_for_budget`` picks N units where
the call site used to take the first N — it never raises the cap
(anti-pendulum: a bigger head is still a head).

Units whose offset is a named absence claim no position: they never seed a
band and only fill leftover budget after positioned units, in stable order.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from argumentation_analysis.core.shared_state import unit_extent

__all__ = [
    "SelectableUnit",
    "SelectionResult",
    "TargetSelection",
    "select_for_budget",
    "select_across_targets",
    "coverage_figure",
    "stratified_position",
    "merged_population_units",
    "named_move_residue",
    "named_moves_with_retained_finding",
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
    selected positioned units — the end being the last unit's END
    (``offset + len(text)``, #3393), never its start. ``None`` when the
    strategy has no text length (population bands) or no selected unit
    carries an offset. It is what makes a head-bound selection SAY
    head-bound: bands over text positions can saturate on a thin spread,
    the span cannot (review of #2887: a population anchored in the first
    3,000 characters of a 56k text rendered « 8/8 bandes » — bands built
    over the population itself recompute the checked field from what it
    checks).

    ``largest_uncovered_stretch`` (#2896 a) is the largest FRACTION of the
    source text no selected unit covers — measured on the units' coverage
    intervals, merged (#3393), the text's start and end included. It is the
    number that can FAIL: « 3/3 bands » stayed true on the paid run while a
    0.41 stretch (0.01 → 0.42) held 15 located units nobody read. ``None``
    under the same conditions as ``span``.
    """

    selected: Tuple[SelectableUnit, ...]
    k: int
    n_total: int
    bands_covered: int
    bands_total: int
    span: Optional[Tuple[float, float]] = None
    largest_uncovered_stretch: Optional[float] = None
    #: #3395 — how many of the selected units OVERLAP a first-reading move
    #: (``select_for_budget(..., priority_spans=...)``, the rule of
    #: ``_unit_overlaps_spans``, R1142). Zero on every call that passes no
    #: spans, so a caller can print "N des M unités examinées recouvrent un
    #: geste de la lecture première" — and print nothing when there was no
    #: reading to prefer.
    priority_taken: int = 0


def _text_band(offset: int, text_length: int, band_count: int) -> int:
    """The fixed-width text band of ``offset`` — clamped, never out of range."""
    width = text_length / band_count
    return min(int(offset // width), band_count - 1) if width else 0


def _nested_target_fractions(q: int) -> List[float]:
    """#3523 — interior targets in NESTED-INSERTION order: ``1/2``, ``1/4``,
    ``3/4``, ``1/8``, ``3/8``, ``5/8``, ``7/8``, ``1/16``, ...

    Each level bisects every gap of the previous one, left to right, so
    the first ``q`` fractions are a PREFIX of the first ``q + 1``: raising
    the budget ADDS a target instead of re-spacing the grid. That is the
    #3523 defect this replaces: the former grid ``j/(q+1)`` moved every
    target whenever ``q`` grew, and a unit taken at ``q`` could lose its
    target at ``q + 1`` (measured on the recorded c6 states: one document
    kept 2 of 5 judge passages at budget 45 and 1 of 5 at 60).

    At the dyadic levels (``q = 2**m - 1``: 1, 3, 7, 15, 31) the target
    SET equals the old even grid ``{j/(q+1)}`` — every budget the panel
    probes (3 per text band, 15 at budget 45) keeps the old targets. What
    moves is the ASSIGNMENT order: insertion-first, so the ``q``-run's
    choices are replayed verbatim and only the new target picks.
    """
    fractions: List[float] = []
    denominator = 2
    while len(fractions) < q:
        for numerator in range(1, denominator, 2):
            fractions.append(numerator / denominator)
            if len(fractions) >= q:
                break
        denominator *= 2
    return fractions


def _spread_indices(m: int, q: int) -> List[int]:
    """The RANK variant of the interior spread: ``q`` target positions over
    a band's ``m`` offset-sorted units, in the NESTED order
    (``_nested_target_fractions``) so a raise never drops an index.

    Kept as the fallback for a degenerate band extent (co-located units,
    where no target geometry exists) — and as the measured lesson: rank
    quantiles follow unit DENSITY (the paid run's tier 1, dense in its
    first 5 %, spent every pick there; the thesis at offset fraction
    0.107 was never taken), which is why the recorded path reads
    POSITION targets instead (``_pick_by_targets``).
    """
    if q <= 0 or m <= 0:
        return []
    if q >= m:
        return list(range(m))
    seen: Dict[int, None] = {}  # dict-as-ordered-set
    for fraction in _nested_target_fractions(q):
        seen[min(round(fraction * m), m - 1)] = None
    return list(seen)


def _pick_by_targets(
    positioned: Sequence[Tuple[SelectableUnit, int]],
    band: Sequence[int],
    q: int,
    start: float,
    end: float,
) -> List[int]:
    """#2896 (b) retouch (R1053) — ``q`` interior POSITION targets over
    the band's ``[start, end]`` extent, in their NESTED-INSERTION order
    (``_nested_target_fractions``: 1/2, 1/4, 3/4, 1/8, ...); each target
    takes the not-yet-taken unit closest to it, ties to the lower offset.

    #3523 — the targets are consumed in insertion order, never re-spaced
    by ``q``. The ``q``-run's sequence is therefore replayed verbatim when
    one more grant arrives: the earlier targets see the same pools and
    make the same choices, and only the NEW target picks a unit. So
    ``selection(k + 1) ⊇ selection(k)`` by construction — a budget raise
    can never drop a unit the pass already examined. The former ascending
    order over ``j/(q+1)`` re-placed every target whenever ``q`` moved.

    Position, not rank: a target lands where the TEXT needs reading and
    grabs the nearest unit, so a band dense at its head still sends its
    later targets across its extent. ``band`` is offset-ascending
    (``positioned`` is offset-sorted and band lists preserve that order),
    so the strict ``<`` below breaks distance ties toward the lower
    offset by construction.
    """
    picked: List[int] = []
    taken: Dict[int, bool] = {}
    for fraction in _nested_target_fractions(q):
        target = start + fraction * (end - start)
        best = -1
        best_d = -1.0
        for idx in band:
            if idx in taken:
                continue
            d = abs(float(positioned[idx][0].offset or 0) - target)
            if best < 0 or d < best_d:
                best, best_d = idx, d
        if best >= 0:
            taken[best] = True
            picked.append(best)
    return picked


def _band_extent(
    b: int,
    band_lists: Sequence[Sequence[int]],
    positioned: Sequence[Tuple[SelectableUnit, int]],
    text_length: Optional[int],
    band_count: int,
) -> Tuple[float, float]:
    """The band's OFFSET extent the position targets live in.

    Text bands (``text_length`` given): the fixed-width slice
    ``[b·width, (b+1)·width]`` — the same geometry ``_text_band`` assigns
    units by. Equal-count bands (the stateless fallback): from the band's
    first unit's offset to the next band's first unit's offset (its own
    last unit for the final band) — a boundary at real data, never an
    invented one.
    """
    if text_length:
        width = text_length / band_count
        return (b * width, (b + 1) * width)
    start = float(positioned[band_lists[b][0]][0].offset or 0)
    if b + 1 < len(band_lists) and band_lists[b + 1]:
        end = float(positioned[band_lists[b + 1][0]][0].offset or 0)
    else:
        end = float(positioned[band_lists[b][-1]][0].offset or 0)
    return (start, end)


def _positioned_spans(
    positioned: Sequence[SelectableUnit], text_length: Optional[int]
) -> List[Tuple[int, int]]:
    """#3393 — each positioned unit COVERS the extent ``unit_extent`` reads.

    A unit is not a point, and since #3502 its extent is its PASSAGE — the
    source quote when the unit carries one, the text otherwise — under the
    one rule of ``shared_state.unit_extent``: the paraphrase ``text`` runs
    ×2.6 past the located passage in the median (the coordinator's panel
    measure), and counting the overrun overstated the coverage figure. The
    old span took the last unit's START for the extent's end, so the
    coverage side said 0.00–0.73 where the reading record's own site lines
    said 0.00–1.00 for the same units: two producers, two truths, one
    wrong. Empty list without a text length (the caller's span/uncovered
    then render ``None``, the same honesty rule as before).
    """
    if not text_length:
        return []
    spans: List[Tuple[int, int]] = []
    for u in positioned:
        extent = unit_extent(u, str(u.text or ""))
        if extent is None:
            continue
        spans.append((int(extent[0]), min(int(extent[1]), text_length)))
    return spans


def _span_fraction(
    spans: Sequence[Tuple[int, int]], text_length: Optional[int]
) -> Optional[Tuple[float, float]]:
    """The (start, end) fraction of the covered intervals — ``None`` when
    nothing is positioned (no invented fraction, the #2887 rule)."""
    if not text_length or not spans:
        return None
    return (
        min(s for s, _ in spans) / text_length,
        max(e for _, e in spans) / text_length,
    )


def _largest_uncovered_stretch(
    selected_spans: Sequence[Tuple[int, int]], text_length: Optional[int]
) -> Optional[float]:
    """#2896 (a) — the largest text fraction no selected unit covers.

    Measured on COVERAGE intervals (#3393): the spans are merged first, then
    the edges count — the gap from the text's start to the first covered
    character, the gaps between merged runs, and the gap from the last
    covered character to the text's end. A tail unit running to the end
    leaves no uncovered tail, which the point-based read overreported by
    that unit's whole length. ``None`` without a text length or without a
    positioned pick (the same honesty conditions as ``span`` — an invented
    fraction would defeat the metric that exists to fail).
    """
    if not text_length or not selected_spans:
        return None
    ordered = sorted(selected_spans)
    gaps: List[int] = []
    first_s = ordered[0][0]
    cur_e = ordered[0][1]
    for s, e in ordered[1:]:
        if s > cur_e:
            gaps.append(s - cur_e)
        cur_e = max(cur_e, e)
    edges = [first_s] + gaps + [text_length - cur_e]
    return max(edges) / text_length


def _offset_in_spans(offset: int, spans: Optional[Sequence[Tuple[int, int]]]) -> bool:
    """#3395 — is this text position inside a first-reading move's span?"""
    if not spans:
        return False
    return any(int(a) <= offset < int(b) for a, b in spans)


def _population_starts(positioned: Sequence[Tuple[SelectableUnit, int]]) -> List[int]:
    """#3395 (R1142) — the distinct unit starts, ascending.

    The geometry the nearest-before rule of ``_unit_overlaps_spans`` reads:
    which unit start is the nearest one at or before a quote's start.
    """
    return sorted({unit.offset or 0 for unit, _ in positioned})


def _unit_overlaps_spans(
    unit: SelectableUnit,
    spans: Sequence[Tuple[int, int]],
    starts: Sequence[int],
) -> bool:
    """#3395 (R1142) — does this unit's evidence overlap a first-reading move?

    Two named rules, one per extent case. The old test — "the unit's start
    falls inside the quote" — never preferred a unit that starts BEFORE the
    quote and contains it, and measured on the cycle-0 states only 18-40 % of
    quotes contain a unit start, so consumer A stayed inert on four moves out
    of five on the long documents:

    - **extent known** (``source_quote`` carries the unit's passage): plain
      interval intersection — ``[u, u + len(source_quote))`` against every
      move span ``[a, b)``. Contains, contained, partial — all overlap.
    - **extent unknown** (the median ``source_quote`` length is 0 on half the
      panel documents): the unit's evidence is its start POINT. It overlaps a
      span when that point lies in it, or when the start is the NEAREST unit
      start at or before the span's start — the passage the quote lies in. A
      unit that merely starts earlier does not qualify: the nearest unit owns
      the passage.
    """
    u = unit.offset or 0
    if unit.source_quote:
        end = u + len(unit.source_quote)
        return any(u < int(b) and end > int(a) for a, b in spans)
    if _offset_in_spans(u, spans):
        return True
    return any(
        u <= int(a) and not any(u < s <= int(a) for s in starts) for a, _ in spans
    )


def _prefer_priority(
    positioned: Sequence[Tuple[SelectableUnit, int]],
    picked: List[int],
    n: int,
    priority_spans: Optional[Sequence[Tuple[int, int]]],
) -> Tuple[List[int], int]:
    """#3395 — make room for the units that overlap a first-reading move.

    ``picked`` holds indices into ``positioned`` and was established by the
    band round-robin. A unit whose evidence overlaps a defining move's quote
    (``_unit_overlaps_spans``, R1142: interval intersection when the extent
    is known, nearest-start-before otherwise) is a unit the report has
    ALREADY named, so the descent must examine it instead of one the
    stratified pass happened to prefer. Each missing priority unit takes the
    place of a picked NON-priority unit — the one farthest (by offset) from
    every priority span, so the pass gives up what relates least to the moves
    first, ties broken by position. The budget, the population and the
    returned text order are untouched; the coverage figure is recomputed
    downstream from ``picked``, so it stays the truth about what was actually
    read.

    Returns ``(picked, priority_taken)``. With no spans this is the identity
    — the byte-identical path every other caller keeps.

    #3523 — this swap preserves the nesting contract. The victim sequence
    is STATIC: the key (distance to the nearest span, then index) is a
    property of the unit, so "farthest of the remaining" consumed one at a
    time is exactly the non-priority units of ``picked`` in descending
    key order; and the missing priority units are visited in text order.
    With ``picked(k) ⊆ picked(k + 1)``, a unit the swap left in place at
    ``k`` can only lose its place to a victim consumed EARLIER in the
    static order, which a larger ``picked`` never pushes forward — every
    unit ``k`` kept (picked or swapped in) is kept at ``k + 1``.
    """
    if not priority_spans or not picked:
        return picked, 0
    spans = [(int(a), int(b)) for a, b in priority_spans if int(b) > int(a)]
    if not spans:
        return picked, 0
    starts = _population_starts(positioned)

    priority_all = {
        i
        for i, (unit, _) in enumerate(positioned)
        if _unit_overlaps_spans(unit, spans, starts)
    }
    if not priority_all:
        return picked, 0
    taken = [i for i in picked if i in priority_all]
    selected = list(picked)
    # Missing priority units, in text order (``positioned`` is offset-sorted).
    for candidate in sorted(priority_all):
        if candidate in selected:
            continue
        # Give up the picked non-priority unit farthest from every span.
        victims = [i for i in selected if i not in priority_all]
        if not victims:
            break
        farthest = max(
            victims,
            key=lambda i: (
                min(
                    abs((positioned[i][0].offset or 0) - (start + end) / 2)
                    for start, end in spans
                ),
                -i,
            ),
        )
        selected[selected.index(farthest)] = candidate
    return selected, len([i for i in selected if i in priority_all])


def stratified_position(
    units: Sequence[SelectableUnit],
    n: int,
    band_count: Optional[int] = None,
    text_length: Optional[int] = None,
    priority_spans: Optional[Sequence[Tuple[int, int]]] = None,
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

    Within a band the picks sit at interior POSITION targets (#2896 b,
    R1053 retouch): the round-robin's grant allocation runs first (counts
    only), then each band's ``q`` grants go to its nested targets
    ``start_b + f·width_b`` for ``f`` in ``_nested_target_fractions``
    (1/2, 1/4, 3/4, ...) — each target takes the nearest not-yet-taken
    unit (``_pick_by_targets``). The measured reason: rank quantiles
    follow unit DENSITY — on the paid-run population a tier dense in its
    first 5 % spent every pick there and the thesis passage (offset
    fraction 0.107) was never taken, while position targets took it; the
    largest uncovered stretch measured 0.342/0.288/0.285 (rank) vs
    0.224/0.193/0.174 (position) at k=6/8/10. ``k``, the grant allocation
    and the bands are unchanged; only the inner rule moved.

    #3523 — NESTED: ``stratified_position(k + Δ)`` keeps every unit
    ``stratified_position(k)`` picked, so a budget raise adds units and
    never drops an examined one. In the TEXT-band path (``text_length``
    given — every state-backed caller) the band count is fixed
    (``band_count`` or 3), the round-robin grants are monotone in ``n``,
    the within-band targets are consumed in insertion order
    (``_nested_target_fractions``), the absent fill takes the first
    ``n - picked`` in insertion order, and ``_prefer_priority`` consumes
    its victims in a static farthest-first sequence — each piece only
    ever ADDS picks. The equal-count fallback (no ``text_length``) is the
    stated exception: its band count IS ``min(n, len(positioned))`` (the
    slice-A rule, one band per pick — pinned by
    ``test_no_text_length_keeps_population_bands_and_no_span``), so its
    geometry moves with ``n``. Every caller of that path passes a FIXED
    ``n`` (they never compare ``k`` against ``k + Δ``), and the one
    ramped caller — the no-state per-argument fallback — has no offsets:
    its population is all-absent, and the insertion-order fill is itself
    nested. Absent-offset units fill what remains, last, in insertion
    order. The returned selection is ALWAYS in TEXT order (offset
    ascending, absent last), whatever the interleaving picked —
    downstream phases read the document's order, not the extraction
    clock's.
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
        sel_spans = _positioned_spans([u for u, _ in positioned], text_length)
        span = _span_fraction(sel_spans, text_length)
        return SelectionResult(
            all_ordered,
            len(units),
            len(units),
            covered,
            bands,
            span,
            _largest_uncovered_stretch(sel_spans, text_length),
            # The budget holds the whole population, so every priority unit is
            # in the selection by construction — counted, not claimed, under
            # the same overlap rule the bounded path applies (R1142).
            sum(
                1
                for unit, _ in positioned
                if _unit_overlaps_spans(
                    unit,
                    [
                        (int(a), int(b))
                        for a, b in (priority_spans or ())
                        if int(b) > int(a)
                    ],
                    _population_starts(positioned),
                )
            ),
        )

    # #2896 (b, R1053 retouch) — pass 1: the round-robin's grant
    # allocation, counts only (identical walk to the pre-spread picker, so
    # each band's share and the absent-fill budget are unchanged); pass 2:
    # each band's grants go to its interior POSITION targets — the nearest
    # unit to each target — instead of its rank quantiles.
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
        q = grants[b]
        if q <= 0 or not bl:
            continue
        if q >= len(bl):
            picked.extend(bl)
            for idx in bl:
                chosen[idx] = True
            continue
        start, end = _band_extent(b, band_lists, positioned, text_length, bands)
        if end > start:
            picks = _pick_by_targets(positioned, bl, q, start, end)
        else:
            # Degenerate extent (co-located units): no target geometry
            # exists — the rank spread is the stated fallback.
            picks = [bl[j] for j in _spread_indices(len(bl), q)]
        for idx in picks:
            picked.append(idx)
            chosen[idx] = True
    # Leftover budget → absent-offset units, stable insertion order.
    absent_picked = 0
    while len(picked) + absent_picked < n and absent_picked < len(absent):
        absent_picked += 1

    # #3395 — the first reading's moves get the seats they earn: a unit the
    # report has already named is examined instead of one the stratified pass
    # preferred. Recomputed coverage below then tells the truth about the
    # final picks, not the pre-swap ones.
    picked, priority_taken = _prefer_priority(positioned, picked, n, priority_spans)

    selected_positioned = [positioned[i][0] for i in picked if i < len(positioned)]
    selected_absent = [absent[j][0] for j in range(absent_picked)]
    covered = len(
        {b for b, bl in enumerate(band_lists) if any(i in chosen for i in bl)}
    )
    # Text order ALWAYS (review nit): the round-robin interleaves bands,
    # the document does not.
    selected_positioned.sort(key=lambda u: u.offset or 0)
    ordered = tuple(selected_positioned) + tuple(selected_absent)
    sel_spans = _positioned_spans(selected_positioned, text_length)
    span = _span_fraction(sel_spans, text_length)
    return SelectionResult(
        ordered,
        len(ordered),
        len(units),
        covered,
        bands,
        span,
        _largest_uncovered_stretch(sel_spans, text_length),
        priority_taken,
    )


def select_for_budget(
    units: Sequence[SelectableUnit],
    n: int,
    strategy: str = "stratified_position",
    band_count: Optional[int] = None,
    text_length: Optional[int] = None,
    priority_spans: Optional[Sequence[Tuple[int, int]]] = None,
) -> SelectionResult:
    """The dispatch point every budget-bounded population goes through.

    One strategy today (``stratified_position``). An unknown name is a loud
    error, not a silent fallback to the head (#1019). ``text_length`` routes
    the strategy to fixed text bands and yields the coverage span — pass it
    wherever the source text length is known (every state-backed call site).

    ``priority_spans`` (#3395) names the text ranges the report has ALREADY
    identified — the first reading's defining moves. Units inside them are
    examined first: the pass gives up the picked unit farthest from every
    span, never a priority unit, and keeps its budget. Absent (the default),
    the selection is byte-identical to the pre-#3395 behaviour.

    #3523 — the selection is NESTED: for every ``k``, every unit
    ``select_for_budget(population, k, ...)`` returns is also returned at
    ``k + Δ`` (same strategy, bands and spans; the exception, stated in
    ``stratified_position``, is the offset-less count-band fallback whose
    band count follows ``n``). A budget raise — the #3523 ceiling move —
    therefore adds examined units and never withdraws one. Witnessed in
    ``test_nested_selection_3523.py`` and held by construction, not by a
    post-hoc repair.
    """
    if strategy != "stratified_position":
        raise ValueError(
            f"select_for_budget: unknown strategy {strategy!r} — the only "
            "implemented strategy is 'stratified_position'"
        )
    return stratified_position(
        units,
        n,
        band_count=band_count,
        text_length=text_length,
        priority_spans=priority_spans,
    )


@dataclass(frozen=True)
class TargetSelection:
    """One selected entry, with what its TARGET contributes to the reading.

    ``rank`` is the entry's position in the producer's order within its target
    (1-based) and ``population`` the number the RECORD holds for that target —
    not the number shown. ``cut`` is true only when the target's population is
    not fully briefed, so a population that fits the budget renders exactly as
    before (#3373 control).
    """

    entry: Any
    target: str = ""
    rank: int = 0
    population: int = 0
    cut: bool = False


def select_across_targets(
    entries: Sequence[Any],
    n: int,
    target_key: str = "target_arg_id",
) -> List[TargetSelection]:
    """#3373 — take one entry per TARGET before any target takes a second.

    The counter-argument phase writes its output target by target, so the
    briefing's ``[:n]`` held the first targets' entries and nothing beyond
    them: on the R1137a record, 15 counters over 4 units out of 43 over 10,
    and the writer counted its briefing (« Cinq » for a unit carrying six).

    Every target is served in rounds — the first entry of each target, then
    the second of each, and so on — so no target is invisible while another
    is doubled, as long as the targets fit the budget. Within a target the
    producer's order holds. Entries that name no target are served after the
    targeted ones: they carry no population to state (a real rebuttal, merely
    unanchored — #3201), and they never crowd out a countered unit.

    The rounds decide WHAT is briefed; the producer's order decides WHERE it
    prints (R1140 rework). The round-robin interleaves targets; the returned
    list re-sorts the targeted picks by each entry's original index in
    ``entries``, and the unanchored follow in producer order. A population
    that fits therefore renders block for block as before, and under a cut
    each target's lines stay contiguous — the writer counts a run of lines,
    not a scatter.

    The budget is real and unchanged: never more than ``n``.
    """
    if n <= 0:
        return []
    groups: Dict[str, List[Tuple[int, Any]]] = {}
    unanchored: List[Tuple[int, Any]] = []
    for index, entry in enumerate(entries):
        target = ""
        if isinstance(entry, dict):
            value = entry.get(target_key)
            if isinstance(value, str):
                target = value.strip()
        else:
            value = getattr(entry, target_key, None)
            if isinstance(value, str):
                target = value.strip()
        if target:
            groups.setdefault(target, []).append((index, entry))
        else:
            unanchored.append((index, entry))

    populations = {target: len(items) for target, items in groups.items()}
    targeted: List[Tuple[int, TargetSelection]] = []
    round_index = 0
    while len(targeted) < n:
        progressed = False
        for target, items in groups.items():
            if round_index < len(items):
                progressed = True
                rank = round_index + 1
                origin, entry = items[round_index]
                targeted.append(
                    (
                        origin,
                        TargetSelection(
                            entry=entry,
                            target=target,
                            rank=rank,
                            population=populations[target],
                        ),
                    )
                )
                if len(targeted) >= n:
                    break
        if not progressed:
            break
        round_index += 1

    unanchored_picks = [
        TargetSelection(entry=entry, target="", rank=0, population=0)
        for _, entry in unanchored[: max(0, n - len(targeted))]
    ]

    # R1140 — the producer's order decides WHERE: the round-robin's picks
    # re-sorted by their original index in ``entries`` (stable for entries a
    # target serves in order, since ``items`` itself is index-ascending), the
    # unanchored already in producer order.
    selected: List[TargetSelection] = [
        item for _, item in sorted(targeted, key=lambda pair: pair[0])
    ] + unanchored_picks

    # #3373 rework (R1139) — ``cut`` is decided on WHAT IS SHOWN, never on the
    # rank. Comparing the rank against the population marked every line of a
    # target but its last, even when the target was briefed whole: 12 counters
    # over 5 targets under a cap of 15 produced 7 lines flagged onto a cut that
    # never happened. A target is cut exactly when the briefing shows fewer of
    # its entries than the record holds.
    shown = Counter(item.target for item in selected if item.target)
    selected = [
        replace(item, cut=shown[item.target] < item.population) if item.target else item
        for item in selected
    ]

    return selected


def coverage_figure(
    units: Sequence[SelectableUnit],
    text_length: Optional[int] = None,
    band_count: Optional[int] = None,
) -> Tuple[int, int, Optional[Tuple[float, float]], Optional[float]]:
    """The coverage figure of a GIVEN population — not of a selection.

    ``select_for_budget`` measures what a budget KEPT; this measures what a
    population ALREADY IS. A phase that does not select but CONSUMES (the
    governance vote: its options are the units the quality phase scored, not
    a fresh pick) still has a coverage — it must be measurable on the very
    units it consumed, or the record names another set.

    Same geometry, same honesty rules as the recorded path: fixed text bands
    when the text length is known (the span then says HOW THIN the covered
    fraction is), no bands and no span without it (a fraction of an unknown
    text would be invented), and a unit without an offset claims no position.

    Returns ``(bands_covered, bands_total, span, largest_uncovered_stretch)``.
    """
    positioned = [u for u in units if isinstance(u.offset, int)]
    offsets = [int(u.offset or 0) for u in positioned]
    bands_total = 0
    bands_covered = 0
    spans = _positioned_spans(positioned, text_length)
    span = _span_fraction(spans, text_length)
    if text_length and positioned:
        bands = band_count if band_count is not None else 3
        bands_total = bands
        bands_covered = len({_text_band(o, text_length, bands) for o in offsets})
    return (
        bands_covered,
        bands_total,
        span,
        _largest_uncovered_stretch(spans, text_length),
    )


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


def _positioned(units: Sequence[SelectableUnit]) -> List[SelectableUnit]:
    """The units that claim a position — the only ones "overlap" can read."""
    return [
        u for u in units if isinstance(u.offset, int) and not isinstance(u.offset, bool)
    ]


def anchored_units_for_named_moves(
    state: Any, population: Sequence[SelectableUnit]
) -> List[SelectableUnit]:
    """#3518 — the units the first reading's anchors supply where the
    extraction cut none.

    A named, positioned move whose span no population unit overlaps (the
    selector's own predicate — ``_unit_overlaps_spans`` over
    ``_population_starts``, the same geometry the residue reads) could never
    be examined, whatever the budget: there was nothing to examine. The
    anchor is verbatim and located (#3516), so the move SUPPLIES the unit:
    ``text`` and ``source_quote`` are the anchor (the descent window, #3376,
    centres on it), ``offset`` is the move's, ``producer`` names the first
    reading. One unit per passage: a later move over an already-anchored
    passage adds nothing. The id is the move's index in ``defining_moves``
    order — the same index the residue records — so every reader joins on it
    without a second mapping, and it cannot collide with the extraction's
    ``arg_N``/``paragraph_N`` namespaces.

    ONE producer, deterministic from the state: every consumer that must
    resolve these ids (the per-argument population, the coverage review's
    rows, the tier-2 binding, the fallacy target guard, the winner writer)
    re-derives the same list through this function. ``[]`` when the reading
    named nothing or every named move already overlaps a unit — the
    population stays byte-identical (the #3518 control).
    """
    from argumentation_analysis.agents.core.reading import (
        FIRST_READING_BASIS,
        defining_moves,
    )

    moves = defining_moves(state)
    if not moves:
        return []
    positioned = _positioned(list(population))
    starts = _population_starts([(u, u.offset or 0) for u in positioned])
    anchored: List[SelectableUnit] = []
    for index, move in enumerate(moves):
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            continue
        span = (offset, offset + len(quote))
        if any(_unit_overlaps_spans(u, [span], starts) for u in positioned):
            continue
        if any(
            (u.offset or 0) < span[1]
            and (u.offset or 0) + len(u.source_quote or "") > span[0]
            for u in anchored
        ):
            continue
        anchored.append(
            SelectableUnit(
                unit_id=f"reading_{index}",
                text=quote,
                producer=FIRST_READING_BASIS,
                offset=offset,
                source_quote=quote,
            )
        )
    return anchored


def anchored_unit_ids(state: Any) -> frozenset[str]:
    """The anchored units' ids, derived on the merged population — the ONE
    membership rule for writers that resolve a unit id (#3518: the fallacy
    target guard). Re-deriving is safe: the producer is deterministic from
    the state."""
    merged = merged_population_units(state)
    return frozenset(u.unit_id for u in anchored_units_for_named_moves(state, merged))


def named_move_residue(
    state: Any,
    selected_units: Sequence[SelectableUnit],
    population_units: Sequence[SelectableUnit],
) -> Dict[str, Any]:
    """#3511 (R1164 review §1+§2) — which named moves the examined set
    reached, and why the others did not: « nommé, non examiné » WITH its
    reason, never a silent truncation.

    The ONE producer, beside the geometry it reads: both writers call it —
    the per-argument selection (``invoke_callables``) and the winner reading
    (``_write_fallacy_winner_reading_to_state``, #3326), the latter on the
    MERGED selection, because ``record_analysis_coverage`` rebuilds the
    entry from scratch and a second write with ``added_by`` alone would
    erase this record (the measured defect: the keys gone on 5 of the 6
    long documents in c5).

    "Examined" is the selector's OWN word — ``_unit_overlaps_spans`` over
    ``_population_starts``, the same predicate ``_prefer_priority`` uses —
    never a paraphrase extent (the R1164 review §2: the paraphrase runs
    ~2.6× past the passage in the median, and counted 5 moves examined the
    selector's rule does not reach). Over ``defining_moves(state)`` (the
    same list, the same sort, the note reads indices against), a move is
    EXAMINED when at least one selected unit overlaps its span; the
    residue's reason is closed:

    * ``unpositioned`` — the move carries no located quote: no span, no
      overlap, nothing to examine against;
    * ``budget`` — the population holds an overlapping unit but the
      selection did not buy it;
    * ``no_overlapping_unit`` — the extraction never produced a unit there:
      the move is named, the pass had nothing to examine.

    Opaque by construction (kind, slot, index, reason — never a quote): the
    record joins the coverage entry, which renders to the reader. ``{}``
    when no move was named (a state the reading never ran on keeps its
    byte-identical record).
    """
    from argumentation_analysis.agents.core.reading import defining_moves

    moves = defining_moves(state)
    if not moves:
        return {}
    population = _positioned(population_units)
    # ``_population_starts`` reads the (unit, offset) pairs the selector's
    # own paths carry; the pair's int is the same offset the unit holds.
    starts = _population_starts([(u, u.offset or 0) for u in population])
    selected = _positioned(selected_units)

    examined: List[int] = []
    unexamined: List[Dict[str, Any]] = []
    for index, move in enumerate(moves):
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            unexamined.append(
                {
                    "index": index,
                    "kind": str(move.get("kind") or ""),
                    "slot": str(move.get("slot") or ""),
                    "reason": "unpositioned",
                }
            )
            continue
        span = (offset, offset + len(quote))
        if any(_unit_overlaps_spans(u, [span], starts) for u in selected):
            examined.append(index)
        elif any(_unit_overlaps_spans(u, [span], starts) for u in population):
            unexamined.append(
                {
                    "index": index,
                    "kind": str(move.get("kind") or ""),
                    "slot": str(move.get("slot") or ""),
                    "reason": "budget",
                }
            )
        else:
            unexamined.append(
                {
                    "index": index,
                    "kind": str(move.get("kind") or ""),
                    "slot": str(move.get("slot") or ""),
                    "reason": "no_overlapping_unit",
                }
            )
    return {
        "named_moves_total": len(moves),
        "named_moves_examined": examined,
        "named_unexamined": unexamined,
    }


def named_moves_with_retained_finding(state: Any) -> frozenset:
    """#3511 (R1164 review §3) — the named moves a lens retained a finding on.

    The #3510 predicate, REUSED not copied: ``coverage_family_by_unit``
    reads the coverage review's retained fallacies per unit; this binds
    them to the named moves by the selector's own overlap rule
    (``_unit_overlaps_spans`` over ``_population_starts`` — the same
    geometry ``named_move_residue`` reads, so "examined" and "carries a
    finding" name the same spans). Returns indices into
    ``defining_moves(state)`` order; empty is a measured « no lens
    retained anything on a named move » (no review record, or none bound).
    """
    from argumentation_analysis.agents.core.reading import (
        coverage_family_by_unit,
        defining_moves,
    )

    finding_units = coverage_family_by_unit(state)
    if not finding_units:
        return frozenset()
    moves = defining_moves(state)
    if not moves:
        return frozenset()
    # #3518 — the population the tier-2 binds through carries the anchored
    # units: a finding retained on one (``reading_N``, #3510's keying) must
    # reach its move, or the examination this PR buys would carry no finding.
    merged = merged_population_units(state)
    population = _positioned(
        list(merged) + anchored_units_for_named_moves(state, merged)
    )
    starts = _population_starts([(u, u.offset or 0) for u in population])
    carried = set()
    for index, move in enumerate(moves):
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            continue
        span = (offset, offset + len(quote))
        if any(
            u.unit_id in finding_units and _unit_overlaps_spans(u, [span], starts)
            for u in population
        ):
            carried.add(index)
    return frozenset(carried)
