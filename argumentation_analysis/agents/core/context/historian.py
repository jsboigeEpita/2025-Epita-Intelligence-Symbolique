"""Historian persona — the situation before the analysis (#3377, Epic #3374).

The pipeline may not use what the model knows. On an undated document the
render says the date "is only a deduction from the content" and that a place
"remains to be verified elsewhere"; the same-model zero-shot of #2841 dates and
situates it in its title line. That is M1: global context, where the zero-shot
wins. This persona closes it without blurring the line the renderer keeps — the
historian's output is labelled **model knowledge**, in the state and in the
render, and never reads as the text's own content.

What it writes (``state.historical_context``): a one-sentence situation, then
items — date, place, actors, and what was at stake then — each with a
confidence and a ``supports`` hint naming which element of the document the
claim explains, and ``blind_spot`` (#3432 ask 2): what the thesis leaves out,
historically — a reading, not a move, so it carries no quote either. No
quotation: a quote would make the claim look textual, which
is the failure mode this module exists to prevent.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    stamp_basis,
)

# #3576 — one father for the call → strip fence → parse → retry logic the two
# context personas share; the strategist imports the same helper.
from argumentation_analysis.agents.core.context._json_reply import (
    request_json_reply,
)
from argumentation_analysis.agents.core.context.stated_dates import (
    PROMPT_MAX_DATES,
    StatedDate,
    StatedMonthDay,
    extract_past_month_days,
    extract_stated_dates,
    past_cited_bound,
    stated_month_days,
    stated_years,
)
from argumentation_analysis.agents.core.reading import defining_moves
from argumentation_analysis.core.metadata_prompt import metadata_prompt_value
from argumentation_analysis.core.reading_window import persona_reading

logger = logging.getLogger("Historian")

#: Cap on the items the state carries. A situation, not an encyclopaedia: the
#: read is an orientation for the acts, and an unbounded list would crowd the
#: Act I prompt without adding a stake.
MAX_ITEMS = 8

#: How many extracted stakes the historian's prompt restates to the model —
#: a bound on the prompt, not on the era it may situate. Named so the reader
#: can check it against the rendered prompt instead of a hidden truncation.
_PROMPT_MAX_STAKES = 6

#: Cap on the blind spot (#3432 ask 2): it rides the Act III prompt, so an
#: unbounded sentence would crowd the conclusion it is there to sharpen.
#: Same order of magnitude as the interpretive question's cap (#1914).
BLIND_SPOT_CAP = 400

#: #3555 — how many place names the situation may contribute to the conflict
#: field. A situation is one sentence; more than a handful of names is a list
#: the render does not need, and the bound keeps the state small.
PLACE_MAX_CANDIDATES = 5

#: Characters of context quoted around a venue statement (#3555). Same order
#: as the dated references' quote (#3479): enough to name the passage, short
#: of becoming an excerpt of the text.
_PLACE_QUOTE_CONTEXT = 48

#: A capitalised word — the shape a place name takes in prose. The first
#: character class covers the accented capitals (``Évremont``) that ``[A-Z]``
#: alone misses, and ``\w`` continues through accents and hyphens.
_CAP_WORD = r"[A-ZÀ-ÖØ-Þ][\w'’-]*"

#: A run of up to five capitalised words (``Valbourg Belle Rive``,
#: ``Ville-Neuve``): a place name is a run, and a venue statement names one.
_CAP_RUN = rf"{_CAP_WORD}(?:\s+{_CAP_WORD}){{0,4}}"

#: Words a venue capture ends on that name the KIND of place, not the place
#: (``here in Valbourg City`` names Valbourg): stripped from the right, never
#: from the left — ``City`` inside ``Valburg City`` is part of the name and the
#: capture already runs through it.
_GENERIC_PLACE_WORDS = frozenset(
    {"city", "town", "village", "place", "cité", "ville", "capital"}
)

#: #3555 — the forms in which a document states WHERE it is being given.
#: Deictic only: ``this ... city of X`` and ``here in X`` point at the place
#: of the speech act itself. Measured on the cycle-7 corpus (R1167): the
#: address form ``people of X`` is NOT here — it named states and a
#: continent in documents given elsewhere, so admitting it would declare
#: venues the speaker is not in. That missed form is named in the pull
#: request rather than guessed at.
_DOCUMENT_VENUE_CUES = (
    re.compile(rf"\bthis (?:\w+ ){{0,3}}(?:city|town|village) of (?P<name>{_CAP_RUN})"),
    re.compile(rf"\bhere in (?P<name>{_CAP_RUN})"),
    re.compile(
        rf"\bcette (?:\w+ ){{0,3}}(?:ville|cité) (?:de |d')(?P<name>{_CAP_RUN})"
    ),
    re.compile(rf"\bici,? (?:à|en|dans) (?P<name>{_CAP_RUN})"),
)

#: #3555 — the prepositions that place a speech in the historian's French
#: situation (``prononcé à Valcourt``, ``depuis Waldborg``, ``au Palais-Neuf``). The
#: region prepositions (``dans``, ``en``) are NOT here: measured on the c10
#: state, a situation naming the STATE that contains the document's venue
#: states something compatible, and reading it as a venue would refute a
#: situation that is right.
_SITUATION_VENUE_PREPOSITIONS = ("à", "au", "aux", "depuis", "devant")

_SITUATION_VENUE_RE = re.compile(
    rf"\b(?:{'|'.join(_SITUATION_VENUE_PREPOSITIONS)})\b"
    rf"(?:\s+(?:la|le|les))?(?:\s+l')?\s*(?P<name>{_CAP_RUN})"
)

#: ``dans la ville de X`` names the kind of place explicitly and IS a venue;
#: a bare ``dans X`` does not (see above).
_SITUATION_PLACE_KIND_RE = re.compile(
    rf"\b(?:dans|en)\s+(?:la\s+|le\s+|l')?(?:ville|cité|village)\s+"
    rf"(?:de\s+|d')?(?P<name>{_CAP_RUN})"
)

#: #3586 — « à » also governs a PERSON: « face à Jean Dorlac », « répond à
#: X », « s'adresse à X », « opposé à X ». A relation cue, measured at cycle
#: 12 on doc_H, where the situation's « face à <person> » became the only
#: venue candidate and refuted a situation that was right. Each pattern ends
#: where the venitive preposition starts; it reads the text BEFORE the match.
#: The three verbs are read by their STEM (``répond\\w*``, ``s'adress\\w*``,
#: ``oppos\\w*`` — review of 15/11): every tense is covered by construction
#: and the elided pronoun before the verb (« qui l'opposait à X », measured at
#: c13-c14) does not matter, because the cue reads the end of the text before
#: the match. « siège au X » names a role in an institution, not the place
#: the speech was given (measured at c8, review of 15/11).
_PERSON_RELATION_CUES = (
    re.compile(r"\bface\s+$", re.IGNORECASE),
    re.compile(r"\brépond\w*\s+$", re.IGNORECASE),
    re.compile(r"\bs[’']?adress\w*\s+$", re.IGNORECASE),
    re.compile(r"\boppos\w*\s+$", re.IGNORECASE),
    re.compile(r"\bsiège\s+$", re.IGNORECASE),
)

HISTORIAN_PROMPT = """You are a historian. Situate the document below before anyone
analyses its reasoning: what period, what place, which actors, and what was at
stake THEN (not what the document argues).

Hard rules:
- You are stating what you know, as a historian. This is MODEL KNOWLEDGE, not
  the document's content; the report will label it as such.
- Never quote the document. Say what you know, and, for each item, name the
  element of the document it explains (its "supports" field) in your own words.
- State a confidence between 0 and 1 per item. A date you infer from style is
  not a date you know: say 0.3, not 0.9.
- "blind_spot" answers ONE question (#3432 ask 2): what does the thesis named
  in the excerpt LEAVE OUT, historically — who or what is absent from the
  story it tells? It is model knowledge too, never a quote, and an empty
  string is a valid answer: an invented omission would render as knowledge.
- If you do not know, return an empty list. An invented situation is worse than
  no situation: it would be rendered as knowledge.

Answer in French, with ONLY this JSON, no fences, no commentary:
{{"situation": "one sentence situating the document",
  "blind_spot": "what the thesis leaves out, historically — empty string if none",
  "items": [{{"claim": "...", "confidence": 0.0,
             "supports": "which element of the document this explains"}}]}}

Source metadata given by the pipeline: speaker={speaker}, venue={venue},
topic={topic}, era={era}, language={language}.

Enjeux already extracted from the text (read them, do not restate them as
history):
{stakes_block}

{dates_section}Document excerpt:
{excerpt}
"""


@dataclass
class HistoricalItem:
    """One item of model knowledge about the situation."""

    claim: str
    confidence: float = 0.0
    supports: str = ""
    basis: str = MODEL_KNOWLEDGE_BASIS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "confidence": self.confidence,
            "supports": self.supports,
            "basis": self.basis,
        }


@dataclass
class HistoricalContext:
    """The historian's read, ready for the state.

    ``status`` is discriminated on purpose (#3096's lesson): an LLM failure must
    never read as "completed, empty". The invoke turns a non-``ok`` status into
    a degraded phase carrying the reason.
    """

    situation: str = ""
    blind_spot: str = ""
    items: List[HistoricalItem] = field(default_factory=list)
    status: str = "no_llm"
    error: str = ""
    #: #3576 — how many model calls the reply took (1, or 2 when the second
    #: chance was used). Written to the state only when a second chance was
    #: actually used, so the pre-#3576 success shape is unchanged.
    attempts: int = 0
    #: #3576 — the bounded record of a reply ``json.loads`` refused (same
    #: father as the strategist's): decoder message, position, reply length
    #: and the window around the position. Empty unless ``parse_error``.
    parse_failure: Dict[str, Any] = field(default_factory=dict)
    # #3479 — set by the deterministic confrontation when the document's own
    # stated dates refute the situation's dating. ``to_state`` exposes the
    # degradation ONLY when it fired: a consistent dating changes nothing
    # anywhere, and neither does a text that states no date at all.
    dating_degraded: bool = False
    dating_model_year: Optional[int] = None
    dating_refuted_by: Optional[Dict[str, Any]] = None
    # #3555 — set by the deterministic confrontation when the document states
    # where it is being given and the situation names other places. Same
    # convention as the dating: the key exists only when the check fired.
    place_degraded: bool = False
    place_document: Optional[Dict[str, Any]] = None
    place_model_places: List[str] = field(default_factory=list)

    def to_state(self) -> Dict[str, Any]:
        payload = {
            "situation": self.situation,
            "blind_spot": self.blind_spot,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "basis": MODEL_KNOWLEDGE_BASIS,
        }
        # #3576 — the second chance and the parse cause ride the read they
        # belong to. Each key exists only when it carries something (the same
        # convention as ``dating``/``place`` below), so a first-try success
        # writes the pre-#3576 shape byte for byte.
        if self.attempts > 1:
            payload["attempts"] = self.attempts
        if self.error:
            payload["error"] = self.error
        if self.parse_failure:
            payload["parse_failure"] = dict(self.parse_failure)
        if self.dating_degraded:
            # #3479 — uncertain dating, named by the document's own dated
            # reference. The key exists only when the confrontation fired.
            payload["dating"] = {
                "status": "uncertain",
                "model_year": self.dating_model_year,
                "refuted_by": dict(self.dating_refuted_by or {}),
            }
        if self.place_degraded:
            # #3555 — the document states its own venue and the situation
            # names other places, named by the document's passage and offset.
            payload["place"] = {
                "status": "refuted",
                "document": dict(self.place_document or {}),
                "model_places": list(self.place_model_places),
            }
        return payload


def _clamp_confidence(value: Any) -> float:
    """Clamp a model-reported confidence into [0, 1]; unreadable → 0.0.

    Unreadable is 0.0 and not a default: an unmeasured confidence must read as
    unmeasured, the same rule #3029 applies to an absent detection score.
    """
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _stakes_block(state: Any) -> str:
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    descriptions = []
    for stake in (stakes.get("stakes") or [])[:_PROMPT_MAX_STAKES]:
        if isinstance(stake, dict):
            description = stake.get("description") or ""
            if description:
                descriptions.append(f"- {description}")
    return "\n".join(descriptions) if descriptions else "  (aucun enjeu extrait)"


def _dates_section(
    stated: Optional[List[StatedDate]],
    past_days: Optional[List[StatedMonthDay]] = None,
) -> str:
    """#3479 — the document's own dated references, for the historian's prompt.

    The section lists exactly the dates that BOUND the writing date — the
    same filtered set the confrontation reads (R1149: a calendar date, not
    projected). A year the rule does not bound on must not ride a section
    whose wording says "a dating you assign it earlier than one of them is
    impossible": that would hand the historian junk dated references again.

    #3589 — the month-day references the document cites as already
    delivered ride the same section, beside the years: a floor without a
    year is still a floor, and the model must date with it in view.

    Empty string when the document states no bounding date of either kind:
    the formatted prompt is then byte-identical to the one #3377 defined,
    which is the no-change control the issue demands.
    """
    bounding = [
        entry for entry in (stated or []) if entry.calendar and not entry.projected
    ]
    floors = list(past_days or [])
    if not bounding and not floors:
        return ""
    lines = [
        "Dated references the document itself states (deterministic " "extraction,",
        "offset = character position): the document was written AT OR AFTER",
        "each past-cited one — a dating you assign it earlier than one of",
        "them is impossible.",
    ]
    for entry in bounding[:PROMPT_MAX_DATES]:
        lines.append(f"- {entry.year} — « {entry.quote} » (offset {entry.offset})")
    if floors:
        lines.append(
            "Past month-day references the document itself cites as already "
            "delivered (no year printed): the speech cannot fall on one of "
            "those days, nor before one within the year you assign it."
        )
        for entry in floors[:PROMPT_MAX_DATES]:
            lines.append(
                f"- {entry.day}/{entry.month} — « {entry.quote} » (offset {entry.offset})"
            )
    return "\n".join(lines) + "\n\n"


def build_historian_prompt(
    state: Any,
    excerpt: str,
    stated_dates: Optional[List[StatedDate]] = None,
    past_month_days: Optional[List[StatedMonthDay]] = None,
) -> str:
    """Render the historian's prompt from the gathered evidence.

    #3479 — ``stated_dates`` are the explicit dates the DOCUMENT states,
    extracted from the whole text (not just the excerpt: the dated reference
    may sit outside the reading window). The historian dates with them in
    view. ``None`` or empty keeps the prompt byte-identical to the one #3377
    defined — a document that states no date changes nothing.

    #3589 — ``past_month_days`` are the month-day references the document
    cites as already delivered (no year printed). Same rule: ``None`` or
    empty changes nothing.
    """
    metadata = getattr(state, "source_metadata", {}) or {}
    # #3512 — an unrecorded field renders as an instruction, never as the
    # corpus placeholder: the model copies what the prompt shows.
    return HISTORIAN_PROMPT.format(
        speaker=metadata_prompt_value(metadata, "speaker"),
        venue=metadata_prompt_value(metadata, "venue"),
        topic=metadata_prompt_value(metadata, "topic"),
        era=metadata_prompt_value(metadata, "era", "date_or_year"),
        language=metadata_prompt_value(metadata, "language"),
        stakes_block=_stakes_block(state),
        dates_section=_dates_section(stated_dates, past_month_days),
        excerpt=excerpt,
    )


async def build_historical_context(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
) -> HistoricalContext:
    """Build ``state.historical_context`` — the situation, labelled as model knowledge.

    The excerpt is the first reading's anchors (#2850 lot 10): the thesis, the
    mechanism and the moves with their positions, then the text around those
    positions, within one call's capacity. Without a usable position the
    opening window survives — and the recorded status says it is a fallback,
    not a choice.

    ``llm_callable`` is injected: the invoke layer owns the client, the runaway
    guard and the provider route; this module owns the persona. No LLM → status
    ``no_llm`` and an empty read (never a fabricated one).
    """
    raw_text = getattr(state, "raw_text", "") or ""
    recorder = state if hasattr(state, "record_reading_window") else None
    excerpt, selection, extra = persona_reading(raw_text, defining_moves(state))
    if recorder is not None:
        recorder.record_reading_window("historian", selection, extra)

    # #3479 — the document's own dated references, read BEFORE the historian
    # writes a date: they ride the prompt (the model dates with them in
    # view) and the post-check below confronts the answer against them.
    stated = extract_stated_dates(raw_text)
    # #3589 — the month-day references cited as already delivered, no year
    # printed: the same two consumers, one shape finer than the years.
    past_days = extract_past_month_days(raw_text)

    result = HistoricalContext()
    if llm_callable is None:
        logger.debug("Historian: no LLM callable; returning an empty read.")
        return result

    prompt = build_historian_prompt(
        state, excerpt, stated_dates=stated, past_month_days=past_days
    )
    try:
        reply = await request_json_reply(llm_callable, prompt)
    except Exception as e:  # pragma: no cover - provider failures
        result.status = "llm_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Historian LLM error: %s", e)
        return result

    result.attempts = reply.attempts
    result.error = reply.error
    if reply.status == "parse_error":
        # #3576 — the same cause record as the strategist's (one helper): the
        # state, not only the log, can now answer WHY a reply failed to parse.
        result.status = "parse_error"
        result.parse_failure = dict(reply.parse_failure)
        # The log line keeps its exact pre-#3576 text (the bare decoder string).
        logger.warning("Historian parse error: %s", reply.detail)
        return result
    if reply.status != "ok":
        # An empty completion: ONE call, never retried. Only a MALFORMED reply
        # gets the second chance; the two statuses stay discriminated (#3576).
        result.status = "llm_error"
        return result

    parsed = reply.payload
    try:
        result.situation = str(parsed.get("situation", "") or "").strip()
        # #3432 ask 2 — the thesis's historical blind spot, model knowledge.
        # Capped and stripped: an unbounded sentence would crowd the Act III
        # prompt it rides, and an empty string is the honest "none named".
        result.blind_spot = str(parsed.get("blind_spot", "") or "").strip()[
            :BLIND_SPOT_CAP
        ]
        raw_items = parsed.get("items") or []
        items = []
        for raw in raw_items[:MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            claim = str(raw.get("claim", "") or "").strip()
            if not claim:
                continue
            items.append(
                HistoricalItem(
                    claim=claim,
                    confidence=_clamp_confidence(raw.get("confidence")),
                    supports=str(raw.get("supports", "") or "").strip(),
                )
            )
        # ``stamp_basis`` runs over the dicts so the label is written here, not
        # by the model: the round-trip is deliberate, an item can never escape
        # this module without a basis.
        stamped = stamp_basis([item.to_dict() for item in items])
        result.items = [
            HistoricalItem(
                claim=entry["claim"],
                confidence=entry["confidence"],
                supports=entry["supports"],
                basis=entry["basis"],
            )
            for entry in stamped
        ]
        result.status = "ok"
        _confront_dating(result, stated)
        # #3589 — the day-granular sibling: the year channel above compared
        # years only, so a situation claiming the very day the document
        # cites as already delivered was invisible at year granularity.
        _confront_dating_day(result, past_days)
        # #3555 — the document's own venue, read from the whole text: the
        # reading window can leave the statement out, so the excerpt is not
        # the reference here either.
        _confront_place(result, raw_text)
        logger.info(
            "Historian: %d item(s), situation=%s",
            len(result.items),
            bool(result.situation),
        )
    except Exception as e:  # pragma: no cover - unexpected payload shapes
        result.status = "llm_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Historian LLM error: %s", e)
    return result


def _confront_dating(result: HistoricalContext, stated: List[StatedDate]) -> None:
    """#3479 — degrade a dating the document's own dates refute.

    The LATEST year the situation names, compared with the LATEST year the
    document cites as past: the whole situation predating that floor is
    impossible — the text cites the reference as already past — and the
    dating becomes uncertain, named by the quoted reference that refutes it.
    ``max`` on the situation side (R1148): ``min`` fired as soon as the
    situation MENTIONED an earlier context event ("ten years after the
    crisis of YYYY") while its dating was right; ``max`` fires only when the
    dating itself is refuted. Deterministic post-check, no second model
    opinion.

    Anti-pendulum: this does not stop the historian from dating. A consistent
    situation passes through untouched, and so does a situation with no year
    at all — the confrontation only fires on the impossible.
    """
    bound = past_cited_bound(stated)
    if bound is None:
        return
    years = stated_years(result.situation)
    if not years:
        return
    model_year = max(years)
    if model_year >= bound.year:
        return
    result.dating_degraded = True
    result.dating_model_year = model_year
    result.dating_refuted_by = {
        "year": bound.year,
        "quote": bound.quote,
        "offset": bound.offset,
    }
    logger.info(
        "Historian dating degraded: situation at-or-after %d, document cites "
        "%d as past (offset %d) — dating uncertain",
        model_year,
        bound.year,
        bound.offset,
    )


def _confront_dating_day(
    result: HistoricalContext, past_days: List[StatedMonthDay]
) -> None:
    """#3589 — degrade a dating the document's cited DAYS refute.

    The year channel above compared YEARS only: a situation claiming the
    very speech the document cites as already delivered ("le discours
    prononcé le 14 mars", no year printed) stayed invisible at year
    granularity, where a later date in the same year is possible. This
    sibling fires on ONE shape: the claimed day COINCIDES with a day the
    document cites as already delivered — the situation claims the very
    cited speech, and the document is a later one.

    The claim must be the situation's OWN day (R1170): a situation naming
    more than one distinct month-day ("Allocution du 20 mars, en réponse au
    discours prononcé le 14 mars") describes relations among events, not
    its own date, and passes untouched. The precede clause of the first
    draft is gone (R1170): a day without a year places nothing within the
    claimed year — a winter speech cites the previous summer — and it fired
    on none of the 40 replayed states.

    The payload's shape stays :meth:`HistoricalContext.to_state`'s, with
    ``refuted_by`` carrying the month-day reference and its offset (and no
    ``year`` key: that channel wrote its own refutation, and when it
    fired this check stays silent — one degradation, named once). Same
    anti-pendulum rule as the years: this does not stop the historian from
    dating, and a situation carrying no month-day passes untouched.
    """
    if not past_days or result.dating_degraded:
        return
    distinct = {
        (claim.month, claim.day) for claim in stated_month_days(result.situation)
    }
    if len(distinct) != 1:
        return
    claimed = next(iter(distinct))
    refuting = next(
        (day for day in past_days if (day.month, day.day) == claimed),
        None,
    )
    if refuting is None:
        return
    result.dating_degraded = True
    years = stated_years(result.situation)
    result.dating_model_year = max(years) if years else None
    result.dating_refuted_by = {
        "month": refuting.month,
        "day": refuting.day,
        "quote": refuting.quote,
        "offset": refuting.offset,
    }
    logger.info(
        "Historian dating degraded (day channel): situation claims %d/%d, "
        "document cites %d/%d as already delivered (offset %d) — dating "
        "uncertain",
        claimed[0],
        claimed[1],
        refuting.month,
        refuting.day,
        refuting.offset,
    )


def _strip_generic_tail(run: str) -> str:
    """Drop the words that name the KIND of place from a captured run's right
    end — ``here in Valbourg City`` names Valbourg, not City."""
    words = run.split()
    while words and words[-1].lower() in _GENERIC_PLACE_WORDS:
        words.pop()
    return " ".join(words)


def _is_word_char(char: str) -> bool:
    """The characters a quote must not cut through: letters, digits, and the
    joiners French prose uses inside a word (``d'une``, ``Port-Rouge``)."""
    return char.isalnum() or char in "'’-"


def _snap_quote_start(text: str, index: int) -> int:
    """#3586 — move a quote window's start BACK to the beginning of the word
    it lands in. The window expands outward: it never drops text to look
    tidy, and it never begins on a fragment."""
    while (
        0 < index < len(text)
        and _is_word_char(text[index - 1])
        and _is_word_char(text[index])
    ):
        index -= 1
    return index


def _snap_quote_end(text: str, index: int) -> int:
    """#3586 — move a quote window's end FORWARD to the end of the word it
    lands in."""
    while (
        0 < index < len(text)
        and _is_word_char(text[index - 1])
        and _is_word_char(text[index])
    ):
        index += 1
    return index


def _document_venue_statements(text: str) -> List[Dict[str, Any]]:
    """#3555 — where the DOCUMENT says it is being given, in text order.

    Deterministic and deictic: only the forms that point at the place of the
    speech act (``this … city of X``, ``here in X``, and their French twins)
    count. No gazetteer and no list of places — the cue is a construction, so
    a place the corpus has never seen is caught the same way. The ``offset``
    is the place NAME's position, not the cue's: that is the position a
    render can point a reader at, and the one #3555's measurement names. The
    quote window snaps outward to word boundaries (#3586): it never starts or
    ends inside a word.

    The reading is deliberately narrow, and the pull request states what it
    does not catch: an address such as ``people of X`` (measured naming
    audiences the speaker is not among), a dateline or header line in any
    other form, and a venue stated only in a language none of the cues cover.
    """
    if not text:
        return []
    statements: List[Dict[str, Any]] = []
    seen_offsets = set()
    for cue in _DOCUMENT_VENUE_CUES:
        for match in cue.finditer(text):
            name = _strip_generic_tail(match.group("name"))
            if not name:
                continue
            start = match.start("name")
            if start in seen_offsets:
                continue
            seen_offsets.add(start)
            window_start = _snap_quote_start(text, max(0, start - _PLACE_QUOTE_CONTEXT))
            window_end = _snap_quote_end(
                text,
                min(len(text), start + len(match.group("name")) + _PLACE_QUOTE_CONTEXT),
            )
            statements.append(
                {
                    "name": name,
                    "offset": start,
                    "quote": " ".join(text[window_start:window_end].split()),
                }
            )
    statements.sort(key=lambda entry: entry["offset"])
    return statements


def _governed_by_a_person_relation(situation: str, match: re.Match[str]) -> bool:
    """#3586 — is this venitive match the complement of a relation to a
    PERSON? ``face à Jean Dorlac``, ``répond à X``, ``s'adresse à X``,
    ``opposait à X`` (any tense: the verbs are read by their stem), and
    ``siège au X`` (a role in an institution): the capitalised run is the
    person or the institution, not a venue."""
    before = situation[: match.start()]
    return any(cue.search(before) for cue in _PERSON_RELATION_CUES)


def _situation_place_candidates(situation: str) -> List[str]:
    """#3555 — the places the historian's situation places the SPEECH at.

    Read through the venitive prepositions and the explicit ``dans la ville
    de`` form (see the two patterns above). This is a candidate list, not a
    verdict: the confrontation below decides, and the state records what the
    situation named.

    #3586: a venitive match governed by a relation to a person is not a
    venue (``_governed_by_a_person_relation``). Five cues are covered —
    « face à », and the three verbs read by their stem so every tense and
    every elided pronoun is covered by construction: « répond / répondrait /
    répondit à », « s'adresse / s'adressait à », « opposé / l'opposait à »
    (the c13-c14 shape), plus « siège au <institution> » (a role, not the
    place the speech was given; c8). Left out, and named in the pull request:
    « devant <person> » (no construction separates it from « devant
    <assembly> », and enumerating person names is excluded by the privacy
    rule), and relations carried by another preposition (``aux côtés de``,
    ``à l'égard de``).
    """
    if not situation:
        return []
    found: List[str] = []
    matches = sorted(
        [
            m
            for m in _SITUATION_VENUE_RE.finditer(situation)
            if not _governed_by_a_person_relation(situation, m)
        ]
        + list(_SITUATION_PLACE_KIND_RE.finditer(situation)),
        key=lambda m: m.start("name"),
    )
    for match in matches:
        name = _strip_generic_tail(match.group("name"))
        if not name or name in found:
            continue
        found.append(name)
        if len(found) >= PLACE_MAX_CANDIDATES:
            break
    return found


def _names_share(left: str, right: str) -> bool:
    """Do two place names name the same place, as far as a reader can tell?

    Equality, containment (``Port`` / ``Port Neuf``) or a common prefix of four
    characters — the last one is the measured cross-language class: the same
    city written in two languages, as an invented ``Valbourg`` / ``Valburg``
    pair shows. Four characters is conservative on purpose: it can only
    SUPPRESS a refutation, never create one (``Brienne`` / ``Brissac`` share
    three and stay distinct).
    """
    left_l, right_l = left.lower(), right.lower()
    if left_l == right_l or left_l in right_l or right_l in left_l:
        return True
    shorter = min(len(left_l), len(right_l))
    if shorter < 4:
        return False
    return left_l[:4] == right_l[:4]


def _confront_place(result: HistoricalContext, raw_text: str) -> None:
    """#3555 — record a venue the document itself contradicts.

    The dating's sibling (#3479), one level harder: a year is a token, a place
    is a name. The check therefore leans on the document being POSITIVE — it
    must state its own venue deictically — and on the situation placing the
    speech somewhere else. A document that says nothing about where it was
    given changes nothing; a situation that names no place changes nothing;
    and a situation that shares a name with the document's venue changes
    nothing (a city and its region are not a conflict). A false refutation is
    worse than a missed one, the rule #3479 states for dates.

    The whole ``raw_text`` is read, never the excerpt: the venue statement is
    exactly what the reading window can leave out (measured on the cycle-7
    document, both statements outside the historian's 4 361 characters).
    """
    statements = _document_venue_statements(raw_text)
    if not statements:
        return
    candidates = _situation_place_candidates(result.situation)
    if not candidates:
        return
    venue_tokens = [str(entry["name"]) for entry in statements]
    for entry in statements:
        venue_tokens.extend(str(entry["name"]).split())
    if any(
        _names_share(token, venue)
        for candidate in candidates
        for token in candidate.split()
        for venue in venue_tokens
    ):
        return
    first = statements[0]
    result.place_degraded = True
    result.place_model_places = candidates
    result.place_document = {
        "name": first["name"],
        "quote": first["quote"],
        "offset": first["offset"],
        "statements": len(statements),
    }
    logger.info(
        "Historian place degraded: document states its venue at %s (offset %d), "
        "situation names %s — place refuted",
        first["name"],
        first["offset"],
        ", ".join(candidates),
    )


async def extract_historical_context(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_historical_context(**kwargs)).to_state()


def context_note(state: Any) -> str:
    """The labelled block a downstream reader prepends to its own prompt.

    ONE producer for the wording (#3377): the NL→KB translator and any later
    consumer must say the same thing about the same read, or two readers will
    disagree about what "model knowledge" covers. Empty string when there is
    nothing to say — a consumer that appended an empty header would advertise a
    provenance it does not have.
    """
    context = getattr(state, "historical_context", {}) or {}
    if not isinstance(context, dict):
        return ""
    situation = str(context.get("situation") or "").strip()
    items = [
        item
        for item in (context.get("items") or [])
        if isinstance(item, dict) and str(item.get("claim") or "").strip()
    ]
    if not situation and not items:
        return ""

    lines = [
        "SITUATION HISTORIQUE — SAVOIR DU MODÈLE, jamais le contenu du texte :",
        "  Utilise-la pour résoudre les références (époque, acteurs, "
        "institutions), jamais pour ajouter une prémisse au texte.",
    ]
    if situation:
        lines.append(f"  Situation : {situation}")
    for item in items:
        try:
            confidence = float(item.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0
        lines.append(f"  - {item['claim']} (confiance {confidence:.2f})")
    return "\n".join(lines)
