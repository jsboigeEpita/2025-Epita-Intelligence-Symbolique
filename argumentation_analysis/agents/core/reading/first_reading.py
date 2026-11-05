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
specialist sees it. Your job, in this order:

1. Name the document's CENTRAL THESIS — the claim the whole document builds
   toward — and the MECHANISM it argues it by: the device, the proof or the
   chain the document leans on to carry that thesis. On a long document these
   are often stated late, sometimes once, nowhere near the opening; a reader
   who stopped at the first page would miss them. Each of the two comes with
   its own verbatim quote.
2. Then the other moves the document makes, most important first. A local
   move — a claim, a concession, an audience address, a threat, a dilemma —
   comes only after the thesis and the mechanism.

Hard rules:
- One call, one pass. Say what the text DOES, not what it should have done.
- No verdict. Never say whether a move is a fallacy, valid, good or bad: the
  instruments decide that afterwards, and your line must not read as their
  verdict.
- Every entry carries a VERBATIM quote copied from the document, character for
  character: no translation, no paraphrase, no ellipsis, no two passages
  joined. A quote the document does not carry is discarded by the pipeline.
- Do not date, place or situate the document in history. Another reader does
  that.
- At most {max_moves} entries in total, thesis and mechanism included. Fewer
  is a valid answer; an entry you cannot fill with a verbatim quote from the
  document is omitted, and an empty list of other moves is valid.

Answer in French, with ONLY this JSON — no fences, no commentary:
{{"thesis": {{"reading": "one sentence naming the central thesis",
             "quote": "a verbatim span of the document"}},
 "mechanism": {{"reading": "one sentence naming the mechanism that carries it",
                "quote": "a verbatim span of the document"}},
 "moves": [{{"kind": "concession|device|claim|audience|threat|dilemma|other",
             "reading": "one sentence naming the move",
             "quote": "a verbatim span of the document"}}]}}

Document:
{excerpt}
"""


@dataclass
class DefiningMove:
    """One move the first reading named, with the text's own words for it.

    ``slot`` marks the two entries the question asks for FIRST (#3415): the
    central thesis (``"thesis"``) and the mechanism that carries it
    (``"mechanism"``). Empty for a local move — the record carries the key
    only when there is a slot to state (honest absence, so a slot-less
    record stays byte-identical to a pre-#3415 one).
    """

    kind: str
    reading: str
    quote: str
    offset: Optional[int] = None
    basis: str = FIRST_READING_BASIS
    slot: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "kind": self.kind,
            "reading": self.reading,
            "quote": self.quote,
            "offset": self.offset,
            "basis": self.basis,
        }
        if self.slot:
            payload["slot"] = self.slot
        return payload

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
    ``malformed_moves`` (#3415) counts the answer objects the document-level
    JSON parse could not read but the per-object salvage could not keep either:
    one bad character must cost its own move, never the whole reading.
    """

    moves: List[DefiningMove] = field(default_factory=list)
    dropped_quotes: int = 0
    malformed_moves: int = 0
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
        if self.malformed_moves:
            payload["malformed_moves"] = self.malformed_moves
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


def _key_before(text: str, start: int) -> Optional[str]:
    """The object key naming the span that starts at ``start``, if any.

    ``"thesis": {`` names the span; an array element (``[`` or ``,`` before
    it) does not, and answers ``None``. Only plain names read as keys — the
    answer's own vocabulary — so a quote's tail never passes for one.
    """
    head = text[:start].rstrip()
    if not head.endswith(":"):
        return None
    head = head[:-1].rstrip()
    if not head.endswith('"'):
        return None
    end = len(head) - 1
    i = end - 1
    while i >= 0:
        if head[i] == '"' and (i == 0 or head[i - 1] != "\\"):
            key = head[i + 1 : end]
            return key if key and all(c.isalnum() or c in "_-" for c in key) else None
        i -= 1
    return None


def _balanced_object_spans(text: str) -> List[Tuple[Optional[str], str]]:
    """The outermost balanced ``{...}`` spans of ``text``, string-aware, each
    with the key that names it (``None`` for an array element).

    #3415 rework (R1144): a bare span lost the key that said WHICH object it
    was — the salvage re-scans a failed wrapper's inside, and without the key
    it could no longer tell the thesis from the mechanism: both came back as
    anonymous moves, and the note printed « autre : » instead of their names.
    """
    spans: List[Tuple[Optional[str], str]] = []
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                spans.append((_key_before(text, start), text[start : i + 1]))
                start = -1
    return spans


def _salvage_objects(
    text: str,
) -> Tuple[List[Tuple[Optional[str], Dict[str, Any]]], int]:
    """Parse every balanced object on its own; count what nothing could read.

    #3415 ask 2 — cycle 1 measured the failure class: one bad character (a
    stray ``','``) made the document-level ``json.loads`` reject the whole
    answer and cost every move. Salvage is per-object: an outer span that
    fails is re-scanned INSIDE (the wrapper is structure, not a move — it
    counts only when it swallowed nothing readable), and a leaf span that
    fails is one lost move. Each readable object keeps the key it was found
    under (R1144), so the splice can route a slot back to its name.
    """
    objects: List[Tuple[Optional[str], Dict[str, Any]]] = []
    malformed = 0
    for key, span in _balanced_object_spans(text):
        try:
            obj = json.loads(span)
        except json.JSONDecodeError:
            inner, inner_bad = _salvage_objects(span[1:-1])
            objects.extend(inner)
            malformed += inner_bad if inner else 1
        else:
            if isinstance(obj, dict):
                objects.append((key, obj))
            else:
                malformed += 1
    return objects, malformed


def _parse_answer(content: str) -> Tuple[Dict[str, Any], int]:
    """The answer dict and the count of objects no path could read.

    Clean parse first; on a document-level ``JSONDecodeError`` the salvage
    path keeps every object that reads on its own, splices a wrapper's
    ``moves`` list and slots back in, and counts the rest — so a malformed
    answer costs its own objects, never the reading.
    """
    text = (content or "").strip()
    try:
        parsed = _parse_json_object(text)
    except json.JSONDecodeError:
        objects, malformed = _salvage_objects(text)
        spliced: Dict[str, Any] = {}
        extra_moves: List[Any] = []
        for key, obj in objects:
            # R1144 — the key that named a slot object is how salvage knows
            # it is the thesis or the mechanism, never a local move. Without
            # it the recovered object came back anonymous ("autre"), losing
            # the very thing the question had asked for first.
            if key in ("thesis", "mechanism"):
                if key not in spliced:
                    spliced[key] = obj
                continue
            if isinstance(obj.get("moves"), list):
                extra_moves.extend(obj["moves"])
                for slot in ("thesis", "mechanism"):
                    if isinstance(obj.get(slot), dict) and slot not in spliced:
                        spliced[slot] = obj[slot]
            elif "kind" in obj or ("reading" in obj and "quote" in obj):
                extra_moves.append(obj)
        if extra_moves:
            spliced["moves"] = extra_moves
        return spliced, malformed
    return parsed if isinstance(parsed, dict) else {}, 0


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
        parsed, malformed = _parse_answer(content or "")
        raw_moves = parsed.get("moves")
        if not isinstance(raw_moves, list):
            raw_moves = None
        has_slot = isinstance(parsed.get("thesis"), dict) or isinstance(
            parsed.get("mechanism"), dict
        )
        if raw_moves is None and not has_slot:
            # Nothing readable: a clean answer with no entry at all, or a
            # malformed one the salvage could not save anything from. The
            # malformed count says which of the two it was.
            result.status = "parse_error"
            result.error = (
                f"no readable entry in the answer ({malformed} unreadable object(s))"
                if malformed
                else "no 'moves' list in the answer"
            )
            result.malformed_moves = malformed
            return result

        moves: List[DefiningMove] = []
        dropped = 0

        def _keep(entry: Any, kind: str, slot: str) -> None:
            """One verified entry — the citation rule is the same for a slot
            (#3415) as for a local move: a quote the document does not carry
            is counted and dropped, never kept."""
            nonlocal dropped
            if not isinstance(entry, dict):
                return
            reading = str(entry.get("reading", "") or "").strip()
            quote = str(entry.get("quote", "") or "").strip()
            if not reading or not quote:
                dropped += 1
                return
            if not quote_occurs_in(raw_text, quote):
                # The one citation rule (#3389). Counted, never kept.
                dropped += 1
                logger.info("FirstReading: dropped an entry whose quote is absent")
                return
            index = locate_quote(raw_text, quote)
            moves.append(
                DefiningMove(
                    kind=kind,
                    reading=reading,
                    quote=quote,
                    offset=index if index >= 0 else None,
                    slot=slot,
                )
            )

        # #3415 ask 1 — the two entries the question asks for FIRST: the
        # central thesis and the mechanism that carries it. The kinds stay in
        # the closed vocabulary (thesis / device); the slot marks what each
        # is, and both are kept ahead of the local moves whatever their
        # position in the document (a late mechanism is the measured case).
        _keep(parsed.get("thesis"), "thesis", "thesis")
        _keep(parsed.get("mechanism"), "device", "mechanism")
        for raw in raw_moves or []:
            if not isinstance(raw, dict):
                continue
            _keep(raw, move_kind(raw.get("kind")), "")
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
        result.malformed_moves = malformed
        result.status = "ok"
        logger.info(
            "FirstReading: %d move(s), %d dropped, %d malformed, whole_document=%s",
            len(result.moves),
            result.dropped_quotes,
            result.malformed_moves,
            result.read_scope.get("whole_document"),
        )
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
    malformed = record.get("malformed_moves") or 0
    for move in moves:
        offset = move.get("offset")
        position = f" [texte, position {offset}]" if isinstance(offset, int) else ""
        # R1142 — the label prints in French (#3393, the reader's
        # vocabulary); the English key stays in the state. #3415 — the two
        # slots the question asks for first print under their own names, so
        # the writer can point at the thesis and the mechanism as such.
        slot = str(move.get("slot") or "")
        if slot == "thesis":
            label = "thèse centrale"
        elif slot == "mechanism":
            label = "mécanisme"
        else:
            label = _KIND_LABELS_FR.get(str(move.get("kind")), "autre")
        lines.append(
            f"  - {label} : {move.get('reading')} "
            f"— « {move.get('quote')} »{position}"
        )
    if dropped:
        lines.append(f"  {dropped} geste(s) écarté(s) : citation absente du document.")
    if malformed:
        # #3415 ask 2 — a malformed object costs its own move, never the
        # reading; what was lost is stated, not hidden.
        lines.append(f"  {malformed} objet(s) illisible(s) : geste(s) perdu(s).")
    return "\n".join(lines)
