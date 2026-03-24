"""
Orchestration Sherlock-Watson-Moriarty Oracle Enhanced
Système d'orchestration multi-agents avec Oracle authentique

DEPRECATION NOTICE (#215):
- RealLLMOrchestrator is deprecated. Use UnifiedPipeline or ConversationOrchestrator instead.
- See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
"""

from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from .conversation_orchestrator import ConversationOrchestrator
from .real_llm_orchestrator import RealLLMOrchestrator  # Deprecated shim
from .logique_complexe_orchestrator import LogiqueComplexeOrchestrator
from .strategies import CyclicSelectionStrategy, OracleTerminationStrategy

__all__ = [
    "CluedoExtendedOrchestrator",
    "ConversationOrchestrator",
    "RealLLMOrchestrator",  # Deprecated - kept for backward compatibility
    "LogiqueComplexeOrchestrator",
    "CyclicSelectionStrategy",
    "OracleTerminationStrategy",
]
