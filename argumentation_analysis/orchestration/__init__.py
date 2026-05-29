"""
Orchestration Sherlock-Watson-Moriarty Oracle Enhanced
Système d'orchestration multi-agents avec Oracle authentique

DEPRECATION NOTICE (#215):
- RealLLMOrchestrator is deprecated. Use UnifiedPipeline or ConversationOrchestrator instead.
- See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
"""

from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from .conversation_orchestrator import ConversationOrchestrator
# `RealLLMOrchestrator` is an archived shim (deprecated 2026-03-24, #215). It
# is still importable via its explicit path
# `argumentation_analysis.orchestration.real_llm_orchestrator` for back-compat
# (all current callers use that direct path — see commit history). Auto-importing
# it here would fire DeprecationWarning on every `argumentation_analysis.orchestration`
# import. Use `UnifiedPipeline` or `ConversationOrchestrator` instead.
from .logique_complexe_orchestrator import LogiqueComplexeOrchestrator
from .strategies import CyclicSelectionStrategy, OracleTerminationStrategy

__all__ = [
    "CluedoExtendedOrchestrator",
    "ConversationOrchestrator",
    "LogiqueComplexeOrchestrator",
    "CyclicSelectionStrategy",
    "OracleTerminationStrategy",
]
