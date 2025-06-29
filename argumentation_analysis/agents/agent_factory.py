# Fichier : argumentation_analysis/agents/agent_factory.py

from semantic_kernel import Kernel
from .abc.abstract_agent import AbstractAgent
# Les imports des agents concrets seront ajoutés dans les prochains WOs.
# from .concrete_agents import InformalFallacyAgent, ProjectManagerAgent

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
        # L'implémentation complète sera faite dans le WO-03.
        raise NotImplementedError("Implémentation de InformalFallacyAgent à venir dans WO-03")

    def create_project_manager_agent(self) -> AbstractAgent:
        """Crée et configure l'agent chef de projet."""
        # L'implémentation complète sera faite dans le WO-04.
        raise NotImplementedError("Implémentation de ProjectManagerAgent à venir dans WO-04")