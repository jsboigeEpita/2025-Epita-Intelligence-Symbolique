"""
Governance agents and methods — multi-agent governance simulation.

Provides 5 voting rules + 2 distributed-consensus protocols (Byzantine, Raft
are *protocols*, not scrutins — see ``governance_methods.py`` for the
distinction), plus 8 social-choice functions (``social_choice.py``: approval,
STV, Copeland, Kemeny-Young + safe, Schulze, Condorcet winner, pairwise
matrix). 3 agent archetypes (base, BDI, reactive) with Q-learning, coalition
formation with Shapley values, conflict resolution, manipulability
analysis, and distributed consensus.

The wording "7 voting methods" was the category error #1981. Total surface:
**5 scrutins + 2 protocoles + 8 fonctions de choix social = 15**.

Integration from student project 2.1.6_multiagent_governance_prototype (GitHub #43).
"""

from .governance_agent import Agent, BDIAgent, ReactiveAgent, AgentFactory
from .governance_methods import GOVERNANCE_METHODS
from .simulation import simulate_governance, manipulability_analysis
from .conflict_resolution import detect_conflicts, resolve_conflict
from .metrics import consensus_rate, fairness_index, satisfaction, summarize_results

__all__ = [
    "Agent",
    "BDIAgent",
    "ReactiveAgent",
    "AgentFactory",
    "GOVERNANCE_METHODS",
    "simulate_governance",
    "manipulability_analysis",
    "detect_conflicts",
    "resolve_conflict",
    "consensus_rate",
    "fairness_index",
    "satisfaction",
    "summarize_results",
]

# #1842: no register_with_capability_registry here. The governance
# capability table lives on the production surface
# (registry_setup.setup_registry); this module's former second table was
# only ever called by tests and shared no capability string with it.
