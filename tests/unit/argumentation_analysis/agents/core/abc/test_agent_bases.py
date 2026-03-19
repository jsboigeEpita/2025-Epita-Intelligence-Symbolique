"""
Tests for agent_bases.py (BaseAgent, BaseLogicAgent).

NOTE: These tests use mocks to avoid requiring actual LLM API keys.
The BaseAgent requires an LLM service, so we mock the ChatCompletionClientBase.
"""

import logging
from unittest.mock import MagicMock, patch, AsyncMock, Mock
import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent, BaseLogicAgent


# =====================================================================
# BaseAgent Tests
# =====================================================================


class TestBaseAgent:
    """Tests for the BaseAgent abstract base class."""

    def _create_mock_kernel_with_service(self):
        """Helper to create a mock kernel with an LLM service."""
        kernel = MagicMock(spec=Kernel)
        mock_service = MagicMock(spec=ChatCompletionClientBase)
        mock_service.service_id = "test_service"
        kernel.get_service = MagicMock(return_value=mock_service)
        kernel.services = {"test_service": mock_service}
        return kernel

    def test_base_agent_is_abstract(self):
        """Verify BaseAgent cannot be instantiated directly."""
        kernel = MagicMock(spec=Kernel)

        with pytest.raises(TypeError):
            BaseAgent(kernel, "TestAgent")

    def test_base_agent_attributes_initialized(self):
        """Verify BaseAgent initializes expected attributes via subclass."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {"test": "capability"}

        agent = ConcreteAgent(kernel, "TestAgent", description="Test Description")

        assert agent.id == "TestAgent"
        assert agent.name == "TestAgent"
        assert agent.description == "Test Description"
        assert hasattr(agent, "_agent_logger")
        assert isinstance(agent._agent_logger, logging.Logger)

    def test_base_agent_with_system_prompt(self):
        """Verify system prompt is stored."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

        agent = ConcreteAgent(
            kernel,
            "TestAgent",
            system_prompt="You are a test agent.",
        )

        assert agent.instructions == "You are a test agent."

    def test_base_agent_logger_name(self):
        """Verify logger is named after agent class."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

        agent = ConcreteAgent(kernel, "TestAgent")
        assert "ConcreteAgent" in agent._agent_logger.name

    def test_base_agent_invoke_single_must_be_implemented(self):
        """Verify invoke_single is abstract."""
        kernel = self._create_mock_kernel_with_service()

        class IncompleteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

        # Should still raise TypeError due to abstract method
        with pytest.raises(TypeError):
            IncompleteAgent(kernel, "IncompleteAgent")

    def test_base_agent_get_response_must_be_implemented(self):
        """Verify get_response is abstract."""
        kernel = self._create_mock_kernel_with_service()

        class IncompleteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

        with pytest.raises(TypeError):
            IncompleteAgent(kernel, "IncompleteAgent")

    def test_base_agent_setup_components_is_not_abstract_in_base(self):
        """Verify setup_agent_components is NOT abstract in BaseAgent (only in BaseLogicAgent)."""
        kernel = self._create_mock_kernel_with_service()

        # BaseAgent doesn't require setup_agent_components to be abstract
        # (it's only abstract in BaseLogicAgent)
        class MinimalAgent(BaseAgent):
            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

        # This should work fine - setup_agent_components is not abstract in BaseAgent
        agent = MinimalAgent(kernel, "MinimalAgent")
        assert agent.id == "MinimalAgent"

    @pytest.mark.asyncio
    async def test_base_agent_concrete_implementation(self):
        """Verify a concrete implementation can be created and used."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                self._llm_service_id = kwargs.get("service_id", "default")

            async def invoke_single(self, **kwargs):
                return {"result": "test_result"}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {"test_capability": True}

        agent = ConcreteAgent(kernel, "Concrete")
        # Call setup_agent_components explicitly (it's not called automatically)
        agent.setup_agent_components(service_id="test_service")

        result = await agent.invoke_single()

        assert result == {"result": "test_result"}
        assert agent._llm_service_id == "test_service"


# =====================================================================
# BaseLogicAgent Tests
# =====================================================================


class TestBaseLogicAgent:
    """Tests for the BaseLogicAgent abstract base class."""

    def _create_mock_kernel_with_service(self):
        """Helper to create a mock kernel with an LLM service."""
        kernel = MagicMock(spec=Kernel)
        mock_service = MagicMock(spec=ChatCompletionClientBase)
        mock_service.service_id = "test_service"
        kernel.get_service = MagicMock(return_value=mock_service)
        kernel.services = {"test_service": mock_service}
        return kernel

    def test_base_logic_agent_is_abstract(self):
        """Verify BaseLogicAgent cannot be instantiated directly."""
        kernel = MagicMock(spec=Kernel)

        with pytest.raises(TypeError):
            BaseLogicAgent(kernel, "TestLogicAgent", "PL")

    def test_base_logic_agent_has_base_agent_attributes(self):
        """Verify BaseLogicAgent has BaseAgent attributes."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteLogicAgent(BaseLogicAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

            async def execute_query(self, belief_set, query: str):
                return f"Query result: {query}"

            def text_to_belief_set(self, text, context=None):
                pass

            def generate_queries(self, text, belief_set, context=None):
                pass

            def interpret_results(self, text, belief_set, queries, results, context=None):
                pass

            def validate_formula(self, formula):
                pass

            def is_consistent(self, belief_set):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        agent = ConcreteLogicAgent(kernel, "LogicAgent", "PL", description="Logic Agent")

        assert agent.id == "LogicAgent"
        assert agent.description == "Logic Agent"
        assert hasattr(agent, "_agent_logger")

    def test_base_logic_agent_logic_type_property(self):
        """Verify logic_type property returns the logic type name."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteLogicAgent(BaseLogicAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

            async def execute_query(self, belief_set, query: str):
                pass

            def text_to_belief_set(self, text, context=None):
                pass

            def generate_queries(self, text, belief_set, context=None):
                pass

            def interpret_results(self, text, belief_set, queries, results, context=None):
                pass

            def validate_formula(self, formula):
                pass

            def is_consistent(self, belief_set):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        agent = ConcreteLogicAgent(kernel, "LogicAgent", "FOL")
        assert agent.logic_type == "FOL"

    def test_base_logic_agent_setup_components(self):
        """Verify setup_agent_components sets llm_service_id."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteLogicAgent(BaseLogicAgent):
            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

            async def execute_query(self, belief_set, query: str):
                pass

            def text_to_belief_set(self, text, context=None):
                pass

            def generate_queries(self, text, belief_set, context=None):
                pass

            def interpret_results(self, text, belief_set, queries, results, context=None):
                pass

            def validate_formula(self, formula):
                pass

            def is_consistent(self, belief_set):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        agent = ConcreteLogicAgent(kernel, "LogicAgent", "PL")
        agent.setup_agent_components(llm_service_id="custom_service")
        assert agent._llm_service_id == "custom_service"

    def test_base_logic_agent_execute_query_must_be_implemented(self):
        """Verify execute_query is abstract."""
        kernel = self._create_mock_kernel_with_service()

        class IncompleteLogicAgent(BaseLogicAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                pass

            async def get_response(self, *args, **kwargs):
                pass

            def get_agent_capabilities(self):
                return {}

            def text_to_belief_set(self, text, context=None):
                pass

            def generate_queries(self, text, belief_set, context=None):
                pass

            def interpret_results(self, text, belief_set, queries, results, context=None):
                pass

            def validate_formula(self, formula):
                pass

            def is_consistent(self, belief_set):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        with pytest.raises(TypeError):
            IncompleteLogicAgent(kernel, "Incomplete", "PL")

    @pytest.mark.asyncio
    async def test_base_logic_agent_concrete_implementation(self):
        """Verify a concrete logic agent can be created and used."""
        kernel = self._create_mock_kernel_with_service()

        class ConcreteLogicAgent(BaseLogicAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                return {"logic_result": "derived"}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {"logic_types": ["propositional"]}

            async def execute_query(self, belief_set, query: str):
                return f"Executed: {query}"

            def text_to_belief_set(self, text, context=None):
                pass

            def generate_queries(self, text, belief_set, context=None):
                pass

            def interpret_results(self, text, belief_set, queries, results, context=None):
                pass

            def validate_formula(self, formula):
                pass

            def is_consistent(self, belief_set):
                pass

            def _create_belief_set_from_data(self, belief_set_data):
                pass

        agent = ConcreteLogicAgent(kernel, "PropLogic", "PL")
        result = await agent.invoke_single()

        assert result == {"logic_result": "derived"}
        assert agent.get_agent_capabilities() == {"logic_types": ["propositional"]}


# =====================================================================
# Integration Tests
# =====================================================================


class TestAgentBasesIntegration:
    """Integration tests for agent bases with Semantic Kernel."""

    def _create_mock_kernel_with_service(self):
        """Helper to create a mock kernel with an LLM service."""
        kernel = MagicMock(spec=Kernel)
        mock_service = MagicMock(spec=ChatCompletionClientBase)
        mock_service.service_id = "test_service"
        kernel.get_service = MagicMock(return_value=mock_service)
        kernel.services = {"test_service": mock_service}
        return kernel

    def test_base_agent_with_mock_kernel(self):
        """Verify BaseAgent works with mocked Kernel."""
        kernel = self._create_mock_kernel_with_service()

        class TestAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                # Verify the method can be called
                self._setup_called = True

            async def invoke_single(self, **kwargs):
                return {"status": "ok"}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {"test": True}

        agent = TestAgent(kernel, "Test")
        # setup_agent_components must be called explicitly
        agent.setup_agent_components()
        # Verify the kernel is properly set
        assert agent.kernel is kernel
        assert agent.id == "Test"

    def test_multiple_agents_same_kernel(self):
        """Verify multiple agents can share the same kernel."""
        kernel = self._create_mock_kernel_with_service()

        class TestAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                return {}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {"test": True}

        agent1 = TestAgent(kernel, "Agent1")
        agent2 = TestAgent(kernel, "Agent2")

        assert agent1.id == "Agent1"
        assert agent2.id == "Agent2"
        # Both agents share the same kernel instance
        assert agent1.kernel is agent2.kernel

    def test_agent_get_capabilities_dict(self):
        """Verify get_agent_capabilities returns a dict."""
        kernel = self._create_mock_kernel_with_service()

        class CapabilitiesAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                return {}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {
                    "reasoning": True,
                    "analysis": True,
                    "synthesis": True,
                    "supported_logics": ["propositional", "first_order"]
                }

        agent = CapabilitiesAgent(kernel, "Caps")
        caps = agent.get_agent_capabilities()
        assert isinstance(caps, dict)
        assert caps["reasoning"] is True
        assert "propositional" in caps["supported_logics"]

    def test_agent_get_agent_info(self):
        """Verify get_agent_info returns complete agent information."""
        kernel = self._create_mock_kernel_with_service()

        class InfoAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                self._llm_service_id = kwargs.get("llm_service_id", "default")

            async def invoke_single(self, **kwargs):
                return {}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {"version": "1.0", "features": ["test"]}

        agent = InfoAgent(kernel, "InfoAgent", system_prompt="Test prompt", llm_service_id="custom")
        info = agent.get_agent_info()

        assert info["name"] == "InfoAgent"
        assert info["class"] == "InfoAgent"
        assert info["system_prompt"] == "Test prompt"
        assert info["llm_service_id"] == "custom"
        assert info["capabilities"]["version"] == "1.0"

    def test_agent_properties(self):
        """Verify agent properties work correctly."""
        kernel = self._create_mock_kernel_with_service()

        class PropertyAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                return {}

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {}

        agent = PropertyAgent(kernel, "PropAgent", system_prompt="Test instructions")

        # Test agent_name property
        assert agent.agent_name == "PropAgent"

        # Test system_prompt property
        assert agent.system_prompt == "Test instructions"

        # Test logger property
        assert isinstance(agent.logger, logging.Logger)
        assert "PropertyAgent" in agent.logger.name

    def test_agent_invoke_returns_generator(self):
        """Verify invoke method returns an async generator."""
        kernel = self._create_mock_kernel_with_service()

        class GeneratorAgent(BaseAgent):
            def setup_agent_components(self, **kwargs):
                pass

            async def invoke_single(self, **kwargs):
                return "single result"

            async def get_response(self, *args, **kwargs):
                return await self.invoke_single(**kwargs)

            def get_agent_capabilities(self):
                return {}

        agent = GeneratorAgent(kernel, "GenAgent")

        # invoke should return an async generator
        result = agent.invoke()
        assert hasattr(result, "__aiter__")

        # invoke_stream should also return an async generator
        stream = agent.invoke_stream()
        assert hasattr(stream, "__aiter__")
