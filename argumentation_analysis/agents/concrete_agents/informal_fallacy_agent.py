# Fichier : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py

import importlib
from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer as IdentificationPlugin
from argumentation_analysis.utils.path_operations import get_prompt_path

class InformalFallacyAgent(BaseAgent):
    """
    Agent spécialisé dans l'identification et l'analyse des sophismes informels
    dans un texte donné.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Fallacy_Analyst", config_name: str = "simple", taxonomy_file_path: Optional[str] = None, **kwargs):
        """
        Initialise une instance de InformalFallacyAgent.

        Args:
            kernel (Kernel): Le kernel Semantic Kernel à associer à l'agent.
            agent_name (str, optional): Le nom de l'agent.
            config_name (str, optional): La configuration des plugins à charger.
            taxonomy_file_path (Optional[str], optional): Chemin vers le fichier de taxonomie.
        """
        prompt_path = get_prompt_path("InformalFallacyAgent")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent expert dans la détection des sophismes informels.",
            **kwargs
        )
        # On passe le chemin de la taxonomie à la méthode de configuration
        self._add_plugins_from_config(config_name, taxonomy_file_path)

    def _add_plugins_from_config(self, config_name: str, taxonomy_file_path: Optional[str] = None):
        """Ajoute les plugins au kernel en fonction de la configuration."""
        
        # Récupérer le service LLM à partir du kernel pour l'injecter dans le workflow
        try:
            # Note: `get_service` est la nouvelle API de Semantic Kernel v1.0+
            llm_service = self._kernel.get_service()
        except Exception:
            # Fallback pour les anciennes versions ou si non trouvé
            llm_service = next(iter(self._kernel.services.values()), None)

        if not llm_service:
            raise ValueError("LLM service not found in the kernel, required for FallacyWorkflowPlugin.")

        if config_name == "simple":
            self._kernel.add_plugin(IdentificationPlugin(), plugin_name="FallacyIdentificationPlugin")
        elif config_name == "explore_only":
            self._kernel.add_plugin(TaxonomyDisplayPlugin(), plugin_name="TaxonomyDisplayPlugin")
        elif config_name == "workflow_only":
            try:
                # Chargement dynamique du plugin
                module = importlib.import_module("plugins.FallacyWorkflow.plugin")
                FallacyWorkflowPlugin = getattr(module, "FallacyWorkflowPlugin")
                self._kernel.add_plugin(FallacyWorkflowPlugin(master_kernel=self._kernel, llm_service=llm_service, taxonomy_file_path=taxonomy_file_path), plugin_name="FallacyWorkflowPlugin")
            except (ModuleNotFoundError, AttributeError) as e:
                self.logger.error(f"Could not dynamically load FallacyWorkflowPlugin: {e}")

            self._kernel.add_plugin(TaxonomyDisplayPlugin(), plugin_name="TaxonomyDisplayPlugin")
        elif config_name == "full":
            self._kernel.add_plugin(IdentificationPlugin(), plugin_name="FallacyIdentificationPlugin")
            
            try:
                # Chargement dynamique du plugin
                module = importlib.import_module("plugins.FallacyWorkflow.plugin")
                FallacyWorkflowPlugin = getattr(module, "FallacyWorkflowPlugin")
                self._kernel.add_plugin(FallacyWorkflowPlugin(master_kernel=self._kernel, llm_service=llm_service, taxonomy_file_path=taxonomy_file_path), plugin_name="FallacyWorkflowPlugin")
            except (ModuleNotFoundError, AttributeError) as e:
                self.logger.error(f"Could not dynamically load FallacyWorkflowPlugin: {e}")

            self._kernel.add_plugin(TaxonomyDisplayPlugin(), plugin_name="TaxonomyDisplayPlugin")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Décrit les capacités spécifiques de cet agent.

        Returns:
            Dict[str, Any]: Un dictionnaire détaillant les plugins utilisés.
        """
        return {
            "plugins": ["FallacyIdPlugin"]
        }

    async def get_response(self, text_to_analyze: str, **kwargs: Any) -> Any:
        # Implémentation du contrat de BaseAgent
        return await self.analyze_text(text_to_analyze, **kwargs)

    async def analyze_text(self, text_to_analyze: str, auto_invoke_kernel_functions: bool = True, **kwargs) -> Any:
        """
        Analyse un texte pour y déceler des sophismes informels.

        Args:
            text_to_analyze (str): Le texte à analyser.
            auto_invoke_kernel_functions (bool): Si True, autorise l'appel d'outils.

        Returns:
            Any: Le résultat de l'analyse du plugin.
        """
        return await self.invoke_single(text_to_analyze=text_to_analyze, auto_invoke_kernel_functions=auto_invoke_kernel_functions)

    async def invoke_single(self, text_to_analyze: str, auto_invoke_kernel_functions: bool = True, **kwargs: Any) -> Any:
        """
        Invoque le plugin d'identification de sophismes.
        Construit un prompt complet en injectant le texte à analyser.
        """
        from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
        from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

        # Construction du prompt final
        final_prompt = f"{self.system_prompt}\n\nTexte à analyser:\n\"\"\"\n{text_to_analyze}\n\"\"\""
        
        arguments = KernelArguments()

        # Configuration pour forcer ou non l'appel de fonction
        if not auto_invoke_kernel_functions:
            arguments.execution_settings = {
                self._llm_service_id: OpenAIPromptExecutionSettings(
                    function_choice_behavior="none"
                )
            }

        return await self._kernel.invoke_prompt(
            prompt=final_prompt,
            arguments=arguments
        )