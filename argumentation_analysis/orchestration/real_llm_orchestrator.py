# Archived: 2026-03-24 — Minimal shim for backward compatibility (#215)
# Original: 668-line orchestrator with analysis_map routing, superseded by
#           unified_pipeline.py and conversation_orchestrator.py
# Full archive: docs/archives/orchestration_legacy/real_llm_orchestrator.py
"""
Shim module for RealLLMOrchestrator backward compatibility.

DEPRECATED: Use these alternatives instead:
- For pipeline orchestration: argumentation_analysis.orchestration.unified_pipeline.UnifiedPipeline
- For conversational analysis: argumentation_analysis.orchestration.conversation_orchestrator.ConversationOrchestrator
- For analysis requests: argumentation_analysis.core.shared_state.UnifiedAnalysisState
"""

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class LLMAnalysisRequest:
    """DEPRECATED: Structure for LLM analysis requests.

    Use UnifiedAnalysisState or direct agent invocation instead.
    """

    text: str
    analysis_type: str
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    timeout: int = 30


@dataclass
class LLMAnalysisResult:
    """DEPRECATED: Structure for LLM analysis results.

    Use UnifiedAnalysisState or analysis plugins instead.
    """

    request_id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class RealLLMOrchestrator:
    """DEPRECATED: Use UnifiedPipeline or ConversationOrchestrator instead.

    This class was a 668-line orchestrator managing multiple analysis types
    through an analysis_map routing system. It has been superseded by:

    - UnifiedPipeline: Modern pipeline with phase-based orchestration
    - ConversationOrchestrator: Multi-agent conversational orchestration
    - AnalysisToolsPlugin: Direct plugin-based analysis

    See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "RealLLMOrchestrator is deprecated and will be removed in a future version. "
            "Use UnifiedPipeline for pipeline orchestration or ConversationOrchestrator "
            "for conversational multi-agent analysis. "
            "See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def analyze_text(self, *args, **kwargs):
        raise NotImplementedError(
            "RealLLMOrchestrator has been archived. Use:\n"
            "  - UnifiedPipeline.run_unified_analysis() for pipeline orchestration\n"
            "  - run_conversational_analysis() for multi-agent dialogue\n"
            "See docs/architecture/ORCHESTRATION_MODES.md for details."
        )

    async def initialize(self, *args, **kwargs):
        raise NotImplementedError(
            "RealLLMOrchestrator has been archived. Initialize UnifiedPipeline instead."
        )


# Alias for backward compatibility - imports ConversationLogger from conversation_orchestrator
# This maintains the original export pattern without code duplication
def _get_conversation_logger():
    """Lazy import to avoid circular dependencies."""
    from .conversation_orchestrator import ConversationLogger

    return ConversationLogger


# Create the alias class dynamically for import compatibility
class RealConversationLogger:
    """DEPRECATED: Alias for ConversationLogger from conversation_orchestrator.

    Use: from argumentation_analysis.orchestration.conversation_orchestrator import ConversationLogger
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "RealConversationLogger is deprecated. Import ConversationLogger directly "
            "from argumentation_analysis.orchestration.conversation_orchestrator",
            DeprecationWarning,
            stacklevel=2,
        )
        # Delegate to actual ConversationLogger
        ConversationLogger = _get_conversation_logger()
        self._logger = ConversationLogger(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._logger, name)


# Export list for backward compatibility
__all__ = [
    "RealLLMOrchestrator",
    "LLMAnalysisRequest",
    "LLMAnalysisResult",
    "RealConversationLogger",
]
