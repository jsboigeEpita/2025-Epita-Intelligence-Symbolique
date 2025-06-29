# Fichier : argumentation_analysis/agents/agent_factory.py

from semantic_kernel import Kernel
from .abc.abstract_agent import AbstractAgent
from .concrete_agents.informal_fallacy_agent import InformalFallacyAgent
# L'import de ProjectManagerAgent sera ajouté dans le WO-04.
# from .concrete_agents import ProjectManagerAgent

class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Permet le découplage entre l'orchestrateur et les implémentations concrètes.
    """

    def __init__(self, kernel: Kernel, llm_service_id: str):
        """Initialise la factory avec les dépendances partagées."""
        self._kernel = kernel
        self._llm_service_id = llm_service_id

    def create_informal_fallacy_agent(self) -> AbstractAgent:
        """Crée et configure un agent d'analyse des sophismes."""
        agent = InformalFallacyAgent(kernel=self._kernel.clone(), name="Fallacy_Analyst")
        agent.setup_agent_components(llm_service_id=self._llm_service_id)
        return agent

    def create_project_manager_agent(self) -> AbstractAgent:
        """Crée et configure l'agent chef de projet."""
        # L'implémentation complète sera faite dans le WO-04.
        raise NotImplementedError("Implémentation de ProjectManagerAgent à venir dans WO-04")