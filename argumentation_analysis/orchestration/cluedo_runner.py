# argumentation_analysis/orchestration/cluedo_runner.py
import logging
from typing import Dict, Any

from semantic_kernel import Kernel
from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
)

logger = logging.getLogger(__name__)


async def run_cluedo_oracle_game(
    kernel: Kernel,
    settings: AppSettings,
    initial_question: str = "L'enquête commence. Sherlock, menez l'investigation !",
    max_turns: int = 15,
    max_cycles: int = 5,
    oracle_strategy: str = "balanced",
) -> Dict[str, Any]:
    """
    Interface simplifiée pour exécuter une partie Cluedo avec Oracle.
    """
    orchestrator = CluedoExtendedOrchestrator(
        kernel=kernel,
        settings=settings,
        max_turns=max_turns,
        max_cycles=max_cycles,
        oracle_strategy=oracle_strategy,
    )

    await orchestrator.setup_workflow()
    return await orchestrator.execute_workflow(initial_question)
