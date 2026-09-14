from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional, Type, Union
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

# `toulmin` is deliberately absent from every speciality (#2145). Its only
# @kernel_function raises NotImplementedError, so mounting it offers a live
# agent a tool that cannot do anything but raise — and waste a turn. The
# analyzer that mounted it on its own kernel no longer does either: its prompt
# asks the finetuned model for the Toulmin JSON directly
# (`test_analyzer_does_not_promise_a_raising_tool_2145`). The plugin, its
# registry entry, its raise-pinning test and its benchmark case all stay: what
# was withdrawn is a *promise*, not a file.
# `test_toulmin_mount_follows_its_body_2145` couples the speciality map to the
# body, so implementing the body turns the guard red and forces the re-mount
# decision instead of leaving a comment to rot.
AGENT_SPECIALITY_MAP = {
    "project_manager": ["narrative_synthesis"],
    "informal_fallacy": ["french_fallacy", "fallacy_workflow"],
    "extract": ["text_to_kb"],
    "formal_logic": [
        "tweety_logic",
        "nl_to_logic",
        "coordinated_logic",
        "atms",
        "ranking",
        "aspic",
        "belief_revision",
        "logic_agents",
        "tweety_interpretation",
        "text_to_kb",
        "kb_to_tweety",
    ],
    "quality": ["quality_scoring"],
    "debate": ["debate"],
    "counter_argument": ["counter_argument"],
    "governance": ["governance"],
    "sherlock": [],  # Sherlock uses its own investigation tools
    "watson": ["tweety_logic", "logic_agents"],
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
    "nl_to_logic": (
        "argumentation_analysis.plugins.nl_to_logic_plugin",
        "NLToLogicPlugin",
    ),
    "quality_scoring": (
        "argumentation_analysis.plugins.quality_scoring_plugin",
        "QualityScoringPlugin",
    ),
    "governance": (
        "argumentation_analysis.plugins.governance_plugin",
        "GovernancePlugin",
    ),
    "debate": (
        "argumentation_analysis.agents.core.debate.debate_agent",
        "DebatePlugin",
    ),
    "counter_argument": (
        "argumentation_analysis.agents.core.counter_argument.counter_agent",
        "CounterArgumentPlugin",
    ),
    "fallacy_workflow": (
        "argumentation_analysis.plugins.fallacy_workflow_plugin",
        "FallacyWorkflowPlugin",
    ),
    "atms": (
        "argumentation_analysis.plugins.atms_plugin",
        "ATMSPlugin",
    ),
    "state_manager": (
        "argumentation_analysis.core.state_manager_plugin",
        "StateManagerPlugin",
    ),
    # Plugins with @kernel_function exposing Tweety handlers (#468)
    "ranking": (
        "argumentation_analysis.plugins.ranking_plugin",
        "RankingPlugin",
    ),
    "aspic": (
        "argumentation_analysis.plugins.aspic_plugin",
        "ASPICPlugin",
    ),
    "belief_revision": (
        "argumentation_analysis.plugins.belief_revision_plugin",
        "BeliefRevisionPlugin",
    ),
    # PL/FOL/Modal logic operations (#477)
    "logic_agents": (
        "argumentation_analysis.plugins.logic_agent_plugin",
        "LogicAgentPlugin",
    ),
    # Tweety result interpretation (#476)
    "tweety_interpretation": (
        "argumentation_analysis.plugins.tweety_result_interpretation_plugin",
        "TweetyResultInterpretationPlugin",
    ),
    # NL → KB extraction with iterative descent (#474)
    "text_to_kb": (
        "argumentation_analysis.plugins.text_to_kb_plugin",
        "TextToKBPlugin",
    ),
    # KB → Tweety formula translation with retry (#475)
    "kb_to_tweety": (
        "argumentation_analysis.plugins.kb_to_tweety_plugin",
        "KBToTweetyPlugin",
    ),
    "narrative_synthesis": (
        "argumentation_analysis.plugins.narrative_synthesis_plugin",
        "NarrativeSynthesisPlugin",
    ),
    "toulmin": (
        "argumentation_analysis.plugins.toulmin_plugin",
        "ToulminPlugin",
    ),
    # 2-pass coordinated logic (PL atoms + FOL signature) (#560, #561)
    "coordinated_logic": (
        "argumentation_analysis.plugins.coordinated_logic_plugin",
        "CoordinatedLogicPlugin",
    ),
    # Complex plugins (need constructor args — loaded via special handling)
    # "exploration": needs TaxonomyNavigator — loaded by FallacyWorkflowPlugin
    # "jtms": needs JTMSService — loaded by orchestration layer
    # See docs/architecture/PATTERN_NESTED_SK_KERNELS.md for master/slave kernel pattern
}


def _plugin_function_names(plugin: Any) -> list[str]:
    """The @kernel_function names a plugin instance exposes, as SK sees them.

    Read through a throwaway kernel rather than by introspecting decorators:
    SK is the authority on what an agent will actually be offered, so ask it.

    A plugin SK refuses to register exposes nothing *enumerable*, and said so
    out loud — a detector that answers "no functions" when it could not read
    is indistinguishable from one that measured an unambiguous plugin, which
    is the failure mode this whole file is about. It must never raise either:
    a diagnostic may not break the mount it observes.
    """
    probe = Kernel()
    try:
        probe.add_plugin(plugin, plugin_name="_collision_probe")
    except Exception as e:
        _factory_logger.warning(
            "Could not enumerate the functions of %s (%s) — any collision it "
            "has goes unreported for this mount",
            type(plugin).__name__,
            e,
        )
        return []
    return sorted(probe.plugins["_collision_probe"].functions.keys())


def _function_collisions(
    owned: Mapping[str, Iterable[str]],
) -> list[tuple[str, list[str]]]:
    """Homonym function names among a mapping of plugin name → its functions.

    Pure on purpose: the guard enumerates the collision surface through this
    rather than by reading log lines.
    """
    owners: dict[str, list[str]] = {}
    for plugin_name, fn_names in owned.items():
        for fn_name in fn_names:
            owners.setdefault(fn_name, []).append(plugin_name)
    return [
        (fn_name, sorted(names))
        for fn_name, names in sorted(owners.items())
        if len(names) > 1
    ]


def _report_function_collisions(
    agent_speciality: str, mounted: list[tuple[str, Any]]
) -> list[tuple[str, list[str]]]:
    """Report homonym @kernel_function names among the plugins an agent gets.

    A collision is not an error — SK addresses a function as
    ``<plugin>-<function>``, so both survive — it is an *ambiguity*: the agent
    is offered two tools with the same leaf name and nothing marks the
    canonical one. The four pairs in this package (#2145) are the measured
    case; the defect was that nothing said so out loud.

    Returns the collisions found, so a guard can enumerate them instead of
    trusting a log line nobody reads.
    """
    collisions = _function_collisions(
        {plugin_name: _plugin_function_names(plugin) for plugin_name, plugin in mounted}
    )
    for fn_name, names in collisions:
        _factory_logger.warning(
            "Homonymous @kernel_function '%s' for speciality '%s': mounted by %s "
            "— the agent is offered %d tools under the same name and nothing "
            "marks the canonical one (#2145)",
            fn_name,
            agent_speciality,
            names,
            len(names),
        )
    return collisions


def get_plugin_instances(
    agent_speciality: str,
    state: Any = None,
    kernel: Optional[Kernel] = None,
    llm_service: Any = None,
    state_plugin_class: Optional[type] = None,
) -> list[Any]:
    """Return instantiated plugin objects for an agent's speciality.

    Useful for ChatCompletionAgent(plugins=[...]) scoping where each agent
    gets its own plugin instances rather than sharing via kernel.

    Args:
        agent_speciality: Key into AGENT_SPECIALITY_MAP.
        state: Optional RhetoricalAnalysisState for StateManagerPlugin.
        kernel: Optional SK Kernel for complex plugins (e.g. FallacyWorkflowPlugin).
        llm_service: Optional LLM service for complex plugins.
        state_plugin_class: Optional phase-scoped state plugin class to use
            instead of the full StateManagerPlugin (#605). When provided,
            this class is instantiated with ``state`` and used as the state
            plugin. Pass ``None`` (default) to use the full StateManagerPlugin.

    Returns:
        List of plugin instances (state plugin first if state provided).
    """
    instances: list[Any] = []
    mounted: list[tuple[str, Any]] = []

    # State plugin: phase-scoped class or full StateManagerPlugin
    if state is not None:
        try:
            if state_plugin_class is not None:
                instance = state_plugin_class(state=state)
                instances.append(instance)
                mounted.append(("state_manager", instance))
                _factory_logger.debug(
                    "Using phase-scoped state plugin: %s", state_plugin_class.__name__
                )
            else:
                mod = importlib.import_module(
                    "argumentation_analysis.core.state_manager_plugin"
                )
                plugin_cls = getattr(mod, "StateManagerPlugin")
                instance = plugin_cls(state=state)
                instances.append(instance)
                mounted.append(("state_manager", instance))
        except Exception as e:
            _factory_logger.warning(
                "State plugin not instantiated for '%s': %s — the agent runs "
                "without the shared communication medium",
                agent_speciality,
                e,
            )

    # Load speciality plugins
    plugin_names = AGENT_SPECIALITY_MAP.get(agent_speciality, [])
    for plugin_name in plugin_names:
        entry = _PLUGIN_REGISTRY.get(plugin_name)
        if entry is None:
            _factory_logger.warning(
                "Unknown plugin '%s' declared for speciality '%s' — no registry "
                "entry, so it is silently absent from the agent",
                plugin_name,
                agent_speciality,
            )
            continue
        module_path, class_name = entry
        try:
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, class_name)
            # Complex plugins need kernel + llm_service (e.g. FallacyWorkflowPlugin)
            if plugin_name == "fallacy_workflow":
                if kernel is not None and llm_service is not None:
                    instance = plugin_cls(master_kernel=kernel, llm_service=llm_service)
                    instances.append(instance)
                    mounted.append((plugin_name, instance))
                else:
                    _factory_logger.warning(
                        "Plugin '%s' not given to '%s': requires kernel and "
                        "llm_service — the agent is degraded",
                        plugin_name,
                        agent_speciality,
                    )
                    continue
            else:
                instance = plugin_cls()
                instances.append(instance)
                mounted.append((plugin_name, instance))
        except Exception as e:
            _factory_logger.warning(
                "Plugin '%s' not instantiated for '%s': %s — the agent runs "
                "without it",
                plugin_name,
                agent_speciality,
                e,
            )

    _report_function_collisions(agent_speciality, mounted)
    return instances


def load_plugins_for_agent(
    kernel: Kernel,
    agent_speciality: str,
    state: Any = None,
    llm_service: Any = None,
) -> list[str]:
    """Load only the plugins relevant to an agent's speciality onto its kernel.

    Always loads StateManagerPlugin (if state is provided) as the shared
    communication medium.  Then loads speciality-specific plugins from
    AGENT_SPECIALITY_MAP.

    Args:
        kernel: The Semantic Kernel instance.
        agent_speciality: Key into AGENT_SPECIALITY_MAP.
        state: Optional RhetoricalAnalysisState for StateManagerPlugin.
        llm_service: Optional LLM service for complex plugins.

    Returns:
        List of loaded plugin names.
    """
    loaded: list[str] = []
    mounted: list[tuple[str, Any]] = []

    # Always load StateManager if state is available
    if state is not None:
        try:
            mod = importlib.import_module(
                "argumentation_analysis.core.state_manager_plugin"
            )
            plugin_cls = getattr(mod, "StateManagerPlugin")
            instance = plugin_cls(state=state)
            kernel.add_plugin(instance, plugin_name="state_manager")
            loaded.append("state_manager")
            mounted.append(("state_manager", instance))
        except Exception as e:
            _factory_logger.warning(
                "StateManagerPlugin not loaded for '%s': %s — the agent runs "
                "without the shared communication medium",
                agent_speciality,
                e,
            )

    # Load speciality plugins
    plugin_names = AGENT_SPECIALITY_MAP.get(agent_speciality, [])
    for plugin_name in plugin_names:
        entry = _PLUGIN_REGISTRY.get(plugin_name)
        if entry is None:
            _factory_logger.warning("Unknown plugin '%s' in registry", plugin_name)
            continue
        module_path, class_name = entry
        try:
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, class_name)
            # Complex plugins need kernel + llm_service
            if plugin_name == "fallacy_workflow":
                if llm_service is not None:
                    instance = plugin_cls(master_kernel=kernel, llm_service=llm_service)
                else:
                    _factory_logger.warning(
                        "Plugin '%s' not loaded for '%s': requires llm_service — "
                        "the agent is degraded",
                        plugin_name,
                        agent_speciality,
                    )
                    continue
            else:
                instance = plugin_cls()
            kernel.add_plugin(instance, plugin_name=plugin_name)
            loaded.append(plugin_name)
            mounted.append((plugin_name, instance))
        except Exception as e:
            _factory_logger.warning(
                "Plugin '%s' not loaded for '%s': %s — the agent runs without it",
                plugin_name,
                agent_speciality,
                e,
            )

    _report_function_collisions(agent_speciality, mounted)
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
    ) -> Union[Agent, "TracedAgent"]:
        agent_to_create = InformalFallacyAgent(
            kernel=self.kernel,
            config_name=config_name,
            taxonomy_file_path=taxonomy_file_path,
            llm_service_id=self.llm_service_id,
        )

        if trace_log_path:
            return TracedAgent(
                agent_to_wrap=agent_to_create, trace_log_path=trace_log_path
            )
        return agent_to_create

    def create_agent(
        self, agent_type: AgentType, **kwargs: Any
    ) -> Union[Agent, "TracedAgent"]:
        if agent_type == AgentType.INFORMAL_FALLACY:
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

        return agent_class(kernel=self.kernel, **kwargs)  # type: ignore[return-value]  # SherlockJTMSAgent doesn't inherit Agent

    def create_project_manager_agent(
        self, trace_log_path: Optional[str] = None
    ) -> Union[Agent, "TracedAgent"]:
        plugins: list[Any] = [ProjectManagementPlugin()]
        with open(
            "argumentation_analysis/agents/prompts/ProjectManagerAgent/skprompt.txt",
            "r",
        ) as f:
            prompt = f.read()
        llm_service: Any = self.kernel.get_service(self.llm_service_id)
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
    ) -> Union[Agent, "TracedAgent"]:
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
    ) -> Union[Agent, "TracedAgent"]:
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
    ) -> Union[Agent, "TracedAgent"]:
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
    ) -> Union[Agent, "TracedAgent"]:
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
        enable_auto_function_calling: bool = True,
        **kwargs: Any,
    ) -> Union[Agent, "TracedAgent"]:
        if "service_id" not in kwargs:
            kwargs["service_id"] = self.llm_service_id

        agent = agent_class(kernel=self.kernel, **kwargs)

        if enable_auto_function_calling:
            self._enable_function_choice_behavior(agent)

        if trace_log_path:
            # TracedAgent expects ChatCompletionAgent; callers always pass subclasses
            return TracedAgent(agent_to_wrap=agent, trace_log_path=trace_log_path)  # type: ignore[arg-type]
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
                object.__setattr__(agent, "_function_choice_behavior", fcb)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Could not enable FunctionChoiceBehavior on {getattr(agent, 'name', '?')}: {e}"
            )
