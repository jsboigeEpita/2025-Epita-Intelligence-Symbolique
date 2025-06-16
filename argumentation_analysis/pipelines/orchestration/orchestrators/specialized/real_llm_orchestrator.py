#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Specialized Real LLM Orchestrator Core Module.
"""

import logging
from typing import Dict, Any, Optional
import semantic_kernel as sk

logger = logging.getLogger(__name__)

try:
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
except ImportError as e:
    logger.warning(f"RealLLMOrchestrator not available: {e}")
    RealLLMOrchestrator = None


class RealLLMOrchestratorWrapper:
    def __init__(self, kernel: Optional[sk.Kernel] = None):
        if not RealLLMOrchestrator or not kernel:
            raise ImportError("RealLLMOrchestrator or SK Kernel is not available.")
        self.orchestrator = RealLLMOrchestrator(mode="real", llm_service=kernel)
        self.initialized = False

    async def initialize(self):
        """Initializes the underlying orchestrator."""
        if hasattr(self.orchestrator, 'initialize'):
             await self.orchestrator.initialize()
        self.initialized = True
        logger.info("[REAL_LLM] RealLLMOrchestrator initialized.")
    
    async def analyze(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs a comprehensive analysis using the real LLM.
        """
        if not self.initialized:
            await self.initialize()

        logger.info("[REAL_LLM] Running comprehensive analysis...")
        if not hasattr(self.orchestrator, 'analyze_text_comprehensive'):
             return {"status": "error", "error": "Method 'analyze_text_comprehensive' not found in orchestrator."}

        try:
            return await self.orchestrator.analyze_text_comprehensive(text, context=context)
        except Exception as e:
            logger.error(f"Error during Real LLM analysis: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}