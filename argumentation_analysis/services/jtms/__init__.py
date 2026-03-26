"""
Truth Maintenance Systems — JTMS, ATMS, Extended Beliefs, and Conflict Resolution.

Integrated from student project 1.4.1-JTMS (Zebic, Leguere, Shan, Breant).
Extended with agent-aware beliefs and multi-strategy conflict resolution (#214).

JTMS (Justification-based): Tracks a single truth value per belief, propagates
    via justification rules. Good for "what is true now?" queries.

ATMS (Assumption-based): Tracks all assumption environments under which each
    node can be derived. Good for "under which assumptions is X derivable?" queries.

ExtendedBelief: Belief wrapper with agent source, confidence, and audit trail.
JTMSSession: Per-agent session with extended beliefs and contradiction detection.
ConflictResolver: 5-strategy conflict resolution for multi-agent scenarios.
"""

from argumentation_analysis.services.jtms.jtms_core import (
    Belief,
    Justification,
    JTMS,
)
from argumentation_analysis.services.jtms.atms_core import (
    ATMSNode,
    ATMSJustification,
    ATMS,
)
from argumentation_analysis.services.jtms.extended_belief import (
    ExtendedBelief,
    JTMSSession,
)
from argumentation_analysis.services.jtms.conflict_resolution import (
    ConflictResolver,
)

__all__ = [
    "Belief",
    "Justification",
    "JTMS",
    "ATMSNode",
    "ATMSJustification",
    "ATMS",
    "ExtendedBelief",
    "JTMSSession",
    "ConflictResolver",
]
