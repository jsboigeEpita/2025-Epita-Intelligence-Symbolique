"""Rule-vs-ML detection candidate bridge for the Dung-arbitration stage (I1 #1501 PR2).

The arbitration stage (:mod:`dung_arbitration_stage`) consumes
:class:`SophismCandidate` atoms. The neural/ML side already produces them
(:func:`neuro_symbolic_arbitrator.llm_neural_detect_async`, from #1429 PR3 —
currently 0 production callers, parked with this stage as its named consumer,
owner record #2928). This
module supplies the **rule side** and a combiner, so the stage can arbitrate
across detector provenances (rule taxonomy vs ML) — the "rule-vs-ML" dimension
the #1501 dispatch asks for.

The bridge is a PURE transformer: it maps detection dicts (from
:meth:`TaxonomySophismDetector.detect_sophisms_from_taxonomy`) to opaque
:class:`SophismCandidate` atoms without interpreting their meaning, and combines
several detector sources into one candidate batch with unique opaque ids. It
implements no detection logic of its own (anti-pendule: reuse
``TaxonomySophismDetector``, don't reimplement) and is JVM/LLM-free so it is
unit-testable with synthetic atoms.

Provenance, not a direct attack channel
---------------------------------------
The anchor a detection carries decides its rivalry group (#2920). An ANCHORED
detection (``target_argument`` — the per-argument hierarchical tier writes it)
shares a span with every other candidate on the same target, across families
AND across detector provenances, so cross-source disagreement CAN surface
through the same-span rivalry there. An ANCHORLESS detection (the lexical
taxonomy detector scans the whole passage) keeps the ``(detector, family)``
anchor, where same-span groups are always same-family and the rivalry policy
never fires. The declared Walton-Krabbe relations channel — once the second,
explicit attack dimension — was retired (#1649 R1065): its producer never
existed. Provenance is recorded on each candidate so a downstream
report can attribute each atom to its detector.

Privacy HARD
------------
Callers MUST pass opaque family labels and opaque span anchors. The bridge never
ingests source text directly — ``span_text_for`` is the caller's responsibility
(the upstream that holds the real text + segmentation), matching #1429's
``span_text_for`` contract.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    SophismCandidate,
)

# Shape produced by TaxonomySophismDetector.detect_sophisms_from_taxonomy. Kept
# as a loose Mapping (not a TypedDict) because the student detector is untyped
# student code whose dict keys are not contractually frozen.
TaxonomyDetection = Mapping[str, Any]


def _opaque_span_id(family: str, detector: str) -> str:
    """Deterministic opaque span anchor for a rule detection that has no text span.

    The taxonomy detector is lexical over the whole passage (no span), so two
    rule detections of the SAME family under the SAME detector collapse to one
    span_id (a passage may legitimately surface the same fallacy twice is not
    modelled at the rule level — same family ⇒ same anchor). Families from
    different detectors stay distinct (detector is part of the hash input), so a
    rule and an ML detection of the same family do NOT falsely collapse.
    """

    raw = f"{detector}::{family}".encode("utf-8")
    return "span_" + hashlib.md5(raw).hexdigest()[:8]


def _anchored_span_id(target_argument: str) -> str:
    """Deterministic opaque span anchor for a detection that CARRIES a target.

    #2920: the per-argument hierarchical tier grounds each fallacy on an
    argument identifier (``target_argument``, #1633). Anchoring on the target
    ALONE — detector and family are NOT hash inputs — puts every candidate on
    the same argument into one rivalry group, whatever produced it: the
    same-span different-family policy can finally fire, across families and
    across detector provenances (the #1501 rule-vs-ML dimension). The value is
    an opaque id (never the raw text of the target).
    """

    raw = f"anchored::{target_argument}".encode("utf-8")
    return "span_" + hashlib.md5(raw).hexdigest()[:8]


def _coerce_confidence(value: Any, default: float = 0.5) -> float:
    """Clamp a detection confidence into [0, 1], defaulting on bad/missing input."""

    try:
        c = float(value)
    except (TypeError, ValueError):
        return default
    if c != c:  # NaN
        return default
    return max(0.0, min(1.0, c))


def taxonomy_detection_to_candidate(
    detection: TaxonomyDetection,
    *,
    index: int,
    detector: str = "rule_taxonomy",
) -> SophismCandidate:
    """Map ONE taxonomy detection dict to an opaque :class:`SophismCandidate`.

    ``family`` is the detection's family/name (opaque label — the stage never
    interprets it); ``confidence`` is clamped to ``[0, 1]`` (defaults to 0.5 if
    missing or malformed).

    ``span_id`` — the anchor the rivalry policy groups by — is derived from the
    anchor the detection ACTUALLY carries (#2920):

    * a detection with ``target_argument`` (the per-argument hierarchical tier
      writes it — an argument IDENTIFIER, #1633: never text-match it) is
      anchored on that target alone: two candidates share the span iff they
      target the same argument, whatever their family or detector, so the
      same-span different-family rivalry CAN fire — including across detector
      provenances (the #1501 rule-vs-ML dimension);
    * an anchorless detection (the lexical taxonomy detector scans the whole
      passage) falls back to the ``(detector, family)`` hash, where the
      same-span-same-family grouping never attacks by construction.

    Args:
        detection: One row of a detector output (rule taxonomy rows or
            hierarchical-phase fallacies).
        index: Position in the source batch — used to mint a unique opaque id.
        detector: Provenance label embedded in the id (and in the fallback span
            anchor) so a rule detection never collides with an ML detection.
    """

    # Tolerant family lookup: the rule detector (TaxonomySophismDetector) emits
    # ``famille``/``name``/``nom_vulgarise``; the ML/hierarchical phase emits
    # ``family``/``fallacy_type``. One converter serves both provenances — the
    # family is an opaque label the stage never interprets (#1501 rule-vs-ML).
    family = (
        str(
            detection.get("famille")
            or detection.get("family")
            or detection.get("fallacy_type")
            or detection.get("name")
            or detection.get("nom_vulgarise")
            or "unknown"
        ).strip()
        or "unknown"
    )
    confidence = _coerce_confidence(detection.get("confidence", 0.5))
    target = str(detection.get("target_argument") or "").strip()
    if target:
        span_id = _anchored_span_id(target)
    else:
        span_id = _opaque_span_id(family, detector)
    return SophismCandidate(
        candidate_id=f"{detector}_{index}",
        family=family,
        span_id=span_id,
        confidence=confidence,
    )


def taxonomy_detections_to_candidates(
    detections: Sequence[TaxonomyDetection],
    *,
    detector: str = "rule_taxonomy",
) -> list[SophismCandidate]:
    """Map a batch of taxonomy detections to opaque candidates (stable order)."""

    return [
        taxonomy_detection_to_candidate(d, index=i, detector=detector)
        for i, d in enumerate(detections)
    ]


def combine_candidate_sources(
    sources: Mapping[str, Sequence[SophismCandidate]],
) -> list[SophismCandidate]:
    """Union several detector outputs into one candidate batch (unique ids).

    Each source key is a provenance label (e.g. ``"rule_taxonomy"``,
    ``"ml_llm"``). Candidates keep their original ``candidate_id`` but are
    prefixed with the source label when needed to guarantee global uniqueness
    (defensive — ids that already include their source are left untouched).
    Order is stable: sources in insertion order, candidates in source order.
    """

    seen: set[str] = set()
    combined: list[SophismCandidate] = []
    for source, cands in sources.items():
        for i, cand in enumerate(cands):
            cid = cand.candidate_id
            if cid in seen:
                cid = f"{source}_{i}_{cid}"
                cand = SophismCandidate(
                    candidate_id=cid,
                    family=cand.family,
                    span_id=cand.span_id,
                    confidence=cand.confidence,
                    failed_critical_questions=cand.failed_critical_questions,
                )
            if cid in seen:
                continue
            seen.add(cid)
            combined.append(cand)
    return combined
