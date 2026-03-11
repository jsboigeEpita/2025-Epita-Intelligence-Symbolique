"""
JTMS (Justification-based Truth Maintenance System) core module.

Integrated from student project 1.4.1-JTMS.
Provides non-monotonic reasoning via belief networks with justifications.

Classes:
    Belief — A named proposition with truth value and justification support
    Justification — A rule relating premises (in/out lists) to a conclusion
    JTMS — The truth maintenance system managing beliefs and propagation
"""

from argumentation_analysis.services.jtms.jtms_core import (
    Belief,
    Justification,
    JTMS,
)

__all__ = ["Belief", "Justification", "JTMS"]
