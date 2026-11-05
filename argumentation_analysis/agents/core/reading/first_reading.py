"""#3395 — the first reading: the document read once, whole, before the lenses.

The v1 panel measured the gap (M1, ``#2841`` and cycle 0 of ``#3374``): on 8 of
10 documents, the same-model zero-shot carries the document's defining move and
no line of the render does — the synthesis never sees the text
(``deep_synthesis_agent`` writes from state artefacts only) and the acts see
only the extracted units, which on a long document cover 5-19 % of it. The
zero-shot reads the whole text in one call; that is where it wins.

This module is that reader, made a PRODUCER instead of an adversary: one call,
on the same model, over the whole text — the zero-shot arm's own read
(``max_chars=0``, #2841 rule 4: the same cut on both arms, R1142) — writing
``state.defining_moves``.

**It supplies moves, not verdicts.** Each move is a kind, a one-line reading
and a VERBATIM quote with its offset. No fallacy, no score, no strategy
judgement: the lenses (taxonomy descent, quality, formal branch) still decide,
and the instruments' findings still carry S2 and S3. A first-reading line is
labelled as such wherever it reaches the reader — it is never presented as a
lens's verdict.

**The quote is checked against the text in memory**, with the one citation rule
the repo already owns (#3389's ``normalised_quote_in``): case, whitespace,
typographic apostrophes and quotation marks are normalised, ``[…]`` reads as an
elision gap, and a span under a word or two is a keyword rather than a
citation. A quote that fails is DROPPED and counted — never kept "because the
model probably copied it".

**Not the historian of #3377.** The historian writes what the model knows about
the situation, labelled ``model_knowledge``. This module writes the text's own
content, labelled ``first_reading``. Two fields, two producers, two labels; a
reader never confuses what the text says with what we know about its period.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from argumentation_analysis.core.reading_window import (
    FIRST_READING_WINDOW,
    STATUS_SELECTED,
    WindowSelection,
    locate_quote,
    selected_text_and_selection,
)

logger = logging.getLogger("FirstReading")

#: The provenance label of every move this module writes. One constant so the
#: state, the render and the export boundary cannot spell it three ways.
FIRST_READING_BASIS = "first_reading"

#: The closed vocabulary of a move's kind. The model picks a word from it; an
#: unknown word is ``other`` (absence, never a measurement — #3029), so the
#: render can print the same eight words it prints for every other document.
MOVE_KINDS = (
    "thesis",
    "concession",
    "device",
    "claim",
    "audience",
    "threat",
    "dilemma",
    "other",
)

#: How many moves the state carries. A reading, not a summary of the document:
#: the panel's documents yield three to six defining moves, and an unbounded
#: list would crowd the acts' prompts with what the lenses can already see.
MAX_MOVES = 12

#: How many moves the prompt asks for — a bound on the answer, stated to the
#: model rather than truncated after the fact.
_PROMPT_MAX_MOVES = MAX_MOVES

#: French words the model tends to answer with, mapped to the vocabulary. The
#: kind is a hint about the move, not a verdict: a synonym is not an error.
_KIND_SYNONYMS = {
    "thèse": "thesis",
    "these": "thesis",
    "concession": "concession",
    "concession faite": "concession",
    "procédé": "device",
    "procede": "device",
    "procédé central": "device",
    "affirmation": "claim",
    "affirmation principale": "claim",
    "revendication": "claim",
    "public": "audience",
    "appel au public": "audience",
    "menace": "threat",
    "menace implicite": "threat",
    "dilemme": "dilemma",
    "autre": "other",
}

#: The French label of each kind — the NOTE's vocabulary (R1142, #3393: the
#: reader's language). The state keeps the English key of the closed
#: vocabulary (the export boundary and the tests read the key); the note is
#: prose, and the report's prose is French.
_KIND_LABELS_FR = {
    "thesis": "thèse",
    "concession": "concession",
    "device": "procédé",
    "claim": "affirmation",
    "audience": "public",
    "threat": "menace",
    "dilemma": "dilemme",
    "other": "autre",
}

FIRST_READING_PROMPT = """You are reading the document below ONCE, whole, before any
specialist sees it. Your job is to name the moves the document itself makes —
the ones a reader who read the whole thing would point to first.

Hard rules:
- One call, one pass. Say what the text DOES, not what it should have done.
- No verdict. Never say whether a move is a fallacy, valid, good or bad: the
  instruments decide that afterwards, and your line must not read as their
  verdict.
- Every move carries a VERBATIM quote copied from the document, character for
  character: no translation, no paraphrase, no ellipsis, no two passages
  joined. A quote the document does not carry is discarded by the pipeline.
- Do not date, place or situate the document in history. Another reader does
  that.
- At most {max_moves} moves, most important first. Fewer is a valid answer; an
  empty list is a valid answer when the text makes no defining move.

Answer in French, with ONLY this JSON — no fences, no commentary:
{{"moves": [{{"kind": "thesis|concession|device|claim|audience|threat|dilemma|other",
             "reading": "one sentence naming the move",
             "quote": "a verbatim span of the document"}}]}}

Document:
{excerpt}
"""


@dataclass
class DefiningMove:
    """One move the first reading named, with the text's own words for it."""

    kind: str
    reading: str
    quote: str
    offset: Optional[int] = None
    basis: str = FIRST_READING_BASIS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "reading": self.reading,
            "quote": self.quote,
            "offset": self.offset,
            "basis": self.basis,
        }

    def span(self) -> Optional[Tuple[int, int]]:
        """``(start, end)`` in the document, or ``None`` when unpositioned."""
        if self.offset is None:
            return None
        return (self.offset, self.offset + len(self.quote))


@dataclass
class FirstReading:
    """The first reading, ready for the state.

    ``status`` is discriminated on purpose (#3096): an LLM failure must never
    read as "completed, nothing found". ``dropped_quotes`` counts the moves
    whose quote the document does not carry — the number the render can state,
    because a silently discarded move is the defect this module repairs.
    """

    moves: List[DefiningMove] = field(default_factory=list)
    dropped_quotes: int = 0
    status: str = "no_llm"
    error: str = ""
    read_scope: Dict[str, Any] = field(default_factory=dict)

    def to_state(self) -> Dict[str, Any]:
        payload = {
            "moves": [move.to_dict() for move in self.moves],
            "dropped_quotes": self.dropped_quotes,
            "status": self.status,
            "read_scope": dict(self.read_scope),
            "basis": FIRST_READING_BASIS,
        }
        # #3395 — ``error`` only when there IS one: the writers' shared guard
        # treats the presence of the key as a failed invoke (the #3377
        # convention), so an empty string here would make every successful
        # reading look like an error and be dropped silently.
        if self.error:
            payload["error"] = self.error
        return payload


def move_kind(value: Any) -> str:
    """The closed-vocabulary kind of a move, ``other`` when unknown.

    A kind is how the report names the move ("the concession", "the central
    device"), so it must be one of eight words the render knows how to print.
    An unrecognised answer — including a French synonym the model reached for —
    reads as ``other``: absence is stated, never passed through as a made-up
    vocabulary word (#3029).
    """
    if not isinstance(value, str):
        return "other"
    candidate = value.strip().lower()
    if candidate in MOVE_KINDS:
        return candidate
    return _KIND_SYNONYMS.get(candidate, "other")


def _parse_json_object(content: str) -> Any:
    """The model's JSON, fenced or not."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text) if text else {}


def build_first_reading_prompt(excerpt: str) -> str:
    """The one prompt of the first reading."""
    return FIRST_READING_PROMPT.format(max_moves=_PROMPT_MAX_MOVES, excerpt=excerpt)


async def build_first_reading(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
) -> FirstReading:
    """Read ``state.raw_text`` once and write ``state.defining_moves``.

    The text is read WHOLE — no cut, the zero-shot arm's own read (#2841
    rule 4, R1142): a 30 000 bound left the four longest panel documents
    (47 644 to 179 139 characters) partially unread, exactly where M1 is
    worst. ``FIRST_READING_WINDOW = 0`` means the window is the document;
    a bounded value keeps the shared #1737 selector's windowed path for
    non-panel use. The selection is recorded on the state like every other
    read, so the scope is a measured claim, and a text past the model's
    context fails loud (``llm_error``) rather than reading a window the
    comparison cannot use.

    Quotes are verified against ``state.raw_text`` — the text IN MEMORY, not
    the window — so a quote found outside the read window still verifies; only
    its offset is then unknown. No LLM → status ``no_llm`` and an empty read,
    never a fabricated one.
    """
    raw_text = getattr(state, "raw_text", "") or ""
    if not raw_text.strip():
        result = FirstReading(status="empty_input")
        return result

    # Resolved before the slice: ``next()`` falls back for a state that cannot
    # record, and the value is what the payload states about its own scope.
    # It is the STATE (the shared selector's own ``state`` argument), not a
    # callable: the no-cut branch below once called it as one, and every
    # spectacular run of cycle 1 failed on « 'UnifiedAnalysisState' object is
    # not callable » (R1143) — the witnesses used a bare namespace that never
    # reached that call.
    recording_state = state if hasattr(state, "record_reading_window") else None
    if FIRST_READING_WINDOW > 0:
        excerpt, selection = selected_text_and_selection(
            raw_text, FIRST_READING_WINDOW, "first_reading", recording_state
        )
    else:
        # R1142 — no cut: the zero-shot arm's own read (#2841 rule 4, the
        # same cut on both arms). The window IS the document, offset 0 by
        # construction — no head selection applies, because there is no
        # "where" to decide when everything is read. Recorded like every
        # other read so the scope stays a measured claim.
        selection = WindowSelection(0, len(raw_text), STATUS_SELECTED)
        excerpt = raw_text
        if recording_state is not None:
            recording_state.record_reading_window("first_reading", selection)

    result = FirstReading(
        read_scope={
            "offset": selection.offset,
            "window": selection.window,
            "status": selection.status,
            "text_length": len(raw_text),
            # The whole document was read iff the window covers it: the acts
            # print this, so "read once, whole" is a measured claim.
            "whole_document": selection.offset == 0
            and len(raw_text) <= selection.window,
        }
    )
    if llm_callable is None:
        logger.debug("FirstReading: no LLM callable; returning an empty read.")
        return result

    try:
        content = await llm_callable(build_first_reading_prompt(excerpt))
        parsed = _parse_json_object(content or "")
        raw_moves = parsed.get("moves") if isinstance(parsed, dict) else None
        if not isinstance(raw_moves, list):
            result.status = "parse_error"
            result.error = "no 'moves' list in the answer"
            return result

        moves: List[DefiningMove] = []
        dropped = 0
        for raw in raw_moves:
            if not isinstance(raw, dict):
                continue
            reading = str(raw.get("reading", "") or "").strip()
            quote = str(raw.get("quote", "") or "").strip()
            if not reading or not quote:
                dropped += 1
                continue
            if not quote_occurs_in(raw_text, quote):
                # The one citation rule (#3389). Counted, never kept.
                dropped += 1
                logger.info("FirstReading: dropped a move whose quote is absent")
                continue
            index = locate_quote(raw_text, quote)
            moves.append(
                DefiningMove(
                    kind=move_kind(raw.get("kind")),
                    reading=reading,
                    quote=quote,
                    offset=index if index >= 0 else None,
                )
            )
            if len(moves) >= MAX_MOVES:
                break

        # A move the model repeated (same quote) is one move: the reading is
        # kept once, in its first position, and the duplicate is counted as
        # dropped like any other unreadable answer.
        unique: List[DefiningMove] = []
        seen = set()
        for move in moves:
            key = move.quote
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            unique.append(move)

        result.moves = unique
        result.dropped_quotes = dropped
        result.status = "ok"
        logger.info(
            "FirstReading: %d move(s), %d dropped, whole_document=%s",
            len(result.moves),
            result.dropped_quotes,
            result.read_scope.get("whole_document"),
        )
    except json.JSONDecodeError as e:
        result.status = "parse_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("FirstReading parse error: %s", e)
    except Exception as e:  # pragma: no cover - provider failures
        result.status = "llm_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("FirstReading LLM error: %s", e)
    return result


def quote_occurs_in(text: str, quote: str) -> bool:
    """#3389's citation rule, applied to a defining move's quote.

    Imported lazily: the restitution package pulls the render's own
    dependencies, and the producer must remain importable from a test that
    never renders anything.
    """
    from argumentation_analysis.reporting.restitution.quote_fidelity import (
        normalised_quote_in,
    )

    return normalised_quote_in(text, quote)


async def extract_first_reading(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_first_reading(**kwargs)).to_state()


# --- the consumers' ONE reader ---------------------------------------------


def defining_moves(state: Any) -> List[Dict[str, Any]]:
    """The recorded moves, in document order, dict-shaped and verified."""
    record = getattr(state, "defining_moves", None)
    if isinstance(state, dict):
        record = state.get("defining_moves")
    if not isinstance(record, dict):
        return []
    moves = [m for m in (record.get("moves") or []) if isinstance(m, dict)]
    moves.sort(key=lambda m: (m.get("offset") is None, m.get("offset") or 0))
    return moves


def defining_move_spans(state: Any) -> List[Tuple[int, int]]:
    """The ``(start, end)`` spans of the positioned moves — the selection hint.

    Unpositioned moves (a verified quote the exact/windowed locator could not
    place) contribute no span: a selection cannot be told to prefer a range it
    cannot name, and inventing one would put the units somewhere they are not.
    """
    spans = []
    for move in defining_moves(state):
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            continue
        spans.append((offset, offset + len(quote)))
    return spans


#: #3416 — how far AFTER a unit's end a recorded concession still counts as
#: the passage around the claim (the August method's « next sentence »). A
#: concession further away belongs to another part of the document, and a
#: statement that is not about the claim is not evidence about it.
DOCUMENT_STATEMENT_AFTER_UNIT = 400


def document_statements_for_unit(
    state: Any,
    unit_text: str = "",
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """#3416 (ask 2) — what the document ITSELF says about a unit's claim.

    The descent reads one unit at a time. A unit extracted as a fragment
    loses the document's own caveat — the concession the speaker makes two
    sentences away — and the descent then confirms the family that caveat
    refutes (the cycle-1 M2 defect). This producer hands the descent the
    document's own words, never a verdict about them:

    * ``relation="overlap"`` — a concession move the first reading recorded
      whose span intersects the unit's;
    * ``relation="adjacent"`` — a recorded concession that starts at most
      ``DOCUMENT_STATEMENT_AFTER_UNIT`` characters after the unit's end: the
      passage around the claim, the way the speaker restates it next.

    No geometry (no offset on either side) means no statement: a citation
    that cannot be placed is not evidence about this claim (the same rule as
    ``defining_move_spans``). Nothing recorded means nothing carried — the
    caller's behaviour is then byte-identical to the pre-#3416 path.
    """
    if not isinstance(offset, int) or isinstance(offset, bool):
        return []
    unit_end = offset + len(unit_text or "")
    statements: List[Dict[str, Any]] = []
    for move in defining_moves(state):
        if str(move.get("kind") or "") != "concession":
            continue
        quote = str(move.get("quote") or "")
        move_offset = move.get("offset")
        if not quote or not isinstance(move_offset, int) or isinstance(move_offset, bool):
            continue
        move_end = move_offset + len(quote)
        if offset < move_end and move_offset < unit_end:
            relation = "overlap"
        elif unit_end <= move_offset <= unit_end + DOCUMENT_STATEMENT_AFTER_UNIT:
            relation = "adjacent"
        else:
            continue
        statements.append(
            {"source": "first_reading_concession", "relation": relation, "quote": quote}
        )
    return statements


def first_reading_note(state: Any) -> str:
    """The labelled block a writer prepends to its own prompt (#3395 ask 3).

    ONE producer for the wording, like ``context_note`` (#3377): every writer
    that reads the moves says the same thing about them, and the label is the
    first line — a first-reading line never reads as a lens's verdict.

    Three states, each printed as what it is:

    * moves recorded — the label, the read scope (whole document or the window
      actually read), and one line per move with its verbatim quote;
    * the producer ran and found nothing — the label and that finding, so the
      writer does not silently invent a centre;
    * the producer did not run or failed — the absence is stated with its
      status, so a writer knows the difference between "nothing to say" and
      "nobody read the document".
    """
    record = getattr(state, "defining_moves", None)
    if isinstance(state, dict):
        record = state.get("defining_moves")
    if not isinstance(record, dict):
        return ""
    status = str(record.get("status") or "")
    moves = defining_moves(state)
    scope = record.get("read_scope") or {}
    dropped = record.get("dropped_quotes") or 0

    if not moves:
        if status in ("", "no_llm"):
            return (
                "LECTURE PREMIÈRE — non enregistrée : aucun lecteur n'a lu le "
                "document en entier. Ne présente aucune ligne comme une lecture "
                "d'ensemble."
            )
        if status != "ok":
            return "LECTURE PREMIÈRE — lecture en échec, aucun geste enregistré."
        # R1142 — « lu en entier » follows the scope the producer RECORDED,
        # never a declaration: a bounded read states its window, so the
        # writer cannot claim a whole reading it did not do.
        if scope.get("whole_document"):
            return (
                "LECTURE PREMIÈRE — le document a été lu en entier, aucun "
                "geste définissant n'y a été relevé. Ne comble pas ce vide "
                "par une lecture d'ensemble de ton cru."
            )
        return (
            "LECTURE PREMIÈRE — lecture bornée à une fenêtre de "
            f"{scope.get('window')} caractères à partir du {scope.get('offset')}, "
            "aucun geste définissant n'y a été relevé. Ne comble pas ce vide "
            "par une lecture d'ensemble de ton cru."
        )

    if scope.get("whole_document"):
        extent = "document entier lu une fois"
    else:
        window = scope.get("window")
        offset = scope.get("offset")
        extent = f"fenêtre lue : {window} caractères à partir du {offset}"
    lines = [
        "LECTURE PREMIÈRE — un seul lecteur, sur le texte entier, avant les "
        "instruments. Ce sont des GESTES DU TEXTE, pas un verdict d'instrument : "
        "ne les présente jamais comme un sophisme ni comme une note.",
        f"  Portée : {extent}.",
    ]
    for move in moves:
        offset = move.get("offset")
        position = f" [texte, position {offset}]" if isinstance(offset, int) else ""
        # R1142 — the label prints in French (#3393, the reader's
        # vocabulary); the English key stays in the state.
        label = _KIND_LABELS_FR.get(str(move.get("kind")), "autre")
        lines.append(
            f"  - {label} : {move.get('reading')} "
            f"— « {move.get('quote')} »{position}"
        )
    if dropped:
        lines.append(f"  {dropped} geste(s) écarté(s) : citation absente du document.")
    return "\n".join(lines)
