"""
Orchestration Sherlock-Watson-Moriarty Oracle Enhanced
Système d'orchestration multi-agents avec Oracle authentique

DEPRECATION NOTICE (#215):
- RealLLMOrchestrator is deprecated. Use UnifiedPipeline or ConversationOrchestrator instead.
- See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
"""

from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from .conversation_orchestrator import ConversationOrchestrator
from .strategies import CyclicSelectionStrategy, OracleTerminationStrategy
# LogiqueComplexeOrchestrator removed (#885) — stub, superseded by FOL/Tweety via Registry
# RealLLMOrchestrator removed (#885) — shim, superseded by UnifiedPipeline

__all__ = [
    "CluedoExtendedOrchestrator",
    "ConversationOrchestrator",
    "CyclicSelectionStrategy",
    "OracleTerminationStrategy",
]
