# Archived: 2026-03-24 — Minimal shim for backward compatibility (#215)
# Original: 69-line AgentGroupChat wrapper, superseded by conversation_orchestrator.py
# Full archive: docs/archives/orchestration_legacy/orchestrator_minimal.py
import warnings


class Orchestrator:
    """Deprecated. Use conversation_orchestrator.ConversationOrchestrator instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Orchestrator is deprecated. Use ConversationOrchestrator or "
            "conversational_orchestrator.run_conversational_analysis() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def run_analysis_async(self, text_content: str):
        raise NotImplementedError(
            "Orchestrator has been archived. Use ConversationOrchestrator or "
            "run_conversational_analysis() for multi-agent analysis."
        )
