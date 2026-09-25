# argumentation_analysis/orchestration/cluedo_runner.py
import asyncio
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


async def main():
    """Point d'entrée pour exécuter le workflow 3-agents de manière autonome."""
    kernel = Kernel()
    # NOTE: Configurez ici votre service LLM, par exemple:
    # from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    # kernel.add_service(AzureChatCompletion(service_id="chat_completion", ...))

    if not kernel.services:
        logger.warning(
            "Aucun service n'est configuré dans le kernel. Le runner ne peut pas s'exécuter."
        )
        print(
            "\n❌ ERREUR: Aucun service LLM n'est configuré. Veuillez éditer 'cluedo_runner.py' pour ajouter un service au kernel."
        )
        return

    try:
        result = await run_cluedo_oracle_game(
            kernel=kernel, oracle_strategy="balanced", max_cycles=5
        )

        print("\n" + "=" * 60)
        print("RÉSULTAT WORKFLOW 3-AGENTS CLUEDO ORACLE")
        print("=" * 60)

        print(f"\n🎯 SUCCÈS: {result['solution_analysis']['success']}")
        print(
            f"📊 TOURS: {result['oracle_statistics']['agent_interactions']['total_turns']}"
        )
        print(
            f"🔮 REQUÊTES ORACLE: {result['oracle_statistics']['workflow_metrics']['oracle_interactions']}"
        )
        print(
            f"💎 CARTES RÉVÉLÉES: {result['oracle_statistics']['workflow_metrics']['cards_revealed']}"
        )
        print(f"⏱️  TEMPS: {result['workflow_info']['execution_time_seconds']:.2f}s")

        if result["solution_analysis"]["success"]:
            print(f"[OK] Solution: {result['final_state']['final_solution']}")
        else:
            print(f"❌ Solution proposée: {result['final_state']['final_solution']}")
            print(f"🎯 Solution correcte: {result['final_state']['correct_solution']}")

        print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"❌ Erreur durant l'exécution: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
