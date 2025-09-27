# Fichier : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py

import importlib
from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer as IdentificationPlugin
from argumentation_analysis.agents.core.informal.informal_definitions import INFORMAL_AGENT_INSTRUCTIONS

class InformalFallacyAgent(BaseAgent):
    """
    Agent spécialisé dans l'identification et l'analyse des sophismes informels
    dans un texte donné.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Fallacy_Analyst", config_name: str = "simple", taxonomy_file_path: Optional[str] = None, **kwargs):
        """
        Initialise une instance de InformalFallacyAgent.
        """
        prompt = INFORMAL_AGENT_INSTRUCTIONS
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent expert dans la détection des sophismes informels.",
            **kwargs
        )
        self._chat_function = None
        self._add_plugins_from_config(config_name, taxonomy_file_path)

    def _add_plugins_from_config(self, config_name: str, taxonomy_file_path: Optional[str] = None):
        """Ajoute les plugins au kernel en fonction de la configuration."""
        try:
            llm_service = self._kernel.get_service()
        except Exception:
            llm_service = next(iter(self._kernel.services.values()), None)

        if not llm_service:
            raise ValueError("LLM service not found in the kernel.")

        if config_name in ["simple", "full"]:
            self._kernel.add_plugin(IdentificationPlugin(), plugin_name="FallacyIdentificationPlugin")
        if config_name in ["explore_only", "workflow_only", "full"]:
            self._kernel.add_plugin(TaxonomyDisplayPlugin(), plugin_name="TaxonomyDisplayPlugin")
        if config_name in ["workflow_only", "full"]:
             try:
                module = importlib.import_module("plugins.FallacyWorkflow.plugin")
                FallacyWorkflowPlugin = getattr(module, "FallacyWorkflowPlugin")
                self._kernel.add_plugin(FallacyWorkflowPlugin(master_kernel=self._kernel, llm_service=llm_service, taxonomy_file_path=taxonomy_file_path), plugin_name="FallacyWorkflowPlugin")
             except (ModuleNotFoundError, AttributeError) as e:
                self.logger.error(f"Could not dynamically load FallacyWorkflowPlugin: {e}")

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {"plugins": ["FallacyIdPlugin", "TaxonomyDisplayPlugin", "FallacyWorkflowPlugin"]}

    async def get_response(self, text_to_analyze: str, **kwargs: Any) -> Any:
        return await self.analyze_text(text_to_analyze, **kwargs)

    async def analyze_text(self, text_to_analyze: str, auto_invoke_kernel_functions: bool = True, **kwargs) -> Any:
        # history doit être passé en kwarg
        history = kwargs.get("history", ChatHistory())
        return await self.invoke_single(text_to_analyze=text_to_analyze, history=history, auto_invoke_kernel_functions=auto_invoke_kernel_functions)
        
    async def invoke_single(self, text_to_analyze: str, history: Optional[ChatHistory] = None, auto_invoke_kernel_functions: bool = True, **kwargs: Any) -> Any:
        """
        Invoque l'agent avec une instruction claire de "tool-calling".
        """
        if history is None:
            history = ChatHistory()
            
        final_prompt = f"{self.system_prompt}\n\nTexte à analyser:\n\"\"\"\n{text_to_analyze}\n\"\"\""
        
        arguments = KernelArguments(history=history)

        execution_settings = OpenAIChatPromptExecutionSettings(
            tool_choice="auto" if auto_invoke_kernel_functions else "none"
        )
        
        return await self._kernel.invoke_prompt(
            prompt=final_prompt,
            arguments=arguments,
            settings=execution_settings # ceci devrait être passé comme settings ou dans les arguments
        )