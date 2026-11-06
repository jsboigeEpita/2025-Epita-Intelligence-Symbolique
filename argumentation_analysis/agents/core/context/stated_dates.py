"""The explicit dates a document states, read deterministically (#3479).

The historian persona dates the document from what the model knows (#3377) —
and on a corpus text whose header carries no date, that knowledge was never
confronted with the text itself: the persona dated a speech EARLIER than an
event the document cites as already past, and the render inherited the
anachronism (#3465 ask 4, cycle 3b). This module reads the dates OUT of the
document — no model, no second opinion — each with the quote and the offset a
render can name.

Two consumers, both in :mod:`~argumentation_analysis.agents.core.context.historian`:

- the historian's prompt carries the stated dates as the document's own dated
  references, so the model dates WITH them in view;
- the deterministic post-check compares the situation's dating against the
  latest year cited as past and degrades an impossible earlier dating.

Not a persona and no capability of its own: the census counts personas, this
is their instrument.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

#: An explicit year: four digits, 1000-2099, on word boundaries. A year is the
#: one date shape this extraction can read without a model and without a
#: calendar of month names — and every finer-grained date still contains the
#: year, so nothing stated is missed by shape.
_YEAR_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")

#: Markers that make a stated year a PROJECTION rather than a dated reference
#: ("d'ici 2088", "à l'horizon 2088"): a projected year does not bound the
#: writing date below, so it never takes part in the confrontation — but it
#: still rides the prompt, it IS a date the document states. The list is
#: deliberately tiny and named: over-listing would silence real references.
_FUTURE_MARKERS = ("d'ici", "horizon")

#: How far before the year a projection marker may sit and still count.
_MARKER_WINDOW = 24

#: Characters of context quoted around a stated year: enough for a render to
#: name the reference, short enough not to become an excerpt of the text.
_QUOTE_CONTEXT = 48

#: How many stated dates ride the historian's prompt — a bound on the prompt,
#: not on the confrontation (same father as the historian's stake bound).
#: Occurrences beyond it still take part in the confrontation bound.
PROMPT_MAX_DATES = 8


@dataclass(frozen=True)
class StatedDate:
    """One explicit year the document states, positioned for the render.

    ``projected`` is True when a marker says the year is announced as future
    ("d'ici 2088"): a stated date all the same, but never a floor for the
    writing date.
    """

    year: int
    quote: str
    offset: int
    projected: bool = False


def _is_projection(text: str, offset: int) -> bool:
    window = text[max(0, offset - _MARKER_WINDOW) : offset]
    window = window.replace("’", "'").lower()
    return any(marker in window for marker in _FUTURE_MARKERS)


def extract_stated_dates(text: str) -> List[StatedDate]:
    """Every explicit year in the text, in order of appearance.

    Deterministic by construction: same text, same list, same offsets — the
    opposite of an LLM reading, and the reason the confrontation needs no
    second opinion. Whitespace in the quote is collapsed so a reference
    spanning a line break still reads as one; the wording stays verbatim.
    """
    if not text:
        return []
    stated: List[StatedDate] = []
    for match in _YEAR_RE.finditer(text):
        offset = match.start()
        window_start = max(0, offset - _QUOTE_CONTEXT)
        window_end = min(len(text), match.end() + _QUOTE_CONTEXT)
        quote = " ".join(text[window_start:window_end].split())
        stated.append(
            StatedDate(
                year=int(match.group(0)),
                quote=quote,
                offset=offset,
                projected=_is_projection(text, offset),
            )
        )
    return stated


def past_cited_bound(stated: Sequence[StatedDate]) -> Optional[StatedDate]:
    """The latest year the document cites as past — the writing date's floor.

    The document was written at or after this year: it cites it as already
    past. Projected years are excluded (they bound nothing). Among equal
    maxima the first occurrence is returned — the one a render names.
    """
    candidates = [entry for entry in stated if not entry.projected]
    if not candidates:
        return None
    return max(candidates, key=lambda entry: entry.year)


def stated_years(text: str) -> List[int]:
    """Every explicit year in a string, in order of appearance.

    Used on the historian's own answer: the situation's years are the dating
    the confrontation examines.
    """
    return [int(match.group(0)) for match in _YEAR_RE.finditer(text or "")]
