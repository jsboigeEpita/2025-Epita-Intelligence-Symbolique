"""
Orchestration Sherlock-Watson-Moriarty Oracle Enhanced
Système d'orchestration multi-agents avec Oracle authentique
"""

from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from .conversation_orchestrator import ConversationOrchestrator
from .real_llm_orchestrator import RealLLMOrchestrator
from .logique_complexe_orchestrator import LogiqueComplexeOrchestrator
from .strategies import CyclicSelectionStrategy, OracleTerminationStrategy

__all__ = [
    "CluedoExtendedOrchestrator",
    "ConversationOrchestrator",
    "RealLLMOrchestrator",
    "LogiqueComplexeOrchestrator",
    "CyclicSelectionStrategy",
    "OracleTerminationStrategy",
]
