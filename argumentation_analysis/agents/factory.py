# Fichier : argumentation_analysis/agents/agent_factory.py

from typing import List, Optional, Type
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunction
from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
import importlib

# Les imports directs sont conservés là où il n'y a pas de risque de cycle
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer,
)
from .plugins.project_management_plugin import ProjectManagementPlugin
from .plugins.taxonomy_display_plugin import TaxonomyDisplayPlugin
from .utils.tracer import TracedAgent
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
    SherlockEnqueteAgent,
)
from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
    WatsonLogicAssistant,
)

# L'Enum AgentType et les classes d'agents de base sont nécessaires pour les signatures
from .agents import (
    AgentType,
    FallacyAgentBase,
    MethodicalAuditorAgent,
    ParallelExplorerAgent,
    ResearchAssistantAgent,
)
from .concrete_agents.informal_fallacy_agent import InformalFallacyAgent


class AgentFactory:
    """
    Usine pour la création et la configuration centralisée des agents.
    """

    def __init__(self, kernel: Kernel, llm_service_id: str):
        self.kernel = kernel
        self.llm_service_id = llm_service_id

    def create_informal_fallacy_agent(
        self,
        config_name: str = "simple",
        trace_log_path: Optional[str] = None,
        taxonomy_file_path: Optional[str] = None,
    ) -> Agent:
        # La logique de création des plugins est déléguée à l'agent lui-même.
        # La factory se contente de passer la configuration.
        # Cela élimine la logique dupliquée et les incohérences.
        agent_to_create = InformalFallacyAgent(
            kernel=self.kernel,
            config_name=config_name,
            taxonomy_file_path=taxonomy_file_path,  # Ajout du passage de l'argument manquant
            llm_service_id=self.llm_service_id,
        )

        if trace_log_path:
            return TracedAgent(
                agent_to_wrap=agent_to_create, trace_log_path=trace_log_path
            )
        return agent_to_create

    def create_agent(self, agent_type: AgentType, **kwargs) -> FallacyAgentBase:
        # Cette méthode est maintenant le point d'entrée principal.
        # Elle peut utiliser create_informal_fallacy_agent si nécessaire.
        if agent_type == AgentType.INFORMAL_FALLACY:
            # Fait le pont avec la nouvelle méthode de création détaillée
            # On passe les kwargs pour permettre plus de flexibilité (comme 'config_name')
            return self.create_informal_fallacy_agent(**kwargs)

        # --- Importation locale pour briser le cycle d'importation ---
        from .sherlock_jtms_agent import SherlockJTMSAgent

        agent_map = {
            AgentType.METHODICAL_AUDITOR: MethodicalAuditorAgent,
            AgentType.PARALLEL_EXPLORER: ParallelExplorerAgent,
            AgentType.RESEARCH_ASSISTANT: ResearchAssistantAgent,
            AgentType.SHERLOCK_JTMS: SherlockJTMSAgent,
        }
        agent_class = agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(
                f"Unknown agent type for this creation method: {agent_type}"
            )

        # Assure que llm_service_id est passé s'il n'est pas dans kwargs
        if "llm_service_id" not in kwargs:
            kwargs["llm_service_id"] = self.llm_service_id

        return agent_class(kernel=self.kernel, **kwargs)

    def create_project_manager_agent(
        self, trace_log_path: Optional[str] = None
    ) -> Agent:
        plugins = [ProjectManagementPlugin()]
        with open(
            "argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt",
            "r",
        ) as f:
            prompt = f.read()
        llm_service = self.kernel.get_service(self.llm_service_id)
        agent = ChatCompletionAgent(
            kernel=self.kernel,
            service=llm_service,
            name="Project_Manager",
            instructions=prompt,
            plugins=plugins,
        )
        if trace_log_path:
            return TracedAgent(agent_to_wrap=agent, trace_log_path=trace_log_path)
        return agent

    def create_sherlock_agent(
        self, agent_name: str = "Sherlock", trace_log_path: Optional[str] = None
    ) -> Agent:
        return self._create_agent(
            agent_class=SherlockEnqueteAgent,
            agent_name=agent_name,
            service_id=self.llm_service_id,
            trace_log_path=trace_log_path,
        )

    def create_watson_agent(
        self,
        agent_name: str = "Watson",
        trace_log_path: Optional[str] = None,
        constants: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> Agent:
        return self._create_agent(
            agent_class=WatsonLogicAssistant,
            agent_name=agent_name,
            service_id=self.llm_service_id,
            trace_log_path=trace_log_path,
            constants=constants,
            system_prompt=system_prompt,
        )

    def create_counter_argument_agent(
        self,
        agent_name: str = "CounterArgumentAgent",
        trace_log_path: Optional[str] = None,
    ) -> Agent:
        """Create a counter-argument generation agent."""
        from argumentation_analysis.agents.core.counter_argument.counter_agent import (
            CounterArgumentAgent,
        )

        return self._create_agent(
            agent_class=CounterArgumentAgent,
            agent_name=agent_name,
            trace_log_path=trace_log_path,
        )

    def create_debate_agent(
        self,
        agent_name: str = "DebateAgent",
        personality: str = "The Scholar",
        position: str = "for",
        trace_log_path: Optional[str] = None,
    ) -> Agent:
        """Create a debate agent with specified personality and position."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        return self._create_agent(
            agent_class=DebateAgent,
            agent_name=agent_name,
            personality=personality,
            position=position,
            trace_log_path=trace_log_path,
        )

    def _create_agent(
        self,
        agent_class: Type[Agent],
        trace_log_path: Optional[str] = None,
        enable_auto_function_calling: bool = False,
        **kwargs,
    ) -> Agent:
        """Create an agent instance with optional auto function calling.

        Args:
            agent_class: The agent class to instantiate.
            trace_log_path: Optional path for execution tracing.
            enable_auto_function_calling: If True, configure the agent's kernel
                execution settings so it can auto-invoke @kernel_function plugins
                during AgentGroupChat conversations. Required for conversational mode.
            **kwargs: Additional agent-specific parameters.
        """
        if "service_id" not in kwargs:
            kwargs["service_id"] = self.llm_service_id

        agent = agent_class(kernel=self.kernel, **kwargs)

        if enable_auto_function_calling:
            self._enable_function_choice_behavior(agent)

        if trace_log_path:
            return TracedAgent(agent_to_wrap=agent, trace_log_path=trace_log_path)
        return agent

    def _enable_function_choice_behavior(self, agent: Agent) -> None:
        """Enable FunctionChoiceBehavior.Auto() on an agent.

        In SK 1.40, function_choice_behavior is set directly on the
        ChatCompletionAgent instance. This allows the agent to auto-invoke
        @kernel_function plugins as tool calls during AgentGroupChat
        conversations, rather than only producing text.
        """
        try:
            fcb = FunctionChoiceBehavior.Auto(
                auto_invoke_kernel_functions=True,
                maximum_auto_invoke_attempts=5,
            )
            # SK 1.40: function_choice_behavior is a direct attribute on ChatCompletionAgent
            if hasattr(agent, "function_choice_behavior"):
                object.__setattr__(agent, "function_choice_behavior", fcb)
            else:
                # Fallback: store for manual use by orchestrator
                agent._function_choice_behavior = fcb
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Could not enable FunctionChoiceBehavior on {getattr(agent, 'name', '?')}: {e}"
            )
