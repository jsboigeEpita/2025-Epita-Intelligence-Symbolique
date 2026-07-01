"""The restitution report renderer — assembles the 3 acts into one readable
Markdown (Epic #1134 / R6).

Replaces the dimensional dump (``UnifiedReportTemplate._render_markdown``) as the
report a reader meets first. The dump is retained, folded, as an engineering
appendix (provenance) — see :mod:`.appendix`.

Contract:

* **Input**: a :class:`~.acts.RestitutionActs` (3 markdown acts + opaque source
  id) and an optional shared-state mapping for the appendix.
* **Output**: a single Markdown string = header → Acte I/II/III → readability
  verdict → folded appendix.
* **Honesty**: a missing act is *named*, not omitted (fail-loud, #1019/#369).
  The readability gate's verdict is surfaced verbatim in the report for
  transparency — the report does not claim to be readable if the gate disagrees.
* **Privacy**: ``raw_text``/snippet keys are stripped from any appendix state;
  the renderer never writes to disk — the caller picks the (gitignored for real
  corpora) path. Only the opaque ``source_id`` reaches the header.

This renderer is deliberately decoupled from *how* the acts are produced. The
generators R2/R3/R4 slot in by populating a ``RestitutionActs``; the renderer
itself is agnostic (file-disjoint lane, per the coordinator dispatch).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .acts import ACT_TITLES, RestitutionActs
from .appendix import render_appendix
from .factual_consistency_check import check_factual_consistency
from .readability_gate import GateVerdict, ReadabilityGate

# Minimum substantive length for an act body, below which we treat it as
# "present but thin" and flag it (distinct from entirely missing). Generous: an
# honest degraded-act fallback wording is ~80 chars, so a real act should clear
# this comfortably.
_MIN_ACT_CHARS = 120

_MISSING_ACT_WORDING = {
    1: (
        "Acte I indisponible — le générateur de mise en situation n'a pas "
        "produit de cadre (non câblé ou en échec). Le rapport entre directement "
        "dans l'analyse sans filet de cadrage."
    ),
    2: (
        "Acte II indisponible — le récit dialectique n'a pas pu être généré "
        "(cœur narratif absent). Le rapport n'a pas de substance narrative."
    ),
    3: (
        "Acte III indisponible — la conclusion actionnable n'a pas été générée "
        "(portes G1–G4 non évaluées). Le rapport s'arrête sans synthèse."
    ),
}


@dataclass
class RenderedReport:
    """The rendered restitution report + its gate verdict (for the caller)."""

    markdown: str
    verdict: GateVerdict


class RestitutionReportRenderer:
    """Assemble three acts + appendix into one readable Markdown report.

    Parameters mirror the spec's generation protocol (§7, step 5): assemble,
    run the readability gate, emit under an opaque corpus id.
    """

    def __init__(
        self,
        gate: Optional[ReadabilityGate] = None,
        *,
        min_act_chars: int = _MIN_ACT_CHARS,
    ):
        self.gate = gate or ReadabilityGate()
        self.min_act_chars = min_act_chars

    def render(
        self,
        acts: RestitutionActs,
        *,
        state: Optional[Mapping[str, Any]] = None,
        include_full_state_json: bool = False,
    ) -> RenderedReport:
        """Render the full restitution report.

        Args:
            acts: the three narrative acts + opaque source id.
            state: optional shared-state mapping for the folded appendix.
            include_full_state_json: opt-in full-state appendix (gitignored path
                only). Forwarded to :func:`~.appendix.render_appendix`.
        """
        body_parts: list[str] = []
        thin_notes: list[str] = []

        for n in (1, 2, 3):
            title = ACT_TITLES[n]
            text = (acts.as_dict()[n] or "").strip()

            body_parts.append(f"## {title}")
            body_parts.append("")

            if acts.is_missing(n):
                # fail-loud: name the missing act, never omit
                body_parts.append(f"_{_MISSING_ACT_WORDING[n]}_")
                body_parts.append("")
                continue

            body_parts.append(text)
            body_parts.append("")

            # degradation provenance — surface honestly, don't hide
            key = RestitutionActs.act_key(n)
            if key in acts.degraded:
                body_parts.append(f"> ⚠️ **Acte dégradé** — {acts.degraded[key]}")
                body_parts.append("")

            # thin act — present but suspiciously short (likely a stub)
            if len(text) < self.min_act_chars:
                thin_notes.append(
                    f"{title} est anormalement court ({len(text)} caractères) — "
                    f"sortie probablement stub ou dégradée."
                )

        body = "\n".join(body_parts).strip()

        # run the gate on the acts (presence + weaving + non-dump)
        verdict = self.gate.check(acts)
        if thin_notes:
            verdict = verdict.merge(GateVerdict(band="WARN", reasons=thin_notes))

        # factual cross-check of rendered prose vs appendix (#1316, opt A):
        # detect prose theatre — a formal authority cited for an inconsistency
        # the appendix data does not support. Composes with the structural gate
        # as defense-in-depth with the #1297 prompt guardrail. Skipped honestly
        # (PASS) when no state was provided (no source of truth to check against).
        verdict = verdict.merge(check_factual_consistency(body, state))

        # assemble the final document
        doc = self._assemble(acts, body, verdict, state, include_full_state_json)
        return RenderedReport(markdown=doc, verdict=verdict)

    # -- assembly -------------------------------------------------------------

    def _assemble(
        self,
        acts: RestitutionActs,
        body: str,
        verdict: GateVerdict,
        state: Optional[Mapping[str, Any]],
        include_full_state_json: bool,
    ) -> str:
        source = (acts.source_id or "corpus_anonyme").strip()
        parts: list[str] = []

        # header — opaque id only, privacy HARD
        parts.append(f"# Rapport de restitution — {source}")
        parts.append("")
        parts.append(
            "Récit en trois actes (mise en situation → analyse narrative → "
            "conclusion actionnable). Les cadres formels et informels (Tweety, "
            "Dung/ASPIC, taxonomie, vertus) sont les *preuves* citées en appui "
            "du récit, jamais une énumération (spec §4)."
        )
        parts.append("")

        # the narrative body
        parts.append(body)
        parts.append("")

        # the gate verdict — surfaced for transparency (not hidden)
        parts.append(self._render_verdict_block(verdict))
        parts.append("")

        # the folded dimensional appendix (provenance)
        parts.append(
            render_appendix(state, include_full_state_json=include_full_state_json)
        )

        return "\n".join(parts).rstrip() + "\n"

    @staticmethod
    def _render_verdict_block(verdict: GateVerdict) -> str:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(verdict.band, "•")
        lines = [
            "---",
            "",
            f"## {icon} Gate lisibilité — {verdict.band}",
            "",
        ]
        if verdict.reasons:
            lines.append("Contrôles structurels (règle de tissage, spec §4) :")
            lines.append("")
            for r in verdict.reasons:
                lines.append(f"- {r}")
        else:
            lines.append(
                "Tous les contrôles structurels passent : 3 actes présents et "
                "non-triviaux, aucune référence de cadre nue (énumération)."
            )
        lines.append("")
        lines.append("_Verdict honnête reporté par le gate — non truqué (#1019)._")
        return "\n".join(lines)


def render_restitution_report(
    acts: RestitutionActs,
    *,
    state: Optional[Mapping[str, Any]] = None,
    include_full_state_json: bool = False,
    gate: Optional[ReadabilityGate] = None,
) -> RenderedReport:
    """Shorthand entry point: render a restitution report in one call.

    This is the public face of the package for callers that already hold a
    :class:`RestitutionActs` (e.g. the spectacular pipeline, once the act
    generators R2/R3/R4 populate it). Returns the rendered markdown *and* the
    gate verdict so the caller can branch on readability.
    """
    return RestitutionReportRenderer(gate=gate).render(
        acts, state=state, include_full_state_json=include_full_state_json
    )
