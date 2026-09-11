# Fichier : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py

import importlib
from typing import Any, Dict, List, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.taxonomy_display_plugin import (
    TaxonomyDisplayPlugin,
)
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer as IdentificationPlugin,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    INFORMAL_AGENT_INSTRUCTIONS,
)

# #2121 — the configs this agent understands, named once. The plugin gates below
# are the only consumers; an unrecognised name is refused rather than falling
# through all of them. Before this, ``analysis_service`` (web API) passed the
# invented ``"default_with_plugins"``, matched no gate, and served a plugin-less
# agent while logging that it had been "configured successfully" — a #1019
# false-green the caller had no way to see from the outside.
INFORMAL_AGENT_CONFIGS = ("simple", "explore_only", "workflow_only", "full")


class InformalFallacyAgent(BaseAgent):
    """
    Agent spécialisé dans l'identification et l'analyse des sophismes informels
    dans un texte donné.
    """

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "Fallacy_Analyst",
        config_name: str = "simple",
        taxonomy_file_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialise une instance de InformalFallacyAgent.
        """
        prompt = INFORMAL_AGENT_INSTRUCTIONS
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent expert dans la détection des sophismes informels.",
            **kwargs,
        )
        self._chat_function = None
        self._configured_plugins: List[str] = []
        self._add_plugins_from_config(config_name, taxonomy_file_path)

    def _add_plugins_from_config(
        self, config_name: str, taxonomy_file_path: Optional[str] = None
    ):
        """Ajoute les plugins au kernel en fonction de la configuration.

        Raises:
            ValueError: if ``config_name`` is not one of
                :data:`INFORMAL_AGENT_CONFIGS`. An unknown name used to mount
                no plugin at all (see the module-level note above).
        """
        if config_name not in INFORMAL_AGENT_CONFIGS:
            raise ValueError(
                f"Unknown config_name {config_name!r}; expected one of "
                f"{', '.join(INFORMAL_AGENT_CONFIGS)}."
            )

        try:
            llm_service = self.kernel.get_service()
        except Exception:
            llm_service = next(iter(self.kernel.services.values()), None)

        if not llm_service:
            raise ValueError("LLM service not found in the kernel.")

        if config_name in ["simple", "full"]:
            self.kernel.add_plugin(
                IdentificationPlugin(), plugin_name="FallacyIdentificationPlugin"
            )
            self._configured_plugins.append("FallacyIdentificationPlugin")
        if config_name in ["explore_only", "workflow_only", "full"]:
            self.kernel.add_plugin(
                TaxonomyDisplayPlugin(), plugin_name="TaxonomyDisplayPlugin"
            )
            self._configured_plugins.append("TaxonomyDisplayPlugin")
        if config_name in ["workflow_only", "full"]:
            try:
                module = importlib.import_module(
                    "argumentation_analysis.plugins.fallacy_workflow_plugin"
                )
                FallacyWorkflowPlugin = getattr(module, "FallacyWorkflowPlugin")
                self.kernel.add_plugin(
                    FallacyWorkflowPlugin(
                        master_kernel=self.kernel,
                        llm_service=llm_service,
                        taxonomy_file_path=taxonomy_file_path,
                    ),
                    plugin_name="FallacyWorkflowPlugin",
                )
                self._configured_plugins.append("FallacyWorkflowPlugin")
            except (ModuleNotFoundError, AttributeError) as e:
                self.logger.error(
                    f"Could not dynamically load FallacyWorkflowPlugin: {e}"
                )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """The plugins this agent actually mounted.

        Reported from the mount record rather than a hand-written list: the
        previous constant named ``FallacyIdPlugin``, which is not the name
        under which the plugin is registered (``FallacyIdentificationPlugin``),
        so it advertised a capability the kernel never held (#2121).
        """
        return {"plugins": list(self._configured_plugins)}

    async def get_response(self, text_to_analyze: str, **kwargs: Any) -> Any:
        return await self.analyze_text(text_to_analyze, **kwargs)

    async def analyze_text(
        self, text_to_analyze: str, auto_invoke_kernel_functions: bool = True, **kwargs
    ) -> Any:
        # history doit être passé en kwarg
        history = kwargs.get("history", ChatHistory())
        return await self.invoke_single(
            text_to_analyze=text_to_analyze,
            history=history,
            auto_invoke_kernel_functions=auto_invoke_kernel_functions,
        )

    async def invoke_single(
        self,
        text_to_analyze: str,
        history: Optional[ChatHistory] = None,
        auto_invoke_kernel_functions: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Invoque l'agent avec une instruction claire de "tool-calling".
        """
        if history is None:
            history = ChatHistory()

        final_prompt = (
            f'{self.system_prompt}\n\nTexte à analyser:\n"""\n{text_to_analyze}\n"""'
        )

        # Convert ChatHistory to string to avoid SK 1.37 encoding error
        # (ChatHistory objects don't support automatic encoding as template variables)
        history_str = str(history) if history else ""
        arguments = KernelArguments(history=history_str)

        execution_settings = OpenAIChatPromptExecutionSettings(
            tool_choice="auto" if auto_invoke_kernel_functions else "none"
        )

        return await self.kernel.invoke_prompt(
            prompt=final_prompt,
            arguments=arguments,
            settings=execution_settings,
        )
