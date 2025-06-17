#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Specialized Conversation Orchestrator Core Module.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
except ImportError as e:
    logger.warning(f"ConversationOrchestrator not available: {e}")
    ConversationOrchestrator = None


class ConversationOrchestratorWrapper:
    def __init__(self, mode: str = "advanced"):
        if not ConversationOrchestrator:
            raise ImportError("ConversationOrchestrator is not available.")
        self.orchestrator = ConversationOrchestrator(mode=mode)
        logger.info("[CONVERSATION] ConversationOrchestrator initialized.")

    async def run_conversation(self, text: str) -> Dict[str, Any]:
        """
        Runs a conversational analysis.
        """
        logger.info("[CONVERSATION] Running conversational analysis...")
        if not hasattr(self.orchestrator, 'run_conversation'):
             return {"status": "error", "error": "Method 'run_conversation' not found in orchestrator."}
        try:
            return await self.orchestrator.run_conversation(text)
        except Exception as e:
            logger.error(f"Error during conversation analysis: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}