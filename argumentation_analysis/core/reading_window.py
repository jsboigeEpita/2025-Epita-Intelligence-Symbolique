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
from typing import List

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
    return text[selection.offset : selection.offset + window]


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
