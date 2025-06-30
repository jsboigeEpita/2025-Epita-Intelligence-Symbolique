# Fichier : argumentation_analysis/agents/agent_factory.py

from typing import List, Optional
from semantic_kernel import Kernel
from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

from .plugins.fallacy_identification_plugin import FallacyIdentificationPlugin
from .plugins.project_management_plugin import ProjectManagementPlugin
from .plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from .plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin
from .utils.tracer import TracedAgent


class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    Utilise ChatCompletionAgent comme base pour tous les agents.
    """

    def __init__(self, kernel: Kernel, llm_service_id: str):
        """Initialise la factory avec les dépendances partagées."""
        self.kernel = kernel
        self.llm_service_id = llm_service_id

    def create_informal_fallacy_agent(
        self,
        config_name: str = "simple",
        trace_log_path: Optional[str] = None,
        fallacy_plugin: Optional[FallacyIdentificationPlugin] = None,
    ) -> Agent:
        """
        Crée différentes versions de l'InformalFallacyAgent.
        """
        plugins = []
        
        base_identification_plugin = fallacy_plugin or FallacyIdentificationPlugin()

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

        llm_service = self.kernel.get_service(self.llm_service_id)
        
        function_choice_behavior = None
        if config_name in ["simple", "full", "workflow_only"]:
            function_choice_behavior = FunctionChoiceBehavior.Required(
                auto_invoke=True,
                filters={"included_functions": ["FallacyIdentificationPlugin-identify_fallacies"]},
            )

        agent_to_create = ChatCompletionAgent(
            kernel=self.kernel,
            service=llm_service,
            name="informal_fallacy_agent",
            instructions=prompt,
            plugins=plugins,
            function_choice_behavior=function_choice_behavior,
        )

        if trace_log_path:
            # On encapsule l'agent créé dans le wrapper de trace.
            # Le wrapper est maintenant un simple proxy et n'a pas besoin du kernel/service.
            final_agent = TracedAgent(
                agent_to_wrap=agent_to_create,
                trace_log_path=trace_log_path
            )
        else:
            final_agent = agent_to_create
            
        return final_agent

    def create_project_manager_agent(
        self, trace_log_path: Optional[str] = None
    ) -> Agent:
        """Crée et configure l'agent chef de projet."""
        plugins = [ProjectManagementPlugin()]

        with open("argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt", "r") as f:
            prompt = f.read()

        # Lie les settings au kernel de l'agent
        llm_service = self.kernel.get_service(self.llm_service_id)
        
        agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=llm_service,
            name="Project_Manager",
            instructions=prompt,
            plugins=plugins
        )

        if trace_log_path:
            return TracedAgent(
                agent_to_wrap=agent,
                trace_log_path=trace_log_path
            )
        return agent
