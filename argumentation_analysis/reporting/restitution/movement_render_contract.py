"""The render contract of Act II — carried or counted, never silently
dropped (#3560).

## The gap this closes

Cycle 7 of the v1 panel (#3374) measured it: every attributed finding and
every coverage-review item reaches the Act II prompt — the movements' blocks
render them all — and between that prompt and the reader stands the writer's
discretion alone. No post-weave check verifies that a movement or a review
item the prompt carried was treated, and no count says how many were not.
The tracer stage ``found_not_rendered`` counted 13 such rows at c7 (ten
findings, three review items); at c10 the class turned severe (doc_J,
review-item kind, central in both families).

## The contract

Every movement and every review item handed to the Act II writer is EITHER
treated in the prose OR counted in a stated drop count — the counted form
the first-reading note already uses (« 3 gestes nommés, 1 montré ici —
échantillonné, pas exhaustif »). The writer is taught the form
(:data:`MOVEMENT_COUNT_RULE`, one consigne of the Act II prompt); the
pipeline guarantees it on each channel it can WITNESS: when the measured
untreated set is non-empty and the writer's own count is missing or wrong,
the producer appends the honest count line to the act
(:func:`render_count_line`, same counted form) and the motif lands in the
act's ``degraded`` map under ``act2_render_contract``, archived with the
#2046 fabrication notes — the count line tells the reader, the motif tells
the auditor. A writer whose own count is exact keeps its prose
byte-identical: the pipeline line never fires on a counted drop.

## A count the measure cannot witness

The coordinator's replay on the recorded c7–c10 states (14/11) measured the
review-item predicate as language-bound: with the quote in English and the
act in French, a 4-word run never fires, and the recorded rates split by
quote language (c7 8/41 en against 1/8 fr; c10 8/48 en against 1/4 fr). A
count line built on that predicate would state a number the measure cannot
back — worse than silence. So the review-item channel is MEASURED but not
yet PROVEN (:data:`COVERAGE_ITEM_MEASURE_PROVEN`): the reading exposes
``items_treated`` for the tracer, and no count is stated for the channel;
the motif records « mesure non éprouvée — aucun compte énoncé », counts
only. The predicate itself now reads a bound item through its movement's
beat — the item's unit carried by a treated movement — plus the item's own
claim (the reviewer's French conclusion) and its retained labels, which are
language-free witnesses. The channel flips to proven when the coordinator's
replay confirms it on the recorded states.

## The treatment measure

The same measure as the coordinator's tracer (``.tmp/f1/c7_fnr.py``), so
the check reddens exactly where the tracer counts an uncounted drop:

* a MOVEMENT is treated when the prose names one of its finding names (the
  writer-facing taxonomy name the « Procédé » line carries), or its theme
  (the movement's title is thematic — « Le mouvement ad hominem »), or the
  canonical vocabulary of a non-attack theme (« soutiens » / « non
  examinés » / « échantillon non enregistré » carry no finding to name), or
  shares a 4-word run with one of its units' texts, or with the quote of a
  coverage line bound to one of its units;
* a REVIEW ITEM is treated when the prose shares a 4-word run with its
  quote (same-language only), or its ``unit_id`` belongs to a movement the
  prose treats (the #3505 binding — the movement's beat carries the
  passage, whatever the quote's language), or the prose shares a 4-word
  run with the item's own claim (the reviewer's French ``conclusion``), or
  it names one of the item's retained fallacy names.

Anchors are taxonomy constants, never corpus text. The appended line and
the motif carry COUNTS only (#3249 — ``restitution_acts_degraded`` is a
closed producer vocabulary; a motif that quoted the act would carry corpus
text into it).

## Known bound, named

The measure is lexical. A writer that treats a movement while paraphrasing
every anchor away — neither the family, nor a finding name, nor a 4-word
run of its units — reads as a drop and the count line says so. That is the
honest direction: the alternative (a lenient instrument) is the silent drop
this issue exists to close. The residual is symmetric and named: a writer
that names a movement's family inside ANOTHER movement's beat marks the
named movement treated. Both bounds are the tracer's own, kept rather than
invented beside it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple

from .fr_accord import accord
from .readability_gate import GateVerdict
from argumentation_analysis.utils.taxonomy_loader import generic_fallacy_name

if TYPE_CHECKING:  # pragma: no cover — typing only, never a runtime cycle
    from .act2_narrative_plugin import Act2Evidence

#: The consigne that teaches the counted form. One line of the Act II
#: CONSIGNE — the writer may treat everything (then no count is needed) or
#: state the exact count of what it drops, in the fixed parseable form the
#: check below reads back. The fixed form is the contract's hinge: a count
#: the pipeline cannot parse is a count the reader cannot trust.
MOVEMENT_COUNT_RULE = (
    "- CHAQUE mouvement remis ci-dessus a droit à un battement, et chaque "
    "constat de la revue de couverture que le bloc liste a droit à être "
    "nommé dans la clôture du récit. Ce que tu ne traites pas se compte à "
    "la fin, sous la forme exacte « N mouvements non traités sur M » — et, "
    "pour les constats que la clôture ne reprend pas, « N constats de "
    "couverture non repris sur M ». Un absent sans son compte est une "
    "perte silencieuse, jamais un choix mesuré.\n"
)

#: #3560, coordinator finding 14/11 — is the REVIEW-ITEM channel's treatment
#: measure PROVEN on the recorded panel states? Not yet: the quote's 4-word
#: run is language-bound (an English quote on a French act never fires; the
#: replay measured 8/41 en against 1/8 fr at c7, 8/48 en against 1/4 fr at
#: c10). Until the coordinator's replay confirms the binding/claim predicate
#: on c7–c10, the pipeline states NO count for this channel — a count the
#: measure cannot witness is a false statement to the reader, worse than
#: silence. The motif still records the channel as unmeasured. Flip to True
#: with the replay's figures.
COVERAGE_ITEM_MEASURE_PROVEN = False

#: The writer's stated movement count — « 2 mouvements non traités sur 3 ».
#: First match wins: the consigne teaches ONE line, and a second differing
#: count in the same act is a defect the motif names, not a datum.
_STATED_MOVEMENT_DROPS_RE = re.compile(
    r"(\d+)\s+mouvements?\s+non\s+trait\w+(?:\s+sur\s+\d+)?",
    re.IGNORECASE,
)

#: The writer's stated review-item count — « 1 constat de couverture non
#: repris sur 1 ».
_STATED_ITEM_DROPS_RE = re.compile(
    r"(\d+)\s+constats?\s+de\s+couverture\s+non\s+repris\w*(?:\s+sur\s+\d+)?",
    re.IGNORECASE,
)

#: A « … » span inside a rendered line — where the coverage procede and
#: binding lines carry their fallacy names. Short spans only: a name, not a
#: quoted passage.
_QUOTED_NAME_RE = re.compile(r"«([^»]{2,120})»")

#: Words for the 4-word-run measure — the tracer's own n, letters and digits,
#: accents included, apostrophes split (« l'appel » → « l », « appel »).
_WORD_RE = re.compile(r"[0-9a-zà-öø-ÿ]+")

#: How many consecutive shared words a run carries — the tracer's own window.
_RUN_WORDS = 4


def _norm(text: str) -> str:
    """Lowercase, straightened apostrophes, collapsed whitespace."""
    return " ".join(str(text).lower().replace("’", "'").split())


def _runs(text: str) -> List[str]:
    """The ``_RUN_WORDS``-word runs of ``text``, normalized."""
    words = _WORD_RE.findall(_norm(text))
    return [
        " ".join(words[i : i + _RUN_WORDS]) for i in range(len(words) - _RUN_WORDS + 1)
    ]


def _names_prose_anchor(prose_norm: str, anchors: Sequence[str]) -> bool:
    """True when the prose names one of the anchors (substring, normalized)."""
    for anchor in anchors:
        needle = _norm(anchor)
        if len(needle) >= 4 and needle in prose_norm:
            return True
    return False


def _theme_fallback_anchors(theme: str) -> Tuple[str, ...]:
    """The canonical vocabulary of a theme that carries no finding to name.

    The non-attack movements exist to STATE a fact (« les soutiens qui
    tiennent », « jamais soumises », « pas été enregistré ») — their headers
    and the coverage note say it in this vocabulary, and a beat that treats
    them says it too. Matched as stems, deliberately: the fact has several
    grammatical clothes and the contract is about the beat, not the word.
    """
    t = _norm(theme)
    if "soutien" in t:
        return ("soutien", "tiennent", "ce qui tient")
    if "enregistr" in t or "échantillon" in t:
        return ("enregistr", "échantillon")
    if "examin" in t:
        return ("examin", "soumis")
    return ()


def _movement_anchors(movement: Any) -> List[str]:
    """Every name a treatment of ``movement`` can carry into the prose."""
    anchors: List[str] = []
    for argument in getattr(movement, "arguments", []) or []:
        for fallacy in getattr(argument, "fallacies", []) or []:
            name = generic_fallacy_name(
                str(getattr(fallacy, "type", "") or ""),
                getattr(fallacy, "taxonomy_path", None),
            )
            if name:
                anchors.append(name)
        # The coverage walk's retained fallacies ride the procede lines as
        # « name » (famille …) spans — one home per label (#3505 part 2).
        for procede in getattr(argument, "coverage_procedes", []) or []:
            anchors.extend(
                m.group(1).strip() for m in _QUOTED_NAME_RE.finditer(procede)
            )
    theme = str(getattr(movement, "theme", "") or "")
    if theme:
        anchors.append(theme)
        anchors.extend(_theme_fallback_anchors(theme))
    return anchors


def _movement_treated(movement: Any, prose_norm: str, prose_runs: Set[str]) -> bool:
    """The tracer's measure, at movement granularity."""
    if _names_prose_anchor(prose_norm, _movement_anchors(movement)):
        return True
    for argument in getattr(movement, "arguments", []) or []:
        description = str(getattr(argument, "description", "") or "")
        if description and any(run in prose_runs for run in _runs(description)):
            return True
        # A bound coverage line carries the review's verbatim quote — the
        # passage the tracer's 4-word run reads.
        for cov_line in getattr(argument, "coverage_lines", []) or []:
            for quote in (m.group(1) for m in _QUOTED_NAME_RE.finditer(cov_line)):
                if any(run in prose_runs for run in _runs(quote)):
                    return True
    return False


def _review_items(state: Any) -> List[Dict[str, Any]]:
    """The review items the Act II prompt carries.

    The same gate ``coverage_item_line`` applies: an ``ok`` record, and an
    item with a placeable passage (a quote at an offset). An item the line
    builder skips never reaches the writer — it is not the writer's to
    carry, so it is not part of this contract.
    """
    record = getattr(state, "coverage_review", None)
    if isinstance(state, dict):
        record = state.get("coverage_review")
    if not isinstance(record, dict) or str(record.get("status") or "") != "ok":
        return []
    items: List[Dict[str, Any]] = []
    for item in record.get("items") or []:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote") or "")
        offset = item.get("offset")
        if not quote or not isinstance(offset, int) or isinstance(offset, bool):
            continue
        items.append(item)
    return items


def _item_retained_names(item: Dict[str, Any]) -> List[str]:
    """The writer-facing names of the fallacies the walk retained (if any).

    Mirrors the review's own label builder (``_fallacy_label`` /
    ``_retained_fallacies`` in ``agents.core.reading.coverage_review``): the
    recorded name through :func:`generic_fallacy_name`, plus the family when
    the record states one — both are names the closing beat can carry.
    """
    routed = item.get("routed")
    routed = routed if isinstance(routed, dict) else {}
    finding = routed.get("finding")
    finding = finding if isinstance(finding, dict) else {}
    fallacies = finding.get("fallacies")
    names: List[str] = []
    for fallacy in fallacies if isinstance(fallacies, list) else []:
        data = fallacy if isinstance(fallacy, dict) else {}
        recorded = str(
            data.get("fallacy") or data.get("type") or data.get("fallacy_type") or ""
        ).strip()
        if not recorded:
            continue
        names.append(generic_fallacy_name(recorded, data.get("taxonomy_path")))
        family = str(data.get("family") or "").strip()
        if family:
            names.append(family)
    return names


def _item_own_claim(item: Dict[str, Any]) -> str:
    """The item's own claim, as the reviewer recorded it.

    French by construction (the review answers in French), so a 4-word run
    with the act is a language-free witness of the treatment. The quote is
    NOT read here — it is the language-bound channel — and neither is
    ``reason`` (it argues why the reader would lose something, not what the
    passage says).
    """
    return str(item.get("conclusion") or "")


def _item_treated(
    item: Dict[str, Any],
    prose_norm: str,
    prose_runs: Set[str],
    treated_unit_ids: Set[str],
) -> bool:
    """The tracer's measure, at review-item granularity.

    Four witnesses, strongest first: the quote's 4-word run (same-language
    only), the item's UNIT carried by a movement the prose treats (the
    #3505 binding — the movement's beat renders the passage, whatever the
    quote's language), a 4-word run with the item's own claim, and one of
    the item's retained fallacy names.
    """
    quote = str(item.get("quote") or "")
    if quote and any(run in prose_runs for run in _runs(quote)):
        return True
    unit_id = str(item.get("unit_id") or "")
    if unit_id and unit_id in treated_unit_ids:
        return True
    claim = _item_own_claim(item)
    if claim and any(run in prose_runs for run in _runs(claim)):
        return True
    return _names_prose_anchor(prose_norm, _item_retained_names(item))


@dataclass(frozen=True)
class RenderContractReading:
    """What the render contract measured on one woven act.

    ``stated_*`` is the count the WRITER's prose states (``None`` when it
    states none); ``*_untreated`` is the measured count. A channel is clean
    when everything is treated, or when the writer's count is exact — the
    drop is then counted, which is the contract.
    """

    movements_total: int = 0
    movements_treated: int = 0
    untreated_movement_themes: Tuple[str, ...] = ()
    items_total: int = 0
    items_treated: int = 0
    #: #3560, coordinator finding 14/11 — the review-item channel is MEASURED
    #: but not PROVEN (:data:`COVERAGE_ITEM_MEASURE_PROVEN`): no count is
    #: stated for it and it never reddens the check until its measure is
    #: confirmed on the recorded panel states. The count stays exposed here
    #: for the tracer; the reader is not told a number nothing can back.
    items_measured: bool = True
    stated_movement_drops: Optional[int] = None
    stated_item_drops: Optional[int] = None

    @property
    def movements_untreated(self) -> int:
        return self.movements_total - self.movements_treated

    @property
    def items_untreated(self) -> int:
        return self.items_total - self.items_treated

    @property
    def movements_count_missing_or_wrong(self) -> bool:
        return self.movements_untreated > 0 and (
            self.stated_movement_drops != self.movements_untreated
        )

    @property
    def items_count_missing_or_wrong(self) -> bool:
        return (
            self.items_measured
            and self.items_untreated > 0
            and self.stated_item_drops != self.items_untreated
        )


def _first_int(pattern: re.Pattern, prose: str) -> Optional[int]:
    match = pattern.search(prose)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):  # pragma: no cover — the pattern digits only
        return None


def read_render_contract(
    narrative: str, evidence: Any, state: Any
) -> RenderContractReading:
    """Measure the woven act against what the prompt carried.

    Deterministic, no LLM, no JVM. ``evidence`` is the bundle
    ``build_act2_evidence`` produced for the SAME state the prompt was
    built from — the movements and bound coverage lines it holds are the
    writer's data; ``state`` supplies the review record (bound and block
    items alike, each measured on its own anchors).
    """
    prose_norm = _norm(narrative)
    prose_runs: Set[str] = set(_runs(narrative))
    movements = list(getattr(evidence, "movements", []) or [])
    untreated_themes: List[str] = []
    treated = 0
    #: The units a treated movement's beat carries — the witness a translated
    #: item keeps when its quote shares no run with the act (#3505 binding).
    treated_unit_ids: Set[str] = set()
    for movement in movements:
        if _movement_treated(movement, prose_norm, prose_runs):
            treated += 1
            for argument in getattr(movement, "arguments", []) or []:
                arg_id = str(getattr(argument, "arg_id", "") or "")
                if arg_id:
                    treated_unit_ids.add(arg_id)
        else:
            untreated_themes.append(str(getattr(movement, "theme", "") or ""))
    items = _review_items(state)
    items_treated = sum(
        1
        for item in items
        if _item_treated(item, prose_norm, prose_runs, treated_unit_ids)
    )
    return RenderContractReading(
        movements_total=len(movements),
        movements_treated=treated,
        untreated_movement_themes=tuple(untreated_themes),
        items_total=len(items),
        items_treated=items_treated,
        items_measured=COVERAGE_ITEM_MEASURE_PROVEN,
        stated_movement_drops=_first_int(_STATED_MOVEMENT_DROPS_RE, narrative),
        stated_item_drops=_first_int(_STATED_ITEM_DROPS_RE, narrative),
    )


def check_render_contract(reading: RenderContractReading) -> GateVerdict:
    """Post-weave guarantee: a drop that is neither treated nor counted.

    FAIL exactly on the issue's condition — an item is missing AND the
    stated count is missing or wrong. Silent PASS otherwise: a counted drop
    is a measured choice, not a defect (the ask-4 split).
    """
    if not (
        reading.movements_count_missing_or_wrong or reading.items_count_missing_or_wrong
    ):
        return GateVerdict(band="PASS", reasons=[])
    reasons: List[str] = []
    if reading.movements_count_missing_or_wrong:
        stated = (
            str(reading.stated_movement_drops)
            if reading.stated_movement_drops is not None
            else "aucun"
        )
        reasons.append(
            f"{reading.movements_untreated} "
            f"{accord(reading.movements_untreated, 'mouvement absent', 'mouvements absents')} "
            f"du récit sur {reading.movements_total} remis, compte du rédacteur : "
            f"{stated} (#3560)"
        )
    if reading.items_count_missing_or_wrong:
        stated = (
            str(reading.stated_item_drops)
            if reading.stated_item_drops is not None
            else "aucun"
        )
        reasons.append(
            f"{reading.items_untreated} "
            f"{accord(reading.items_untreated, 'constat de couverture non repris', 'constats de couverture non repris')} "
            f"sur {reading.items_total}, compte du rédacteur : {stated} (#3560)"
        )
    return GateVerdict(band="FAIL", reasons=reasons)


def render_count_line(reading: RenderContractReading) -> str:
    """The producer's stated count — the first-reading note's counted form.

    Empty when every PROVEN channel is clean (all treated, or counted by the
    writer's own exact line). Only the channels the writer left uncounted
    AND whose measure is proven are stated: the line adds what is missing,
    never a second opinion on what the prose already counts. An unmeasured
    channel is never counted here — a number the measure cannot witness is
    a false statement to the reader; the motif records it instead.
    """
    clauses: List[str] = []
    if reading.movements_count_missing_or_wrong:
        clauses.append(
            f"{accord(reading.movements_total, 'mouvement remis au rédacteur', 'mouvements remis au rédacteur')}, "
            f"{accord(reading.movements_treated, 'traité ici', 'traités ici')}"
        )
    if reading.items_count_missing_or_wrong:
        clauses.append(
            f"{accord(reading.items_total, 'constat de couverture remis au rédacteur', 'constats de couverture remis au rédacteur')}, "
            f"{accord(reading.items_treated, 'repris ici', 'repris ici')}"
        )
    if not clauses:
        return ""
    return f"(Compte du récit : {' ; '.join(clauses)}.)"


def render_contract_motif(reading: RenderContractReading) -> str:
    """The motive recorded in the act's ``degraded`` map — empty when clean.

    Act, counts and what the pipeline did — never a quote of the prose
    (#3249): ``restitution_acts_degraded`` is a closed producer vocabulary
    and the anchors themselves stay out of it. A channel whose measure is
    not proven is recorded as measured-not-counted, so the auditor sees the
    withheld count without the reader being told a number nothing backs.
    """
    parts: List[str] = []
    if reading.movements_count_missing_or_wrong:
        stated = (
            f", compte lu : {reading.stated_movement_drops}"
            if reading.stated_movement_drops is not None
            else ""
        )
        parts.append(
            f"{reading.movements_untreated} "
            f"{accord(reading.movements_untreated, 'mouvement absent', 'mouvements absents')} "
            f"du récit sur {reading.movements_total} remis sans compte exact du "
            f"rédacteur{stated}"
        )
    if reading.items_count_missing_or_wrong:
        stated = (
            f", compte lu : {reading.stated_item_drops}"
            if reading.stated_item_drops is not None
            else ""
        )
        parts.append(
            f"{reading.items_untreated} "
            f"{accord(reading.items_untreated, 'constat de couverture non repris', 'constats de couverture non repris')} "
            f"sur {reading.items_total}{stated}"
        )
    if not reading.items_measured and reading.items_total:
        parts.append(
            f"{accord(reading.items_total, 'constat de couverture remis au rédacteur', 'constats de couverture remis au rédacteur')}, "
            "mesure non éprouvée sur ce canal — aucun compte énoncé"
        )
    if not parts:
        return ""
    return "Acte II : " + " ; ".join(parts) + " (#3560)"


def apply_render_contract(narrative: str, evidence: Any, state: Any) -> Tuple[str, str]:
    """Apply the contract to one woven act: the narrative, and the motif.

    The one entry point the act's builder calls, on the FINAL prose (after
    every deterministic pass and the bounded retry — the contract binds the
    text the reader receives). Returns the narrative with the producer's
    count line appended when a channel was left uncounted, and the motif
    for the ``degraded`` map (empty when the contract already held).
    """
    reading = read_render_contract(narrative, evidence, state)
    line = render_count_line(reading)
    motif = render_contract_motif(reading)
    if not line:
        return narrative, motif
    if narrative and not narrative.endswith("\n"):
        narrative = narrative + "\n"
    return narrative + line, motif
