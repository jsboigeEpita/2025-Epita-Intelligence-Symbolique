"""#3492 — the coverage reviewer: a whole-document pass, per question.

Cycle 4b of the panel (#3374) measured three severe M1 items ON the central
thesis, one per long document: a passage the same-model zero-shot examines and
no lens of the pipeline does. Extraction is not the gap — each anchor is an
extracted unit, present in the belief sets, ``text_to_kb``, the Dung framework
and the ASPIC rules, including the 179 k document at relative position 0.76.
The gap is DIRECTION: the deep phases take 8 to 31 units out of 165-739,
banded, and a support the first reading did not name competes on band position
alone. When the first reading DOES name a passage, the lenses follow — 46 of
49 bound moves reach a deep phase on the measured states.

v1 of this module (PR #3495) sampled 24 candidates out of up to 673 and asked
the model to pick among them. The coordinator's free replay of its own
selection on the recorded c4b states measured why that could not work: **0 of
the 3 anchors** reached the reviewer's prompt. ``arg_123`` had gone through 8
phases and none had asked its question; ``arg_156`` was excluded by a single
stakes record; ``arg_664`` was one of 673 candidates of which 24 were shown.
v2 read the DOCUMENT WHOLE and was given the coverage map PER CLASS — gate (a)
passed, gate (b) still named **0 of 3** anchors, and the coordinator's two
later variants measured why:

1. the coverage map made every belief verb eligible ("modal: nothing was
   examined"), and a reviewer asked for the thesis's SUPPORTS does not look
   for what the zero-shot finds: each anchor is an ARGUMENT WITH ITS OWN
   CONCLUSION, named in the zero-shot's argument-by-argument map, not a
   support of the single thesis;
2. on long documents the per-class filter cuts almost nothing (1 of 44): the
   deep lenses read 10 to 31 units of 165-739, so "unexamined" is nearly
   every passage. The binding constraint is how many passages the pass ROUTES
   and RENDERS, not which ones qualify;
3. the three-anchor measure ranks them 11, 3 and 8 of 15 — a cap of three
   cannot carry two of them.

This version therefore ENUMERATES, and filters in code:

* the reviewer is asked the zero-shot's own question — the arguments a
  complete analysis would examine one by one, ranked by how decisive they
  are for a careful reader, each with a verbatim quote, what it concludes on
  its own, and a class. The coverage map is gone from the prompt: the pass
  reads the DOCUMENT WHOLE (``FIRST_READING_WINDOW = 0``, #2841 rule 4) and
  does not need to be told what a lens read, because the decision is
  deterministic code;
* "examined" is decided PER CLASS, never as the union of every phase:
  ``COVERAGE_KEYS_BY_CLASS`` is the one table, and it says that today the
  modal lens records no coverage at all (so nothing counts as examined for a
  modal question), while the statistical, persuasion and inferential
  questions are answered by ``fallacy_per_argument`` and by
  ``fol_reasoning``/``aspic``. A phase that is not the lens of the class
  does not examine that class's question — that IS #3492's measurement (a
  stakes record does not examine a statistical support);
* quotes are verified against ``state.raw_text``, so the offset is a
  DOCUMENT position, and the passage is mapped to an extracted unit by span
  (the first reading's own rule for its moves) only when the route needs an
  id. On the recorded c4b states 336 of 1 406 unit texts occur verbatim in
  the document; the rest are the extractor's paraphrases, and a paraphrase
  verified against itself would reach the reader as the speaker's words.

Each named passage is routed to the lens whose question it raises:

* an epistemic or modal qualifier (belief versus knowledge) → ``modal``;
* a quantified or statistical support → ``fallacy_descent``;
* a support carrying an inference → ``fol``;
* a persuasion or manipulation move → ``fallacy_descent`` (the only
  passage-level lens wired today; v2's three-class table had no home for the
  ``e67ad261`` anchor — the coordinator's own defect, measured).

The lens RUN runs through an injected ``dispatcher``: this module owns the
naming, the verification and the routing decision; the invoke layer owns which
callable each lens name runs on. A lens the run has no callable for is
recorded as ``lens_not_wired`` — a named absence carried to the acts, never a
fabricated finding (#1019, #1941). What the review DID read reaches the acts:
the reviewer's own reading of the passage, attributed to the coverage review
(the pipeline's reader, not a lens verdict), and the fallacies the walk of the
class's lens retained, printed with the writer's generic label (#3493 — a leaf
named by a slogan reaches the reader as the procedure).

Anti-pendulum: no phase's unit budget moves. The cost is one call on the
document plus one bounded call per NAMED passage; the enumeration is capped at
``MAX_ITEMS``, and the Act II note renders ONE line per item so the prompt
grows by the items named, not by a template per item.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple

from argumentation_analysis.agents.core.reading.first_reading import (
    anchor_quote_in,
    defining_moves,
)
from argumentation_analysis.core.shared_state import unit_extent
from argumentation_analysis.utils.taxonomy_loader import generic_fallacy_name

logger = logging.getLogger("CoverageReview")

#: The enumeration width. R1155 measured the three anchors at ranks 11, 3 and
#: 8 of 15 in the zero-shot's own argument map, so a cap of three kept only one
#: of them: the budget is decided from that measure, not from the #3326
#: divergence bound v2 used. 15 is the rank ceiling of the measured map, and
#: the note renders one line per item.
MAX_ITEMS = 15

COVERAGE_REVIEW_BASIS = "coverage_review"

#: The lens each class of passage points at — one table, read by the dispatcher.
LENS_BY_CLASS: Dict[str, str] = {
    "modal": "modal",
    "statistical": "fallacy_descent",
    "inferential": "fol",
    # R1155 — the fourth class the coordinator's three-class table lacked: a
    # persuasion or manipulation move drives the decisive event on one measured
    # anchor and fits none of the other three. ``fallacy_descent`` is the only
    # passage-level lens wired today.
    "persuasion": "fallacy_descent",
}

#: #3492 reprise — the coverage record keys that answer each class's question.
#: One table next to ``LENS_BY_CLASS``, and per class, never the union of every
#: phase: a stakes or quality record does not examine a statistical support.
#: ``modal`` is empty ON PURPOSE — measured: the run records no modal coverage
#: key at all, so no passage can count as examined for a modal question. Naming
#: an absence here is the honest form; the day a modal phase records its
#: selection, this tuple gains the key and the filter applies by itself.
COVERAGE_KEYS_BY_CLASS: Dict[str, Tuple[str, ...]] = {
    "modal": (),
    "statistical": ("fallacy_per_argument",),
    "inferential": ("fol_reasoning", "aspic"),
    # Same lens as ``statistical``: the descent is what reads a passage for
    # manipulative moves today, so its record is the one that says whether the
    # passage was examined.
    "persuasion": ("fallacy_per_argument",),
}

ITEM_CLASSES: Tuple[str, ...] = tuple(LENS_BY_CLASS)

#: Drop reasons — a closed vocabulary, counted, never silently discarded.
DROP_QUOTE_NOT_IN_DOCUMENT = "quote_not_in_document"
DROP_UNKNOWN_CLASS = "unknown_class"
DROP_EXAMINED_BY_CLASS = "examined_by_class"
DROP_CAPPED = "capped"

COVERAGE_REVIEW_PROMPT = """Tu lis ce document pour une analyse complète. Ne
cherche pas seulement les appuis de la thèse : liste les ARGUMENTS qu'une
analyse complète examinerait un par un, chacun avec sa propre conclusion.

Règles strictes :
- Chaque argument est une position autonome : dis ce qu'il conclut PAR
  LUI-MÊME, et pas seulement ce qu'il apporte à la thèse.
- Recopie la citation MOT POUR MOT depuis le document : aucune
  reformulation, aucune jointure de deux passages.
- Ordonne du plus décisif au moins décisif : d'abord ce qu'un lecteur attentif
  perdrait le plus à voir manquer.
- Classe chaque argument dans UNE de ces quatre classes, selon la question
  qu'il pose : "modal" (une réserve épistémique : croyance plutôt que savoir,
  doute, modalité), "statistical" (un appui quantifié ou statistique, un
  taux, une part, une comparaison chiffrée), "inferential" (un appui qui
  porte une inférence : prémisse, conséquence, condition), "persuasion" (un
  mouvement de persuasion ou de manipulation : appel à l'émotion ou à
  l'autorité, cadrage, homme de paille).
- Au plus {max_items} arguments, tous du document. Une liste vide est une
  réponse valide — et la bonne réponse quand le document n'argumente pas.
- Aucune sortie hors du JSON.

Réponds en français, avec UNIQUEMENT ce JSON, sans balises ni commentaire :
{{"items": [{{"quote": "citation exacte du document",
            "conclusion": "ce que cet argument conclut par lui-même",
            "class": "modal",
            "reason": "pourquoi le manquer coûte au lecteur, en une phrase"}}]}}

THÈSE QUE LA PREMIÈRE LECTURE A CITÉE (un repère, pas un filtre) :
{thesis}

DOCUMENT (en entier) :
{document}
"""


@dataclass
class CoverageItem:
    """One passage the review named, with its verified place and its lens."""

    quote: str
    offset: int
    kind: str
    lens: str
    #: The extracted unit whose span carries the passage, when one does: the
    #: route needs an id, the reader only needs the document position.
    unit_id: str = ""
    reason: str = ""
    #: R1155 — what the argument concludes ON ITS OWN (the enumeration's own
    #: field: an argument is not only a support of the thesis), and the rank
    #: the reviewer gave it (1 = most decisive). Recorded, never re-sorted:
    #: the model's order IS the measure the budget was set from.
    conclusion: str = ""
    rank: int = 0
    routed: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "quote": self.quote,
            "offset": self.offset,
            "class": self.kind,
            "lens": self.lens,
            "reason": self.reason,
            "conclusion": self.conclusion,
            "rank": self.rank,
            "routed": dict(self.routed),
        }


@dataclass
class CoverageReview:
    """The reviewer's record — an honest absence when the pass could not run.

    ``status`` is discriminated on purpose (#3096's lesson): a pass that never
    reached the model must not read as "completed, nothing unexamined". An
    ``ok`` status with no item IS the byte-identity control: the reviewer read
    the document and named nothing, and the acts' prompt is unchanged.
    """

    status: str = "no_llm"
    items: List[CoverageItem] = field(default_factory=list)
    examined: int = 0
    examined_by_class: Dict[str, int] = field(default_factory=dict)
    document_chars: int = 0
    dropped: Dict[str, int] = field(default_factory=dict)
    reason: str = ""
    basis: str = COVERAGE_REVIEW_BASIS

    def to_state(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
            "examined": self.examined,
            "examined_by_class": dict(self.examined_by_class),
            "document_chars": self.document_chars,
            "dropped": dict(self.dropped),
            "reason": self.reason,
            "basis": self.basis,
        }


def _as_state_dict(state: Any, key: str) -> Any:
    if isinstance(state, dict):
        return state.get(key)
    return getattr(state, key, None)


def _raw_text(state: Any) -> str:
    text = _as_state_dict(state, "raw_text")
    return text if isinstance(text, str) else ""


def _coverage_entries(state: Any) -> Dict[str, Any]:
    coverage = _as_state_dict(state, "analysis_coverage")
    return coverage if isinstance(coverage, dict) else {}


def examined_unit_ids(state: Any) -> Tuple[Set[str], int]:
    """Every unit the record says a phase really submitted, as one set.

    Informational only — the FILTER below is per class. Kept because the
    record states what the analysis examined, whatever the question, and
    ``anchor_census`` carries no ``unit_ids`` (it counts provenance).
    """
    examined: Set[str] = set()
    for entry in _coverage_entries(state).values():
        if not isinstance(entry, dict):
            continue
        unit_ids = entry.get("unit_ids")
        if not isinstance(unit_ids, (list, tuple)):
            continue
        for unit_id in unit_ids:
            if isinstance(unit_id, str) and unit_id:
                examined.add(unit_id)
    return examined, len(examined)


def examined_unit_ids_for_class(state: Any, kind: str) -> Set[str]:
    """The units the lens of ONE class really read, from its own keys only.

    ``COVERAGE_KEYS_BY_CLASS`` is the whole decision: a class with no key
    (``modal`` today) has examined nothing, whatever the other phases did, and
    a key that is not the class's lens does not count. This is the filter the
    coordinator's replay asked for — the union filter dropped 2 of the 3
    anchors before the model saw anything.
    """
    keys = COVERAGE_KEYS_BY_CLASS.get(kind, ())
    if not keys:
        return set()
    entries = _coverage_entries(state)
    examined: Set[str] = set()
    for key in keys:
        entry = entries.get(key)
        if not isinstance(entry, dict):
            continue
        unit_ids = entry.get("unit_ids")
        if not isinstance(unit_ids, (list, tuple)):
            continue
        for unit_id in unit_ids:
            if isinstance(unit_id, str) and unit_id:
                examined.add(unit_id)
    return examined


def _unit_rows(state: Any) -> List[Dict[str, Any]]:
    """Every extracted unit, in document order, with its offset when known."""
    arguments = _as_state_dict(state, "identified_arguments")
    provenance = _as_state_dict(state, "argument_provenance")
    if not isinstance(arguments, dict):
        return []
    if not isinstance(provenance, dict):
        provenance = {}
    rows: List[Dict[str, Any]] = []
    for unit_id, text in arguments.items():
        if not isinstance(unit_id, str) or not isinstance(text, str):
            continue
        if not text.strip():
            continue
        entry = provenance.get(unit_id)
        offset = entry.get("offset") if isinstance(entry, dict) else None
        if isinstance(offset, bool) or not isinstance(offset, int):
            offset = None
        source_quote = entry.get("source_quote") if isinstance(entry, dict) else None
        if not isinstance(source_quote, str) or not source_quote:
            source_quote = None
        # #3502 — the extent key travels with the row: the offset writer
        # located the SOURCE QUOTE (locate_unit_span), so the span that
        # carries a position is the quote's, never the paraphrase's.
        rows.append(
            {
                "unit_id": unit_id,
                "text": text,
                "offset": offset,
                "source_quote": source_quote,
            }
        )
    rows.sort(key=lambda row: (row["offset"] is None, row["offset"] or 0))
    return rows


def unit_id_at_offset(rows: List[Dict[str, Any]], position: int) -> str:
    """The unit whose span carries a document position — the reading's rule.

    ``first_reading`` maps a move to a unit by span overlap (``offset <
    move_end and move_offset < unit_end``). The same rule here: a passage
    inside a unit's span is that unit's, and a passage no span carries maps to
    NO unit (``""``). The reader is still sent to the right place by the
    document offset, and the caller never borrows a neighbour's id — a wrong
    anchor is worse than none (#1019).

    #3502 — the span is the ONE extent rule, ``unit_extent``: the source
    quote's length when the provenance located one, the text's otherwise
    (``kb_heuristic`` units, whose text is the document chunk). The
    paraphrase runs longer than the passage (median ×2.62 on the panel),
    so measuring by the text handed positions to the wrong unit.

    R1157 — when several spans carry the same position, the MOST SPECIFIC
    covering unit wins: shortest extent first, then earliest offset. The
    rows arrive sorted by offset, and first-covering handed a ``kb_heuristic``
    chunk (text-as-chunk, whole pages long) the positions of every quoted
    unit nested inside it — 327 of 392 quoted units' last quote char mapped
    to a chunk on the coordinator's replay, and 5 of 56 items survived the
    per-lens drop as "no lens read this" while the class's lens HAD examined
    the specific unit. A chunk still owns the positions no extracted unit
    carries: its row stays, it only loses the nesting ties.
    """
    best_id = ""
    best_extent: Optional[Tuple[int, int]] = None
    for row in rows:
        extent = unit_extent(row, str(row.get("text") or ""))
        if extent is None:
            continue
        if not (extent[0] <= position < extent[1]):
            continue
        if best_extent is None or (
            extent[1] - extent[0],
            extent[0],
        ) < (best_extent[1] - best_extent[0], best_extent[0]):
            best_extent = extent
            best_id = str(row["unit_id"])
    return best_id


def _thesis_quote(state: Any) -> str:
    """The thesis the first reading named, verbatim, or an empty string."""
    for move in defining_moves(state):
        if str(move.get("slot") or "") != "thesis":
            continue
        quote = str(move.get("quote") or "").strip()
        if quote:
            return quote
    return ""


def build_coverage_review_prompt(thesis: str, document: str) -> str:
    """The reviewer's one prompt: the thesis as a marker, the WHOLE document.

    R1155 — no coverage map: the enumeration asks the zero-shot's own
    question, and the "was it examined by its class" decision is code. The
    thesis stays as a marker of the document's reading, never as the filter
    (the filter was what made a reviewer look for supports instead of
    arguments).
    """
    return COVERAGE_REVIEW_PROMPT.format(
        max_items=MAX_ITEMS,
        thesis=f"« {thesis} »",
        document=document,
    )


def _parse_json_object(content: str) -> Optional[Dict[str, Any]]:
    """The model's JSON, fences tolerated, ``None`` when unreadable."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _quote_in_document(document: str, quote: str) -> Optional[Tuple[str, int]]:
    """The document's own characters for the passage, with their offset.

    Exact match first; failing that, the #3415 locator, which returns a
    substring of the DOCUMENT — never the model's paraphrase. ``None`` when
    the two share no run long enough to be the same passage: a passage the
    document does not carry is dropped and counted, never rendered.
    """
    if not quote:
        return None
    position = document.find(quote)
    if position >= 0:
        return quote, position
    return anchor_quote_in(document, quote)


async def _route(
    item: CoverageItem,
    dispatcher: Optional[Callable[[CoverageItem], Awaitable[Dict[str, Any]]]],
) -> Dict[str, Any]:
    """Run the lens the class points at; an unwired lens is a NAMED absence."""
    if dispatcher is None:
        return {
            "lens": item.lens,
            "status": "lens_not_wired",
            "reason": "no dispatcher in this run",
        }
    try:
        finding = await dispatcher(item)
    except Exception as e:  # pragma: no cover - provider/plugin failures
        logger.warning("CoverageReview: lens %s failed: %s", item.lens, e)
        return {
            "lens": item.lens,
            "status": "lens_error",
            "reason": f"{type(e).__name__}: {e}",
        }
    if not isinstance(finding, dict) or not finding:
        return {
            "lens": item.lens,
            "status": "lens_no_finding",
            "reason": "the lens returned nothing",
        }
    return {
        "lens": item.lens,
        "status": str(finding.get("status") or "answered"),
        "finding": finding,
    }


async def build_coverage_review(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
    dispatcher: Optional[Callable[[CoverageItem], Awaitable[Dict[str, Any]]]] = None,
) -> CoverageReview:
    """Name the thesis supports no lens of their question examined, then route.

    ``llm_callable`` and ``dispatcher`` are injected: the invoke layer owns
    the client, the runaway guard and the provider route; this module owns the
    question, the verification and the routing decision. No LLM → status
    ``no_llm``; no document → ``no_document`` (a quote cannot be placed in a
    text the run does not hold); no thesis → ``no_reading``. Never a
    fabricated review.
    """
    review = CoverageReview()
    document = _raw_text(state)
    review.document_chars = len(document)
    _, examined_total = examined_unit_ids(state)
    review.examined = examined_total
    review.examined_by_class = {
        kind: len(examined_unit_ids_for_class(state, kind)) for kind in ITEM_CLASSES
    }

    thesis = _thesis_quote(state)
    if not thesis:
        review.status = "no_reading"
        review.reason = "no thesis move recorded"
        return review
    if not document.strip():
        review.status = "no_document"
        review.reason = "raw_text absent — a quote cannot be placed in the document"
        return review
    if llm_callable is None:
        review.status = "no_llm"
        return review

    rows = _unit_rows(state)
    prompt = build_coverage_review_prompt(thesis, document)

    try:
        content = (await llm_callable(prompt) or "").strip()
    except Exception as e:  # pragma: no cover - provider failures
        review.status = "llm_error"
        review.reason = f"{type(e).__name__}: {e}"
        logger.warning("CoverageReview LLM error: %s", e)
        return review
    if not content:
        review.status = "llm_error"
        review.reason = "empty completion"
        return review

    parsed = _parse_json_object(content)
    if parsed is None:
        review.status = "parse_error"
        review.reason = "unreadable JSON"
        return review
    raw_items = parsed.get("items")
    if not isinstance(raw_items, list):
        review.status = "parse_error"
        review.reason = "no items list"
        return review

    dropped: Dict[str, int] = {}

    def _drop(reason: str) -> None:
        dropped[reason] = dropped.get(reason, 0) + 1

    for rank, raw in enumerate(raw_items, start=1):
        if len(review.items) >= MAX_ITEMS:
            _drop(DROP_CAPPED)
            continue
        if not isinstance(raw, dict):
            _drop(DROP_QUOTE_NOT_IN_DOCUMENT)
            continue
        verified = _quote_in_document(document, str(raw.get("quote") or "").strip())
        if verified is None:
            # The document does not carry this passage: what the model wrote
            # was its own words, and printing them as the speaker's is the
            # defect #3492 exists to close.
            _drop(DROP_QUOTE_NOT_IN_DOCUMENT)
            continue
        quote, position = verified
        kind = str(raw.get("class") or "").strip().lower()
        if kind not in LENS_BY_CLASS:
            _drop(DROP_UNKNOWN_CLASS)
            continue
        unit_id = unit_id_at_offset(rows, position)
        if unit_id and unit_id in examined_unit_ids_for_class(state, kind):
            # The per-lens filter stays: the reviewer must not re-name what
            # the lens of ITS class did examine.
            _drop(DROP_EXAMINED_BY_CLASS)
            continue
        review.items.append(
            CoverageItem(
                quote=quote,
                offset=position,
                kind=kind,
                lens=LENS_BY_CLASS[kind],
                unit_id=unit_id,
                reason=str(raw.get("reason") or "").strip(),
                conclusion=str(raw.get("conclusion") or "").strip(),
                # R1155 — the model's OWN order, not the post-filter order:
                # the rank is the measure the budget was set from, and it must
                # survive a drop later in the list.
                rank=rank,
            )
        )

    review.dropped = dropped
    for item in review.items:
        item.routed = await _route(item, dispatcher)
    review.status = "ok"
    logger.info(
        "CoverageReview: %d named in a %d-char document (examined=%d, by class=%s)",
        len(review.items),
        review.document_chars,
        review.examined,
        review.examined_by_class,
    )
    return review


async def extract_coverage_review(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_coverage_review(**kwargs)).to_state()


def _fallacy_label(fallacy: Any) -> str:
    """One retained fallacy, with the WRITER's label (#3493)."""
    data = fallacy if isinstance(fallacy, dict) else {}
    recorded = str(
        data.get("fallacy") or data.get("type") or data.get("fallacy_type") or ""
    ).strip()
    if not recorded:
        return ""
    name = generic_fallacy_name(recorded, data.get("taxonomy_path"))
    family = str(data.get("family") or "").strip()
    return f"« {name} » (famille {family})" if family else f"« {name} »"


def _retained_fallacies(routed: Dict[str, Any]) -> List[Any]:
    finding = routed.get("finding")
    if not isinstance(finding, dict):
        return []
    fallacies = finding.get("fallacies")
    return list(fallacies) if isinstance(fallacies, list) else []


def _logic_verdict_clause(lens: str, finding: Dict[str, Any]) -> str:
    """What a modal or FOL lens answered, said for what it IS (#3496, #3500).

    The verdict is a consistency one: the passage, translated, contradicts the
    run's own KB of that logic or does not. It is NOT an entailment verdict —
    no conclusion formula is translated — and the wording never borrows the
    word of one. #3500: the clause carries the MEASURED shared-symbol count,
    the vocabulary over which the verdict is readable at all.
    """
    formula = str(finding.get("formula") or "")
    verdict = str(finding.get("verdict") or "")
    shared = finding.get("shared_symbols")
    shared_txt = ""
    if isinstance(shared, int) and not isinstance(shared, bool) and shared > 0:
        shared_txt = (
            f" — {shared} symbole(s) partagé(s) avec la base du run, la "
            "mesure du vocabulaire commun"
        )
    if verdict == "contradicts_run_kb":
        return (
            f"lentille {lens} : le passage se traduit en « {formula} » et "
            "CONTREDIT la base formelle du run — il n'y répète pas une thèse, "
            f"il la met en cause{shared_txt}"
        )
    if verdict == "consistent_with_run_kb":
        return (
            f"lentille {lens} : le passage se traduit en « {formula} » et ne "
            "contredit pas la base formelle du run (cohérence, pas implication : "
            f"aucune conclusion n'a été dérivée){shared_txt}"
        )
    # R1158 — an undecided verdict comes from a SOLVER that ran; its raw
    # message never reaches Act II (a Java exception is the finding's trace,
    # not the reader's prose).
    return (
        f"lentille {lens} : passage traduit en « {formula} », verdict indécis"
        f"{shared_txt} — le passage reste non conclu"
    )


def coverage_item_line(item: Dict[str, Any], bullet: str = "— ") -> str:
    """One named passage said in full — the SAME line for both its homes.

    #3505 — the review's finding has two possible homes, and one producer:
    the review's block (a passage no movement carries) and the movement its
    unit belongs to (the act binds it there). The line carries everything the
    reader needs — the passage, its document position and the rank the
    reviewer gave it, what the argument concludes on its own, the reviewer's
    reading ATTRIBUTED to the coverage review (the pipeline's reader, never a
    lens verdict), and what the routed lens answered (R1155: ONE line per
    item, the prompt grows by the items named). An unwired lens keeps its
    clause: named, not examined.

    ``bullet`` prefixes the passage (« — » in the block, empty on a movement
    line, whose channel label already opens the sentence). ``""`` when the
    item carries no placeable passage — the caller skips it, never invents one.
    """
    quote = str(item.get("quote") or "")
    offset = item.get("offset")
    if not quote or not isinstance(offset, int) or isinstance(offset, bool):
        return ""
    kind = str(item.get("class") or "")
    lens = str(item.get("lens") or "")
    place = f"position {offset}"
    rank = item.get("rank")
    if isinstance(rank, int) and not isinstance(rank, bool) and rank > 0:
        place += f", rang {rank}"
    head = f"{bullet}« {quote} » ({place}, classe {kind} → lentille {lens})"
    conclusion = str(item.get("conclusion") or "").strip()
    if conclusion:
        head += f" — conclut : {conclusion}"

    routed_any = item.get("routed")
    routed = routed_any if isinstance(routed_any, dict) else {}
    status = str(routed.get("status") or "")
    finding_any = routed.get("finding")
    finding = finding_any if isinstance(finding_any, dict) else {}
    labels = [
        label for label in map(_fallacy_label, _retained_fallacies(routed)) if label
    ]
    clauses: List[str] = []
    reason = str(item.get("reason") or "").strip()
    if reason:
        clauses.append(
            "la revue de couverture — le lecteur du pipeline, pas une "
            f"lentille — le retient parce que : {reason}"
        )
    if labels:
        clauses.append("sophismes retenus : " + " ; ".join(labels))
    if finding.get("verdict"):
        # #3496 — a logic lens answered a CONSISTENCY question; it must not
        # be rendered in the fallacy vocabulary, nor as a bare "read".
        clauses.append(_logic_verdict_clause(lens, finding))
    elif status == "lens_not_wired":
        clauses.append(
            f"aucune lentille câblée pour ce passage ({lens}) : il est "
            "nommé, non examiné — ne lui prête pas de verdict"
        )
    elif status in ("lens_error", "lens_no_finding"):
        if finding.get("untranslatable"):
            clauses.append(
                f"lentille {lens} : aucune traduction formelle valide du "
                f"passage ({finding.get('reason')}) — il reste non examiné"
            )
        elif finding.get("route_error"):
            # R1158 — the route REFUSED (parser rejection, reasoner
            # absent): no solver decided, so the note never says
            # « verdict indécis », and the raw exception stays in the
            # finding, out of the reader's prose.
            clauses.append(
                f"lentille {lens} : la route de cohérence a refusé de "
                "répondre (rejet du parseur ou raisonneur indisponible) — "
                "aucun solveur n'a tranché ; le passage reste non examiné"
            )
        elif finding.get("no_shared_symbols"):
            # #3500 — the consistency question is only readable over a
            # shared vocabulary: without one, « consistent » holds by
            # construction, and that vacuous truth must not reach the
            # reader as a verdict.
            clauses.append(
                f"lentille {lens} : le passage se traduit (« "
                f"{finding.get('formula')} ») mais ne partage aucun symbole "
                "avec la base formelle du run — aucun verdict de cohérence "
                "ne peut être lu (« cohérent » ne vaudrait alors rien) ; "
                "le passage reste non examiné"
            )
        elif finding.get("kb_alone") == "inconsistent":
            # R1157 — the KB-alone control: a base already inconsistent
            # on its own makes every passage "contradict" by construction.
            # The reader is told WHY nothing is readable, never given the
            # by-construction "contradiction".
            clauses.append(
                f"lentille {lens} : la base formelle du run est déjà "
                "incohérente à elle seule — un passage ne peut pas la "
                "contredire de façon lisible ; le passage reste non examiné"
            )
        elif finding.get("kb_alone") == "undecided":
            clauses.append(
                f"lentille {lens} : la base formelle du run est indécise "
                "à elle seule — aucun verdict de cohérence ne peut être "
                "lu ; le passage reste non examiné"
            )
        else:
            clauses.append(
                f"lentille {lens} non concluante ({status}) : le passage reste "
                "non examiné"
            )
    elif labels:
        clauses.append(f"lentille {lens} : {len(labels)} sophisme(s) retenu(s)")
    else:
        clauses.append(f"lentille {lens} : lue, aucun sophisme retenu sur ce passage")
    return head + " ; " + " ; ".join(clauses) + "."


def coverage_items_by_unit(state: Any) -> Dict[str, List[Dict[str, Any]]]:
    """The review's named passages grouped by the unit their span mapped to.

    #3505 — the binding is the ONE rule: an item's ``unit_id`` was decided at
    review time (span overlap, ``unit_id_at_offset``); this table hands the
    act the mapping without re-deriving it. Items with no unit (``""``) are
    absent — they stay in the block, the closing beat's material. Empty when
    the record never ran or named nothing.
    """
    record = _as_state_dict(state, "coverage_review")
    if not isinstance(record, dict):
        return {}
    if str(record.get("status") or "") != "ok":
        return {}
    by_unit: Dict[str, List[Dict[str, Any]]] = {}
    for item in record.get("items") or []:
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("unit_id") or "")
        if not unit_id:
            continue
        by_unit.setdefault(unit_id, []).append(item)
    return by_unit


def coverage_review_note(
    state: Any, exclude_unit_ids: Optional[Set[str]] = None
) -> str:
    """The block Act II reads — empty when no passage was named.

    Empty on any status that never reached the model, and on an ``ok`` review
    that named nothing: the prompt then omits the section rather than
    advertising a review that did not run — the #3395 rule, and the
    byte-identity control the issue asks for.

    What the review DID read reaches the act, ONE line per item (R1155 — the
    prompt grows by the items named, not by a template per item): the passage,
    its document position and the rank the reviewer gave it, what the argument
    concludes on its own, the reviewer's reading of it ATTRIBUTED to the
    coverage review (the pipeline's reader, never a lens verdict), and the
    fallacies the class's walk retained under the writer's generic label. An
    unwired lens keeps its clause: named, not examined.

    #3505 — ``exclude_unit_ids``: the items whose finding the act binds to
    their unit's movement are NOT repeated here (one home per finding, or the
    reader meets it twice); the block keeps the passages no movement carries.
    All items excluded → the section is omitted whole, like an empty review.
    """
    record = _as_state_dict(state, "coverage_review")
    if not isinstance(record, dict):
        return ""
    if str(record.get("status") or "") != "ok":
        return ""
    items = [item for item in (record.get("items") or []) if isinstance(item, dict)]
    if not items:
        return ""

    lines: List[str] = [
        "[ARGUMENTS QU'AUCUNE LENTILLE DE LEUR QUESTION N'AVAIT EXAMINÉS — "
        "revue de couverture, lecture du document entier, après les phases "
        "profondes]"
    ]
    for item in items:
        line = coverage_item_line(item)
        if not line:
            continue
        unit_id = str(item.get("unit_id") or "")
        if exclude_unit_ids is not None and unit_id in exclude_unit_ids:
            continue
        lines.append(f"  {line}")
    if len(lines) == 1:
        # Every named passage found its movement: no orphan left to carry.
        return ""
    return "\n".join(lines)


__all__ = [
    "COVERAGE_KEYS_BY_CLASS",
    "COVERAGE_REVIEW_BASIS",
    "COVERAGE_REVIEW_PROMPT",
    "CoverageItem",
    "CoverageReview",
    "ITEM_CLASSES",
    "LENS_BY_CLASS",
    "MAX_ITEMS",
    "build_coverage_review",
    "build_coverage_review_prompt",
    "coverage_item_line",
    "coverage_items_by_unit",
    "coverage_review_note",
    "examined_unit_ids",
    "examined_unit_ids_for_class",
    "extract_coverage_review",
    "unit_id_at_offset",
]
