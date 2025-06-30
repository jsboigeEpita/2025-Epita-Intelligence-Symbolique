# Fichier : argumentation_analysis/agents/concrete_agents/project_manager_agent.py

from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.project_management_plugin import ProjectManagementPlugin
from argumentation_analysis.utils.path_operations import get_prompt_path

class ProjectManagerAgent(BaseAgent):
    """
    Agent spécialisé dans la gestion de projet, capable de créer des plans,
    d'assigner des tâches et de suivre l'état d'avancement.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Project_Manager"):
        """
        Initialise une instance de ProjectManagerAgent.

        Args:
            kernel (Kernel): Le kernel Semantic Kernel à associer à l'agent.
            agent_name (str, optional): Le nom de l'agent.
                Defaults to "Project_Manager".
        """
        prompt_path = get_prompt_path("ProjectManagerAgent")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent chef de projet pour décomposer et organiser le travail."
        )

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent, y compris le plugin de gestion de projet.

        Args:
            llm_service_id (str): L'ID du service LLM à utiliser.
        """
        self._llm_service_id = llm_service_id
        self._kernel.add_plugin(
            ProjectManagementPlugin(),
            plugin_name="ProjectMgmtPlugin"
        )
        return super().setup_agent_components(llm_service_id)

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Décrit les capacités spécifiques de cet agent.

        Returns:
            Dict[str, Any]: Un dictionnaire détaillant les plugins utilisés.
        """
        return {
            "plugins": ["ProjectMgmtPlugin"]
        }

    async def get_response(self, topic: str) -> Any:
        """
        Génère un plan de projet pour un sujet donné.

        Args:
            topic (str): Le sujet ou l'objectif du projet.

        Returns:
            Any: Le résultat de la planification du plugin.
        """
        return await self.invoke_single(topic=topic)

    async def invoke_single(self, topic: str) -> Any:
        """
        Invoque le plugin de gestion de projet pour créer un plan.

        Args:
            topic (str): Le sujet à passer au plugin.

        Returns:
            Any: Le plan généré par le plugin.
        """
        arguments = KernelArguments(
            input=topic,
            tool_choice="required"
        )
        return await self._kernel.invoke_prompt(
            function_name="create_project_plan",
            plugin_name="ProjectMgmtPlugin",
            arguments=arguments
        )