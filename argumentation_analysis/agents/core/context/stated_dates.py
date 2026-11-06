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

R1148 review (#3480-series rework): a floor is a YEAR. The first replay on the
recorded panel states measured the check firing on a document whose dating
nothing refutes — the bound was a media timestamp inside a URL query
parameter. A false refutation is worse than a missed one (it prints
« DÉGRADÉE » on a sound dating, carrying a "deterministic" label), so every
doubtful token falls on the side of NO floor: URLs, identifiers, decimals and
digit-grouped quantities are not dated references, and a year announced as
future is projected in the corpus's languages, not only French.
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

#: Sigils that mark the token's non-whitespace run as a URL, query string or
#: identifier rather than prose (R1148's measured false floor lived in
#: ``...?time=NNNN``). A four-digit token inside such a run is not a year.
_IDENTIFIER_SIGILS = ("://", "=", "?", "&", "#")

#: Markers that make a stated year a PROJECTION rather than a dated reference
#: ("d'ici 2088", "à l'horizon 2088", "by 2088", "until 2088"): a projected
#: year does not bound the writing date below, so it never takes part in the
#: confrontation — but it still rides the prompt, it IS a date the document
#: states. One short NAMED list per corpus language (the corpus is not
#: French-only, R1148); over-listing would silence real references, which is
#: the safe side of the error: a doubtful year loses its floor, never gains
#: one.
_FUTURE_MARKERS = (
    ("fr", "d'ici"),
    ("fr", "horizon"),
    ("en", "by"),
    ("en", "until"),
)

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
    ("d'ici 2088", "by 2088"): a stated date all the same, but never a floor
    for the writing date.
    """

    year: int
    quote: str
    offset: int
    projected: bool = False


def _is_year_token(text: str, start: int, end: int) -> bool:
    """Is the four-digit token at ``[start, end)`` a YEAR, not a number?

    R1148's three exclusion classes, each named by the review that measured
    them — a false refutation is worse than a missed one:

    - a decimal on either side (``2019,5``, ``2019.5``, ``1,2019``): a
      separator touching a digit is a decimal part or an English digit
      group, never a date;
    - a digit-grouped quantity (``12 2019``): the token is the tail of a
      space-grouped number when digits sit just before it across one space;
    - a URL, query string or identifier: the token's non-whitespace run
      carries one of :data:`_IDENTIFIER_SIGILS`.

    A sentence-final period (``… en 2019.``) has no digit after it and stays
    a year.
    """
    after = text[end] if end < len(text) else ""
    before = text[start - 1] if start > 0 else ""
    # a decimal part or an English digit group on either side
    if after in ".," and end + 1 < len(text) and text[end + 1].isdigit():
        return False
    if before in ".," and start >= 2 and text[start - 2].isdigit():
        return False
    # the tail of a space-grouped quantity ("12 2019")
    if start >= 2 and text[start - 1].isspace() and text[start - 2].isdigit():
        return False
    # the token's non-whitespace run, URL/identifier sigils
    run_start = start
    while run_start > 0 and not text[run_start - 1].isspace():
        run_start -= 1
    run_end = end
    while run_end < len(text) and not text[run_end].isspace():
        run_end += 1
    run = text[run_start:run_end]
    return not any(sigil in run for sigil in _IDENTIFIER_SIGILS)


def _is_projection(text: str, offset: int) -> bool:
    window = text[max(0, offset - _MARKER_WINDOW) : offset]
    window = window.replace("’", "'").lower()
    # Whole words only: "by" must not fire inside "lobby" — the marker names
    # a word of the announcement, not a substring of one.
    return any(
        re.search(rf"\b{re.escape(marker)}\b", window)
        for _language, marker in _FUTURE_MARKERS
    )


def extract_stated_dates(text: str) -> List[StatedDate]:
    """Every explicit YEAR in the text, in order of appearance.

    Deterministic by construction: same text, same list, same offsets — the
    opposite of an LLM reading, and the reason the confrontation needs no
    second opinion. Whitespace in the quote is collapsed so a reference
    spanning a line break still reads as one; the wording stays verbatim.
    A four-digit token that is not a year (URL, decimal, grouped quantity)
    is not a stated date at all: it neither rides the prompt nor bounds the
    writing date (R1148).
    """
    if not text:
        return []
    stated: List[StatedDate] = []
    for match in _YEAR_RE.finditer(text):
        if not _is_year_token(text, match.start(), match.end()):
            continue
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
    """Every explicit YEAR in a string, in order of appearance.

    Used on the historian's own answer: the situation's years are the dating
    the confrontation examines. The same not-a-year filters apply — a
    doubtful year on the situation side may only keep a sound dating sound,
    never manufacture a refutation.
    """
    return [
        int(match.group(0))
        for match in _YEAR_RE.finditer(text or "")
        if _is_year_token(text or "", match.start(), match.end())
    ]
