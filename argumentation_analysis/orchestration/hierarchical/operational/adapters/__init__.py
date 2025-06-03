"""
Package contenant les adaptateurs pour les agents opérationnels.

Ce package fournit des adaptateurs qui permettent aux agents existants
de fonctionner comme des agents opérationnels dans l'architecture hiérarchique.
"""

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter

__all__ = [
    'ExtractAgentAdapter',
    'InformalAgentAdapter',
    'PLAgentAdapter'
]