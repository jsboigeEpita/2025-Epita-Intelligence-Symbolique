"""
Governance agents and methods — multi-agent governance simulation.

Provides 7 governance/voting methods, 3 agent archetypes (base, BDI,
reactive) with Q-learning, coalition formation with Shapley values,
conflict resolution, manipulability analysis, and distributed consensus.

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


def register_with_capability_registry(registry):
    """Register governance capabilities with the Lego registry."""
    registry.register_plugin(
        name="governance",
        plugin_class=type("GovernanceMethods", (), {"methods": GOVERNANCE_METHODS}),
        capabilities=[
            "collective_decision_making",
            "voting_methods",
            "conflict_resolution",
            "consensus_metrics",
        ],
        metadata={
            "description": (
                "Provides 7 governance/voting methods, conflict detection "
                "and resolution, and consensus metrics for multi-agent "
                "collective decision-making."
            ),
        },
    )
