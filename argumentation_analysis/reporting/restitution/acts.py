"""The 3-act restitution contract (Epic #1134 / R6).

This module defines the *input* contract that the act generators (R2 Acte I /
R3 Acte II / R4 Acte III) produce and that the renderer (R6) consumes. It is a
deliberately tiny, dependency-free dataclass so the renderer stays decoupled
from *how* each act is generated — R6 tests against deterministic fixtures, and
the real generators slot in later without touching the renderer (file-disjoint
lanes, per the coordinator dispatch).

See ``docs/architecture/RESTITUTION_REPORT_SPEC.md`` (R1, #1135) for the full
blueprint. The three acts are markdown strings; an empty or degraded act is
*reported honestly* by the renderer (fail-loud wording), never silently omitted
(#1019 / #369).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

# The three acts, keyed by position, in narrative order (framing → core → action).
ACT_TITLES: Dict[int, str] = {
    1: "Acte I — Mise en situation",
    2: "Acte II — Récit dialectique",
    3: "Acte III — Conclusion actionnable",
}


@dataclass
class RestitutionActs:
    """The three narrative acts of a readable restitution report.

    Attributes:
        act1_framing: Acte I markdown — mise en situation (before citing the
            text): genre, enjeux, expected fallacy spectrum, game-theoretic
            read. The only act that may *anticipate* (spec §1.1).
        act2_narrative: Acte II markdown — the dialectical narrative cut by
            argumentative movement, weaving quality + fallacies + counter-args
            + formal tenue per the §4 weaving rule (the load-bearing core).
        act3_conclusion: Acte III markdown — gated verdict + appréciations +
            que-faire. Must satisfy the G1–G4 non-triviality gates (#1008 §3)
            before rendering real claims.
        source_id: Opaque corpus identifier (e.g. ``doc_A``). Privacy HARD —
            never a speaker name, title or date. Emitted in the report header.
        degraded: Mapping ``{act_key -> reason}`` for acts whose generator ran
            but produced degraded output. Honest provenance; the renderer
            surfaces these notes verbatim rather than hiding them.

    An act that is an empty string is treated as *missing* (generator did not
    run / not yet wired). The renderer emits explicit "acte indisponible"
    wording for it — distinct from a degraded act, which is emitted with its
    degradation note appended.
    """

    act1_framing: str = ""
    act2_narrative: str = ""
    act3_conclusion: str = ""
    source_id: str = ""
    degraded: Dict[str, str] = field(default_factory=dict)

    # --- accessors -----------------------------------------------------------

    def as_dict(self) -> Dict[int, str]:
        """Return the acts keyed by position (1, 2, 3) in narrative order."""
        return {1: self.act1_framing, 2: self.act2_narrative, 3: self.act3_conclusion}

    @staticmethod
    def act_key(n: int) -> str:
        """Stable internal key for an act position (used by ``degraded``)."""
        return {1: "act1_framing", 2: "act2_narrative", 3: "act3_conclusion"}[n]

    def is_missing(self, n: int) -> bool:
        """True if the act at position ``n`` is absent (empty / whitespace)."""
        return not (self.as_dict()[n] or "").strip()
