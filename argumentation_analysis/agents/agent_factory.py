# Fichier : argumentation_analysis/agents/agent_factory.py

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

from .plugins.fallacy_identification_plugin import FallacyIdentificationPlugin
from .plugins.project_management_plugin import ProjectManagementPlugin

class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Utilise ChatCompletionAgent comme base pour tous les agents.
    """

    def __init__(self, kernel: Kernel, llm_service_id: str):
        """Initialise la factory avec les dépendances partagées."""
        self._kernel = kernel # Ce kernel de base sert pour les settings, mais chaque agent aura le sien.
        self._llm_service_id = llm_service_id

    def create_informal_fallacy_agent(self) -> Agent:
        """Crée et configure un agent d'analyse des sophismes."""
        agent_kernel = Kernel()
        agent_kernel.add_plugin(FallacyIdentificationPlugin(), plugin_name="FallacyIdPlugin")
        
        with open("argumentation_analysis/agents/prompts/InformalFallacyAgent/skprompt.txt", "r") as f:
            prompt = f.read()

        execution_settings = OpenAIChatPromptExecutionSettings(
            service_id=self._llm_service_id,
            tool_choice="required",
        )
        # Lie les settings au kernel de l'agent
        agent_kernel.add_service(
            service=self._kernel.get_service(self._llm_service_id)
        )

        return ChatCompletionAgent(
            kernel=agent_kernel,
            name="Fallacy_Analyst",
            instructions=prompt
        )

    def create_project_manager_agent(self) -> Agent:
        """Crée et configure l'agent chef de projet."""
        agent_kernel = Kernel()
        agent_kernel.add_plugin(ProjectManagementPlugin(), plugin_name="ProjectMgmtPlugin")

        with open("argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt", "r") as f:
            prompt = f.read()

        execution_settings = OpenAIChatPromptExecutionSettings(
            service_id=self._llm_service_id,
            tool_choice="required",
        )
        # Lie les settings au kernel de l'agent
        agent_kernel.add_service(
            service=self._kernel.get_service(self._llm_service_id)
        )

        return ChatCompletionAgent(
            kernel=agent_kernel,
            name="Project_Manager",
            instructions=prompt
        )