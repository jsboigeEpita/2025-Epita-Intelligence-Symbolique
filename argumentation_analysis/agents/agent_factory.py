# Fichier : argumentation_analysis/agents/agent_factory.py

from typing import List
from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

from .plugins.fallacy_identification_plugin import FallacyIdentificationPlugin
from .plugins.project_management_plugin import ProjectManagementPlugin
from .plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from .plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin


class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Utilise ChatCompletionAgent comme base pour tous les agents.
    """

    def __init__(self, kernel: Kernel, llm_service_id: str):
        """Initialise la factory avec les dépendances partagées."""
        self.kernel = kernel
        self.llm_service_id = llm_service_id

    def create_informal_fallacy_agent(self, config_name: str = "simple") -> ChatCompletionAgent:
        """
        Crée différentes versions de l'InformalFallacyAgent basées sur une configuration.

        Configurations disponibles:
        - 'simple': Uniquement l'identification de base.
        - 'explore_only': Exploration simple uniquement.
        - 'workflow_only': Exploration parallèle uniquement.
        - 'full': Toutes les capacités.
        """
        plugins = []
        
        # Charger les plugins de base nécessaires
        base_identification_plugin = FallacyIdentificationPlugin()

        if config_name == "simple":
            plugins.append(base_identification_plugin)
        
        elif config_name == "explore_only":
            plugins.append(TaxonomyDisplayPlugin())
            
        elif config_name == "workflow_only":
            workflow_plugin = FallacyWorkflowPlugin(self.kernel)
            plugins.append(workflow_plugin)
            plugins.append(TaxonomyDisplayPlugin())

        elif config_name == "full":
            workflow_plugin = FallacyWorkflowPlugin(self.kernel)
            plugins.append(base_identification_plugin)
            plugins.append(workflow_plugin)
            plugins.append(TaxonomyDisplayPlugin())

        else:
            raise ValueError(f"Configuration d'agent inconnue : {config_name}")

        with open("argumentation_analysis/agents/prompts/InformalFallacyAgent/skprompt.txt", "r") as f:
            prompt = f.read()

        return ChatCompletionAgent(
            kernel=self.kernel,
            instructions=prompt,
            plugins=plugins
        )

    def create_project_manager_agent(self) -> Agent:
        """Crée et configure l'agent chef de projet."""
        agent_kernel = Kernel()
        agent_kernel.add_plugin(ProjectManagementPlugin(), plugin_name="ProjectMgmtPlugin")

        with open("argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt", "r") as f:
            prompt = f.read()

        # Lie les settings au kernel de l'agent
        agent_kernel.add_service(
            service=self.kernel.get_service(self.llm_service_id)
        )

        return ChatCompletionAgent(
            kernel=agent_kernel,
            name="Project_Manager",
            instructions=prompt
        )