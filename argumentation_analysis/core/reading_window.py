"""Selection of the reading window head (#1737 step 2).

The 12+ reading-window sites slice the source text at a fixed offset 0
(``text[:2000..4000]``). On compilation corpora the head is a table of
contents, so the whole analysis chain reads metadata (measured in #1734,
pinned by the #1737 head-nature instrument: corpus_B head is metadata at
every window from 1500 to 4000). This module computes WHERE to read
instead — from the text itself, never a hard-coded offset (a constant
recalibrated on today's input is the exact defect being repaired).

Design constraint (coordinator R817): the selector must rest on properties
INDEPENDENT from the head-nature classifier, otherwise the acceptance test
"classifier says prose at the selected head" cannot fail. The classifier
verdicts from year-token density, list-marker lines, 5-gram repetition,
average sentence length, alpha ratio and sentence density — none of which
measure sub-clause punctuation. Prose carries subordinate clauses; TOC
entries are noun phrases. Measured on the known points (per kchar):
TOC head 1.33 vs every prose point 9.33-17.33 — a 7x gap on an observable
the classifier never reads. The two functions provably disagree on crafted
inputs (see tests): comma-less prose is blessed by the classifier and
refused here; a comma-dense date list is refused by the classifier and
accepted here.

Mechanism: scan the text in fixed stride segments; a segment passes when
its ``,;:`` density reaches the threshold; the selected offset is the
start of the first run of consecutive passing segments long enough to fill
the requested window. A boundary segment (half TOC, half prose) fails on
diluted density, so the run starts at the prose boundary. Deterministic,
pure, no LLM, no I/O — same input, same selection.
"""

import asyncio
import re
from collections.abc import Mapping as _MappingABC
from dataclasses import dataclass
from typing import Any, Awaitable, Dict, List, Mapping, Sequence, Tuple

_STRIDE = 500
_PUNCT_RE = re.compile(r"[,;:]")
#: #3517 — a word is a non-whitespace run. The fold applied to each run is
#: the citation rule's own (``normalise_for_citation``); the split only
#: fixes where a word begins and ends, so the offsets stay the document's.
_WORD_RE = re.compile(r"\S+")
# Per-kchar sub-clause punctuation threshold, calibrated in the gap between
# the known TOC head (1.33/kchar) and the weakest known prose point
# (9.33/kchar); the acceptance artifact re-checks both calibration points.
_PUNCT_PER_KCHAR_THRESHOLD = 4.0

STATUS_SELECTED = "selected"
STATUS_NO_PUNCTUATED_SPAN = "no_punctuated_span_found"
STATUS_EMPTY_INPUT = "empty_input"
STATUS_SHORT_INPUT = "short_input"
#: #3376 — the descent read a window centred on the evidence it was given.
STATUS_CENTRED_ON_QUOTE = "centred_on_quote"
#: #3376 — the descent fell back to the head because its quote could not be
#: located in the text. The fallback is the old behaviour; what is new is
#: that the record says it happened.
STATUS_HEAD_FALLBACK = "head_fallback_quote_not_located"

# --- #2915: window widths, one named constant per MEANING, not per
# --- value. A meaning shared across modules lives here; a file-local
# --- meaning stays in its file (leading underscore). These are the
# --- values the call sites already passed — #2915 only names them.

#: The wide-net window — the pipeline's widest reader. #2913 named it
#: in the fallacy plugin for that file's two readers; #2914's five
#: off-pipeline sites meant the same bound, so the constant moved
#: here (#2915).
WIDE_NET_WINDOW = 8000
#: The LLM extraction window — the excerpt of source text an
#: extraction/detection prompt reads on (#2850's measured 3000).
LLM_EXTRACTION_WINDOW = 3000
#: The logic reading window — the document excerpt a logic phase
#: translates (atoms, signature, reasoning).
LOGIC_READING_WINDOW = 4000
#: The logic per-argument window — the excerpt of ONE argument's
#: text inside batched/formula logic calls (a unit cap, not a
#: document cap).
LOGIC_ARGUMENT_WINDOW = 2000
#: The debate fallback window — debate material when no structured
#: parts exist.
DEBATE_FALLBACK_WINDOW = 1500
#: The fallacy descent window — the excerpt every taxonomy-descent prompt
#: reads (#3376). One bound for every branch, and the value is a quality
#: decision: it moves on a panel A/B, never as a repair side effect.
DESCENT_WINDOW = 500
#: The first-reading window (#3395, R1142) — NO cut: the first reading reads
#: exactly what the zero-shot comparison arm reads (``max_chars=0``, #2841
#: rule 4 — the same cut on both arms). A 30 000 bound covered 6 of the 10
#: panel documents; the four it left unread (47 644 to 179 139 characters)
#: are precisely the long documents where M1 is worst, and the zero-shot arm
#: read the longest of them whole in one call (91 s, 0.026 $). ``0`` means
#: the window IS the document — a text past the model's context fails loud
#: (``llm_error``, persisted) rather than reading a window the comparison
#: cannot use, and ``read_scope.whole_document`` keeps saying what was read.
FIRST_READING_WINDOW = 0

# --- #2850 lot 10: the whole text, in k calls (dispatch R1144). ---

#: Declared ceiling of the per-argument budget k(L) (dispatch R1144: "k(L)
#: instead of a flat 10, with a declared ceiling"). 30 is the extraction k
#: of the panel's longest document (179,139 chars): at two units per
#: capacity-chunk the longest panel document asks 60 and is rationed to 30 —
#: the ration is stratified by position (``select_for_budget``), and the
#: coverage record says k of N, never a silent drop.
PER_ARGUMENT_CEILING = 30

#: #2850 lot 10 — the per-argument floor: today's flat 10. Below it k(L)
#: never drops, so a short document's pass is byte-identical to today's.
PER_ARGUMENT_FLOOR = 10

#: #3432 ask 6(a) — the first reading's pillar budget has the same shape as
#: ``per_argument_unit_budget``. Three is the old flat bound, so a short
#: document keeps its prompt and state byte-identical. A long document may
#: rest on more than three distinct supports; the budget says HOW MANY may be
#: named, never WHICH, and the model still supplies only the thesis's own
#: supports. Eight is the largest named slot list that leaves room for local
#: moves under the unchanged MAX_MOVES = 12 (thesis + mechanism included).
PILLAR_FLOOR = 3
PILLAR_CEILING = 8

#: #3511 — the first reading's INVENTORY budget, its two declared ends. The
#: floor is the RENDER cap — ``first_reading.MAX_MOVES``, 12; the guard test
#: pins the pair so they cannot drift. The ceiling is the R1164 probe's own
#: measure: asked the zero-shot's question, one draw named 29 to 73
#: arguments on the panel's six long documents, and 80 is that observed
#: maximum plus ~10 %. It is no longer the per-argument family's ceiling
#: (the former tie, 30): the examination now FOLLOWS the inventory
#: (``min(N, max(k(L), named))`` at the selector), so tying the inventory
#: down to the pass's ration would ration the inventory by the pass again.
INVENTORY_FLOOR = 12
INVENTORY_CEILING = 80

#: #2850 lot 10 — the personas' anchored read: the window was built from the
#: first reading's defining moves (positions + passages), not from offset 0.
STATUS_ANCHORED_ON_MOVES = "anchored_on_defining_moves"

#: #2850 lot 10 — the personas' opening window survived because the first
#: reading failed (no LLM, no move, no position): the record names the
#: fallback instead of presenting the head as a choice.
STATUS_HEAD_FALLBACK_NO_MOVES = "head_fallback_no_first_reading"

#: #3522 — the document fitted ONE call (its length plus the header under
#: ``capacity``) and was read WHOLE. The measured defect this replaces: a
#: 5 049-character document was read to 1 225 characters as the first
#: reading named more moves, because the merged passages were cut at their
#: head (cycle 6, `state.reading_window_status`).
STATUS_WHOLE_DOCUMENT = "whole_document"


@dataclass(frozen=True)
class WindowSelection:
    """Result of the head selection.

    ``offset`` is where the caller should read from; ``status`` is the
    tri-state verdict (#1737: never a silent window). ``STATUS_SELECTED``
    means a punctuation-structured span fills the window from ``offset``;
    the other statuses keep ``offset=0`` so a consumer that ignores the
    status preserves its old behaviour instead of crashing.
    """

    offset: int
    window: int
    status: str


def _segment_passes(segment: str) -> bool:
    if not segment.strip():
        return False
    kchars = max(len(segment), 1) / 1000
    return len(_PUNCT_RE.findall(segment)) / kchars >= _PUNCT_PER_KCHAR_THRESHOLD


def _first_passing_run_start(passes: List[bool], needed: int) -> int:
    run = 0
    for i, ok in enumerate(passes):
        run = run + 1 if ok else 0
        if run >= needed:
            return (i - needed + 1) * _STRIDE
    return -1


def stratified_window_offsets(length: int, window: int, cap: int = 3) -> List[int]:
    """#2850 lot 8 — the offsets of the k stratified reading windows.

    Below one window this is today's single call: ``[0]`` and nothing else,
    byte-identical. Above it, ``k = min(cap, ceil(length / window))`` windows
    spread evenly over the document, the last ending at the document's end.
    Two properties the extraction relies on, both by construction:

    - while ``length <= k * window`` the windows TILE the document (spacing
      ``(length - window) // (k - 1) <= window``), so nothing up to three
      windows' worth of text is left unread;
    - beyond that, the windows sample the head, the middle and the end —
      the spread the audit demanded, never a wider single call.

    Entry 0 is the RAW plan's head offset: the caller keeps its own
    selector-chosen first window (#1737 — a TOC head is skipped by the
    selector, not re-read raw); the tail offsets are read as they are.
    Deterministic, pure — same text, same plan.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if cap <= 0:
        raise ValueError(f"cap must be positive, got {cap}")
    if length <= window:
        return [0]
    k = min(cap, -(-length // window))
    if k <= 1:
        return [0]
    return [i * (length - window) // (k - 1) for i in range(k)]


# --- #2850 lot 9: what ONE extraction call can read, from measurement.

#: Completion tokens one extraction unit costs — its text, its quote and its
#: JSON scaffolding. Upper end of the shape lot 8 posted (≈0.8-1.2 k tokens
#: for five units), because a capacity is a promise the model has to keep and
#: the unfavourable end of the measurement is the one that keeps it.
EXTRACTION_TOKENS_PER_UNIT = 240
#: The fixed part of one extraction answer (summary + JSON envelope), tokens.
EXTRACTION_FIXED_TOKENS = 400
#: Characters one unit costs at the extraction's PEAK density, measured on the
#: 48 local states that carry LLM units: 16 units in one 3 000-character read
#: (5.33 units / 1 000 characters; the median state carries 2.67). The peak is
#: the bound an integral read has to survive, not the median.
EXTRACTION_PEAK_CHARS_PER_UNIT = 188  # ceil(3000 / 16)


def one_call_extraction_capacity(
    max_completion_tokens: int, window: int = LLM_EXTRACTION_WINDOW
) -> int:
    """#2850 lot 9 — the longest document ONE extraction call can read.

    Two ceilings could bind, and only one of them is close: the prompt side of
    a 6 000-character read is a couple of thousand tokens, far under any
    context these models offer, while the ANSWER — one JSON object per unit,
    each carrying the unit's text and its quote — meets the completion cap at
    a document length that is measurable.

    So the capacity is arithmetic over three numbers, none of them a taste:
    the run's completion cap, the tokens one unit costs, and the peak density
    of the units the local states actually produced. ``cap * unit⁻¹ * chars``
    is how many units the cap buys; multiplying by the peak characters per
    unit is how much text can be expected to fill them.

    Below one window is today's window, never a shrink: a capacity that came
    out smaller would otherwise make the reading worse than the rule it
    replaces. A cap of 0 means the knob is off and the provider decides the
    ceiling — nothing is known about it, so no integral read is promised.
    """
    if max_completion_tokens <= 0:
        return window
    units = (
        max_completion_tokens - EXTRACTION_FIXED_TOKENS
    ) // EXTRACTION_TOKENS_PER_UNIT
    return max(window, units * EXTRACTION_PEAK_CHARS_PER_UNIT)


def reads_whole_text_in_one_call(
    length: int,
    max_completion_tokens: int,
    window: int = LLM_EXTRACTION_WINDOW,
) -> bool:
    """#2850 lot 9 — is this document read ONCE, whole?

    Strictly above one window: at or below it the caller keeps the #1737
    selector's single call byte-identical (lot 8's control — the replay band's
    cassettes must not see a new request), and an integral read would only
    relabel a call that already carries the whole document.
    """
    return (
        window < length <= one_call_extraction_capacity(max_completion_tokens, window)
    )


# --- #2850 lot 10: the whole text, in k calls (dispatch R1144). ---

#: The per-call reading capacity every k-calls axis chunks at: lot 9's
#: extraction capacity at the run's default completion cap. One number for
#: every multi-call reader (fact extraction, wide net, one call, the
#: personas' anchored windows), so no axis silently reads wider than the
#: capacity that was measured. A run that raises ``EXTRACTION_MAX_TOKENS``
#: recomputes it on the extraction path; the other axes share this
#: knob-at-default value.
WHOLE_TEXT_CALL_CAPACITY = one_call_extraction_capacity(8192)

#: #3446 — how many of the k reading calls may be IN FLIGHT at once. The
#: k calls tile the document (#2850 lot 10) but flew SEQUENTIALLY: on the
#: cycle-2 measures a 179k-char document cost 30 extraction + 30 wide-net
#: calls wall-to-wall, one stall (#3435) freezing the whole axis. The bound
#: is one name beside the capacity it bounds the calls OF — not a rate
#: limit (the #3435 budget composes inside each call) and not a window
#: change (every call still carries one capacity, byte-identical prompt).
K_CALL_CONCURRENCY = 4


async def gather_k_calls(
    calls: Sequence[Awaitable[Any]], bound: int | None = None
) -> List[Any]:
    """#3446 — run the k reading calls concurrently under one bound.

    Results come back in PLAN order — the order of ``calls`` — whatever
    order they complete in, so the merges that follow (cross-window dedup,
    first-quote-wins, answered-span union) read the same list the
    sequential loop read. The semaphore bounds how many calls are in
    flight; it does not cancel, retry or reorder anything. A call that
    raises still raises here, exactly as it did inline. No I/O of its
    own — the awaitables carry it.
    """
    if bound is None:
        # Read at call time so a monkeypatched knob is honoured (the def-time
        # default would freeze the first value it saw).
        bound = K_CALL_CONCURRENCY
    if bound <= 0:
        raise ValueError(f"bound must be positive, got {bound}")
    if not calls:
        return []
    gate = asyncio.Semaphore(bound)

    async def _one(awaitable: Awaitable[Any]) -> Any:
        async with gate:
            return await awaitable

    return list(await asyncio.gather(*(_one(c) for c in calls)))


def chunked_reading_offsets(length: int, capacity: int, start: int = 0) -> List[int]:
    """#2850 lot 10 — the offsets of the k chunks that TILE the document.

    ``k = ceil((length - start) / capacity)``; chunk ``i`` reads
    ``[offset_i, min(offset_i + capacity, length))`` — contiguous by
    construction, so the union of the chunks that answer IS the span
    ``[start, length)``. ``start`` carries the #1737 selector's offset: the
    head the selector already skipped (a table of contents) stays skipped —
    tiling from 0 would re-read metadata the selection exists to drop.

    Below one capacity this is ``[start]`` — today's single call,
    byte-identical. Deterministic, pure.
    """
    if capacity <= 0:
        raise ValueError(f"capacity must be positive, got {capacity}")
    if start < 0 or length <= start:
        return [max(0, start)]
    return [start + i * capacity for i in range(-(-(length - start) // capacity))]


def per_argument_unit_budget(
    length: int,
    capacity: int = WHOLE_TEXT_CALL_CAPACITY,
    ceiling: int = PER_ARGUMENT_CEILING,
    floor: int = PER_ARGUMENT_FLOOR,
) -> int:
    """#2850 lot 10 — k(L): the per-argument pass's unit budget.

    Two units per capacity-chunk, floored at today's 10 (a short document
    changes nothing), ceilinged at :data:`PER_ARGUMENT_CEILING` (declared).
    The units the budget buys are still chosen by position and salience
    (``select_for_budget`` + the first reading's priority spans) — this
    function only says HOW MANY, never WHICH.
    """
    k = 2 * (-(-length // capacity))
    return max(floor, min(ceiling, k))


def pillar_budget(
    length: int,
    capacity: int = WHOLE_TEXT_CALL_CAPACITY,
    ceiling: int = PILLAR_CEILING,
    floor: int = PILLAR_FLOOR,
) -> int:
    """#3432 ask 6(a) — how many thesis supports a first reading may name.

    One pillar per capacity-chunk, floored at the former flat three, with a
    named ceiling. Length buys room for supports the model has identified; it
    never invents a support, relaxes the citation rule, or raises MAX_MOVES.
    At the floor the prompt and state keep the pre-#3432 flat-three form.
    """
    k = -(-length // capacity)
    return max(floor, min(ceiling, k))


def inventory_budget(
    length: int,
    ceiling: int = INVENTORY_CEILING,
    floor: int = INVENTORY_FLOOR,
) -> int:
    """#3511 (R1164 rework) — how many entries the first reading's inventory
    may name (slots and local moves together).

    **No density**: the R1164 probe asked the zero-shot's question and the
    model named 29 arguments on a ~5k-character document — it does not ration
    arguments by length — so the bound no longer scales with the document.
    What remains is the pair of ends: every document gets the ceiling (the
    probe's observed maximum, 73, plus ~10 %, a bound the completion cap
    already holds — 73 arguments answered in ~4.2k completion tokens under
    8192), and the floor stays DECLARED as the pinned invariant with the
    render cap (``INVENTORY_FLOOR == first_reading.MAX_MOVES``, the guard
    test), never as a smaller bound a short document would get. The NOTE
    stays at 12 lines whatever the inventory carries (``MAX_MOVES``,
    render-only — one constant, one meaning). This says HOW MANY may be
    named, never WHICH: the model still names the arguments, and the
    citation rule still discards a quote the document does not carry.
    """
    del length  # no density: the bound does not scale with the document
    return max(floor, ceiling)


#: #2850 lot 10 — the personas' read: at most this many chars of each
#: passage around a defining move's position, so a handful of moves spread
#: over a long document still fit one call.
PERSONA_PASSAGE_MAX = 1200

#: #3522 — the share of one call the anchored passages must keep. The c5
#: panel measured about 3 600 characters actually read on the long
#: documents; c6 fell to about 2 950 as the anchors header grew with the
#: inventory (#3516) and took half the call. The header is fitted so the
#: passages keep at least this share whenever the capacity can hold it —
#: each passage's marker is paid for first, so the share is characters of
#: TEXT, not budget spent on the `[passage i — position N]` lines.
PERSONA_PASSAGE_SHARE = 3600

#: #2850 lot 10 — how much text on each side of a move's own span the
#: passage carries, when the budget allows it.
PERSONA_PASSAGE_PAD = 300

#: #2850 lot 10 — the floor under which a passage stops being a passage:
#: below this, the header (which must carry the thesis and mechanism) gets
#: the budget and the record says fewer moves were anchored.
_PERSONA_PASSAGE_FLOOR = 80

#: #3442 reach — the ROLE of a slot, in the reader's language. Mirrors
#: ``_SLOT_LABELS_FR`` in ``agents/core/reading/first_reading.py``: that
#: module imports this one, so the twin lives here rather than the import
#: turning circular. A pillar's ``kind`` stays in the closed vocabulary
#: (``claim``, ``concession``…) and is printed beside the role — the note
#: and the persona header spell the same slot the same way.
_PERSONA_SLOT_LABELS_FR = {
    "thesis": "thèse centrale",
    "mechanism": "mécanisme",
    "pillar": "pilier de la thèse",
}


def _anchors_header_lines(moves: Sequence[Mapping[str, Any]]) -> List[str]:
    """One line per defining move: role (or kind), position, reading.

    The header is what makes the passages readable as a whole — a reader
    (and the persona) sees the thesis, the mechanism and the moves each with
    its position, then the text around those positions. Deterministic; the
    label is written here, never by a model.

    A slot's ROLE is the label, its kind in parentheses: #3442's own rule —
    « the slot is printed, because “affirmation” would read as one more
    local move beside the ones the document makes elsewhere ». Without the
    role, a pillar would arrive as an ordinary ``claim`` and the persona
    would not know the passage carries the thesis.
    """
    lines: List[str] = []
    for move in moves:
        kind = str(move.get("kind") or "move")
        slot = str(move.get("slot") or "").strip()
        if slot == "pillar":
            label = f"{_PERSONA_SLOT_LABELS_FR[slot]} ({kind})"
        elif slot in _PERSONA_SLOT_LABELS_FR:
            label = _PERSONA_SLOT_LABELS_FR[slot]
        else:
            label = kind
        reading = str(move.get("reading") or "").strip()
        offset = move.get("offset")
        where = (
            f"position {offset}"
            if isinstance(offset, int) and not isinstance(offset, bool)
            else "position non localisée"
        )
        lines.append(f"- [{label}] {where} : {reading}")
    return lines


def _fit_anchors_header(
    moves: Sequence[Mapping[str, Any]], cap: int
) -> Tuple[str, int]:
    """#3522 — the anchors header, fitted by WHOLE LINES to ``cap``.

    Returns the header text and how many moves it actually names. The
    previous form cut the joined text at ``cap``, which printed half a
    reading as if it were a move's whole label; stopping on a line boundary
    keeps every printed line truthful, and the count lets the record say how
    many moves travelled with the read. When not even one line fits, the
    first is truncated and keeps the ellipsis — an anchor named partially
    beats no anchor at all, and the record says how many were carried.
    """
    if cap <= 0:
        return "", 0
    kept: List[str] = []
    used = 0
    for line in _anchors_header_lines(moves):
        cost = len(line) + (1 if kept else 0)
        if used + cost <= cap:
            kept.append(line)
            used += cost
            continue
        if not kept:
            kept.append(line[: max(0, cap - 1)].rstrip() + "…")
        break
    return "\n".join(kept), len(kept)


def _windowed_passage(
    text: str,
    start: int,
    end: int,
    allowance: int,
    anchors: Sequence[Tuple[int, int]],
) -> Tuple[str, int, int, int]:
    """#3522 — read a merged span without cutting it at its head.

    A span short enough is read whole. A longer one is windowed around the
    anchors it carries: each anchor's own quote is included, and what is
    left of the allowance is shared around them. The defect this replaces
    cut the merged span at its first ``allowance`` characters, so when many
    moves merged into one span — exactly what more named moves produce — the
    persona read the span's head and none of the moves past it.

    Returns ``(chunk, first_offset, last_offset, anchors_carried)``. The
    allowance stays a hard bound: a quote longer than the whole allowance
    (far past the citation rule's 8-40 words) is the only thing cut, and the
    separators count against it.
    """
    if end - start <= allowance:
        return text[start:end], start, end, len(anchors)
    if not anchors:
        return text[start : start + allowance], start, start + allowance, 0

    # The separators between windows are part of the allowance: reserving
    # them up front is what lets every anchor get a window instead of the
    # last ones falling off the end by three characters each.
    separator_room = 3 * max(0, len(anchors) - 1)
    share = max(1, (allowance - separator_room) // len(anchors))
    windows: List[Tuple[int, int]] = []
    for anchor_start, anchor_end in anchors:
        own = max(0, anchor_end - anchor_start)
        extra = max(0, (share - own) // 2) if share > own else 0
        window_start = max(start, anchor_start - extra)
        window_end = min(end, anchor_end + extra)
        if windows and window_start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], window_end))
        else:
            windows.append((window_start, window_end))

    picked: List[Tuple[int, int]] = []
    used = 0
    for window_start, window_end in windows:
        length = window_end - window_start
        separator = 3 if picked else 0  # " … "
        if picked and used + separator + length > allowance:
            break
        if not picked and length > allowance:
            window_end = window_start + allowance
            length = allowance
        picked.append((window_start, window_end))
        used += separator + length

    if not picked:
        return "", start, start, 0
    chunk = " … ".join(text[a:b] for a, b in picked)
    carried = sum(
        1
        for anchor_start, anchor_end in anchors
        if any(a <= anchor_start and anchor_end <= b for a, b in picked)
    )
    return chunk, picked[0][0], picked[-1][1], carried


def _merge_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    merged: List[List[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def persona_reading(
    text: str,
    moves: Sequence[Mapping[str, Any]],
    capacity: int = WHOLE_TEXT_CALL_CAPACITY,
    window: int = LLM_EXTRACTION_WINDOW,
) -> Tuple[str, WindowSelection, Dict[str, Any]]:
    """#2850 lot 10 — the excerpt a persona reads, anchored on the first reading.

    The personas read the DOCUMENT, not its opening: the first reading's
    thesis, mechanism and moves travel with their positions, and the text
    around those positions follows — the whole excerpt within one call's
    ``capacity``.

    * the document fits ``capacity`` with its header → ``STATUS_WHOLE_DOCUMENT``:
      the whole text is read, never a cut of it (#3522);
    * positioned moves → ``STATUS_ANCHORED_ON_MOVES``: merged passages around
      the spans, windowed around each anchor instead of cut at the passage's
      head, and stratified by position when the budget cannot carry them all
      (the extra block says ``windows`` read of ``moves_total``);
    * no usable position (the first reading failed, found nothing, or could
      not place its quotes) → ``STATUS_HEAD_FALLBACK_NO_MOVES``: the opening
      window survives, and the record says it is a fallback, not a choice.

    Returns ``(excerpt, selection, extra)``: the caller records the selection
    with the extra block (``windows``, ``chars_read``, ``moves_total``,
    ``moves_read``), so the bounds block can print what was actually read.
    Pure and deterministic — no LLM, no I/O.
    """
    if capacity <= 0:
        raise ValueError(f"capacity must be positive, got {capacity}")

    moves = [m for m in (moves or []) if isinstance(m, _MappingABC)]
    anchors: List[Tuple[int, int]] = []
    positioned: List[Tuple[int, int]] = []
    for move in moves:
        offset = move.get("offset")
        if not isinstance(offset, int) or isinstance(offset, bool):
            continue
        if offset < 0 or offset > len(text):
            continue
        quote = str(move.get("quote") or "")
        anchors.append((offset, min(len(text), offset + len(quote))))
        positioned.append(
            (
                max(0, offset - PERSONA_PASSAGE_PAD),
                min(len(text), offset + len(quote) + PERSONA_PASSAGE_PAD),
            )
        )
    positioned = [span for span in positioned if span[1] > span[0]]
    total_moves = len(anchors)

    # #3522 ask 1 — a document that fits ONE call is read whole. The header
    # takes whatever room is left, fitted by whole lines; the text wins the
    # argument over the labels, because the labels are only readable by
    # looking at the text they point into. This is measured, not a taste:
    # the panel's two short documents fit, and c6 read them to 1 225 chars.
    if text and len(text) + 2 <= capacity:
        header, header_moves = _fit_anchors_header(moves, capacity - len(text) - 2)
        excerpt = f"{header}\n\n{text}" if header else text
        return (
            excerpt,
            WindowSelection(0, len(text), STATUS_WHOLE_DOCUMENT),
            {
                "windows": 1,
                "chars_read": len(text),
                "moves_total": len(moves),
                "moves_read": header_moves,
            },
        )

    if not positioned:
        excerpt = text[:window]
        return (
            excerpt,
            WindowSelection(0, window, STATUS_HEAD_FALLBACK_NO_MOVES),
            {"chars_read": len(excerpt), "moves_total": len(moves), "moves_read": 0},
        )

    merged = _merge_spans(positioned)

    # A passage needs its marker ("[passage i — position N]\n") plus text:
    # below the floor, read fewer moves — stratified by position — rather
    # than emit markers with nothing under them.
    marker_room = 40

    # #3522 ask 3 — the header never starves the passages. It is fitted to
    # what the c5 share leaves once every passage's marker is paid for; the
    # half-call ceiling survives as the upper bound, and a capacity too small
    # to hold the share at all keeps the previous split.
    passage_need = PERSONA_PASSAGE_SHARE + len(merged) * marker_room
    if passage_need + 2 < capacity:
        header_cap = min(capacity // 2, capacity - passage_need - 2)
    else:
        header_cap = capacity // 2
    header, _header_moves = _fit_anchors_header(moves, max(0, header_cap))
    remaining = capacity - len(header) - 2  # the blank line under the header

    def _per_passage(span_count: int) -> int:
        # #3522 — a passage's marker is part of what it costs, so the marker
        # is paid BEFORE the text is shared out. The old division spent the
        # whole budget on text and then found no room for the markers it had
        # already promised, which is how the read fell under its share.
        if span_count <= 0:
            return 0
        return (remaining - span_count * marker_room) // span_count

    per = _per_passage(len(merged))
    if per < _PERSONA_PASSAGE_FLOOR:
        fit = max(1, remaining // (_PERSONA_PASSAGE_FLOOR + marker_room))
        if fit < len(merged):
            step = len(merged) / fit
            picked = sorted({int(i * step) for i in range(fit)})
            merged = [merged[i] for i in picked]
        per = max(1, _per_passage(len(merged)))

    per = max(1, min(PERSONA_PASSAGE_MAX, per))
    chunks: List[str] = []
    read_spans: List[Tuple[int, int]] = []
    used = 0
    moves_read = 0
    for index, (start, end) in enumerate(merged):
        marker = f"[passage {index + 1} — position {start}]\n"
        allowance = min(per, remaining - used - len(marker) - 2)
        if allowance <= 0:
            break
        inside = [a for a in anchors if a[0] >= start and a[1] <= end]
        chunk, first, last, carried = _windowed_passage(
            text, start, end, allowance, inside
        )
        if not chunk:
            continue
        chunks.append(f"{marker}{chunk}")
        read_spans.append((first, last))
        used += len(marker) + len(chunk) + 2
        moves_read += carried

    body = "\n\n".join(chunks)
    excerpt = f"{header}\n\n{body}" if header else body
    chars_read = sum(len(chunk) for chunk in chunks)
    offset = read_spans[0][0] if read_spans else 0
    extent = max(end for _, end in read_spans) - offset if read_spans else 0
    return (
        excerpt,
        WindowSelection(offset, extent, STATUS_ANCHORED_ON_MOVES),
        {
            "windows": len(chunks),
            "chars_read": chars_read,
            "moves_total": total_moves,
            "moves_read": moves_read,
        },
    )


def select_reading_head(
    text: str, window: int, stride: int = _STRIDE
) -> WindowSelection:
    """Compute where to start reading ``text`` for a ``window``-char span.

    Returns the start of the first stride-aligned run of
    punctuation-structured segments long enough to cover ``window``. When
    the head itself qualifies (ordinary prose corpora) the selection is
    offset 0 and nothing moves — that is the non-regression property: a
    corpus that already reads prose keeps reading the same span.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if stride <= 0:
        raise ValueError(f"stride must be positive, got {stride}")
    if not text or not text.strip():
        return WindowSelection(0, window, STATUS_EMPTY_INPUT)

    segments = [text[i : i + stride] for i in range(0, len(text), stride)]
    if len(text) < window:
        # Too short to fill any window: judge the head segments anyway so a
        # short punctuated text still reports selected, otherwise say so.
        if (
            _first_passing_run_start(
                [_segment_passes(s) for s in segments], len(segments)
            )
            == 0
        ):
            return WindowSelection(0, window, STATUS_SELECTED)
        return WindowSelection(0, window, STATUS_SHORT_INPUT)

    needed = max(1, -(-window // stride))
    passes = [_segment_passes(s) for s in segments]
    offset = _first_passing_run_start(passes, needed)
    if offset < 0:
        return WindowSelection(0, window, STATUS_NO_PUNCTUATED_SPAN)
    # The boundary segment can pass on diluted density while still carrying
    # a ragged tail of the skipped head (one partial line). Line-structured
    # documents (TOC entries, prose paragraphs) put a newline at that
    # boundary: advance past it so the window starts clean. Only when
    # something was skipped: an offset-0 selection reproduces today's
    # window exactly (non-regression on already-prose corpora).
    if offset > 0:
        nl = text.find("\n", offset)
        if 0 <= nl < offset + stride:
            offset = nl + 1
    return WindowSelection(offset, window, STATUS_SELECTED)


def head_selection(text: str, window: int) -> WindowSelection:
    """The selection of a fixed head read — ``text[:window]`` mirrored (#2850 lot 7).

    A site that slices the head by construction reads offset 0, never a sought
    span: this records what that read actually was without moving the slice.
    ``STATUS_SHORT_INPUT`` says the text was shorter than the window (read
    whole); ``STATUS_SELECTED`` that the window truly bounds the text.
    """
    if not text or not text.strip():
        return WindowSelection(0, window, STATUS_EMPTY_INPUT)
    if len(text) < window:
        return WindowSelection(0, window, STATUS_SHORT_INPUT)
    return WindowSelection(0, window, STATUS_SELECTED)


def folded_words(text: str) -> List[Tuple[str, int, int]]:
    """#3517 — ``(folded, start, end)`` per word: the citation rule's own
    fold, carrying the ORIGINAL text's offsets.

    The folding is ``normalise_for_citation`` per non-whitespace run and
    nothing more (#3389, #3465): case, typographic apostrophes and quotation
    marks, markdown markup. No stemming, no punctuation stripping, no
    stop-word removal — a word the two texts do not spell the same way is a
    different word, which is what keeps every consumer of this fold on the
    right side of "no fuzzy matching". Because only the CHARACTERS are
    folded, never the layout, the offsets address the document itself: this
    is the seam the locator (#3517) and the anchor scan (#3415) share, so
    "found" and "anchored" read the same words.

    #3517 note: the LOCATOR reads the rule's fold at character level
    (``folded_with_offsets``), because the rule matches substrings, not
    words; this word view is the anchor scan's (#3415). Both apply the same
    ``normalise_for_citation`` — one fold, two granularities.

    Imported lazily: the citation rule lives in the reporting package, and
    the window module must stay importable where nothing renders.
    """
    from argumentation_analysis.reporting.restitution.quote_fidelity import (
        normalise_for_citation,
    )

    words: List[Tuple[str, int, int]] = []
    for match in _WORD_RE.finditer(text or ""):
        folded = normalise_for_citation(match.group(0))
        if folded:
            words.append((folded, match.start(), match.end()))
    return words


def locate_quote(text: str, quote: str) -> int:
    """#3376/#3517 — the offset of a quote the document carries, or -1.

    Three passes, strongest first:

    1. **Exact match** — byte-identical, the offset ``text.find`` returns.
    2. **Whitespace runs** (#3376) — a model reproduces the wording but not
       the line breaks, so any whitespace run stands for any other.
    3. **The citation rule's fold** (#3517) — the rule that decides whether
       the quote "occurs" (#3389, #3465: case, typographic apostrophes and
       quotation marks, markdown markup, elision gaps ``[…]``) decides
       whether it can be located: a quote the rule accepts has an offset.
       Before this pass the two disagreed, and 11 % of the first reading's
       kept entries rendered with ``offset: None`` — kept by the rule,
       positioned by nothing, invisible to every span consumer (the
       selector's priority, the residue, the descent window).

    The fold is the rule's, character for character — never a resemblance
    score, never a relaxed rule. An elided quote locates at its FIRST
    fragment's start; the later fragments must follow in order, each after
    the previous one's end, exactly as ``occurs_in_document`` requires. The
    returned offset addresses the document (``text[offset:]`` starts the
    passage), never a folded copy.
    """
    if not text or not quote:
        return -1
    needle = quote.strip()
    if not needle:
        return -1
    index = text.find(needle)
    if index >= 0:
        return index
    tokens = [re.escape(token) for token in needle.split()]
    if tokens:
        match = re.search(r"\s+".join(tokens), text)
        if match:
            return match.start()
    return _locate_folded(text, needle)


def _locate_folded(text: str, needle: str) -> int:
    """The citation-rule pass of :func:`locate_quote` — the rule, with a map.

    The SAME fragments :func:`occurs_in_document` searches for, in the SAME
    folded document, in the SAME order — read through
    ``folded_with_offsets``, which keeps every folded character's original
    position. The predicate "the rule accepts ⟹ the locator finds" holds by
    construction (one fold, one fragment producer, one search), and the
    answer is the DOCUMENT offset of the first fragment's first character —
    never an offset into the folded copy.
    """
    from argumentation_analysis.reporting.restitution.quote_fidelity import (
        citation_fragments,
        folded_with_offsets,
    )

    fragments = citation_fragments(needle)
    if not fragments:
        return -1
    haystack, offsets = folded_with_offsets(text)
    if not haystack:
        return -1
    cursor = 0
    first = -1
    for fragment in fragments:
        found = haystack.find(fragment, cursor)
        if found < 0:
            return -1
        if first < 0:
            first = found
        cursor = found + len(fragment)
    return offsets[first]


def descent_selection(
    text: str, quote: str, window: int = DESCENT_WINDOW
) -> WindowSelection:
    """#3376 — WHERE the taxonomy descent reads for one candidate.

    A located quote centres the window on it, at the same size the descent
    always used: the descent then judges the candidate against the text the
    candidate was found in, instead of the document's opening. An unlocated
    quote (or none at all) keeps the head — the old behaviour — and says so
    through ``STATUS_HEAD_FALLBACK``, because a fallback nobody records is
    the defect this repairs.

    The offset is clamped so the window never runs past the end, and a text
    shorter than the window is read whole (offset 0): the bound bounds the
    prompt, it never pads it.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if not text or not text.strip():
        return WindowSelection(0, window, STATUS_EMPTY_INPUT)
    index = locate_quote(text, quote)
    if index < 0:
        head = head_selection(text, window)
        return WindowSelection(head.offset, head.window, STATUS_HEAD_FALLBACK)
    length = len(text)
    if length <= window:
        return WindowSelection(0, window, STATUS_CENTRED_ON_QUOTE)
    span = min(len((quote or "").strip()), window)
    offset = index - max(0, (window - span) // 2)
    offset = max(0, min(offset, length - window))
    return WindowSelection(offset, window, STATUS_CENTRED_ON_QUOTE)


def descent_text_and_selection(
    text: str, quote: str, window: int = DESCENT_WINDOW
) -> Tuple[str, WindowSelection]:
    """#3376 — the slice a descent prompt carries, and the selection that made it.

    Same contract as ``selected_text_and_selection``: one implementation of
    the slice, so the prompt cannot read a window the record does not name.
    """
    selection = descent_selection(text, quote, window)
    return text[selection.offset : selection.offset + selection.window], selection


def selected_text_and_selection(
    text: str, window: int, site: str, state: object = None
) -> Tuple[str, WindowSelection]:
    """#1737 step 3 — the slice AND the selection that produced it.

    One implementation of the record-or-fail-loud contract; ``selected_text``
    keeps the slice-only signature every other site uses. A site that must
    amend its own entry later — #3136: the PL wide-net pass adds the formulas
    the head produced, after the first record — carries the selection it
    recorded instead of recomputing one that could drift.
    """
    selection = select_reading_head(text, window)
    if state is not None:
        recorder = getattr(state, "record_reading_window", None)
        if recorder is None:
            raise TypeError(
                f"reading site '{site}': state {type(state).__name__} has no "
                "record_reading_window — pass the shared state or None, not "
                "an unrelated object"
            )
        recorder(site, selection)
    return text[selection.offset : selection.offset + window], selection


def selected_text(text: str, window: int, site: str, state: object = None) -> str:
    """#1737 step 3 wiring point: the slice a reading site feeds onward.

    Computes the selection (pure, deterministic), records it on the shared
    state when one is reachable, and returns the window slice. Sites with
    access to the shared state pass it (``context['_state_object']`` in the
    invoke layer, ``self.state`` in managers) so the status reaches the
    report; stateless components call without it and still get the computed
    slice. A state object that cannot record is a wiring bug, not a
    condition to shrug off: it fails loud (#1019) rather than silently
    dropping the status.
    """
    return selected_text_and_selection(text, window, site, state=state)[0]


def reading_state_from_context(context: object) -> object:
    """Resolve the shared state from a workflow context dict (#1737 step 3).

    The workflow executor writes the shared state as ``_state_object``
    (preferred) or ``unified_state``. Returns None when no
    ``UnifiedAnalysisState`` is reachable — stateless callers then skip the
    recording instead of guessing at an unrelated object.
    """
    state = None
    if isinstance(context, dict):
        state = context.get("_state_object") or context.get("unified_state")
    if state is None:
        return None
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    return state if isinstance(state, UnifiedAnalysisState) else None
