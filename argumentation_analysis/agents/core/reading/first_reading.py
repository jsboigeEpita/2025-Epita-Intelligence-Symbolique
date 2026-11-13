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
model probably copied it". The rule itself is untouched (#3415 ask 4): what a
failed quote may gain is a SECOND chance at being evidence, never a cheaper
pass.

**A failed quote is re-anchored on the document, and never invents its words**
(#3415 ask 4). The paid probe of 2026-11-05 measured the defect this repairs:
on the longest panel document the mechanism survived the rule 3/3 and the
thesis 1/3 — a thesis whose citation failed was lost WITH its reading, under an
anonymous « 1 geste écarté ». So the two slots the question asks for first
(``thesis``, ``mechanism``) do not fall on a failed citation any more:

* the document is searched for the passage carrying the longest run of
  consecutive words the quote and the text share (``anchor_quote_in``), and the
  passage must clear BOTH declared floors (``ANCHOR_MIN_RUN`` words,
  ``ANCHOR_MIN_SHARE`` of the quote's own words). Above them the move keeps its
  reading and takes the DOCUMENT's characters as its quote, flagged
  ``anchor="relocated"`` — the model's words are never printed between « »;
* below them the move keeps its reading with NO quote, flagged
  ``anchor="unanchored"``, and the note prints it without guillemets. The
  reading reaching Act II and Act III is the point of #3395; the citation was
  its ornament.

No second model call: the anchor is a deterministic word scan over the text
already in memory. A local move keeps the pre-#3415 rule — a failed citation
costs it, counted — because the measured loss was the centre of the document,
and widening the rule to twelve local moves would buy noise. And the record
NAMES the slot it lost (``dropped_slots``): a slot that produced nothing says
which one and why, so the next probe reads a fact instead of a count.

**The pillars, not only the thesis** (#3432). Cycle 2 of the panel measured
that the render now STATES the central thesis (9/10 documents) but does not
EXAMINE it: 25 severe M1 items remain, on 7 documents, and the zero-shot names
what the thesis rests on — the two or three passages of evidence or reasoning
that carry it — which no line of the render does. Those passages are usually
far from the thesis one, and the per-argument selection (#3395) prefers the
units overlapping a defining move, so they were rarely read at all. The third
slot names them (``slot="pillar"``, bounded by :func:`pillar_budget`), each with its
own verbatim quote and a kind from the closed vocabulary; being first-pass
moves, their spans join ``first_pass_move_spans`` and the selector examines
them first. The
slot points the lenses at the passages that carry the thesis — it does not
judge them, and it does not raise ``MAX_MOVES`` to catch them by volume.

**The second pass over the bare stretches** (#3511(b), coordinator decision
13/11). Cycle 6 and the three coordinator draws measured that ONE whole-document
draw names 20-46 moves but leaves long stretches with no anchor at all: a
single draw cannot certify the reading (26/11/20/14/19 of 39 across draws),
the longest document stays at 0 of 11 in every variant, and the misses sit in
the stretches the draw left bare — repeating the same call is measured not to
repair it. After the whole-document reading, a stretch of the document that no
anchored move covers, longer than the document's own even-coverage gap
(:func:`bare_stretch_spans`), gets its own reading call asking the first
reading's own question, and the moves it returns join the inventory with a
second-pass marker — same citation rule, whole-document offsets. The pass is
bounded in number by the document's own chunk count
(:func:`second_pass_call_bound`): a document the pipeline reads in one
capacity chunk issues no second call at all, and the bite of the bound is
recorded on the state and stated in the note. A document with no bare
stretch issues no second call and keeps a byte-identical inventory.

What the thesis LEAVES OUT is not a reading of the text: it belongs to the
historian and strategist personas (#3377), labelled ``model_knowledge``, and
never to this module.

**Not the historian of #3377.** The historian writes what the model knows about
the situation, labelled ``model_knowledge``. This module writes the text's own
content, labelled ``first_reading``. Two fields, two producers, two labels; a
reader never confuses what the text says with what we know about its period.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from argumentation_analysis.core.reading_window import (
    FIRST_READING_WINDOW,
    PER_ARGUMENT_CEILING,
    STATUS_SELECTED,
    WHOLE_TEXT_CALL_CAPACITY,
    WindowSelection,
    folded_words,
    inventory_budget,
    locate_quote,
    per_argument_unit_budget,
    pillar_budget,
    selected_text_and_selection,
)
from argumentation_analysis.core.shared_state import unit_extent

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

#: How many move LINES the NOTE shows (#3511: render-only). The state may
#: carry more — :func:`inventory_budget` bounds what the reading names — but
#: a reader's first page stays a page: the note shows the slots first, then
#: the moves the examination reached and a lens retained a finding on, then
#: a sample spread over the document, and says « N gestes nommés, M montrés
#: ici » when it truncates. Before #3511 this constant also capped the
#: inventory and the prompt — one number, two meanings: the render bar could
#: not measure the inventory (the panel measured 9-12 named where the
#: zero-shot names 11-18, the module full on 3 of 6 long documents).
MAX_MOVES = 12

#: #3432 — the FLOOR of the pillar budget, the former flat bound. Ask 6(a)
#: scales the bound with the document's length via ``pillar_budget``: a long
#: document can rest on more than three supports, while a short one keeps its
#: prompt and state byte-identical. This is a bound on named supports, not a
#: volume of local moves: ``MAX_MOVES`` stays where it was.
MAX_PILLARS = 3

#: #3480 rework (R1148) — step 2's bound sentence, at the floor. The paid
#: probe (0.086 $) measured the model obeying THIS sentence over the hard
#: rules: with "the two or three passages" still in step 2, it named three
#: pillars on every long document whatever ``At most N`` said. The wrap is
#: part of the value so the rendered floor prompt keeps the template's
#: former bytes exactly; above the floor :func:`pillar_prose` names the
#: computed budget instead.
_PILLAR_PROSE_FLOOR = "the two or three passages the\n   thesis would fall without"


def pillar_prose(max_pillars: int) -> str:
    """The sentence step 2 states the pillar bound in (#3480 rework).

    One producer: the caller fills this from its own
    ``pillar_budget(len(excerpt))`` — the number is never restated here. At
    or below :data:`MAX_PILLARS` the sentence is the flat-three prompt's own
    bytes, so a short document's prompt stays byte-identical; above it the
    sentence NAMES the budget, because a bound the model is not told in the
    sentence it reads does not bind (the measured defect).
    """
    if max_pillars <= MAX_PILLARS:
        return _PILLAR_PROSE_FLOOR
    return (
        "the passages the thesis would fall without, at most\n   "
        f"{max_pillars} on a document of this length"
    )


#: #3415 ask 4 — the two floors a document passage must clear before it can
#: anchor a slot whose quote failed the citation rule. Both are DECLARED here,
#: not tuned per call site, so the record can state what it accepted: a run of
#: this many consecutive words, covering at least this share of the quote's own
#: words. A short overlap is a coincidence of vocabulary (« la réforme » occurs
#: everywhere), and anchoring a thesis on one would be the fuzzy match this
#: repo refuses.
ANCHOR_MIN_RUN = 8
ANCHOR_MIN_SHARE = 0.5

#: #3511(b) — the provenance marker of a move the second pass named. The move
#: is still a first-reading move (same ``basis``, same label in the note); the
#: marker says WHICH pass named it, so the record and the replay can tell a
#: bare-stretch repair from a whole-draw name without a second inventory.
SECOND_PASS_MARKER = "second"

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

#: The two slots the question asks for first, under the names the NOTE prints
#: (#3415). One table so the move line and the lost-slot line cannot spell the
#: same slot two ways.
_SLOT_LABELS_FR = {
    "thesis": "thèse centrale",
    "mechanism": "mécanisme",
    # #3432 — the passages the thesis rests on. The kind of each pillar stays
    # in the closed vocabulary (the state records it); the NOTE prints the
    # slot, because « affirmation » would read as one more local move beside
    # the ones the document makes elsewhere.
    "pillar": "pilier de la thèse",
}

#: Why a slot produced nothing, in the reader's language (#3415 ask 4). The
#: state keeps the code; the note prints the phrase.
_SLOT_DROP_LABELS_FR = {
    "not_an_object": "réponse illisible",
    "no_reading": "lecture vide",
    "duplicate": "citation en double",
}

#: The two states a moved anchor can take (#3415 ask 4). One spelling each,
#: in the state, the note and the tests.
ANCHOR_RELOCATED = "relocated"
ANCHOR_UNANCHORED = "unanchored"


def _slot_label(slot: str) -> str:
    """The French name of a slot, or ``""`` when the value is not a slot."""
    return _SLOT_LABELS_FR.get(slot, "")


def _move_label(move: Dict[str, Any]) -> str:
    """The note's name for one move: its slot when it has one, else its kind.

    R1142 — the label prints in French (#3393, the reader's vocabulary); the
    English key stays in the state. #3415 — the two slots the question asks
    for first print under their own names, so the writer can point at the
    thesis and the mechanism as such.
    """
    return _slot_label(str(move.get("slot") or "")) or _KIND_LABELS_FR.get(
        str(move.get("kind")), "autre"
    )


FIRST_READING_PROMPT = """You are reading the document below ONCE, whole, before any
specialist sees it. Your job, in this order:

1. Name the document's CENTRAL THESIS — the claim the whole document builds
   toward — and the MECHANISM it argues it by: the device, the proof or the
   chain the document leans on to carry that thesis. On a long document these
   are often stated late, sometimes once, nowhere near the opening; a reader
   who stopped at the first page would miss them. Each of the two comes with
   its own verbatim quote.
2. Name the PILLARS the thesis rests on: {pillar_bound} — the evidence it cites, the premise it leans
   on, the ruling it claims to follow. They are usually FAR from the thesis
   passage, sometimes in another part of the document; that distance is
   exactly why a reader who only looks beside the thesis misses them. Each
   pillar comes with its own verbatim quote and a kind from the closed
   vocabulary.
3. Then EVERY argument the text carries, exhaustively: wherever it sits in
   the document — opening, middle or end, beside the thesis or far from it —
   name it. Each argument comes with ONE verbatim anchor in the text's own
   language, of 8 to 40 words, copied from the document: the anchor is where
   the argument lives, and an argument whose anchor you cannot quote verbatim
   is omitted rather than guessed.

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
- At most {max_moves} entries in total, thesis, mechanism and pillars
  included. Fewer is a valid answer; an entry you cannot fill with a verbatim
  quote from the document is omitted, and an empty list of other moves is
  valid.
- At most {max_pillars} pillars, and only those the thesis genuinely rests on:
  a pillar is not a restatement of the thesis and not a local remark.

Answer in French, with ONLY this JSON — no fences, no commentary:
{{"thesis": {{"reading": "one sentence naming the central thesis",
             "quote": "a verbatim span of the document"}},
 "mechanism": {{"reading": "one sentence naming the mechanism that carries it",
                "quote": "a verbatim span of the document"}},
 "pillars": [{{"kind": "claim|concession|device|audience|threat|dilemma|other",
              "reading": "one sentence naming what the thesis rests on",
              "quote": "a verbatim span of the document, usually far from the thesis"}}],
 "moves": [{{"kind": "concession|device|claim|audience|threat|dilemma|other",
             "reading": "one sentence naming the move",
             "quote": "a verbatim span of the document, 8 to 40 words — the argument's anchor"}}]}}

Document:
{excerpt}
"""


@dataclass
class DefiningMove:
    """One move the first reading named, with the text's own words for it.

    ``slot`` marks the entries the question asks for FIRST (#3415, #3432): the
    central thesis (``"thesis"``), the mechanism that carries it
    (``"mechanism"``) and each passage the thesis rests on (``"pillar"``,
    repeated up to :func:`pillar_budget`). Empty for a local move — the record
    carries the key
    only when there is a slot to state (honest absence, so a slot-less
    record stays byte-identical to a pre-#3415 one).

    ``anchor`` states how the quote relates to the document (#3415 ask 4), and
    is EMPTY when the quote passed the citation rule as given — the ordinary
    case, and the one a control record must keep byte-identical:

    * ``"relocated"`` — the model's quote failed the rule; the document
      carries a passage that clears the anchor floors, and ``quote``/``offset``
      are that passage, in the document's own characters;
    * ``"unanchored"`` — the model's quote failed and nothing in the document
      carried enough of it: the reading is kept, ``quote`` is empty and
      ``offset`` is ``None``, and the render prints no guillemets. The model's
      words are never presented as the document's.
    """

    kind: str
    reading: str
    quote: str
    offset: Optional[int] = None
    basis: str = FIRST_READING_BASIS
    slot: str = ""
    anchor: str = ""
    reading_pass: str = ""

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
        if self.anchor:
            payload["anchor"] = self.anchor
        if self.reading_pass:
            # #3511(b) — the second-pass marker. Only a move the second pass
            # named carries it: a first-pass-only record stays byte-identical.
            payload["pass"] = self.reading_pass
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

    ``dropped_slots`` (#3415 ask 4) NAMES the slot a reading lost, and why:
    ``[{"slot": "thesis", "reason": "no_reading"}]``. ``dropped_quotes`` alone
    could say only « 1 geste écarté » — the paid probe read that count and
    could not tell the central thesis from a local claim, which is how a
    thesis lost to a failed citation stayed invisible. A slot whose citation
    fails is no longer dropped (it is kept, anchored or not); this list is
    therefore the slots that produced NOTHING at all.
    """

    moves: List[DefiningMove] = field(default_factory=list)
    dropped_quotes: int = 0
    malformed_moves: int = 0
    dropped_slots: List[Dict[str, str]] = field(default_factory=list)
    status: str = "no_llm"
    error: str = ""
    read_scope: Dict[str, Any] = field(default_factory=dict)
    second_pass: Dict[str, Any] = field(default_factory=dict)

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
        if self.dropped_slots:
            payload["dropped_slots"] = [dict(entry) for entry in self.dropped_slots]
        # #3511(b) — the second pass's own record, ONLY when the pass ran: a
        # document with no bare stretch (or a text the pipeline reads in one
        # capacity chunk) keeps a byte-identical payload.
        if self.second_pass:
            payload["second_pass"] = dict(self.second_pass)
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

    #3415 rework (R1144, CI) — the scan reads the buffer IN PLACE. It used to
    take ``text[:start]``, which the #2850 census rightly reads as a head
    slice: a coverage-ish window over the answer, and a full-answer copy for
    every recovered object. Nothing needs the copy — the only thing the scan
    wants is what lies before ``start``, and it can walk there.
    """

    def _before_whitespace(index: int) -> int:
        while index >= 0 and text[index] in " \t\r\n":
            index -= 1
        return index

    colon = _before_whitespace(start - 1)
    if colon < 0 or text[colon] != ":":
        return None
    end = _before_whitespace(colon - 1)
    if end < 0 or text[end] != '"':
        return None
    i = end - 1
    while i >= 0:
        if text[i] == '"' and (i == 0 or text[i - 1] != "\\"):
            key = text[i + 1 : end]
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


def _array_span(text: str, key: str) -> Optional[Tuple[int, int]]:
    """``(start, end)`` of the top-level array named ``key``, string-aware.

    #3432 — the salvage could route back a slot that is an OBJECT (``thesis``,
    ``mechanism``), because ``_key_before`` names a ``{`` preceded by
    ``"key":``. An array's elements are preceded by ``[`` or ``,`` and carry
    no name at all: inside a failed wrapper, every pillar came back anonymous
    and was spliced as one more local move. This scan gives the array its own
    address, so its elements can be recovered with their slot.
    """
    needle = f'"{key}"'
    at = text.find(needle)
    while at != -1:
        i = at + len(needle)
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        if i < len(text) and text[i] == ":":
            i += 1
            while i < len(text) and text[i] in " \t\r\n":
                i += 1
            if i < len(text) and text[i] == "[":
                depth = 0
                in_string = False
                escape = False
                for j in range(i, len(text)):
                    ch = text[j]
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
                    if ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            return (i, j + 1)
                return None
        at = text.find(needle, at + len(needle))
    return None


def _salvage_array(text: str, key: str) -> Tuple[List[Any], int]:
    """Every readable element of the array named ``key``, and what was lost.

    Same principle as ``_salvage_objects``: one unreadable element costs that
    element, never the array.
    """
    span = _array_span(text, key)
    if span is None:
        return [], 0
    inner = text[span[0] + 1 : span[1] - 1]
    values: List[Any] = []
    malformed = 0
    for _name, element in _balanced_object_spans(inner):
        try:
            value = json.loads(element)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(value, dict):
            values.append(value)
        else:
            malformed += 1
    return values, malformed


def _parse_answer(content: str, max_pillars: int) -> Tuple[Dict[str, Any], int]:
    """The answer dict and the count of objects no path could read.

    ``max_pillars`` is the bound already stated in this call's prompt: the
    salvage must not silently restore the old flat-three bound on a long text.

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
        # #3432 — the pillars array is recovered by its own address, before
        # the object splice. Its elements are anonymous to ``_key_before``
        # (« ``[`` or ``,`` before it »), so without this they were spliced as
        # local moves and the slot they name was lost with the malformed
        # sibling that cost the wrapper its parse.
        recovered_pillars, pillar_bad = _salvage_array(text, "pillars")
        malformed += pillar_bad
        if recovered_pillars:
            spliced["pillars"] = recovered_pillars[:max_pillars]
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
                # #3432 — the pillars are a LIST under their own key, so the
                # pre-#3432 salvage could not route them back to their slot:
                # one bad character elsewhere and every pillar arrived as an
                # anonymous local move. Same principle as the two dict slots.
                if isinstance(obj.get("pillars"), list) and "pillars" not in spliced:
                    spliced["pillars"] = obj["pillars"]
            elif "kind" in obj or ("reading" in obj and "quote" in obj):
                # A pillar already recovered from its array must not come
                # back a second time as a local move (#3432).
                if recovered_pillars and any(obj == p for p in recovered_pillars):
                    continue
                extra_moves.append(obj)
        if extra_moves:
            spliced["moves"] = extra_moves
        return spliced, malformed
    return parsed if isinstance(parsed, dict) else {}, 0


def build_first_reading_prompt(excerpt: str) -> str:
    """The one prompt of the first reading, with its length-aware bounds.

    #3480 rework (R1148) — the pillar bound is computed ONCE and reaches the
    prompt twice, as the number of the hard rule and as the sentence of step
    2 (:func:`pillar_prose`): the model obeyed the sentence, never the rule,
    so both must name the same figure from this single call.

    #3511 — the total bound is the INVENTORY budget (:func:`inventory_budget`),
    computed from the same excerpt: a bound the model is not told does not
    bind (the #3480 lesson, at the inventory's scale). It is never the render
    cap — ``MAX_MOVES`` says what the NOTE shows, not what the reading may
    name.
    """
    bound = pillar_budget(len(excerpt))
    return FIRST_READING_PROMPT.format(
        max_moves=inventory_budget(len(excerpt)),
        max_pillars=bound,
        pillar_bound=pillar_prose(bound),
        excerpt=excerpt,
    )


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
        max_pillars = pillar_budget(len(excerpt))
        # #3511 — the inventory bound the PROMPT stated is the bound the
        # parse enforces: what the model was told it may name is what the
        # state may carry. The render cap (``MAX_MOVES``) never truncates
        # the record — the note chooses what it shows, and says so.
        max_inventory = inventory_budget(len(excerpt))
        content = await llm_callable(build_first_reading_prompt(excerpt))
        parsed, malformed = _parse_answer(content or "", max_pillars)
        raw_moves = parsed.get("moves")
        if not isinstance(raw_moves, list):
            raw_moves = None
        _pillars = parsed.get("pillars")
        has_slot = (
            isinstance(parsed.get("thesis"), dict)
            or isinstance(parsed.get("mechanism"), dict)
            or (isinstance(_pillars, list) and bool(_pillars))
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
            """One entry, through the citation rule — then, for a slot only,
            through the anchor (#3415 ask 4).

            A local move keeps the pre-#3415 rule: a quote the document does
            not carry is counted and dropped. The two slots the question asks
            for FIRST are what the panel measures, and a thesis that falls on
            its citation takes its reading with it — so a failed citation
            sends them to ``anchor_quote_in``: a document passage that clears
            the floors re-anchors the move on the DOCUMENT's words, and one
            that does not leaves the move with its reading and no quote at all.
            In neither case do the model's words reach a guillemet."""
            nonlocal dropped
            if not isinstance(entry, dict):
                if slot:
                    result.dropped_slots.append(
                        {"slot": slot, "reason": "not_an_object"}
                    )
                else:
                    dropped += 1
                return
            reading = str(entry.get("reading", "") or "").strip()
            quote = str(entry.get("quote", "") or "").strip()
            if not reading:
                # A slot with no reading has nothing to record: it is NAMED
                # (#3415 ask 4), where the counter alone could not say which.
                if slot:
                    result.dropped_slots.append({"slot": slot, "reason": "no_reading"})
                else:
                    dropped += 1
                return
            if quote and quote_occurs_in(raw_text, quote):
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
                return
            if slot:
                anchored = anchor_quote_in(raw_text, quote) if quote else None
                if anchored is not None:
                    passage, start = anchored
                    logger.info(
                        "FirstReading: slot %s re-anchored on a document passage",
                        slot,
                    )
                    moves.append(
                        DefiningMove(
                            kind=kind,
                            reading=reading,
                            quote=passage,
                            offset=start,
                            slot=slot,
                            anchor=ANCHOR_RELOCATED,
                        )
                    )
                    return
                logger.info(
                    "FirstReading: slot %s kept unanchored (no document passage)", slot
                )
                moves.append(
                    DefiningMove(
                        kind=kind,
                        reading=reading,
                        quote="",
                        offset=None,
                        slot=slot,
                        anchor=ANCHOR_UNANCHORED,
                    )
                )
                return
            # The one citation rule (#3389). Counted, never kept.
            dropped += 1
            logger.info("FirstReading: dropped an entry whose quote is absent")

        # #3415 ask 1 — the two entries the question asks for FIRST: the
        # central thesis and the mechanism that carries it. The kinds stay in
        # the closed vocabulary (thesis / device); the slot marks what each
        # is, and both are kept ahead of the local moves whatever their
        # position in the document (a late mechanism is the measured case).
        _keep(parsed.get("thesis"), "thesis", "thesis")
        _keep(parsed.get("mechanism"), "device", "mechanism")
        # #3432 — the pillars the thesis rests on, kept AHEAD of the local
        # moves whatever their position in the document. The panel measured
        # them far from the thesis passage (the zero-shot finds them, the
        # per-argument selection does not), and the selection prefers the
        # units a first-pass move overlaps (``first_pass_move_spans``): kept at
        # their document order, a pillar would lose its place to a local
        # claim that happens to sit beside the thesis. Bounded by
        # ``pillar_budget(len(excerpt))``, the SAME bound stated to the model;
        # ``MAX_MOVES`` never moves.
        pillars = parsed.get("pillars")
        if isinstance(pillars, list):
            for raw in pillars[:max_pillars]:
                pillar_kind = (
                    move_kind(raw.get("kind")) if isinstance(raw, dict) else "other"
                )
                if pillar_kind == "other":
                    # A pillar without a kind from the closed vocabulary is
                    # still a claim the thesis rests on — the kind is a hint,
                    # not a verdict, and refusing it would lose the passage.
                    pillar_kind = "claim"
                _keep(raw, pillar_kind, "pillar")
                if len(moves) >= max_inventory:
                    break
        for raw in raw_moves or []:
            if not isinstance(raw, dict):
                continue
            _keep(raw, move_kind(raw.get("kind")), "")
            if len(moves) >= max_inventory:
                break

        # A move the model repeated (same quote) is one move: the reading is
        # kept once, in its first position, and the duplicate is counted as
        # dropped like any other unreadable answer. An UNANCHORED slot has no
        # quote to compare (#3415 ask 4), so it keys on its own slot and
        # reading — keying on the empty string collapsed every unanchored move
        # into the first one.
        unique: List[DefiningMove] = []
        seen = set()
        for move in moves:
            key = move.quote or f"#{move.slot}:{move.reading}"
            if key in seen:
                if move.slot:
                    result.dropped_slots.append(
                        {"slot": move.slot, "reason": "duplicate"}
                    )
                else:
                    dropped += 1
                continue
            seen.add(key)
            unique.append(move)

        result.moves = unique
        result.dropped_quotes = dropped
        result.malformed_moves = malformed
        result.status = "ok"
        # #3511(b) — the second pass over the bare stretches, only after a
        # successful whole-document reading: a FAILED reading is degraded,
        # not bare. A document with no bare stretch (or a one-chunk
        # document, or a reading that anchored nothing) returns from the
        # pass unchanged — byte-identical inventory, no record key.
        try:
            await _second_reading_pass(result, raw_text, llm_callable, max_inventory)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("SecondReading pass failed whole: %s", e)
        logger.info(
            "FirstReading: %d move(s), %d dropped, %d malformed, whole_document=%s"
            "%s",
            len(result.moves),
            result.dropped_quotes,
            result.malformed_moves,
            result.read_scope.get("whole_document"),
            (
                f", second pass: {result.second_pass['calls']} call(s), "
                f"{result.second_pass['moves_kept']} move(s) kept"
                if result.second_pass
                else ""
            ),
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


def _folded_words(text: str) -> List[Tuple[str, int, int]]:
    """``(folded, start, end)`` per word — the fold, with original offsets.

    #3517 — the implementation lives in :func:`reading_window.folded_words`
    now: the locator and the anchor are the same question ("where do these
    folded words sit in the document?") and must read the same fold. This
    name stays as the anchor module's local handle on it.
    """
    return folded_words(text)


def anchor_quote_in(text: str, quote: str) -> Optional[Tuple[str, int]]:
    """The document passage carrying the longest shared word run, or ``None``.

    #3415 ask 4. A quote the citation rule refused is not thereby a
    fabrication: the model may have joined two passages, changed one word, or
    re-cut the span. This scan looks for what the two DO share — the longest
    run of consecutive words equal after the citation rule's own folding — and
    answers the document's characters for that run plus their offset.

    ``None`` unless the run clears BOTH floors (:data:`ANCHOR_MIN_RUN`
    consecutive words, :data:`ANCHOR_MIN_SHARE` of the quote's words). Under
    them the overlap is a coincidence of vocabulary, and a passage anchored on
    one would put the reader's eye on a sentence the model never quoted.

    The passage returned is a substring of ``text`` by construction — it is
    cut from the document at word boundaries — so printing it between « » is
    honest, and the citation rule accepts it without any relaxation.

    Deterministic and local: no model call, no network, no RNG. Cost is one
    pass over the document's words plus one extension per candidate position of
    each quote word.
    """
    words = _folded_words(text)
    needle = [folded for folded, _start, _end in _folded_words(quote)]
    if not words or not needle:
        return None
    positions: Dict[str, List[int]] = {}
    for index, (folded, _start, _end) in enumerate(words):
        positions.setdefault(folded, []).append(index)
    best_run = 0
    best_text = -1
    for qi, folded in enumerate(needle):
        for pi in positions.get(folded, ()):
            run = 0
            while (
                qi + run < len(needle)
                and pi + run < len(words)
                and needle[qi + run] == words[pi + run][0]
            ):
                run += 1
            if run > best_run:
                best_run, best_text = run, pi
    required = max(ANCHOR_MIN_RUN, math.ceil(ANCHOR_MIN_SHARE * len(needle)))
    if best_run < required:
        return None
    start = words[best_text][1]
    end = words[best_text + best_run - 1][2]
    return text[start:end], start


# --- #3511(b): the second pass over the bare stretches -----------------------


def _merged_anchor_spans(moves: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """The anchored moves' spans, merged — one anchor group per covered run.

    Overlapping and adjacent quotes (the c7 panel states carry consecutive
    anchored quotes) are one coverage run: they leave ONE stretch between
    them, not a shard per quote. Only positioned moves contribute — an
    unanchored slot has no span, and a span it never earned would shrink the
    document's bare stretches by invention.
    """
    spans = []
    for move in moves:
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if isinstance(offset, int) and not isinstance(offset, bool) and quote:
            spans.append((offset, offset + len(quote)))
    spans.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def bare_stretch_spans(
    raw_text: str, moves: List[Dict[str, Any]]
) -> Tuple[List[Tuple[int, int]], int]:
    """#3511(b) — the document's bare stretches, and the gap that defines one.

    A stretch is BARE when it is a maximal span no anchored move covers,
    LONGER than the document's own even-coverage gap ``L / (k + 1)`` — with
    ``k`` merged anchor groups, an even reading leaves every one of the
    ``k + 1`` anchor-free segments at that length, so a segment above it
    carries more than its proportional share of unnamed text: it is where the
    single whole-document draw's names ran out. Both terms are the document's
    own (its length and the anchors its reading produced) — no threshold
    tuned on the panel. ``k = 0`` (nothing anchored) gives a gap of ``L`` and
    no stretch at all: re-asking the same question on the same failed read is
    the measured non-repair (coordinator R1166).

    Returns ``(stretches, gap)`` with the stretches LONGEST FIRST (ties by
    document position) — the order the bounded pass reads them in, so the
    longest hole is always the first repaired whatever the bound.
    """
    length = len(raw_text)
    merged = _merged_anchor_spans(moves)
    gap = length // (len(merged) + 1)
    segments: List[Tuple[int, int]] = []
    previous = 0
    for start, end in merged:
        if start > previous:
            segments.append((previous, start))
        previous = max(previous, end)
    if previous < length:
        segments.append((previous, length))
    bare = [(s, e) for s, e in segments if e - s > gap]
    bare.sort(key=lambda span: (-(span[1] - span[0]), span[0]))
    return bare, gap


def second_pass_call_bound(text_length: int) -> int:
    """#3511(b) — how many second-pass calls a document may spend.

    One call per capacity chunk BEYOND THE FIRST (the pipeline's own reading
    unit, ``WHOLE_TEXT_CALL_CAPACITY``): a document the pipeline reads in a
    single chunk issues no second call at all — one pass over a one-chunk
    document has already attended all of it — and a multi-chunk document can
    never spend more calls re-reading its holes than it spends chunks reading
    itself. The bound is the document's own, like the gap; when it bites, the
    state records the stretches left unread (:func:`_second_reading_pass`).
    """
    if text_length <= WHOLE_TEXT_CALL_CAPACITY:
        return 0
    return -(-text_length // WHOLE_TEXT_CALL_CAPACITY) - 1


SECOND_READING_PROMPT = """You are reading ONE STRETCH of a longer document, once, whole. \
The document's central thesis has already been named by an earlier pass over the whole text:
{thesis_context}

Your job: name EVERY argument this stretch carries, exhaustively: wherever it
sits in the stretch — opening, middle or end — name it. Each argument comes
with ONE verbatim anchor in the text's own language, of 8 to 40 words, copied
from the stretch: the anchor is where the argument lives, and an argument
whose anchor you cannot quote verbatim is omitted rather than guessed.

Hard rules:
- One call, one pass. Say what the text DOES, not what it should have done.
- No verdict. Never say whether a move is a fallacy, valid, good or bad: the
  instruments decide that afterwards.
- Do not restate the thesis and do not quote from outside the stretch.
- Every entry carries a VERBATIM quote copied from the stretch, character for
  character: no translation, no paraphrase, no ellipsis, no two passages
  joined. A quote the stretch does not carry is discarded by the pipeline.
- Do not date, place or situate the document in history. Another reader does
  that.
- At most {max_moves} entries. Fewer is a valid answer; an empty list of
  moves is valid.

Answer in French, with ONLY this JSON — no fences, no commentary:
{{"moves": [{{"kind": "concession|device|claim|audience|threat|dilemma|other",
             "reading": "one sentence naming the move",
             "quote": "a verbatim span of the stretch, 8 to 40 words — the argument's anchor"}}]}}

Stretch:
{excerpt}
"""


def build_second_reading_prompt(
    stretch: str, thesis_reading: str, max_moves: int
) -> str:
    """The second pass's one prompt: the stretch, the thesis the first pass
    named, and the first reading's own exhaustive question.

    The thesis is CONTEXT, never a slot to fill: the pass exists to name what
    the whole-document draw left bare, not to re-decide the centre. Its quote
    is deliberately absent — a model handed the verbatim centre echoes it, and
    the containment rule (:func:`_second_reading_pass`) would drop the echo.
    """
    context = (
        f"« {thesis_reading} »"
        if thesis_reading
        else "no central thesis was named by the earlier pass."
    )
    return SECOND_READING_PROMPT.format(
        thesis_context=context, max_moves=max_moves, excerpt=stretch
    )


async def _second_reading_pass(
    result: FirstReading,
    raw_text: str,
    llm_callable: Callable[[str], Awaitable[str]],
    max_inventory: int,
) -> None:
    """Read the bare stretches and join their moves to the inventory.

    #3511(b), the coordinator decision of 13/11. Called only after a
    successful whole-document reading — a FAILED reading is degraded, not
    bare. For every bare stretch the bound allows, longest first:

    * the call asks the first reading's own question over the stretch, with
      the thesis the first pass named as context;
    * every returned entry passes the SAME citation rule (``quote_occurs_in``
      against the stretch it was asked about) and locates by the same
      locator, so its offset is a whole-document offset by construction.
      R1167 finding 2: the locator reads the STRETCH (``locate_quote`` over
      ``raw_text[start:end]``, plus ``start``), never the whole document —
      a phrase the document also carries EARLIER would otherwise locate at
      its first occurrence, outside the stretch, and the containment rule
      would drop the very argument the call was sent to find;
    * a quote whose anchor does not land INSIDE its stretch is not kept (it
      echoes the context or another passage — the call was about the
      stretch); a passage another move already anchors takes no second move
      (across passes), keyed on the LOCATED SPAN — the same words in two
      passages are two passages, not a duplicate;
    * the inventory's declared bound still caps the total, and is NOT first
      come, first served in stretch order (R1167): each stretch the pass
      reads takes a SHARE of the slots still open — the slots left, split
      over the stretches still to read — so the longest stretch can no
      longer fill the inventory and leave the tail a count only. What a
      stretch loses to its share is counted on the stretch
      (``inventory_lost``) and in the total (``inventory_capped``), never
      silently dropped;
    * the kept moves carry :data:`SECOND_PASS_MARKER` provenance.

    A stretch call that raises costs its stretch (``failed_calls``), never
    the reading: the first pass's inventory stands, and ``calls`` counts the
    stretches actually read — an attempt that raised is not a re-read
    (R1167 finding 3). The record is written on ``result.second_pass`` — the
    gap, the bounds, each qualifying stretch with whether the pass read it
    and what its share cost it, and the counts — and the note states the
    bite of both bounds (:func:`first_reading_note`).
    """
    bare, gap = bare_stretch_spans(raw_text, [m.to_dict() for m in result.moves])
    bound = second_pass_call_bound(len(raw_text))
    record: Dict[str, Any] = {
        "gap": gap,
        "call_bound": bound,
        "inventory_bound": max_inventory,
        "stretches": [],
        "calls": 0,
        "moves_kept": 0,
        "dropped_quotes": 0,
        "malformed": 0,
        "failed_calls": 0,
    }
    if not bare or bound <= 0:
        return

    thesis = next((m.reading for m in result.moves if m.slot == "thesis"), "")
    # One move per PASSAGE, across passes — the located span is the passage.
    seen = {m.span() for m in result.moves if m.span()}
    reads_left = min(len(bare), bound)  # every stretch the bound still reads
    for position, (start, end) in enumerate(bare):
        # The bound reads the FIRST ``bound`` stretches of the longest-first
        # order — ``position < bound``, never ``position < reads_left``:
        # ``reads_left`` decrements as stretches are read (it sizes the
        # inventory SHARE) and would un-read the tail of the bound's own set.
        read_flag = position < bound
        record["stretches"].append(
            {"offset": start, "length": end - start, "read": read_flag}
        )
        if not read_flag:
            continue  # the bound bites: the stretch is recorded, not read
        stretch_text = raw_text[start:end]
        # The stretch's SHARE of the inventory (R1167): the slots still open,
        # split over the stretches still to read. Slots a stretch does not
        # use flow to the later ones; the hard cap below still guards the
        # declared bound when the floor (one slot) overshoots it.
        slots_left = max_inventory - len(result.moves)
        share = max(1, slots_left // reads_left) if slots_left > 0 else 0
        kept_here = 0
        lost_here = 0
        try:
            content = await llm_callable(
                build_second_reading_prompt(
                    stretch_text, thesis, inventory_budget(end - start)
                )
            )
        except Exception as e:  # pragma: no cover - provider failures
            record["failed_calls"] += 1
            logger.warning("SecondReading stretch %d-%d failed: %s", start, end, e)
            reads_left -= 1
            continue
        record["calls"] += 1
        parsed, malformed = _parse_answer(content or "", 0)
        record["malformed"] += malformed
        raw_moves = parsed.get("moves")
        if isinstance(raw_moves, list):
            for raw in raw_moves:
                if not isinstance(raw, dict):
                    record["malformed"] += 1
                    continue
                reading = str(raw.get("reading", "") or "").strip()
                quote = str(raw.get("quote", "") or "").strip()
                if not reading or not quote:
                    record["dropped_quotes"] += 1
                    continue
                if kept_here >= share or len(result.moves) >= max_inventory:
                    lost_here += 1
                    record["inventory_capped"] = record.get("inventory_capped", 0) + 1
                    continue
                if not quote_occurs_in(stretch_text, quote):
                    record["dropped_quotes"] += 1
                    continue
                local = locate_quote(stretch_text, quote)
                index = -1 if local < 0 else local + start
                if index < 0 or not (start <= index < end):
                    # Unlocatable, or an echo of the context or another
                    # passage: the call was about the stretch.
                    record["dropped_quotes"] += 1
                    continue
                if (index, index + len(quote)) in seen:
                    record["dropped_quotes"] += 1
                    continue
                seen.add((index, index + len(quote)))
                result.moves.append(
                    DefiningMove(
                        kind=move_kind(raw.get("kind")),
                        reading=reading,
                        quote=quote,
                        offset=index,
                        reading_pass=SECOND_PASS_MARKER,
                    )
                )
                kept_here += 1
                record["moves_kept"] += 1
        reads_left -= 1
        if lost_here:
            record["stretches"][-1]["inventory_lost"] = lost_here
    result.second_pass = record


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
    """The ``(start, end)`` spans of the positioned moves.

    Unpositioned moves (a verified quote the exact/windowed locator could not
    place) contribute no span: a selection cannot be told to prefer a range it
    cannot name, and inventing one would put the units somewhere they are not.
    The selector's priority hint is the FIRST pass's subset of these —
    :func:`first_pass_move_spans` (R1167: the second pass's moves must not
    dissolve the first reading's priority).
    """
    spans = []
    for move in defining_moves(state):
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            continue
        spans.append((offset, offset + len(quote)))
    return spans


def first_pass_move_spans(state: Any) -> List[Tuple[int, int]]:
    """The spans of the FIRST pass's positioned moves — the selector's hint.

    #3511(b) revision (R1167): the second pass's moves join the inventory and
    the population (their anchored units exist so a bare stretch CAN be
    examined), but they do not join the PRIORITY the whole-document reading
    gives the selection. The records measured why: every move was a priority
    span, a full inventory spread the reserved seats over ~80 anchors, and
    the selection fell back to chance — the pass dissolved the very priority
    it was supposed to reinforce. The spans here are the whole-document
    reading's own centres; a second-pass move is one when the budget rule
    reaches it, never a reserved seat.

    A move is second-pass exactly when its record carries
    :data:`SECOND_PASS_MARKER` under ``pass`` (the writer copies moves as
    written), so a state whose reading never ran the pass keeps the same
    spans as ``defining_move_spans`` — byte-identical selection.
    """
    spans = []
    for move in defining_moves(state):
        if move.get("pass") == SECOND_PASS_MARKER:
            continue
        offset = move.get("offset")
        quote = str(move.get("quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            continue
        spans.append((offset, offset + len(quote)))
    return spans


def examined_unit_budget(state: Any, bound: Optional[int] = None) -> Optional[int]:
    """#3511 (R1164 rework) — the per-argument budget once the reading has
    named its arguments: ``min(N, PER_ARGUMENT_CEILING, max(k(L), named))``.

    A function of the STATE deliberately, so the coordinator replays panel
    states through this one seam, free. The named never REDUCE the budget
    (``max(k(L), named)``) — and the pass never outnames the inventory
    (``min`` against ``N``, the inventory bound, defaulting to
    :func:`inventory_budget` over the same text): examining more arguments
    than were named would spend units the reading never pointed at. The
    R1164 replay measured this configuration at 20/39 passages examined
    against 12/39 with the pass capped at 30. ``bound`` is the seam's own
    injection point — a replay or a witness states the bound it wants; the
    production call site passes the state alone.

    #3511(b) — the ceiling term. The second pass can push the named count
    past ``k(L)``'s ceiling (the c7 draws already named 46 on one document;
    a bare-stretch pass adds more), and the pass's real cost is the units it
    then examines (~0.019 $ per unit, #3523): the coordinator's decision
    caps the EXAMINED count at :data:`PER_ARGUMENT_CEILING` whatever the
    named count reaches. Named moves beyond the cap are not lost — they land
    in the residue (« nommé, non examiné », reason ``budget``) beside the
    one producer that records it.
    """
    raw = getattr(state, "raw_text", None)
    if isinstance(state, dict):
        raw = state.get("raw_text")
    if not isinstance(raw, str) or not raw:
        return None
    inventory = bound if bound is not None else inventory_budget(len(raw))
    return min(
        inventory,
        PER_ARGUMENT_CEILING,
        max(per_argument_unit_budget(len(raw)), len(defining_moves(state))),
    )


#: #3416 — how far AFTER a unit's end a recorded concession still counts as
#: the passage around the claim (the August method's « next sentence »). A
#: concession further away belongs to another part of the document, and a
#: statement that is not about the claim is not evidence about it.
DOCUMENT_STATEMENT_AFTER_UNIT = 400


def document_statements_for_unit(
    state: Any,
    entry: Any,
    unit_text: str = "",
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

    #3502 — the unit's extent is its PASSAGE, read from the provenance
    ``entry`` by ``shared_state.unit_extent``: the source quote when the
    entry carries one, the text otherwise. The paraphrase the descent hands
    over runs ×2.6 past the located passage in the median (the coordinator's
    panel measure), and a concession recorded in that overrun is the document
    speaking about the NEXT passage — not carried here.

    No geometry (no offset on either side) means no statement: a citation
    that cannot be placed is not evidence about this claim (the same rule as
    ``defining_move_spans``). Nothing recorded means nothing carried — the
    caller's behaviour is then byte-identical to the pre-#3416 path.
    """
    extent = unit_extent(entry, unit_text)
    if extent is None:
        return []
    unit_start, unit_end = extent
    statements: List[Dict[str, Any]] = []
    for move in defining_moves(state):
        if str(move.get("kind") or "") != "concession":
            continue
        quote = str(move.get("quote") or "")
        move_offset = move.get("offset")
        if (
            not quote
            or not isinstance(move_offset, int)
            or isinstance(move_offset, bool)
        ):
            continue
        move_end = move_offset + len(quote)
        if unit_start < move_end and move_offset < unit_end:
            relation = "overlap"
        elif unit_end <= move_offset <= unit_end + DOCUMENT_STATEMENT_AFTER_UNIT:
            relation = "adjacent"
        else:
            continue
        statements.append(
            {"source": "first_reading_concession", "relation": relation, "quote": quote}
        )
    return statements


#: #3428 — how much frame text rides on either side of the unit. The window
#: is one sentence before and one sentence after, so it is bounded by
#: construction — the cap only tames a document whose "sentence" runs for
#: pages without a full stop, and keeps the side ADJACENT to the unit (the
#: tail of the before-window, the head of the after-window).
FRAME_CONTEXT_MAX_CHARS = 600

#: #3428 — a sentence ends at a run of terminal punctuation followed by
#: whitespace: ``.`` ``!`` ``?`` ``…`` (with optional closing quotes/brackets
#: before the space). Deterministic local scan, no model, no segmentation
#: library — the frame says where the sentence boundaries are, it does not
#: interpret them.
_SENTENCE_END_RE = re.compile(r'[.!?…]+[»"”\')\]]*\s+')


def document_frame_for_unit(
    state: Any,
    unit_text: str = "",
    offset: Optional[int] = None,
    source_quote: Optional[str] = None,
) -> Dict[str, str]:
    """#3428 — the document's frame AROUND one unit, or ``{}``.

    The per-unit descent reads the extracted unit alone. Cycle 2 measured
    what that loses (13 of the 27 M2 contresens): a unit cut from its
    sentence drops the antecedent of a noun and the premises before it; a
    unit extracted as a paraphrase drops the document's own modality. This
    producer hands the descent the LOCAL frame, verbatim, from the run's
    own memory — no second call:

    * ``before`` — from the start of the sentence BEFORE the unit's
      sentence up to the unit's start (so it carries the previous sentence
      AND the opening of the unit's own sentence when the unit starts
      mid-sentence);
    * ``after`` — from the unit's end to the end of the sentence AFTER the
      unit's sentence (the unit's own completion plus the next sentence);
    * ``source_quote`` — the verbatim passage the provenance recorded,
      i.e. the document's own words where a PARAPHRASE was extracted. For
      a paraphrase the offsets describe the quote, so the unit's end is
      computed on the quote, not on the paraphrase's length.

    Offsets come from the caller (provenance) — never from a search of the
    unit text in the document: a paraphrase would cite the wrong passage,
    and a wrong frame is worse than none (#1019). No offset, no raw text
    or an offset outside the text ⇒ ``{}``, and the descent then emits its
    pre-#3428 prompts byte for byte.
    """
    if not isinstance(offset, int) or isinstance(offset, bool):
        return {}
    raw = str(getattr(state, "raw_text", "") or "")
    if not raw or not (0 <= offset < len(raw)):
        return {}
    parts: Dict[str, str] = {}
    key = str(source_quote) if source_quote else str(unit_text or "")
    unit_end = min(offset + max(len(key), 0), len(raw))
    breaks = list(_SENTENCE_END_RE.finditer(raw))
    # before: two sentence-start boundaries back from the unit's start
    # (starts[0] = 0 — the opening of the document's first sentence).
    starts = [0] + [m.end() for m in breaks]
    idx = 0
    for i, s in enumerate(starts):
        if s <= offset:
            idx = i
        else:
            break
    s_prev = starts[idx - 1] if idx >= 1 else 0
    before = raw[s_prev:offset].strip()[-FRAME_CONTEXT_MAX_CHARS:].strip()
    if before:
        parts["before"] = before
    # after: from the unit's end past TWO sentence-end boundaries (the
    # unit's own completion, then the whole next sentence). A document
    # that ends sooner keeps what is there — the remainder is the next
    # sentence, terminated or not.
    after_matches = [m for m in breaks if m.start() >= unit_end]
    if len(after_matches) >= 2:
        after_end = after_matches[1].end()
    else:
        after_end = len(raw)
    after = raw[unit_end:after_end].strip()[:FRAME_CONTEXT_MAX_CHARS].strip()
    if after:
        parts["after"] = after
    quote = str(source_quote or "").strip()
    if quote:
        parts["source_quote"] = quote
    return parts


#: #3431 — the reader's position bands: (lower bound of the share, its part).
#: Below the first bound the part is the opening. A raw character offset
#: names nothing to a writer who does not hold the document (measured, panel
#: cycle 2: a thesis at 94 % read as an opening); the share and its part do.
#: The péroraison band exists because a peroration is a rhetorical fact a
#: « fin » at 98 % would hide.
_POSITION_BANDS_FR = (
    (0.25, "vers le milieu du texte"),
    (0.75, "vers la fin du texte"),
    (0.95, "dans la péroraison"),
)
_POSITION_OPENING_FR = "vers le début du texte"


def _reader_position_fr(offset: Any, text_length: Any) -> str:
    """The move's position in the READER's terms, or ``""``.

    Computed from the record's own ``text_length`` (the length of the text
    the producer read): the share of the text at which the quote starts and
    the part that share falls in, e.g. ``", vers la fin du texte (94 %)"``.
    No raw offset is printed to a writer — the offset itself stays in the
    state, where the selection and the census read it.
    """
    if not isinstance(offset, int) or isinstance(offset, bool):
        return ""
    if not isinstance(text_length, int) or isinstance(text_length, bool):
        return ""
    if text_length <= 0:
        return ""
    share = min(1.0, max(0.0, offset / text_length))
    percent = int(round(share * 100))
    part = next(
        (label for bound, label in reversed(_POSITION_BANDS_FR) if share >= bound),
        _POSITION_OPENING_FR,
    )
    return f", {part} ({percent} %)"


def _unexamined_move_indices(state: Any) -> Optional[frozenset]:
    """#3511 — the indices (in ``defining_moves`` order) the examined set did
    NOT reach.

    Read from the selector's coverage record: the selector computes the
    residue over the SAME list with the SAME sort, so an index here is an
    index there. ``None`` when no selection was recorded (a state the
    per-argument pass never ran on, an older snapshot): the caller shows no
    « atteint par l'examen » tier rather than inventing the claim. An empty
    frozenset is a MEASURED « every named move was reached ».
    """
    coverage = getattr(state, "analysis_coverage", None)
    if isinstance(state, dict):
        coverage = state.get("analysis_coverage")
    if not isinstance(coverage, dict):
        return None
    entry = coverage.get("fallacy_per_argument")
    if not isinstance(entry, dict):
        return None
    residue = entry.get("named_unexamined")
    if not isinstance(residue, list):
        return None
    return frozenset(
        i
        for i in (item.get("index") for item in residue if isinstance(item, dict))
        if isinstance(i, int) and not isinstance(i, bool)
    )


def _spread_sample(pool: List[int], count: int) -> List[int]:
    """An even-position sample of ``pool`` (already in document order).

    The positional stratum of the page (#3511 ask 4): when the note cannot
    show every gesture, the ones it does show still stand for the whole
    document — first, middle and last — instead of crowding the head.
    """
    if count <= 0 or not pool:
        return []
    if len(pool) <= count:
        return list(pool)
    step = len(pool) / count
    return [pool[min(len(pool) - 1, round(i * step))] for i in range(count)]


def _shown_move_indices(
    moves: List[Dict[str, Any]],
    unexamined: Optional[frozenset],
    findings: Optional[frozenset] = None,
) -> List[int]:
    """#3511 — which moves the page shows, and in what order.

    Under :data:`MAX_MOVES` every gesture shows, in document order (the
    #3431 render). Over it the page is CHOSEN, never cut from the tail:

    1. the slots — thesis, mechanism, pillars — in document order;
    2. the moves the examination reached AND a lens retained a finding on
       (``findings`` is a measured set), spread-sampled over the document
       — never the first ``room`` of them (R1164 review §3: with
       ``k_eff`` every positioned move is meant to be reached, so
       "reached" stops discriminating and fills from the head);
    3. a positional sample of the remainder (:func:`_spread_sample`).

    ``unexamined is None`` (no selection recorded) skips tier 2: the note
    shows the slots and a spread, and claims no examination it cannot read.
    ``findings`` empty is a MEASURED « no lens retained anything » — tier 2
    is then empty and the spread carries the page.
    """
    if len(moves) <= MAX_MOVES:
        return list(range(len(moves)))
    slot_idx = [i for i, m in enumerate(moves) if _slot_label(str(m.get("slot") or ""))]
    rest_idx = [
        i for i, m in enumerate(moves) if not _slot_label(str(m.get("slot") or ""))
    ]
    room = MAX_MOVES - len(slot_idx)
    if room <= 0:
        return slot_idx[:MAX_MOVES]
    if unexamined is None:
        return slot_idx + _spread_sample(rest_idx, room)
    carried = findings or frozenset()
    finding = [i for i in rest_idx if i not in unexamined and i in carried]
    rest3 = [i for i in rest_idx if i not in set(finding)]
    take = _spread_sample(finding, room)
    return slot_idx + take + _spread_sample(rest3, room - len(take))


def _finding_move_indices(state: Any) -> frozenset:
    """#3511 (R1164 review §3) — the moves a lens retained a finding on.

    ONE predicate, reused not copied: ``named_moves_with_retained_finding``
    (orchestration/selection.py) binds #3510's ``coverage_family_by_unit``
    — an argument the review's walk retained a fallacy on — to the named
    moves by the selector's own overlap rule. Imported lazily: the render
    path pulls its dependencies at call time, like ``quote_fidelity``
    (``quote_occurs_in``), so importing this module never drags the
    orchestration package in.
    """
    from argumentation_analysis.orchestration.selection import (
        named_moves_with_retained_finding,
    )

    return named_moves_with_retained_finding(state)


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
    # #3511 — the page stays a page: at most MAX_MOVES move lines. Under the
    # cap every gesture shows, in document order (the #3431 render,
    # byte-identical). Over it the page is chosen — the slots, then the moves
    # the examination reached and a lens retained a finding on, then a spread
    # — and the count line says what is not shown, never a silent truncation.
    unexamined = _unexamined_move_indices(state)
    shown_idx = _shown_move_indices(moves, unexamined, _finding_move_indices(state))
    truncating = len(shown_idx) < len(moves)
    if truncating:
        order_line = (
            "  Ordre : thèse, mécanisme et piliers d'abord, puis les gestes "
            "que l'examen a atteints et dont une lentille a retenu un "
            "constat, puis un échantillon étalé sur le document — la "
            "position de chaque geste est dans sa ligne."
        )
    else:
        # #3431 ask 2 — the order is STATED, because the record beneath it
        # stores the thesis and mechanism slots first (#3420) while this note
        # lists the gestures as the document lays them out: a writer told
        # nothing was reading the first slot as the opening (measured, panel
        # cycle 2: a thesis at 94 % read as the speech's opening call).
        order_line = "  Ordre : celui du document, du premier geste au dernier."
    lines = [
        "LECTURE PREMIÈRE — un seul lecteur, sur le texte entier, avant les "
        "instruments. Ce sont des GESTES DU TEXTE, pas un verdict d'instrument : "
        "ne les présente jamais comme un sophisme ni comme une note.",
        f"  Portée : {extent}.",
        order_line,
    ]
    if truncating:
        lines.append(
            f"  {len(moves)} gestes nommés, {len(shown_idx)} montrés ici — "
            "échantillonné, pas exhaustif."
        )
    malformed = record.get("malformed_moves") or 0
    text_length = scope.get("text_length")
    for i in shown_idx:
        move = moves[i]
        offset = move.get("offset")
        # #3431 ask 1 — the position in the READER's terms (share of the text
        # and its part), never a raw character offset a writer cannot place
        # without the document in hand. The offset stays in the state.
        position = _reader_position_fr(offset, text_length)
        label = _move_label(move)
        anchor = str(move.get("anchor") or "")
        if anchor == ANCHOR_UNANCHORED:
            # #3415 ask 4 — the reading survived its failed citation, without
            # one. No guillemets: the model's words are not the document's.
            lines.append(
                f"  - {label} : {move.get('reading')} "
                "— citation non ancrée : le document ne porte pas ce passage."
            )
            continue
        marker = (
            " (réancrée sur un passage du document)"
            if anchor == ANCHOR_RELOCATED
            else ""
        )
        lines.append(
            f"  - {label} : {move.get('reading')} "
            f"— « {move.get('quote')} »{position}{marker}"
        )
    if dropped:
        lines.append(f"  {dropped} geste(s) écarté(s) : citation absente du document.")
    if malformed:
        # #3415 ask 2 — a malformed object costs its own move, never the
        # reading; what was lost is stated, not hidden.
        lines.append(f"  {malformed} objet(s) illisible(s) : geste(s) perdu(s).")
    second = record.get("second_pass")
    if isinstance(second, dict) and (second.get("calls") or second.get("failed_calls")):
        # #3511(b) — the pass that read the bare stretches states itself:
        # how many stretches were actually re-read after the whole-document
        # reading, and — the coordinator's ask — that a bound BIT, with what
        # it left unread or unnamed. R1167 finding 3: an attempt that raised
        # is not a re-read, so the failed calls say their own count instead
        # of hiding inside « relue(s) ». A pass that did not run at all says
        # nothing (the note stays byte-identical).
        capped = sum(
            1
            for s in second.get("stretches") or []
            if isinstance(s, dict) and not s.get("read")
        )
        line = (
            f"  Passe seconde : {second.get('calls')} tranche(s) relue(s) "
            "après la lecture d'ensemble"
        )
        failed = second.get("failed_calls") or 0
        if failed:
            line += f", {failed} appel(s) en échec"
        lost = second.get("inventory_capped") or 0
        if lost:
            line += (
                f", {lost} geste(s) écarté(s) au plafond d'inventaire "
                f"({second.get('inventory_bound')})"
            )
        if capped:
            line += (
                f", {capped} tranche(s) nue(s) au-delà de la borne d'appels "
                f"({second.get('call_bound')})"
            )
        lines.append(line + ".")
    for lost in record.get("dropped_slots") or []:
        # #3415 ask 4 — the slot is NAMED. « 1 geste écarté » could not tell
        # the central thesis from a local claim, which is how the probe read
        # a lost thesis as a count.
        if not isinstance(lost, dict):
            continue
        label = _slot_label(str(lost.get("slot") or ""))
        reason = _SLOT_DROP_LABELS_FR.get(str(lost.get("reason") or ""), "geste perdu")
        lines.append(f"  - {label} : aucun geste retenu ({reason}).")
    return "\n".join(lines)
