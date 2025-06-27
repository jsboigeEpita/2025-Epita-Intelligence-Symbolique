import asyncio
import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from dotenv import load_dotenv
import logging
import json

from argumentation_analysis.orchestration.engine.main_orchestrator import MainOrchestrator, OrchestrationStrategy
from argumentation_analysis.orchestration.engine.config import OrchestrationConfig
from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    kernel = sk.Kernel()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY doit être défini.")

    kernel.add_service(
        OpenAIChatCompletion(service_id="chat_completion", api_key=api_key)
    )

    config = OrchestrationConfig()
    config.strategy = OrchestrationStrategy.HIERARCHICAL_FULL
    
    shared_middleware = MessageMiddleware()
    shared_middleware.register_channel(HierarchicalChannel("hierarchical_channel"))

    strategic_manager = StrategicManager(middleware=shared_middleware)
    tactical_coordinator = TacticalCoordinator(middleware=shared_middleware)
    operational_manager = OperationalManager(middleware=shared_middleware)

    orchestrator = MainOrchestrator(
        config=config,
        kernel=kernel,
        strategic_manager=strategic_manager,
        tactical_coordinator=tactical_coordinator,
        operational_manager=operational_manager
    )

    text_to_analyze = "Les voitures autonomes sont une mauvaise idée car elles vont supprimer des millions d'emplois de chauffeurs et les algorithmes ne pourront jamais prendre de décisions éthiques parfaites en cas d'accident inévitable."
    
    results = await orchestrator.run_analysis(text_input=text_to_analyze)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exécution interrompue par l'utilisateur.")