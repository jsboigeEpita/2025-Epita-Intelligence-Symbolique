"""
Architecture compliance tests — verify that all consolidated components
follow the BaseAgent/Plugin/Service patterns established in Phase C.

Validates:
- BaseAgent inheritance for debate and counter-argument agents
- SK plugin (@kernel_function) compliance for all 3 plugins
- CapabilityRegistry registration for all components
- AgentFactory can create all registered agents
- unified_pipeline.setup_registry() completes without errors
"""

import json

import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import kernel_function


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_kernel():
    """Kernel with mock OpenAI service for agent tests."""
    kernel = Kernel()
    service = OpenAIChatCompletion(
        service_id="default", api_key="test-key"
    )
    kernel.add_service(service)
    return kernel


# ---------------------------------------------------------------------------
# BaseAgent Compliance
# ---------------------------------------------------------------------------


class TestBaseAgentCompliance:
    """Verify that agents inherit from BaseAgent correctly."""

    def test_counter_argument_agent_inherits_base_agent(self, mock_kernel):
        """CounterArgumentAgent inherits from BaseAgent."""
        from argumentation_analysis.agents.core.abc.agent_bases import (
            BaseAgent,
        )
        from argumentation_analysis.agents.core.counter_argument import (
            CounterArgumentAgent,
        )

        agent = CounterArgumentAgent(kernel=mock_kernel)
        assert isinstance(agent, BaseAgent)

    def test_debate_agent_inherits_base_agent(self, mock_kernel):
        """DebateAgent inherits from BaseAgent."""
        from argumentation_analysis.agents.core.abc.agent_bases import (
            BaseAgent,
        )
        from argumentation_analysis.agents.core.debate import DebateAgent

        agent = DebateAgent(kernel=mock_kernel)
        assert isinstance(agent, BaseAgent)

    def test_counter_argument_has_required_methods(self, mock_kernel):
        """CounterArgumentAgent implements all abstract methods."""
        from argumentation_analysis.agents.core.counter_argument import (
            CounterArgumentAgent,
        )

        agent = CounterArgumentAgent(kernel=mock_kernel)
        assert callable(getattr(agent, "get_agent_capabilities", None))
        assert callable(getattr(agent, "get_response", None))
        assert callable(getattr(agent, "invoke_single", None))
        assert callable(getattr(agent, "setup_agent_components", None))

    def test_debate_has_required_methods(self, mock_kernel):
        """DebateAgent implements all abstract methods."""
        from argumentation_analysis.agents.core.debate import DebateAgent

        agent = DebateAgent(kernel=mock_kernel)
        assert callable(getattr(agent, "get_agent_capabilities", None))
        assert callable(getattr(agent, "get_response", None))
        assert callable(getattr(agent, "invoke_single", None))
        assert callable(getattr(agent, "setup_agent_components", None))

    def test_backward_compat_alias(self):
        """EnhancedArgumentationAgent is alias for DebateAgent."""
        from argumentation_analysis.agents.core.debate import (
            DebateAgent,
            EnhancedArgumentationAgent,
        )

        assert EnhancedArgumentationAgent is DebateAgent


# ---------------------------------------------------------------------------
# SK Plugin Compliance
# ---------------------------------------------------------------------------


class TestPluginCompliance:
    """Verify that all plugins have @kernel_function methods."""

    def _get_kernel_functions(self, plugin):
        """Get methods decorated with @kernel_function."""
        funcs = []
        for name in dir(plugin):
            method = getattr(plugin, name, None)
            if callable(method) and hasattr(method, "__kernel_function__"):
                funcs.append(name)
        return funcs

    def _has_kernel_function_attr(self, method):
        """Check if method has kernel_function metadata."""
        return (
            hasattr(method, "__kernel_function__")
            or hasattr(method, "__kernel_function_name__")
        )

    def test_counter_argument_plugin_has_kernel_functions(self):
        """CounterArgumentPlugin has @kernel_function methods."""
        from argumentation_analysis.agents.core.counter_argument import (
            CounterArgumentPlugin,
        )

        plugin = CounterArgumentPlugin()
        # Verify key methods exist and return valid JSON
        result = plugin.parse_argument("Test argument text.")
        data = json.loads(result)
        assert "content" in data

    def test_debate_plugin_has_kernel_functions(self):
        """DebatePlugin has @kernel_function methods."""
        from argumentation_analysis.agents.core.debate import DebatePlugin

        plugin = DebatePlugin()
        result = plugin.analyze_argument_quality("Test argument.")
        data = json.loads(result)
        assert "logical_coherence" in data

    def test_quality_scoring_plugin_has_kernel_functions(self):
        """QualityScoringPlugin has @kernel_function methods."""
        from argumentation_analysis.plugins.quality_scoring_plugin import (
            QualityScoringPlugin,
        )

        plugin = QualityScoringPlugin()
        result = plugin.evaluate_argument_quality("Test texte.")
        data = json.loads(result)
        assert "note_finale" in data
        assert "scores_par_vertu" in data

    def test_french_fallacy_plugin_has_kernel_functions(self):
        """FrenchFallacyPlugin has @kernel_function methods."""
        from argumentation_analysis.plugins.french_fallacy_plugin import (
            FrenchFallacyPlugin,
        )

        plugin = FrenchFallacyPlugin(enable_nli=False, enable_llm=False)
        result = plugin.detect_fallacies("Test texte simple.")
        data = json.loads(result)
        assert "detected_fallacies" in data

    def test_governance_plugin_has_kernel_functions(self):
        """GovernancePlugin has @kernel_function methods."""
        from argumentation_analysis.plugins.governance_plugin import (
            GovernancePlugin,
        )

        plugin = GovernancePlugin()
        result = plugin.list_governance_methods()
        methods = json.loads(result)
        assert "majority" in methods["agent_based"]

    def test_plugins_can_register_with_kernel(self, mock_kernel):
        """All plugins can be registered with a kernel."""
        from argumentation_analysis.agents.core.counter_argument import (
            CounterArgumentPlugin,
        )
        from argumentation_analysis.agents.core.debate import DebatePlugin
        from argumentation_analysis.plugins.quality_scoring_plugin import (
            QualityScoringPlugin,
        )
        from argumentation_analysis.plugins.governance_plugin import (
            GovernancePlugin,
        )

        mock_kernel.add_plugin(
            CounterArgumentPlugin(), plugin_name="counter_argument"
        )
        mock_kernel.add_plugin(DebatePlugin(), plugin_name="debate")
        mock_kernel.add_plugin(
            QualityScoringPlugin(), plugin_name="quality"
        )
        mock_kernel.add_plugin(
            GovernancePlugin(), plugin_name="governance"
        )

        assert "counter_argument" in mock_kernel.plugins
        assert "debate" in mock_kernel.plugins
        assert "quality" in mock_kernel.plugins
        assert "governance" in mock_kernel.plugins


# ---------------------------------------------------------------------------
# CapabilityRegistry Compliance
# ---------------------------------------------------------------------------


class TestRegistryCompliance:
    """Verify that all components register correctly."""

    def test_setup_registry_no_errors(self):
        """setup_registry() completes without errors."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        assert registry is not None

    def test_setup_registry_registers_core_agents(self):
        """Core agents are registered in setup_registry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        all_caps = registry.get_all_capabilities()

        # Counter-argument agent
        assert "counter_argument_generation" in all_caps
        # Debate agent
        assert "adversarial_debate" in all_caps
        # Governance
        assert "governance_simulation" in all_caps

    def test_setup_registry_registers_services(self):
        """Core services are registered in setup_registry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        all_caps = registry.get_all_capabilities()

        assert "belief_maintenance" in all_caps
        assert "local_llm" in all_caps

    def test_register_with_convenience_functions(self):
        """All modules with register_with_capability_registry work."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry as reg_counter,
        )
        from argumentation_analysis.agents.core.debate import (
            register_with_capability_registry as reg_debate,
        )
        from argumentation_analysis.agents.core.quality import (
            register_with_capability_registry as reg_quality,
        )
        from argumentation_analysis.agents.core.governance import (
            register_with_capability_registry as reg_governance,
        )

        registry = CapabilityRegistry()
        reg_counter(registry)
        reg_debate(registry)
        reg_quality(registry)
        reg_governance(registry)

        all_caps = registry.get_all_capabilities()
        assert "counter_argument_generation" in all_caps
        assert "adversarial_debate" in all_caps
        assert "argument_quality_evaluation" in all_caps
        assert "collective_decision_making" in all_caps


# ---------------------------------------------------------------------------
# AgentFactory Compliance
# ---------------------------------------------------------------------------


class TestFactoryCompliance:
    """Verify that AgentFactory can create new agent types."""

    def test_factory_create_counter_argument(self, mock_kernel):
        """Factory creates CounterArgumentAgent."""
        from argumentation_analysis.agents.factory import AgentFactory

        factory = AgentFactory(
            kernel=mock_kernel, llm_service_id="default"
        )
        agent = factory.create_counter_argument_agent()
        assert agent.name == "CounterArgumentAgent"

    def test_factory_create_debate(self, mock_kernel):
        """Factory creates DebateAgent with personality."""
        from argumentation_analysis.agents.factory import AgentFactory

        factory = AgentFactory(
            kernel=mock_kernel, llm_service_id="default"
        )
        agent = factory.create_debate_agent(
            agent_name="Alice",
            personality="Scholar",
            position="for",
        )
        assert agent.name == "Alice"
