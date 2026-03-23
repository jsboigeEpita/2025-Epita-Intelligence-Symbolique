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

# L'Enum AgentType et la classe de base sont nécessaires pour les signatures
from .agents import (
    AgentType,
    FallacyAgentBase,
)
from .concrete_agents.informal_fallacy_agent import InformalFallacyAgent


import logging

_factory_logger = logging.getLogger("AgentFactory")

# ---------------------------------------------------------------------------
# Plugin-per-agent mapping (#221, Epic #208-E)
#
# Each agent speciality gets ONLY its relevant plugins + StateManager
# (the shared communication medium). This prevents agents from having
# access to tools outside their expertise, improving tool-call accuracy.
# ---------------------------------------------------------------------------

AGENT_PLUGIN_MAP = {
    "project_manager": [],  # PM only gets StateManager
    "informal_fallacy": ["french_fallacy"],
    "extract": [],  # Extractor uses StateManager only
    "formal_logic": ["tweety_logic"],
    "quality": ["quality_scoring"],
    "debate": [],  # Debate agent has its own internal plugin
    "counter_argument": [],  # Counter-arg agent has its own internal plugin
    "governance": ["governance"],
    "sherlock": [],  # Sherlock uses its own investigation tools
    "watson": ["tweety_logic"],
}

# Registry of plugin name → (module_path, class_name) for lazy loading
_PLUGIN_REGISTRY = {
    "french_fallacy": (
        "argumentation_analysis.plugins.french_fallacy_plugin",
        "FrenchFallacyPlugin",
    ),
    "tweety_logic": (
        "argumentation_analysis.plugins.tweety_logic_plugin",
        "TweetyLogicPlugin",
    ),
    "quality_scoring": (
        "argumentation_analysis.plugins.quality_scoring_plugin",
        "QualityScoringPlugin",
    ),
    "governance": (
        "argumentation_analysis.plugins.governance_plugin",
        "GovernancePlugin",
    ),
    "state_manager": (
        "argumentation_analysis.core.state_manager_plugin",
        "StateManagerPlugin",
    ),
}


def load_plugins_for_agent(kernel: Kernel, agent_speciality: str, state=None) -> list:
    """Load only the plugins relevant to an agent's speciality onto its kernel.

    Always loads StateManagerPlugin (if state is provided) as the shared
    communication medium.  Then loads speciality-specific plugins from
    AGENT_PLUGIN_MAP.

    Args:
        kernel: The Semantic Kernel instance.
        agent_speciality: Key into AGENT_PLUGIN_MAP.
        state: Optional RhetoricalAnalysisState for StateManagerPlugin.

    Returns:
        List of loaded plugin names.
    """
    loaded = []

    # Always load StateManager if state is available
    if state is not None:
        try:
            mod = importlib.import_module(
                "argumentation_analysis.core.state_manager_plugin"
            )
            plugin_cls = getattr(mod, "StateManagerPlugin")
            kernel.add_plugin(plugin_cls(state=state), plugin_name="state_manager")
            loaded.append("state_manager")
        except Exception as e:
            _factory_logger.debug("StateManagerPlugin not loaded: %s", e)

    # Load speciality plugins
    plugin_names = AGENT_PLUGIN_MAP.get(agent_speciality, [])
    for plugin_name in plugin_names:
        entry = _PLUGIN_REGISTRY.get(plugin_name)
        if entry is None:
            _factory_logger.warning("Unknown plugin '%s' in registry", plugin_name)
            continue
        module_path, class_name = entry
        try:
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, class_name)
            instance = plugin_cls()
            kernel.add_plugin(instance, plugin_name=plugin_name)
            loaded.append(plugin_name)
        except Exception as e:
            _factory_logger.debug(
                "Plugin '%s' not loaded for '%s': %s", plugin_name, agent_speciality, e
            )

    _factory_logger.info("Plugins for '%s': %s", agent_speciality, loaded or ["(none)"])
    return loaded


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
