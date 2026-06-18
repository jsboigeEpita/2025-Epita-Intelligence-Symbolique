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

Provenance note: the act invoke-callables return a ``degraded`` dict per act,
but the state-writers store only the narrative string (the structured
``degraded`` is not carried on state). This is acceptable — the act narratives
themselves already carry the honest degradation wording inline (the plugins
append caveats / §4 self-check notes into the text), so the report stays honest
without a state-schema change. Surfacing structured per-act ``degraded`` would
require touching ``state_writers.py`` / ``shared_state.py`` (out of this lane's
scope; the narrative carries the honesty).

Privacy HARD: ``source_id`` must be opaque (``doc_A``, never a speaker name /
title / date). The appendix layer strips ``raw_text`` defensively regardless.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

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


def build_restitution_acts(state: Any, source_id: Optional[str] = None) -> RestitutionActs:
    """Build a ``RestitutionActs`` from a completed spectacular shared-state.

    Reads the three act strings (populated by the ``act1_framing`` /
    ``act2_narrative`` / ``act3_conclusion`` phases) via ``getattr`` with empty
    defaults — works on a dataclass, a dict, or any object exposing the named
    attributes. Missing/empty acts are left empty so the renderer reports them
    honestly ("acte indisponible"), never fabricated (anti-pendule #1019/#369).
    """
    def _read(key: str) -> str:
        if isinstance(state, dict):
            val = state.get(key, "")
        else:
            val = getattr(state, key, "")
        return val if isinstance(val, str) else ""

    return RestitutionActs(
        act1_framing=_read("act1_framing"),
        act2_narrative=_read("act2_narrative"),
        act3_conclusion=_read("act3_conclusion"),
        source_id=_derive_source_id(state, source_id),
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
