#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Archived: 2026-03-24 — Minimal shim for backward compatibility (#215)
# Original: 60-line wrapper around RealLLMOrchestrator
# Full archive: docs/archives/orchestration_legacy/real_llm_orchestrator_wrapper.py
"""
Shim module for RealLLMOrchestratorWrapper backward compatibility.

DEPRECATED: Use these alternatives instead:
- For pipeline orchestration: argumentation_analysis.orchestration.unified_pipeline.UnifiedPipeline
- For conversational analysis: argumentation_analysis.orchestration.conversation_orchestrator.ConversationOrchestrator
"""

import warnings


class RealLLMOrchestratorWrapper:
    """DEPRECATED: Use UnifiedPipeline or ConversationOrchestrator instead.

    This class was a wrapper around RealLLMOrchestrator which has been archived.
    See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.
    """

    def __init__(self, kernel=None):
        warnings.warn(
            "RealLLMOrchestratorWrapper is deprecated and will be removed in a future version. "
            "Use UnifiedPipeline for pipeline orchestration or ConversationOrchestrator "
            "for conversational multi-agent analysis. "
            "See docs/architecture/ORCHESTRATION_MODES.md for migration guidance.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def initialize(self):
        raise NotImplementedError(
            "RealLLMOrchestratorWrapper has been archived. Use:\n"
            "  - UnifiedPipeline.run_unified_analysis() for pipeline orchestration\n"
            "  - run_conversational_analysis() for multi-agent dialogue\n"
            "See docs/architecture/ORCHESTRATION_MODES.md for details."
        )

    async def analyze(self, text, context=None):
        raise NotImplementedError(
            "RealLLMOrchestratorWrapper has been archived. Use:\n"
            "  - UnifiedPipeline.run_unified_analysis() for pipeline orchestration\n"
            "  - run_conversational_analysis() for multi-agent dialogue\n"
            "See docs/architecture/ORCHESTRATION_MODES.md for details."
        )


__all__ = ["RealLLMOrchestratorWrapper"]
