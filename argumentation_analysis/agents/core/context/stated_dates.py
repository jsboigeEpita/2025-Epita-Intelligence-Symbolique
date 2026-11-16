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

R1149 review (final rework): a floor is a CALENDAR DATE. The replay of the
real check on the 20 recorded panel states measured the head firing on 4 —
only one was the true case, a citation dated to the day. The other floors
came from years a bare mention supplies: an unmarked legal clause ("may be
amended after YYYY"), an announced event ("the YYYY <event>"). A year bounds
the writing date only when a month name, French or English, sits within a
short window before it. The error stays on the safe side: a doubtful year
loses its floor and never gains one.

#3589 extends the extraction one shape further: a month-day reference with
NO year at all ("le discours prononcé le 14 mars"), which the year reader
cannot see. A month-day is a floor only when a past-event cue carries it —
the same error rule, one level finer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

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

#: Month names that turn a stated year into a CALENDAR DATE (R1149) — the
#: corpus is not French-only, and the measured true case was an English
#: "speech of <month> <day>, YYYY". Full names only: an abbreviation is a
#: doubtful year, and a doubtful year loses its floor, never gains one.
_MONTH_NAMES = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

#: How far before the year a month name may sit and still carry it (R1149's
#: measured shapes: "January 15, 2019", "du 14 mars 2019").
_MONTH_WINDOW = 20

#: #3589 — past-event cues that make a month-day reference a FLOOR. A month
#: and a day alone ("le 14 mars") can announce a future meeting as well as
#: cite a past speech; the cue names the reference as an event already
#: delivered. One short NAMED list per corpus language, on the same error
#: rule as the years: a month-day no cue carries loses its floor, never
#: gains one.
_PAST_EVENT_CUES = (
    re.compile(r"\bprononc\w*\b", re.IGNORECASE),  # fr "ayant été prononcé le 14 mars"
    re.compile(r"\bdiscours\b", re.IGNORECASE),  # fr "dans le discours du 14 mars"
    re.compile(r"\bvenu\w*\b", re.IGNORECASE),  # fr "venu à Valmont le 14 mars"
    re.compile(
        r"\bdelivered\b", re.IGNORECASE
    ),  # en "having been delivered … 14 March"
    re.compile(r"\bspeech\b", re.IGNORECASE),  # en "in a speech at X on March 14"
    re.compile(r"\bcame\b", re.IGNORECASE),  # en "came to X on the 14th of March"
)

#: How far before the reference a past-event cue may sit and still carry it.
#: The measured shapes keep the cue within one short clause of the date.
_PAST_CUE_WINDOW = 48

#: Ordinal suffixes a day number may carry ("le 1er mai", "the 14th of
#: March"). The digit stays the day: the suffix is decoration, not another
#: number.
_DAY_ORDINAL_SUFFIX = r"(?:er|e|st|nd|rd|th)?"

#: Month-day shapes, day-first ("14 mars", "le 1er mai", "the 14th of
#: March") and month-first ("March 14", "January 15, 2019" read without its
#: year). Full month names only — an abbreviation is as doubtful here as it
#: is for a year (R1149), and a doubtful token loses its floor.
_MONTH_ALTERNATION = "|".join(re.escape(month) for month in _MONTH_NAMES)
_MONTH_DAY_DAY_FIRST = re.compile(
    rf"\b(\d{{1,2}}){_DAY_ORDINAL_SUFFIX}\s+(?:(?:of|de|du)\s+)?({_MONTH_ALTERNATION})\b",
    re.IGNORECASE,
)
_MONTH_DAY_MONTH_FIRST = re.compile(
    rf"\b({_MONTH_ALTERNATION})\s+(\d{{1,2}}){_DAY_ORDINAL_SUFFIX}\b",
    re.IGNORECASE,
)

#: Month name → month number, French and English halves mapped separately
#: (the concatenation in :data:`_MONTH_NAMES` would number the English
#: months 13-24; janvier and january are both 1).
_MONTH_TO_NUMBER = {month: index + 1 for index, month in enumerate(_MONTH_NAMES[:12])}
_MONTH_TO_NUMBER.update(
    {month: index + 1 for index, month in enumerate(_MONTH_NAMES[12:])}
)

#: The latest day each month can carry. February keeps 29: rejecting a real
#: leap-day citation would be a lost floor, and accepting a 30 February is
#: impossible — the regex bounds the day at two digits anyway, and 30/31 are
#: valid days of other months.
_DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

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
    for the writing date. ``calendar`` is True when a month name sits within
    :data:`_MONTH_WINDOW` characters before the year (R1149): only a calendar
    date bounds the writing date — a year a bare mention supplies (a legal
    clause, an announced event) bounds nothing.
    """

    year: int
    quote: str
    offset: int
    projected: bool = False
    calendar: bool = False


@dataclass(frozen=True)
class StatedMonthDay:
    """One month-day reference (#3589), positioned for the render.

    A month name carrying a day number, without a year — the shape on which
    a document cites an earlier speech ("le discours prononcé le 14 mars")
    while stating no year at all. ``offset`` is the position of the
    reference's first token (the day, in the day-first shapes; the month, in
    the month-first ones): the position a render can name.
    """

    month: int
    day: int
    quote: str
    offset: int


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


def _in_calendar_date(text: str, offset: int) -> bool:
    """Does a month name carry the year at ``offset`` (R1149)?

    The measured true floor was a citation dated to the day ("speech of
    January 15, 2019", "du 14 mars 2019"); the measured false floors were
    years a bare mention supplies. A month name within a short window before
    the year is what separates them. Whole words, case-insensitive (a month
    opens sentences); a month further away carries nothing.
    """
    window = text[max(0, offset - _MONTH_WINDOW) : offset].lower()
    return any(re.search(rf"\b{re.escape(month)}\b", window) for month in _MONTH_NAMES)


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
                calendar=_in_calendar_date(text, offset),
            )
        )
    return stated


def past_cited_bound(stated: Sequence[StatedDate]) -> Optional[StatedDate]:
    """The latest CALENDAR DATE the document cites as past — the writing
    date's floor.

    The document was written at or after this year: it cites it as already
    past. Projected years are excluded (they bound nothing), and so is every
    year no month name carries (R1149): a bare mention — a legal clause, an
    announced event — supplies no floor. Among equal maxima the first
    occurrence is returned — the one a render names.
    """
    candidates = [entry for entry in stated if entry.calendar and not entry.projected]
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


def _month_day_matches(text: str) -> List[Tuple[int, int, int, int]]:
    """Every month-day shape in the text, in order of appearance, as
    ``(offset, month, day, match_end)`` tuples with the day validated
    against its month."""
    found: List[tuple] = []
    for pattern, day_group, month_group in (
        (_MONTH_DAY_DAY_FIRST, 1, 2),
        (_MONTH_DAY_MONTH_FIRST, 2, 1),
    ):
        for match in pattern.finditer(text):
            month = _MONTH_TO_NUMBER[match.group(month_group).lower()]
            day = int(match.group(day_group))
            if not 1 <= day <= _DAYS_IN_MONTH[month - 1]:
                continue
            found.append((match.start(), month, day, match.end()))
    return sorted(found)


def _month_day_quote(text: str, start: int, end: int) -> str:
    window_start = max(0, start - _QUOTE_CONTEXT)
    window_end = min(len(text), end + _QUOTE_CONTEXT)
    return " ".join(text[window_start:window_end].split())


def extract_past_month_days(text: str) -> List[StatedMonthDay]:
    """Every month-day the document cites as an ALREADY DELIVERED event.

    #3589 — the year extraction (#3479) reads four-digit tokens only, so a
    document citing an earlier speech as "le discours prononcé le 14 mars"
    (no year printed) states no floor at all: the situation could claim that
    very speech and nothing would see it. This extraction reads the
    month-day shape itself, and keeps ONLY the references a past-event cue
    carries (:data:`_PAST_EVENT_CUES` within :data:`_PAST_CUE_WINDOW`
    characters before the date): a bare month-day can announce a future
    meeting as well as cite a past speech, and a doubtful token loses its
    floor, never gains one.

    Not caught (named for the pull request): a day written in words
    ("le quatorze mars"), an abbreviated month ("14 févr."), a month-day no
    listed cue carries, and a reference the cue introduces more than
    :data:`_PAST_CUE_WINDOW` characters before the date.
    """
    if not text:
        return []
    stated: List[StatedMonthDay] = []
    for offset, month, day, match_end in _month_day_matches(text):
        window = text[max(0, offset - _PAST_CUE_WINDOW) : offset].replace("’", "'")
        if not any(cue.search(window) for cue in _PAST_EVENT_CUES):
            continue
        stated.append(
            StatedMonthDay(
                month=month,
                day=day,
                quote=_month_day_quote(text, offset, match_end),
                offset=offset,
            )
        )
    return stated


def stated_month_days(text: str) -> List[StatedMonthDay]:
    """Every month-day shape a string names, in order of appearance.

    Used on the historian's own answer: each month-day the situation carries
    is a CLAIMED day, with or without a year beside it. No cue filter on
    this side — the situation is the claim under examination, not a
    reference to weigh.
    """
    if not text:
        return []
    return [
        StatedMonthDay(
            month=month,
            day=day,
            quote=_month_day_quote(text, offset, match_end),
            offset=offset,
        )
        for offset, month, day, match_end in _month_day_matches(text)
    ]
