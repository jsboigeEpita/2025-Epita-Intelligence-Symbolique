#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Specialized Complex Logic Orchestrator Core Module.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
except ImportError as e:
    logger.warning(f"LogiqueComplexeOrchestrator not available: {e}")
    LogiqueComplexeOrchestrator = None


class LogicOrchestratorWrapper:
    def __init__(self):
        if not LogiqueComplexeOrchestrator:
            raise ImportError("LogiqueComplexeOrchestrator is not available.")
        self.orchestrator = LogiqueComplexeOrchestrator()
        logger.info("[LOGIC_COMPLEX] LogiqueComplexeOrchestrator initialized.")

    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Runs a complex logic analysis.
        """
        logger.info("[LOGIC_COMPLEX] Running complex logic analysis...")
        if not hasattr(self.orchestrator, 'analyze_complex_logic'):
            return {"status": "error", "error": "Method 'analyze_complex_logic' not found in orchestrator."}

        try:
            results = await self.orchestrator.analyze_complex_logic(text)
            return {"status": "completed", "logic_analysis": results}
        except Exception as e:
            logger.error(f"Error during complex logic analysis: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}