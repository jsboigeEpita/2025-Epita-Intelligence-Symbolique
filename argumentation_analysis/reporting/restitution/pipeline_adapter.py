"""Pipeline wiring — turn a spectacular ``UnifiedAnalysisState`` into a readable
restitution report (Epic #1134 / R6-final #1140).

This is the *missing render path* the coordinator's audit surfaced (R433): the
spectacular workflow produces a rich shared-state — the 3 act generators
(``act1_framing`` / ``act2_narrative`` / ``act3_conclusion`` phases) populate
``state.act1_framing`` / ``state.act2_narrative`` / ``state.act3_conclusion`` —
but nothing was assembling those acts into the readable 3-act Markdown. The old
``render_markdown`` dump (``UnifiedReportTemplate``) is dead code on the
spectacular path; the run just returned a ``state_snapshot`` dict (the very
"très difficile à lire" artifact the owner flagged). This module closes that
gap: it is the single place where a completed spectacular state becomes the
readable report.

Design (anti-pendule, file-disjoint lane per dispatch R433):
  - ``build_restitution_acts(state, source_id)`` — the 1-liner mapping
    state→``RestitutionActs`` (the contract the renderer consumes). Reads the 3
    act strings off the state via ``getattr``; never imports the state class
    (stays decoupled, same idiom as ``state_adapter``).
  - ``render_spectacular_restitution(state, source_id, output_path=None)`` —
    assemble ``RestitutionActs`` + the folded appendix (``state_to_appendix_mapping``)
    + render via ``render_restitution_report``. Optionally write the Markdown to
    disk; the caller picks the (gitignored for real corpora) path. The renderer
    never writes to disk itself — privacy HARD stays at the caller boundary.
  - Missing acts are *named* by the renderer (fail-loud, #1019/#369), so calling
    this on a non-spectacular state (act strings empty) yields an honest
    "acte indisponible" report rather than a crash or silent omission.

Provenance note (superseded — #1608): this module used to record that the act
invoke-callables returned a per-act ``degraded`` dict which the state-writers
dropped, and that carrying it would require touching ``state_writers.py`` /
``shared_state.py`` "out of this lane's scope". That work has since been done:
``shared_state`` carries ``restitution_acts_degraded`` and the act state-writers
persist the motifs into it. The note is kept, corrected, because the reasoning it
recorded was the actual defect — the structured motifs were declared in seven
places and read in none, and the narrative-carries-the-honesty argument is what
made that look acceptable. ``_read_act_degraded`` below is the hop that finally
gives those motifs a reader.

Privacy HARD: ``source_id`` must be opaque (``doc_A``, never a speaker name /
title / date). The appendix layer strips ``raw_text`` defensively regardless.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from .acts import RestitutionActs
from .renderer import RenderedReport, render_restitution_report
from .state_adapter import state_to_appendix_mapping

logger = logging.getLogger(__name__)

# The opaque-id attribute the source_id is derived from when the caller does not
# pass one explicitly. Falls back to an honest "corpus_anonyme".
_SOURCE_ID_FALLBACK = "corpus_anonyme"


def _derive_source_id(state: Any, source_id: Optional[str]) -> str:
    """Resolve an opaque source id, preferring the explicit arg then metadata.

    Never invents a real name — privacy HARD. An absent id degrades to the
    honest fallback (the report header still names the corpus opaquely).
    """
    if source_id:
        return str(source_id)
    metadata = getattr(state, "source_metadata", None)
    if isinstance(metadata, dict):
        for key in ("corpus_id", "source_id", "doc_id"):
            val = metadata.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return _SOURCE_ID_FALLBACK


def _read_foundational_failure(state: Any) -> Optional[str]:
    """Read the normalized failed foundation from the workflow registry (#1913)."""
    if isinstance(state, dict):
        workflows = state.get("workflow_results")
    else:
        workflows = getattr(state, "workflow_results", None)
    if not isinstance(workflows, dict):
        return None

    for workflow_result in workflows.values():
        if not isinstance(workflow_result, dict):
            continue
        outcome = workflow_result.get("analysis_outcome")
        if not isinstance(outcome, dict) or outcome.get("status") != "failed":
            continue
        phase = str(outcome.get("phase") or "extract")
        reason = str(outcome.get("reason") or "cause inconnue")
        return f"Échec de l'extraction fondatrice ({phase}) — {reason}"
    return None


# #2046 — pipeline self-diagnosis motifs leave the reader blockquote for the
# appendix (per-act readability self-checks; the historical deterministic
# repair note persisted by pre-#2035 states). Twin of
# ``appendix._FABRICATION_NOTE_KEYS`` — file-disjoint by design (importing the
# appendix from the wiring module would close a renderer→appendix cycle); the
# accord between the two halves is pinned by test, like every twin here.
_FABRICATION_NOTE_KEYS = frozenset(
    {
        "act1_framing_gate",
        "act2_narrative_gate",
        "act3_conclusion_gate",
        "act3_scope_note_appended",
    }
)


def _read_act_degraded(state: Any) -> Dict[str, str]:
    """Flatten ``state.restitution_acts_degraded`` into ``RestitutionActs.degraded``.

    This is the last hop of the #1608 chain. The two ends already agreed on the
    *key* — the state writers file motifs under ``act1_framing`` /
    ``act2_narrative`` / ``act3_conclusion``, which is exactly what
    ``RestitutionActs.act_key`` returns — but not on the *value*: the state holds
    ``{motif_key -> text}`` (every motif preserved; #1608 deliberately refused to
    throw them away behind a ``bool()``), while the renderer prints a single line
    per act. The join happens here, at the boundary, so neither end has to
    compromise its own shape.

    Motifs are joined sorted by motif key: a rendered report must not depend on
    the order in which a plugin happened to insert them.

    #2046: the join must not stack each motif's final period with the
    separator (« .; ») — one period is dropped per motif and the joined line
    carries the terminal one. And the pipeline's self-diagnosis motifs (the
    ``_FABRICATION_NOTE_KEYS`` family) stop reaching the reader here — the
    appendix archives them (``appendix._fabrication_notes_section``), the
    readable facts stay in the blockquote.

    Anti-pendule: an act with no motif stays absent from the mapping — nothing is
    degraded by default. An unexpected shape is *reported*, not silently dropped:
    losing a degradation motif in silence is the exact failure this chain exists
    to remove.
    """
    if isinstance(state, dict):
        raw = state.get("restitution_acts_degraded")
    else:
        raw = getattr(state, "restitution_acts_degraded", None)
    if not isinstance(raw, dict):
        return {}

    valid_keys = {RestitutionActs.act_key(n) for n in (1, 2, 3)}
    flattened: Dict[str, str] = {}
    for key, motifs in raw.items():
        if key not in valid_keys:
            logger.warning(
                "Ignoring degradation motifs filed under unknown act key %r "
                "(fail-loud): expected one of %s",
                key,
                sorted(valid_keys),
            )
            continue
        if not isinstance(motifs, dict):
            logger.warning(
                "Degradation motifs for %r have an unexpected shape %s "
                "(fail-loud): expected a {motif_key: text} mapping",
                key,
                type(motifs).__name__,
            )
            continue
        parts = []
        for k in sorted(motifs):
            if k in _FABRICATION_NOTE_KEYS:
                continue
            motif = str(motifs[k]).strip()
            if motif:
                parts.append(motif[:-1] if motif.endswith(".") else motif)
        text = "; ".join(parts)
        if text:
            flattened[key] = text + "." if not text.endswith((".", "!", "?")) else text
    return flattened


def build_restitution_acts(
    state: Any, source_id: Optional[str] = None
) -> RestitutionActs:
    """Build a ``RestitutionActs`` from a completed spectacular shared-state.

    Reads the three act strings (populated by the ``act1_framing`` /
    ``act2_narrative`` / ``act3_conclusion`` phases) via ``getattr`` with empty
    defaults — works on a dataclass, a dict, or any object exposing the named
    attributes. Missing/empty acts are left empty so the renderer reports them
    honestly ("acte indisponible"), never fabricated (anti-pendule #1019/#369).

    Degradation motifs persisted by the act state writers (#1608) are read here
    too — see ``_read_act_degraded``. The renderer prints a degradation note for
    a missing act too: when the motif is present it *cedes the floor* to it, so
    the precise reason an act is missing reaches the reader instead of a
    hard-coded (and, for Acte III, false) cause (#1617).
    """

    def _read(key: str) -> str:
        if isinstance(state, dict):
            val = state.get(key, "")
        else:
            val = getattr(state, key, "")
        return val if isinstance(val, str) else ""

    degraded = _read_act_degraded(state)
    foundational_failure = _read_foundational_failure(state)
    if foundational_failure:
        for act_number in (1, 2, 3):
            degraded.setdefault(
                RestitutionActs.act_key(act_number), foundational_failure
            )

    return RestitutionActs(
        act1_framing=_read("act1_framing"),
        act2_narrative=_read("act2_narrative"),
        act3_conclusion=_read("act3_conclusion"),
        source_id=_derive_source_id(state, source_id),
        degraded=degraded,
    )


def render_spectacular_restitution(
    state: Any,
    source_id: Optional[str] = None,
    *,
    output_path: Optional[str] = None,
    include_full_state_json: bool = False,
) -> RenderedReport:
    """Render the readable 3-act restitution report from a spectacular state.

    Assembles ``RestitutionActs`` (from the 3 act strings) + the folded
    dimensional appendix (provenance) and renders via the restitution renderer.
    The gate-lisibilité verdict is returned on ``RenderedReport.verdict`` so the
    caller can branch on readability.

    Args:
        state: a completed ``UnifiedAnalysisState`` (or any object exposing the
            act + spec-§2 keys).
        source_id: opaque corpus id (``doc_A``). If omitted, derived from
            ``state.source_metadata`` (opaque keys only) or the honest fallback.
        output_path: if given, the rendered Markdown is written there (the
            caller picks a gitignored path for real corpora). The renderer never
            writes to disk; this keeps the privacy boundary at the caller.
        include_full_state_json: opt-in full-state appendix (gitignored path
            only). Forwarded to the appendix layer.

    Returns:
        The rendered report (Markdown + gate verdict).
    """
    acts = build_restitution_acts(state, source_id=source_id)
    appendix_state = state_to_appendix_mapping(state)
    report = render_restitution_report(
        acts,
        state=appendix_state,
        include_full_state_json=include_full_state_json,
    )

    if output_path:
        try:
            out_dir = os.path.dirname(os.path.abspath(output_path))
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(report.markdown)
            logger.info(
                "Restitution report written to %s (gate=%s, %d chars)",
                output_path,
                report.verdict.band,
                len(report.markdown),
            )
        except OSError as exc:
            logger.warning(
                "Could not write restitution report to %s (fail-loud): %s",
                output_path,
                exc,
            )

    return report
