# Fichier : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py

from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.identification_plugin import IdentificationPlugin
from argumentation_analysis.utils.path_operations import get_prompt_path

class InformalFallacyAgent(BaseAgent):
    """
    Agent spécialisé dans l'identification et l'analyse des sophismes informels
    dans un texte donné.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Fallacy_Analyst"):
        """
        Initialise une instance de InformalFallacyAgent.

        Args:
            kernel (Kernel): Le kernel Semantic Kernel à associer à l'agent.
            agent_name (str, optional): Le nom de l'agent.
                Defaults to "Fallacy_Analyst".
        """
        prompt_path = get_prompt_path("InformalFallacyAgent")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent expert dans la détection des sophismes informels."
        )

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants de l'agent, y compris le plugin de détection
        de sophismes.

        Args:
            llm_service_id (str): L'ID du service LLM à utiliser.
        """
        self._llm_service_id = llm_service_id
        self._kernel.add_plugin(
            FallacyIdentificationPlugin(),
            plugin_name="FallacyIdPlugin"
        )
        return super().setup_agent_components(llm_service_id)

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Décrit les capacités spécifiques de cet agent.

        Returns:
            Dict[str, Any]: Un dictionnaire détaillant les plugins utilisés.
        """
        return {
            "plugins": ["FallacyIdPlugin"]
        }

    async def get_response(self, text_to_analyze: str) -> Any:
        """
        Analyse un texte pour y déceler des sophismes informels.

        Args:
            text_to_analyze (str): Le texte à analyser.

        Returns:
            Any: Le résultat de l'analyse du plugin.
        """
        return await self.invoke_single(text_to_analyze=text_to_analyze)

    async def invoke_single(self, text_to_analyze: str) -> Any:
        """
        Invoque le plugin d'identification de sophismes.

        Args:
            text_to_analyze (str): Le texte à passer au plugin.

        Returns:
            Any: Le résultat de l'exécution du plugin.
        """
        arguments = KernelArguments(
            input=text_to_analyze,
            tool_choice="required"
        )
        return await self._kernel.invoke_prompt(
            function_name="identify_fallacies",
            plugin_name="FallacyIdPlugin",
            arguments=arguments
        )