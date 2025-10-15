#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Specialized Cluedo Orchestrator Core Module.
"""

import logging
from typing import Dict, Any, Optional
import semantic_kernel as sk

logger = logging.getLogger(__name__)

try:
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
        CluedoExtendedOrchestrator,
    )
    from argumentation_analysis.orchestration.cluedo_runner import (
        run_cluedo_oracle_game as run_cluedo_game,
    )
except ImportError as e:
    logger.warning(f"Cluedo components not available: {e}")
    CluedoExtendedOrchestrator = None
    run_cluedo_game = None


class CluedoOrchestratorWrapper:
    def __init__(self, kernel: Optional[sk.Kernel] = None):
        if not CluedoExtendedOrchestrator:
            raise ImportError("CluedoExtendedOrchestrator is not available.")
        self.orchestrator = CluedoExtendedOrchestrator(kernel=kernel)
        logger.info("[CLUEDO] CluedoOrchestrator initialized.")

    async def run_investigation(self, text: str) -> Dict[str, Any]:
        """
        Runs a Cluedo-style investigation.
        """
        logger.info("[CLUEDO] Running Cluedo investigation...")
        if not run_cluedo_game:
            return {
                "status": "limited",
                "message": "Cluedo investigation unavailable (run_cluedo_game not found).",
            }
        try:
            conversation_history, enquete_state = await run_cluedo_game(
                kernel=self.orchestrator.kernel,
                initial_question=f"Analyze this text as an investigation: {text[:500]}...",
                max_iterations=5,
            )

            return {
                "status": "completed",
                "investigation_type": "cluedo",
                "conversation_history": conversation_history,
                "enquete_state": {
                    "nom_enquete": enquete_state.nom_enquete,
                    "solution_proposee": enquete_state.solution_proposee,
                    "hypotheses": len(enquete_state.hypotheses),
                    "tasks": len(enquete_state.tasks),
                },
            }
        except Exception as e:
            logger.error(f"Error during Cluedo investigation: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
