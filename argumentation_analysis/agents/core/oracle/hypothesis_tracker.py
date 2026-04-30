"""ATMS Hypothesis Tracker for Sherlock Modern (#359).

Tracks >=3 simultaneous hypotheses via ATMS, updating coherence
as new evidence arrives. Contradicted hypotheses trigger visible
retractions with cascade tracking.

Key API:
- create_hypothesis() — declare a named hypothesis with assumptions
- add_evidence() — feed new evidence, update all hypotheses
- get_active_hypotheses() — list coherent hypotheses
- get_retracted_hypotheses() — list contradicted hypotheses with reasons
- get_investigation_state() — full snapshot for trace/reporting
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, FrozenSet

from argumentation_analysis.services.jtms.atms_core import ATMS, ATMSNode

logger = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    """A tracked hypothesis with ATMS label."""

    id: str
    name: str
    assumptions: List[str]
    description: str = ""
    coherent: bool = True
    retraction_reason: str = ""
    evidence_applied: List[str] = field(default_factory=list)
    derived_nodes: Set[str] = field(default_factory=set)


class HypothesisTracker:
    """Tracks >=3 simultaneous hypotheses via ATMS.

    Each hypothesis is a set of assumptions. The ATMS computes
    minimal environments under which nodes can be derived.
    Contradictions invalidate hypotheses.

    Usage:
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h_trust", "Full trust", ["source_reliable", "method_sound"])
        tracker.create_hypothesis("h_doubt", "Skeptical", ["source_unreliable"])
        tracker.add_evidence("claim_A", supports=["source_reliable"], contradicts=[])
        active = tracker.get_active_hypotheses()
    """

    MIN_HYPOTHESES = 3

    def __init__(self):
        self._atms = ATMS()
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._evidence_log: List[Dict[str, Any]] = []
        self._assumption_to_hypothesis: Dict[str, str] = {}
        self._contradicted_assumptions: Set[str] = set()

    def create_hypothesis(
        self,
        hyp_id: str,
        name: str,
        assumptions: List[str],
        description: str = "",
    ) -> Hypothesis:
        """Create a new hypothesis with ATMS assumptions."""
        # Register assumptions in ATMS
        atms_assumptions = []
        for a in assumptions:
            self._atms.add_assumption(a)
            self._assumption_to_hypothesis[a] = hyp_id
            atms_assumptions.append(a)

        hyp = Hypothesis(
            id=hyp_id,
            name=name,
            assumptions=list(assumptions),
            description=description,
        )
        self._hypotheses[hyp_id] = hyp
        return hyp

    def add_evidence(
        self,
        evidence_id: str,
        supports: Optional[List[str]] = None,
        contradicts: Optional[List[str]] = None,
        derives: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add new evidence and update all hypotheses.

        Args:
            evidence_id: Unique name for this evidence.
            supports: Assumption names this evidence supports.
            contradicts: Assumption names this evidence contradicts.
            derives: Additional nodes this evidence derives.

        Returns:
            Dict with updated hypothesis states.
        """
        supports = supports or []
        contradicts = contradicts or []
        derives = derives or []

        # Register evidence node as assumption (evidence is an input fact,
        # so it always has its own environment)
        self._atms.add_assumption(evidence_id)

        # Add justifications: supported assumptions → evidence node
        if supports:
            self._atms.add_justification(
                in_names=supports,
                out_names=[],
                conclusion_name=evidence_id,
            )

        # Contradictions: evidence contradicts assumptions
        # Track directly since ATMS invalidate_environment clears "⊥" label
        if contradicts:
            self._contradicted_assumptions.update(contradicts)
            for c in contradicts:
                if c not in self._atms.nodes:
                    self._atms.add_node(c, is_assumption=False)

        # Additional derivations
        for d in derives:
            self._atms.add_node(d, is_assumption=False)
            self._atms.add_justification(
                in_names=[evidence_id],
                out_names=[],
                conclusion_name=d,
            )

        # Log evidence
        evidence_record = {
            "evidence_id": evidence_id,
            "supports": supports,
            "contradicts": contradicts,
            "derives": derives,
        }
        self._evidence_log.append(evidence_record)

        # Update all hypotheses
        self._update_hypotheses(evidence_id)

        return {
            "evidence_added": evidence_id,
            "active_count": len(self.get_active_hypotheses()),
            "retracted_count": len(self.get_retracted_hypotheses()),
        }

    def _update_hypotheses(self, new_evidence: str) -> None:
        """Update hypothesis coherence based on contradicted assumptions."""
        for hyp_id, hyp in self._hypotheses.items():
            if not hyp.coherent:
                continue

            hyp.evidence_applied.append(new_evidence)

            contradicted = set(hyp.assumptions) & self._contradicted_assumptions
            if contradicted:
                hyp.coherent = False
                hyp.retraction_reason = (
                    f"Contradicted by evidence '{new_evidence}' — "
                    f"assumptions {contradicted} conflict with evidence"
                )

    def get_active_hypotheses(self) -> List[Hypothesis]:
        """Get all currently coherent hypotheses."""
        return [h for h in self._hypotheses.values() if h.coherent]

    def get_retracted_hypotheses(self) -> List[Hypothesis]:
        """Get all contradicted/retracted hypotheses."""
        return [h for h in self._hypotheses.values() if not h.coherent]

    def get_all_hypotheses(self) -> List[Hypothesis]:
        """Get all hypotheses."""
        return list(self._hypotheses.values())

    def get_investigation_state(self) -> Dict[str, Any]:
        """Full snapshot for investigation trace."""
        return {
            "total_hypotheses": len(self._hypotheses),
            "active": [h.id for h in self.get_active_hypotheses()],
            "retracted": [
                {"id": h.id, "reason": h.retraction_reason}
                for h in self.get_retracted_hypotheses()
            ],
            "evidence_count": len(self._evidence_log),
            "evidence_log": list(self._evidence_log),
        }

    def get_hypothesis_comparison(self) -> str:
        """Human-readable comparison of all hypotheses."""
        lines = ["Hypothesis Comparison:"]
        for hyp in self._hypotheses.values():
            status = "COHERENT" if hyp.coherent else "RETRACTED"
            lines.append(
                f"  [{status}] {hyp.id} ({hyp.name}): "
                f"assumptions={hyp.assumptions}"
            )
            if not hyp.coherent:
                lines.append(f"    Reason: {hyp.retraction_reason}")
        return "\n".join(lines)
