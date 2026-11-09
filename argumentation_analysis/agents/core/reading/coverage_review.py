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
Three causes, all of design, and this version answers each:

1. the pass reads the DOCUMENT WHOLE, with the first reading's own window
   (``FIRST_READING_WINDOW = 0`` — no cut, the same read the zero-shot arm
   gets, #2841 rule 4), and is given the coverage map PER CLASS so it can see
   what the lens of each question really read;
2. "examined" is decided PER CLASS, never as the union of every phase:
   ``COVERAGE_KEYS_BY_CLASS`` is the one table, and it says that today the
   modal lens records no coverage at all (so nothing counts as examined for a
   modal question), while the statistical and inferential questions are
   answered by ``fallacy_per_argument`` and by ``fol_reasoning``/``aspic``. A
   phase that is not the lens of the class does not examine that class's
   question — that IS #3492's measurement (a stakes record does not examine a
   statistical support);
3. quotes are verified against ``state.raw_text``, so the offset is a
   DOCUMENT position, and the passage is mapped to an extracted unit by span
   (the first reading's own rule for its moves) only when the route needs an
   id. On the recorded c4b states 336 of 1 406 unit texts occur verbatim in
   the document; the rest are the extractor's paraphrases, and a paraphrase
   verified against itself would reach the reader as the speaker's words.

Each named passage is routed to the lens whose question it raises:

* an epistemic or modal qualifier (belief versus knowledge) → ``modal``;
* a quantified or statistical support → ``fallacy_descent``;
* a support carrying an inference → ``fol``.

The lens RUN runs through an injected ``dispatcher``: this module owns the
naming, the verification and the routing decision; the invoke layer owns which
callable each lens name runs on. A lens the run has no callable for is
recorded as ``lens_not_wired`` — a named absence carried to the acts, never a
fabricated finding (#1019, #1941). What the review DID read reaches the acts:
the reviewer's own reading of the passage, attributed to the coverage review
(the pipeline's reader, not a lens verdict), and the fallacies the walk of the
class's lens retained, printed with the writer's generic label (#3493 — a leaf
named by a slogan reaches the reader as the procedure).

Anti-pendulum: no phase's unit budget moves, and the candidate cap is not
raised — it is gone, because the pass no longer samples. The cost is one call
on the document plus one bounded call per NAMED passage (at most three).
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
from argumentation_analysis.utils.taxonomy_loader import generic_fallacy_name

logger = logging.getLogger("CoverageReview")

#: Cap on the passages the review names. Three is the measured divergence
#: bound the #3326 winner reading already uses (1-3 cited items per run): a
#: wider divergence is a coverage anomaly to surface, not a reading mandate.
MAX_ITEMS = 3

COVERAGE_REVIEW_BASIS = "coverage_review"

#: The lens each class of passage points at — one table, read by the dispatcher.
LENS_BY_CLASS: Dict[str, str] = {
    "modal": "modal",
    "statistical": "fallacy_descent",
    "inferential": "fol",
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
}

ITEM_CLASSES: Tuple[str, ...] = tuple(LENS_BY_CLASS)

#: Drop reasons — a closed vocabulary, counted, never silently discarded.
DROP_QUOTE_NOT_IN_DOCUMENT = "quote_not_in_document"
DROP_UNKNOWN_CLASS = "unknown_class"
DROP_EXAMINED_BY_CLASS = "examined_by_class"
DROP_CAPPED = "capped"

COVERAGE_REVIEW_PROMPT = """Tu relis la couverture d'une analyse. Le document
ci-dessous a déjà été lu une première fois (thèse et mouvements nommés), puis
analysé en profondeur par plusieurs lentilles, chacune n'ayant examiné qu'une
partie du document. Ta seule question : quels passages DU DOCUMENT soutiennent
ou qualifient LA THÈSE et n'ont pas été examinés par la lentille de leur propre
question ?

Règles strictes :
- Ne nomme que des passages DU DOCUMENT ci-dessous.
- Recopie chaque passage MOT POUR MOT depuis le document : aucune
  reformulation, aucune jointure de deux passages.
- Classe chaque passage dans UNE de ces trois classes, selon la question qu'il
  pose : "modal" (une réserve épistémique : croyance plutôt que savoir, doute,
  modalité), "statistical" (un appui quantifié ou statistique, un taux, une
  part, une comparaison chiffrée), "inferential" (un appui qui porte une
  inférence : prémisse, conséquence, condition).
- Une phase qui n'est pas la lentille de ta classe n'examine PAS sa question :
  la carte de couverture dit ce que chaque lentille a réellement lu.
- Au plus {max_items} passages. Une liste vide est une réponse valide — et la
  bonne réponse quand aucun passage ne porte la thèse.
- Aucune sortie hors du JSON.

Réponds en français, avec UNIQUEMENT ce JSON, sans balises ni commentaire :
{{"items": [{{"quote": "citation exacte du document", "class": "modal",
            "reason": "ce que ce passage fait à la thèse, en une phrase"}}]}}

THÈSE DU DOCUMENT (citée par la première lecture) :
{thesis}

CARTE DE COUVERTURE — ce que la lentille de chaque question a réellement lu :
{coverage_map}

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
    routed: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "quote": self.quote,
            "offset": self.offset,
            "class": self.kind,
            "lens": self.lens,
            "reason": self.reason,
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
        rows.append({"unit_id": unit_id, "text": text, "offset": offset})
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
    """
    for row in rows:
        offset = row["offset"]
        if not isinstance(offset, int):
            continue
        if offset <= position < offset + len(row["text"]):
            return str(row["unit_id"])
    return ""


def _coverage_map(state: Any, rows: List[Dict[str, Any]]) -> str:
    """What the lens of each question really read — ids, with their offsets."""
    by_id = {row["unit_id"]: row for row in rows}
    lines: List[str] = []
    for kind in ITEM_CLASSES:
        keys = COVERAGE_KEYS_BY_CLASS.get(kind, ())
        if not keys:
            lines.append(
                f"- question « {kind} » : aucune couverture enregistrée pour "
                "cette lentille — rien n'a été examiné."
            )
            continue
        examined = examined_unit_ids_for_class(state, kind)
        if not examined:
            lines.append(
                f"- question « {kind} » : la lentille n'a rien enregistré — "
                "rien n'a été examiné."
            )
            continue
        placed: List[str] = []
        for unit_id in sorted(examined):
            row = by_id.get(unit_id)
            offset = row["offset"] if row else None
            placed.append(
                f"{unit_id} (position {offset})"
                if isinstance(offset, int)
                else f"{unit_id} (position inconnue)"
            )
        lines.append(
            f"- question « {kind} » : {len(examined)} passages examinés — "
            + ", ".join(placed)
        )
    return "\n".join(lines)


def _thesis_quote(state: Any) -> str:
    """The thesis the first reading named, verbatim, or an empty string."""
    for move in defining_moves(state):
        if str(move.get("slot") or "") != "thesis":
            continue
        quote = str(move.get("quote") or "").strip()
        if quote:
            return quote
    return ""


def build_coverage_review_prompt(thesis: str, document: str, coverage_map: str) -> str:
    """The reviewer's one prompt: the thesis, the map, the WHOLE document."""
    return COVERAGE_REVIEW_PROMPT.format(
        max_items=MAX_ITEMS,
        thesis=f"« {thesis} »",
        coverage_map=coverage_map,
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
    prompt = build_coverage_review_prompt(thesis, document, _coverage_map(state, rows))

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

    for raw in raw_items:
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


def coverage_review_note(state: Any) -> str:
    """The block Act II reads — empty when no passage was named.

    Empty on any status that never reached the model, and on an ``ok`` review
    that named nothing: the prompt then omits the section rather than
    advertising a review that did not run — the #3395 rule, and the
    byte-identity control the issue asks for.

    What the review DID read reaches the act: each passage, the reviewer's own
    reading of it ATTRIBUTED to the coverage review (the pipeline's reader,
    never a lens verdict), and the fallacies the class's walk retained, under
    the writer's generic label. An unwired lens keeps its line: named, not
    examined.
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
        "[APPUIS DE LA THÈSE QU'AUCUNE LENTILLE N'AVAIT EXAMINÉS — revue de "
        "couverture, un passage du document lu en entier, après les phases "
        "profondes]"
    ]
    for item in items:
        quote = str(item.get("quote") or "")
        offset = item.get("offset")
        if not quote or not isinstance(offset, int):
            continue
        lines.append(f"  — « {quote} » (position {offset})")
        reason = str(item.get("reason") or "").strip()
        if reason:
            lines.append(
                "    La revue de couverture — le lecteur du pipeline, pas une "
                f"lentille — lit ce passage comme : {reason}"
            )
        routed_any = item.get("routed")
        routed = routed_any if isinstance(routed_any, dict) else {}
        status = str(routed.get("status") or "")
        lens = str(item.get("lens") or "")
        labels = [
            label for label in map(_fallacy_label, _retained_fallacies(routed)) if label
        ]
        if labels:
            lines.append("    Sophismes retenus sur ce passage : " + " ; ".join(labels))
        if status == "lens_not_wired":
            lines.append(
                f"    Aucune lentille câblée pour ce passage ({lens}) : il est "
                "nommé, non examiné — ne lui prête pas de verdict."
            )
        elif status in ("lens_error", "lens_no_finding"):
            lines.append(
                f"    Lentille {lens} non concluante ({status}) : le passage "
                "reste non examiné."
            )
        elif labels:
            lines.append(f"    Lentille {lens} : {len(labels)} sophisme(s) retenu(s).")
        else:
            lines.append(
                f"    Lentille {lens} : lue, aucun sophisme retenu sur ce passage."
            )
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
    "coverage_review_note",
    "examined_unit_ids",
    "examined_unit_ids_for_class",
    "extract_coverage_review",
    "unit_id_at_offset",
]
