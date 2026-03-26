"""
Extended Belief — rich belief wrapper with agent metadata and traceability.

Extracted from agents/jtms_agent_base.py for canonical access via services/jtms/.
Used by agents (Sherlock, Watson) and by _invoke_jtms for enriched pipeline output.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from argumentation_analysis.services.jtms.jtms_core import JTMS, Belief, Justification

logger = logging.getLogger("ExtendedBelief")


class ExtendedBelief:
    """Belief wrapper with agent source, confidence, and modification history."""

    def __init__(
        self,
        name: str,
        agent_source: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
    ):
        self.name = name
        self.agent_source = agent_source
        self.context = context or {}
        self.confidence = confidence
        self.creation_timestamp = datetime.now()
        self.modification_history: List[Dict[str, Any]] = []

        # Wrapping du Belief JTMS original
        self._jtms_belief = Belief(name)

    @property
    def valid(self):
        return self._jtms_belief.valid

    @property
    def non_monotonic(self):
        return self._jtms_belief.non_monotonic

    @property
    def justifications(self):
        return self._jtms_belief.justifications

    @property
    def implications(self):
        return self._jtms_belief.implications

    def add_justification(self, justification):
        """Add justification with traceability."""
        self._jtms_belief.add_justification(justification)
        self.record_modification(
            "add_justification",
            {
                "justification_id": id(justification),
                "premises": [str(b) for b in justification.in_list],
                "negatives": [str(b) for b in justification.out_list],
            },
        )

    def record_modification(self, action: str, details: Dict):
        """Record modification for audit trail."""
        self.modification_history.append(
            {
                "action": action,
                "timestamp": datetime.now(),
                "details": details,
                "agent": self.agent_source,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "agent_source": self.agent_source,
            "context": self.context,
            "confidence": self.confidence,
            "valid": self.valid,
            "non_monotonic": self.non_monotonic,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "modification_count": len(self.modification_history),
        }


class JTMSSession:
    """JTMS session with per-agent state management and extended beliefs."""

    def __init__(self, session_id: str, owner_agent: str, strict_mode: bool = False):
        self.session_id = session_id
        self.owner_agent = owner_agent
        self.created_at = datetime.now()
        self.last_modified = datetime.now()

        self.jtms = JTMS(strict=strict_mode)
        self.extended_beliefs: Dict[str, ExtendedBelief] = {}

        self.total_inferences = 0
        self.consistency_checks = 0
        self.last_consistency_status = True
        self.version = 1
        self.checkpoints: List[Dict] = []

    def add_belief(
        self,
        name: str,
        agent_source: str,
        context: Optional[Dict] = None,
        confidence: float = 0.0,
    ) -> ExtendedBelief:
        """Add or update an extended belief."""
        if name in self.extended_beliefs:
            existing = self.extended_beliefs[name]
            existing.record_modification(
                "updated_by_agent",
                {
                    "new_agent": agent_source,
                    "new_context": context,
                    "new_confidence": confidence,
                },
            )
            if context:
                existing.context.update(context)
            existing.confidence = max(existing.confidence, confidence)
        else:
            extended_belief = ExtendedBelief(name, agent_source, context, confidence)
            self.extended_beliefs[name] = extended_belief
            self.jtms.add_belief(name)

        self.last_modified = datetime.now()
        return self.extended_beliefs[name]

    def add_justification(
        self,
        in_list: List[str],
        out_list: List[str],
        conclusion: str,
        agent_source: str = "unknown",
    ):
        """Add justification with agent traceability and contradiction detection."""
        all_beliefs_in_rule = list(set(in_list + out_list + [conclusion]))
        for belief_name in all_beliefs_in_rule:
            if belief_name not in self.extended_beliefs:
                self.add_belief(belief_name, agent_source, {"auto_created": True})

        self.jtms.add_justification(in_list, out_list, conclusion)

        # Contradiction detection for rules with OUT-list
        if out_list:
            contradiction_belief = "_CONTRADICTION_"
            if contradiction_belief not in self.extended_beliefs:
                self.add_belief(contradiction_belief, "system", {"auto_created": True})
            for out_item in out_list:
                conflict_in_list = list(set(in_list + [out_item]))
                self.jtms.add_justification(conflict_in_list, [], contradiction_belief)

        if conclusion in self.extended_beliefs:
            self.extended_beliefs[conclusion].record_modification(
                "justification_added",
                {
                    "in_list": in_list,
                    "out_list": out_list,
                    "agent_source": agent_source,
                },
            )

        self.total_inferences += 1
        self.last_modified = datetime.now()

    def set_fact(self, name: str, is_true: bool = True):
        """Declare a belief as ground truth."""
        if name not in self.jtms.beliefs:
            self.add_belief(name, "system_fact", {"description": "Auto-added as a fact"})
        self.jtms.set_belief_validity(name, is_true)
        self.last_modified = datetime.now()

    def check_consistency(self) -> Dict[str, Any]:
        """Check session consistency, return conflicts and non-monotonic beliefs."""
        self.consistency_checks += 1
        conflicts = []
        non_monotonic = []

        contradiction = "_CONTRADICTION_"
        if contradiction in self.jtms.beliefs:
            if self.jtms.beliefs[contradiction].valid:
                conflicts.append({
                    "type": "contradiction_detected",
                    "belief": contradiction,
                })

        for name, belief in self.jtms.beliefs.items():
            if belief.non_monotonic:
                non_monotonic.append(name)

        is_consistent = len(conflicts) == 0
        self.last_consistency_status = is_consistent
        self.last_modified = datetime.now()

        return {
            "is_consistent": is_consistent,
            "conflicts": conflicts,
            "non_monotonic_beliefs": non_monotonic,
        }

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary statistics for this session."""
        return {
            "session_id": self.session_id,
            "owner_agent": self.owner_agent,
            "belief_count": len(self.extended_beliefs),
            "total_inferences": self.total_inferences,
            "consistency_checks": self.consistency_checks,
            "last_consistent": self.last_consistency_status,
            "version": self.version,
        }
