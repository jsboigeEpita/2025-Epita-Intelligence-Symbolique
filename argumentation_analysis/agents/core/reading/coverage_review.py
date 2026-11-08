"""#3492 — the coverage reviewer: what no lens read, pointed at the right one.

Cycle 4b of the panel (#3374) measured three severe M1 items ON the central
thesis, one per long document: a passage the same-model zero-shot examines and
no lens of the pipeline does. Extraction is not the gap — each anchor is an
extracted unit, present in the belief sets, ``text_to_kb``, the Dung framework
and the ASPIC rules, including the 179 k document at relative position 0.76.
The gap is DIRECTION: the deep phases take 8 to 31 units out of 165-739,
banded, and a support the first reading did not name competes on band position
alone. When the first reading DOES name a passage, the lenses follow — 46 of
49 bound moves reach a deep phase on the measured states.

This module applies #3395 a second time, as reviewer of coverage. After the
deep phases, one whole-document pass is given what the analysis examined —
``analysis_coverage[*]["unit_ids"]`` (#2966: the ids the phases really
submitted, never the acts) — and the unexamined candidates. It names at most
``MAX_ITEMS`` supports or qualifiers of the thesis that no lens examined, each
with a verbatim quote verified against the candidate's OWN characters, and
routes each to the lens whose question it raises:

* an epistemic or modal qualifier (belief versus knowledge) → ``modal``;
* a quantified or statistical support → ``fallacy_descent``;
* a support carrying an inference → ``fol``.

The lens RUN runs through an injected ``dispatcher``: this module owns the
naming, the verification and the routing decision; the invoke layer owns which
callable each lens name runs on. A lens the run has no callable for is
recorded as ``lens_not_wired`` — a named absence carried to the acts, never a
fabricated finding (#1019, #1941). A named passage without a wired lens still
reaches the render as an unexamined support: turning a silent omission into a
stated gap is the point, and printing a verdict nothing computed would be the
defect this project keeps closing.

Anti-pendulum: no phase's unit budget moves. The pass spends one call on the
document plus one bounded call per NAMED passage (at most three), and every
passage it names is a passage no lens had read.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set, Tuple

from argumentation_analysis.agents.core.reading.first_reading import (
    anchor_quote_in,
    defining_moves,
)

logger = logging.getLogger("CoverageReview")

#: Cap on the passages the review names. Three is the measured divergence
#: bound the #3326 winner reading already uses (1-3 cited items per run): a
#: wider divergence is a coverage anomaly to surface, not a reading mandate.
MAX_ITEMS = 3

#: Cap on the candidate briefing. The population of unexamined units runs to
#: hundreds on a long document; the prompt carries a stratified sample of it
#: (``select_for_budget``), never a head — the very defect this module closes.
PROMPT_MAX_CANDIDATES = 24

#: Characters of a candidate shown to the model. The model must copy a quote
#: verbatim; a passage longer than this is trimmed and says so.
CANDIDATE_QUOTE_CHARS = 400

COVERAGE_REVIEW_BASIS = "coverage_review"

#: The lens each class of passage points at — one table, read by the dispatcher.
LENS_BY_CLASS: Dict[str, str] = {
    "modal": "modal",
    "statistical": "fallacy_descent",
    "inferential": "fol",
}

ITEM_CLASSES: Tuple[str, ...] = tuple(LENS_BY_CLASS)

#: Drop reasons — a closed vocabulary, counted, never silently discarded.
DROP_UNKNOWN_UNIT = "unknown_unit"
DROP_QUOTE_NOT_VERBATIM = "quote_not_verbatim"
DROP_UNPOSITIONED = "unpositioned_candidate"
DROP_UNKNOWN_CLASS = "unknown_class"
DROP_CAPPED = "capped"

COVERAGE_REVIEW_PROMPT = """Tu relis la couverture d'une analyse. Le document a
déjà été lu une première fois (thèse et mouvements nommés), puis analysé en
profondeur par plusieurs lentilles, chacune n'ayant examiné qu'une partie des
passages. Ta seule question : parmi les passages CANDIDATS ci-dessous, lesquels
soutiennent ou qualifient LA THÈSE et n'ont été examinés par AUCUNE lentille ?

Règles strictes :
- Ne nomme que des passages de la liste CANDIDATS, par leur identifiant.
- Recopie la citation MOT POUR MOT depuis le texte du candidat : aucune
  reformulation, aucune jointure de deux passages.
- Classe chaque passage dans UNE de ces trois classes, selon la question qu'il
  pose : "modal" (une réserve épistémique : croyance plutôt que savoir, doute,
  modalité), "statistical" (un appui quantifié ou statistique, un taux, une
  part, une comparaison chiffrée), "inferential" (un appui qui porte une
  inférence : prémisse, conséquence, condition).
- Au plus {max_items} passages. Une liste vide est une réponse valide — et la
  bonne réponse quand aucun candidat ne porte la thèse.
- Aucune sortie hors du JSON.

Réponds en français, avec UNIQUEMENT ce JSON, sans balises ni commentaire :
{{"items": [{{"unit_id": "arg_N", "quote": "citation exacte", "class": "modal",
            "reason": "ce que ce passage fait à la thèse, en une phrase"}}]}}

THÈSE DU DOCUMENT (citée par la première lecture) :
{thesis}

PASSAGES CANDIDATS (extraits, jamais examinés par une lentille) :
{candidates}
"""


@dataclass
class CoverageItem:
    """One passage the review named, with its verified place and its lens."""

    unit_id: str
    quote: str
    offset: int
    kind: str
    lens: str
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
    reached the model must not read as "completed, nothing unexamined".
    ``no_candidates`` is the byte-identity control: every support the review
    could name was already examined, and the acts' prompt is unchanged.
    """

    status: str = "no_llm"
    items: List[CoverageItem] = field(default_factory=list)
    examined: int = 0
    candidates: int = 0
    briefed: int = 0
    dropped: Dict[str, int] = field(default_factory=dict)
    reason: str = ""
    basis: str = COVERAGE_REVIEW_BASIS

    def to_state(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
            "examined": self.examined,
            "candidates": self.candidates,
            "briefed": self.briefed,
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


def examined_unit_ids(state: Any) -> Tuple[Set[str], int]:
    """The units the record says a phase really submitted, as one set.

    No allowlist of phase names (#2137's lesson: an allowlist ages). Any
    ``analysis_coverage`` entry carrying ``unit_ids`` names units a phase put
    in front of a lens, whatever the phase is called — a new selector is
    covered the day it starts recording. ``anchor_census`` carries no
    ``unit_ids`` (it counts provenance), so it cannot contaminate the set.
    """
    coverage = _as_state_dict(state, "analysis_coverage")
    if not isinstance(coverage, dict):
        return set(), 0
    examined: Set[str] = set()
    for entry in coverage.values():
        if not isinstance(entry, dict):
            continue
        unit_ids = entry.get("unit_ids")
        if not isinstance(unit_ids, (list, tuple)):
            continue
        for unit_id in unit_ids:
            if isinstance(unit_id, str) and unit_id:
                examined.add(unit_id)
    return examined, len(examined)


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
        entry = provenance.get(unit_id) if isinstance(provenance, dict) else None
        offset = entry.get("offset") if isinstance(entry, dict) else None
        if isinstance(offset, bool) or not isinstance(offset, int):
            offset = None
        source_quote = ""
        if isinstance(entry, dict):
            source_quote = str(entry.get("source_quote") or "")
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


def unexamined_candidates(state: Any, examined: Set[str]) -> List[Dict[str, Any]]:
    """The units no phase recorded a submission for, document order.

    Positioned units come first (they are the ones a reader can be sent to),
    then the unpositioned in stable order — the same ordering the selector
    uses, because an unlocated unit cannot anchor a finding.
    """
    return [row for row in _unit_rows(state) if row["unit_id"] not in examined]


def _briefed_candidates(
    candidates: Sequence[Dict[str, Any]], text_length: int
) -> List[Dict[str, Any]]:
    """The bounded sample of candidates the prompt carries.

    ``select_for_budget`` is the ONE selector (#2850 slice A): stratified over
    the document, never the head. A population that fits the budget is
    returned whole, in document order, and the prompt is unchanged.
    """
    if len(candidates) <= PROMPT_MAX_CANDIDATES:
        return list(candidates)
    # Local import: ``argumentation_analysis.orchestration`` pulls the whole
    # invoke layer at package import, and the reading package is imported BY
    # that layer — a module-level import here would close the cycle.
    from argumentation_analysis.orchestration.selection import (
        SelectableUnit,
        select_for_budget,
    )

    units = [
        SelectableUnit(
            unit_id=row["unit_id"],
            text=row["text"],
            offset=row["offset"],
        )
        for row in candidates
    ]
    selection = select_for_budget(
        units,
        PROMPT_MAX_CANDIDATES,
        text_length=text_length or None,
    )
    chosen = {unit.unit_id for unit in selection.selected}
    return [row for row in candidates if row["unit_id"] in chosen]


def _thesis_quote(state: Any) -> str:
    """The thesis the first reading named, verbatim, or an empty string."""
    for move in defining_moves(state):
        if str(move.get("slot") or "") != "thesis":
            continue
        quote = str(move.get("quote") or "").strip()
        if quote:
            return quote
    return ""


def _candidate_block(candidates: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for row in candidates:
        text = str(row["text"]).strip()
        trimmed = len(text) > CANDIDATE_QUOTE_CHARS
        if trimmed:
            text = text[:CANDIDATE_QUOTE_CHARS].rstrip() + " […]"
        position = row["offset"] if isinstance(row["offset"], int) else "inconnue"
        lines.append(f"[{row['unit_id']}] (position {position}) : « {text} »")
    return "\n".join(lines) if lines else "  (aucun candidat)"


def build_coverage_review_prompt(
    thesis: str, candidates: Sequence[Dict[str, Any]]
) -> str:
    """The reviewer's one prompt: the thesis, then the unexamined candidates."""
    return COVERAGE_REVIEW_PROMPT.format(
        max_items=MAX_ITEMS,
        thesis=f"« {thesis} »",
        candidates=_candidate_block(candidates),
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


def _verified_span(candidate_text: str, quote: str) -> Optional[Tuple[str, int]]:
    """The verbatim span of the candidate the quote names, with its offset.

    Exact match first; failing that, the #3415 locator — which returns a
    substring of the candidate's own characters, so what reaches the state is
    always document text and never the model's paraphrase. ``None`` when the
    two share no run long enough to be the same passage.
    """
    if not quote:
        return None
    position = candidate_text.find(quote)
    if position >= 0:
        return quote, position
    return anchor_quote_in(candidate_text, quote)


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
    """Name the thesis supports no lens examined, then route each to its lens.

    ``llm_callable`` and ``dispatcher`` are injected: the invoke layer owns
    the client, the runaway guard and the provider route; this module owns the
    question, the verification and the routing decision. No LLM → status
    ``no_llm`` and an empty read, never a fabricated one.
    """
    review = CoverageReview()
    raw_text = _raw_text(state)
    examined, examined_total = examined_unit_ids(state)
    review.examined = examined_total
    candidates = unexamined_candidates(state, examined)
    review.candidates = len(candidates)
    if not candidates:
        review.status = "no_candidates"
        return review

    thesis = _thesis_quote(state)
    if not thesis:
        review.status = "no_reading"
        review.reason = "no thesis move recorded"
        return review

    if llm_callable is None:
        review.status = "no_llm"
        return review

    briefed = _briefed_candidates(candidates, len(raw_text))
    review.briefed = len(briefed)
    prompt = build_coverage_review_prompt(thesis, briefed)

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

    by_id = {row["unit_id"]: row for row in candidates}
    dropped: Dict[str, int] = {}

    def _drop(reason: str) -> None:
        dropped[reason] = dropped.get(reason, 0) + 1

    for raw in raw_items:
        if len(review.items) >= MAX_ITEMS:
            _drop(DROP_CAPPED)
            continue
        if not isinstance(raw, dict):
            _drop(DROP_UNKNOWN_UNIT)
            continue
        unit_id = str(raw.get("unit_id") or "").strip()
        row = by_id.get(unit_id)
        if row is None:
            _drop(DROP_UNKNOWN_UNIT)
            continue
        offset = row["offset"]
        if not isinstance(offset, int):
            # A passage the reader cannot be sent to is not reported as one
            # (cross_passage's rule): the finding exists, its place does not.
            _drop(DROP_UNPOSITIONED)
            continue
        verified = _verified_span(str(row["text"]), str(raw.get("quote") or ""))
        if verified is None:
            _drop(DROP_QUOTE_NOT_VERBATIM)
            continue
        quote, local = verified
        kind = str(raw.get("class") or "").strip().lower()
        if kind not in LENS_BY_CLASS:
            _drop(DROP_UNKNOWN_CLASS)
            continue
        review.items.append(
            CoverageItem(
                unit_id=unit_id,
                quote=quote,
                offset=offset + local,
                kind=kind,
                lens=LENS_BY_CLASS[kind],
                reason=str(raw.get("reason") or "").strip(),
            )
        )

    review.dropped = dropped
    for item in review.items:
        item.routed = await _route(item, dispatcher)
    review.status = "ok"
    logger.info(
        "CoverageReview: %d named out of %d unexamined (examined=%d, briefed=%d)",
        len(review.items),
        review.candidates,
        review.examined,
        review.briefed,
    )
    return review


async def extract_coverage_review(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_coverage_review(**kwargs)).to_state()


def coverage_review_note(state: Any) -> str:
    """The block Act II reads — empty when no passage was named.

    Empty on ``no_candidates`` (every support was examined) and on any status
    that never reached the model: the prompt then omits the section rather
    than advertising a review that did not run — the #3395 rule, and the
    byte-identity control the issue asks for.
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
        "[APPUIS DE LA THÈSE QU'AUCUNE LENTILLE N'AVAIT EXAMINÉS — "
        "revue de couverture, après les phases profondes]"
    ]
    for item in items:
        quote = str(item.get("quote") or "")
        offset = item.get("offset")
        routed_any = item.get("routed")
        routed = routed_any if isinstance(routed_any, dict) else {}
        status = str(routed.get("status") or "")
        lens = str(item.get("lens") or "")
        if quote and isinstance(offset, int):
            lines.append(f"  — « {quote} » (position {offset})")
        else:
            continue
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
        else:
            lines.append(f"    Lentille {lens} : {status}.")
    return "\n".join(lines)


__all__ = [
    "CANDIDATE_QUOTE_CHARS",
    "COVERAGE_REVIEW_BASIS",
    "COVERAGE_REVIEW_PROMPT",
    "CoverageItem",
    "CoverageReview",
    "ITEM_CLASSES",
    "LENS_BY_CLASS",
    "MAX_ITEMS",
    "PROMPT_MAX_CANDIDATES",
    "build_coverage_review",
    "build_coverage_review_prompt",
    "coverage_review_note",
    "examined_unit_ids",
    "extract_coverage_review",
    "unexamined_candidates",
]
