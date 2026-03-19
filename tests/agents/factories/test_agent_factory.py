# -*- coding: utf-8 -*-
"""
Unit tests for AgentFactory.

Tests cover:
- Factory initialization with kernel and service ID
- create_agent() dispatch for each AgentType
- create_informal_fallacy_agent() with config options
- create_sherlock_agent() / create_watson_agent()
- create_counter_argument_agent() / create_debate_agent() (Phase 4)
- create_project_manager_agent() (prompt file required)
- TracedAgent wrapping when trace_log_path is provided
- Error handling for unknown agent types
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open

from semantic_kernel import Kernel

from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.agents.agents import AgentType


@pytest.fixture
def mock_kernel():
    """Create a mock Kernel with a fake service."""
    kernel = MagicMock(spec=Kernel)
    mock_service = MagicMock()
    kernel.get_service.return_value = mock_service
    return kernel


@pytest.fixture
def factory(mock_kernel):
    """Create an AgentFactory with mocked kernel."""
    return AgentFactory(kernel=mock_kernel, llm_service_id="test-service")


# ===========================================================================
# Factory Initialization
# ===========================================================================


class TestFactoryInit:
    """Tests for AgentFactory construction."""

    def test_init_stores_kernel(self, mock_kernel):
        factory = AgentFactory(kernel=mock_kernel, llm_service_id="svc")
        assert factory.kernel is mock_kernel

    def test_init_stores_service_id(self, mock_kernel):
        factory = AgentFactory(kernel=mock_kernel, llm_service_id="my-svc-id")
        assert factory.llm_service_id == "my-svc-id"


# ===========================================================================
# create_agent() dispatch
# ===========================================================================


class TestCreateAgentDispatch:
    """Tests for create_agent() routing to correct classes."""

    @patch(
        "argumentation_analysis.agents.factory.AgentFactory.create_informal_fallacy_agent"
    )
    def test_dispatch_informal_fallacy(self, mock_create, factory):
        """AgentType.INFORMAL_FALLACY delegates to create_informal_fallacy_agent."""
        mock_agent = MagicMock()
        mock_create.return_value = mock_agent

        result = factory.create_agent(AgentType.INFORMAL_FALLACY, config_name="test")
        mock_create.assert_called_once_with(config_name="test")
        assert result is mock_agent

    @patch("argumentation_analysis.agents.sherlock_jtms_agent.SherlockJTMSAgent")
    def test_dispatch_sherlock_jtms(self, MockSherlockJTMS, factory):
        """AgentType.SHERLOCK_JTMS creates SherlockJTMSAgent."""
        mock_agent = MagicMock()
        MockSherlockJTMS.return_value = mock_agent

        result = factory.create_agent(AgentType.SHERLOCK_JTMS)
        MockSherlockJTMS.assert_called_once_with(
            kernel=factory.kernel, llm_service_id="test-service"
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.MethodicalAuditorAgent")
    def test_dispatch_methodical_auditor(self, MockAgent, factory):
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        result = factory.create_agent(AgentType.METHODICAL_AUDITOR)
        MockAgent.assert_called_once_with(
            kernel=factory.kernel, llm_service_id="test-service"
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.ParallelExplorerAgent")
    def test_dispatch_parallel_explorer(self, MockAgent, factory):
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        result = factory.create_agent(AgentType.PARALLEL_EXPLORER)
        MockAgent.assert_called_once_with(
            kernel=factory.kernel, llm_service_id="test-service"
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.ResearchAssistantAgent")
    def test_dispatch_research_assistant(self, MockAgent, factory):
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        result = factory.create_agent(AgentType.RESEARCH_ASSISTANT)
        MockAgent.assert_called_once_with(
            kernel=factory.kernel, llm_service_id="test-service"
        )
        assert result is mock_agent

    def test_dispatch_unknown_type_raises(self, factory):
        """Unknown AgentType raises ValueError."""
        # Use a mock enum value that's not in the agent_map
        fake_type = MagicMock()
        fake_type.__eq__ = lambda self, other: False
        # Since it won't match INFORMAL_FALLACY or any key, it should raise
        with pytest.raises(ValueError, match="Unknown agent type"):
            factory.create_agent(fake_type)

    @patch("argumentation_analysis.agents.factory.MethodicalAuditorAgent")
    def test_dispatch_passes_custom_llm_service_id(self, MockAgent, factory):
        """If llm_service_id is in kwargs, it overrides the factory default."""
        factory.create_agent(AgentType.METHODICAL_AUDITOR, llm_service_id="custom-svc")
        MockAgent.assert_called_once_with(
            kernel=factory.kernel, llm_service_id="custom-svc"
        )


# ===========================================================================
# create_informal_fallacy_agent()
# ===========================================================================


class TestCreateInformalFallacyAgent:
    """Tests for create_informal_fallacy_agent()."""

    @patch("argumentation_analysis.agents.factory.InformalFallacyAgent")
    def test_creates_agent_with_defaults(self, MockAgent, factory):
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        result = factory.create_informal_fallacy_agent()
        MockAgent.assert_called_once_with(
            kernel=factory.kernel,
            config_name="simple",
            taxonomy_file_path=None,
            llm_service_id="test-service",
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.InformalFallacyAgent")
    def test_creates_agent_with_custom_config(self, MockAgent, factory):
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        factory.create_informal_fallacy_agent(
            config_name="complex", taxonomy_file_path="/path/to/taxonomy.json"
        )
        MockAgent.assert_called_once_with(
            kernel=factory.kernel,
            config_name="complex",
            taxonomy_file_path="/path/to/taxonomy.json",
            llm_service_id="test-service",
        )

    @patch("argumentation_analysis.agents.factory.TracedAgent")
    @patch("argumentation_analysis.agents.factory.InformalFallacyAgent")
    def test_wraps_with_traced_agent(self, MockAgent, MockTraced, factory):
        mock_agent = MagicMock()
        mock_traced = MagicMock()
        MockAgent.return_value = mock_agent
        MockTraced.return_value = mock_traced

        result = factory.create_informal_fallacy_agent(trace_log_path="/tmp/trace.log")
        MockTraced.assert_called_once_with(
            agent_to_wrap=mock_agent, trace_log_path="/tmp/trace.log"
        )
        assert result is mock_traced

    @patch("argumentation_analysis.agents.factory.InformalFallacyAgent")
    def test_no_trace_without_path(self, MockAgent, factory):
        """When trace_log_path is None, no TracedAgent wrapping."""
        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        result = factory.create_informal_fallacy_agent(trace_log_path=None)
        assert result is mock_agent


# ===========================================================================
# create_sherlock_agent() / create_watson_agent()
# ===========================================================================


class TestCreateNamedAgents:
    """Tests for Sherlock and Watson factory methods."""

    @patch("argumentation_analysis.agents.factory.SherlockEnqueteAgent")
    def test_create_sherlock_defaults(self, MockSherlock, factory):
        mock_agent = MagicMock()
        MockSherlock.return_value = mock_agent

        result = factory.create_sherlock_agent()
        MockSherlock.assert_called_once_with(
            kernel=factory.kernel,
            agent_name="Sherlock",
            service_id="test-service",
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.SherlockEnqueteAgent")
    def test_create_sherlock_custom_name(self, MockSherlock, factory):
        MockSherlock.return_value = MagicMock()
        factory.create_sherlock_agent(agent_name="CustomSherlock")
        MockSherlock.assert_called_once_with(
            kernel=factory.kernel,
            agent_name="CustomSherlock",
            service_id="test-service",
        )

    @patch("argumentation_analysis.agents.factory.TracedAgent")
    @patch("argumentation_analysis.agents.factory.SherlockEnqueteAgent")
    def test_create_sherlock_traced(self, MockSherlock, MockTraced, factory):
        mock_agent = MagicMock()
        MockSherlock.return_value = mock_agent
        mock_traced = MagicMock()
        MockTraced.return_value = mock_traced

        result = factory.create_sherlock_agent(trace_log_path="/tmp/trace.log")
        MockTraced.assert_called_once_with(
            agent_to_wrap=mock_agent, trace_log_path="/tmp/trace.log"
        )
        assert result is mock_traced

    @patch("argumentation_analysis.agents.factory.WatsonLogicAssistant")
    def test_create_watson_defaults(self, MockWatson, factory):
        mock_agent = MagicMock()
        MockWatson.return_value = mock_agent

        result = factory.create_watson_agent()
        MockWatson.assert_called_once_with(
            kernel=factory.kernel,
            agent_name="Watson",
            service_id="test-service",
            constants=None,
            system_prompt=None,
        )
        assert result is mock_agent

    @patch("argumentation_analysis.agents.factory.WatsonLogicAssistant")
    def test_create_watson_with_params(self, MockWatson, factory):
        MockWatson.return_value = MagicMock()
        factory.create_watson_agent(
            agent_name="WatsonCustom",
            constants=["A", "B"],
            system_prompt="You are Watson.",
        )
        MockWatson.assert_called_once_with(
            kernel=factory.kernel,
            agent_name="WatsonCustom",
            service_id="test-service",
            constants=["A", "B"],
            system_prompt="You are Watson.",
        )


# ===========================================================================
# create_counter_argument_agent() / create_debate_agent() (Phase 4)
# ===========================================================================


class TestCreatePhase4Agents:
    """Tests for counter-argument and debate agent creation."""

    @patch(
        "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentAgent"
    )
    def test_create_counter_argument_defaults(self, MockCA, factory):
        mock_agent = MagicMock()
        MockCA.return_value = mock_agent

        with patch.object(
            factory, "_create_agent", return_value=mock_agent
        ) as mock_create:
            result = factory.create_counter_argument_agent()
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args
            assert (
                call_kwargs[1].get("agent_name") == "CounterArgumentAgent"
                or call_kwargs.kwargs.get("agent_name") == "CounterArgumentAgent"
            )

    @patch(
        "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentAgent"
    )
    def test_create_counter_argument_custom_name(self, MockCA, factory):
        mock_agent = MagicMock()
        MockCA.return_value = mock_agent

        with patch.object(
            factory, "_create_agent", return_value=mock_agent
        ) as mock_create:
            factory.create_counter_argument_agent(agent_name="MyCA")
            call_kwargs = mock_create.call_args
            assert "MyCA" in str(call_kwargs)

    @patch("argumentation_analysis.agents.core.debate.debate_agent.DebateAgent")
    def test_create_debate_defaults(self, MockDebate, factory):
        mock_agent = MagicMock()
        MockDebate.return_value = mock_agent

        with patch.object(
            factory, "_create_agent", return_value=mock_agent
        ) as mock_create:
            result = factory.create_debate_agent()
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args
            assert "DebateAgent" in str(call_kwargs)
            assert "The Scholar" in str(call_kwargs)
            assert result is mock_agent

    @patch("argumentation_analysis.agents.core.debate.debate_agent.DebateAgent")
    def test_create_debate_custom_params(self, MockDebate, factory):
        mock_agent = MagicMock()
        MockDebate.return_value = mock_agent

        with patch.object(
            factory, "_create_agent", return_value=mock_agent
        ) as mock_create:
            factory.create_debate_agent(
                agent_name="CustomDebater",
                personality="The Diplomat",
                position="against",
            )
            call_kwargs = mock_create.call_args
            assert "CustomDebater" in str(call_kwargs)
            assert "The Diplomat" in str(call_kwargs)
            assert "against" in str(call_kwargs)


# ===========================================================================
# create_project_manager_agent()
# ===========================================================================


class TestCreateProjectManagerAgent:
    """Tests for create_project_manager_agent()."""

    @patch("builtins.open", mock_open(read_data="You are a project manager."))
    @patch("argumentation_analysis.agents.factory.ChatCompletionAgent")
    def test_creates_pm_agent(self, MockCCA, factory):
        mock_agent = MagicMock()
        MockCCA.return_value = mock_agent

        result = factory.create_project_manager_agent()
        MockCCA.assert_called_once()
        call_kwargs = MockCCA.call_args
        assert call_kwargs.kwargs["name"] == "Project_Manager"
        assert "project manager" in call_kwargs.kwargs["instructions"].lower()
        assert result is mock_agent

    @patch("builtins.open", mock_open(read_data="You are a PM."))
    @patch("argumentation_analysis.agents.factory.TracedAgent")
    @patch("argumentation_analysis.agents.factory.ChatCompletionAgent")
    def test_creates_pm_agent_traced(self, MockCCA, MockTraced, factory):
        mock_agent = MagicMock()
        mock_traced = MagicMock()
        MockCCA.return_value = mock_agent
        MockTraced.return_value = mock_traced

        result = factory.create_project_manager_agent(trace_log_path="/tmp/pm.log")
        MockTraced.assert_called_once_with(
            agent_to_wrap=mock_agent, trace_log_path="/tmp/pm.log"
        )
        assert result is mock_traced


# ===========================================================================
# _create_agent() internal
# ===========================================================================


class TestInternalCreateAgent:
    """Tests for the internal _create_agent() helper."""

    def test_injects_service_id(self, factory):
        """_create_agent adds service_id from factory when not provided."""
        MockClass = MagicMock()
        mock_agent = MagicMock()
        MockClass.return_value = mock_agent

        result = factory._create_agent(agent_class=MockClass, agent_name="Test")
        MockClass.assert_called_once_with(
            kernel=factory.kernel, agent_name="Test", service_id="test-service"
        )
        assert result is mock_agent

    def test_respects_explicit_service_id(self, factory):
        """_create_agent does not override explicitly provided service_id."""
        MockClass = MagicMock()
        MockClass.return_value = MagicMock()

        factory._create_agent(
            agent_class=MockClass, service_id="explicit-svc", agent_name="Test"
        )
        MockClass.assert_called_once_with(
            kernel=factory.kernel, service_id="explicit-svc", agent_name="Test"
        )

    def test_trace_wrapping(self, factory):
        """_create_agent wraps with TracedAgent when trace_log_path is set."""
        MockClass = MagicMock()
        mock_agent = MagicMock()
        MockClass.return_value = mock_agent

        with patch("argumentation_analysis.agents.factory.TracedAgent") as MockTraced:
            mock_traced = MagicMock()
            MockTraced.return_value = mock_traced

            result = factory._create_agent(
                agent_class=MockClass, trace_log_path="/tmp/trace.log"
            )
            MockTraced.assert_called_once_with(
                agent_to_wrap=mock_agent, trace_log_path="/tmp/trace.log"
            )
            assert result is mock_traced
