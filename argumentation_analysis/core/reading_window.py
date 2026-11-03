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

import re
from dataclasses import dataclass
from typing import List, Tuple

_STRIDE = 500
_PUNCT_RE = re.compile(r"[,;:]")
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


def locate_quote(text: str, quote: str) -> int:
    """#3376 — the offset of a verbatim quote, or -1 when it is not there.

    Exact match first. A model reproduces the wording but not always the line
    breaks, so a second pass lets any whitespace run stand for any other.
    Nothing else is normalised: a quote that merely resembles the text is not
    evidence, and centring a window on an approximate match would put the
    descent somewhere the candidate was not found.
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
    if not tokens:
        return -1
    match = re.search(r"\s+".join(tokens), text)
    return match.start() if match else -1


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
