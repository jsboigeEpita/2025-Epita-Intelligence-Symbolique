"""
Orchestration Sherlock-Watson-Moriarty Oracle Enhanced
Système d'orchestration multi-agents avec Oracle authentique

Cleanup B-09 #875:
- RealLLMOrchestrator: removed shim (archived docs/archives/orchestration_legacy/)
- ConversationOrchestrator: archived (superseded by 8-agent SK system)
- LogiqueComplexeOrchestrator: removed stub (mock, zero value)
- CluedoOrchestrator (base 2-agent): archived (superseded by CluedoExtendedOrchestrator)
- Use UnifiedPipeline + CapabilityRegistry for all new orchestration.
- See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
"""

from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from .strategies import CyclicSelectionStrategy, OracleTerminationStrategy

__all__ = [
    "CluedoExtendedOrchestrator",
    "CyclicSelectionStrategy",
    "OracleTerminationStrategy",
]
