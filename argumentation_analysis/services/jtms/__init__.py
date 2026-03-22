"""
Truth Maintenance Systems — JTMS and ATMS core modules.

Integrated from student project 1.4.1-JTMS (Zebic, Leguere, Shan, Breant).

JTMS (Justification-based): Tracks a single truth value per belief, propagates
    via justification rules. Good for "what is true now?" queries.

ATMS (Assumption-based): Tracks all assumption environments under which each
    node can be derived. Good for "under which assumptions is X derivable?" queries.

Classes:
    Belief, Justification, JTMS — JTMS components
    ATMSNode, ATMSJustification, ATMS — ATMS components
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

__all__ = [
    "Belief",
    "Justification",
    "JTMS",
    "ATMSNode",
    "ATMSJustification",
    "ATMS",
]
