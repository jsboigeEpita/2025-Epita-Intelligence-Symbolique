"""
Tests for sherlock_enquete_agent.py (SherlockEnqueteAgent, SherlockTools).
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock
import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
    SherlockTools,
    SherlockEnqueteAgent,
    SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT,
)


def _create_mock_kernel():
    """Helper to create a mock kernel with a ChatCompletionClientBase service."""
    kernel = MagicMock(spec=Kernel)
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.service_id = "test_service"
    kernel.get_service = MagicMock(return_value=mock_service)
    kernel.services = {"test_service": mock_service}
    return kernel


# =====================================================================
# SherlockTools Tests
# =====================================================================


class TestSherlockTools:
    """Tests for SherlockTools plugin."""

    def test_initialization(self):
        """Verify tools are initialized with kernel."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)
        assert tools.kernel is kernel
        assert hasattr(tools, "logger")

    @pytest.mark.asyncio
    async def test_get_current_case_description_success(self):
        """Verify case description retrieval."""
        kernel = MagicMock(spec=Kernel)

        mock_response = MagicMock()
        mock_response.value = "Case description: The Murder at the Manor"
        kernel.invoke = AsyncMock(return_value=mock_response)

        tools = SherlockTools(kernel)
        result = await tools.get_current_case_description()
        assert "Case description" in result
        assert "Murder at the Manor" in result

    @pytest.mark.asyncio
    async def test_get_current_case_description_no_value_attribute(self):
        """Verify case description handles response without value attribute."""
        kernel = MagicMock(spec=Kernel)

        mock_response = MagicMock()
        # Remove value attribute to test fallback
        if hasattr(mock_response, 'value'):
            del mock_response.value
        # Mock __str__ to return string when value attribute is missing
        mock_response.__str__ = MagicMock(return_value="Direct string response")
        kernel.invoke = AsyncMock(return_value=mock_response)

        tools = SherlockTools(kernel)
        result = await tools.get_current_case_description()
        assert "Direct string response" in result

    @pytest.mark.asyncio
    async def test_get_current_case_description_error(self):
        """Verify case description handles errors."""
        kernel = MagicMock(spec=Kernel)
        kernel.invoke = AsyncMock(side_effect=RuntimeError("Test error"))

        tools = SherlockTools(kernel)
        result = await tools.get_current_case_description()
        assert "Erreur" in result
        assert "Test error" in result

    @pytest.mark.asyncio
    async def test_add_new_hypothesis_success(self):
        """Verify hypothesis addition."""
        kernel = MagicMock(spec=Kernel)
        kernel.invoke = AsyncMock(return_value="Success")

        tools = SherlockTools(kernel)
        result = await tools.add_new_hypothesis("The butler did it", 0.9)
        assert "ajout\u00e9e avec succ\u00e8s" in result
        assert "The butler did it" in result

    @pytest.mark.asyncio
    async def test_add_new_hypothesis_error(self):
        """Verify hypothesis addition handles errors."""
        kernel = MagicMock(spec=Kernel)
        kernel.invoke = AsyncMock(side_effect=RuntimeError("Test error"))

        tools = SherlockTools(kernel)
        result = await tools.add_new_hypothesis("Test hypothesis", 0.5)
        assert "Erreur" in result

    @pytest.mark.asyncio
    async def test_propose_final_solution_dict(self):
        """Verify solution proposal with dict input."""
        kernel = MagicMock(spec=Kernel)
        kernel.invoke = AsyncMock(return_value="Solution recorded")

        tools = SherlockTools(kernel)
        solution = {"suspect": "Mustard", "weapon": "Knife", "room": "Kitchen"}
        result = await tools.propose_final_solution(solution)
        assert "propos\u00e9e avec succ\u00e8s" in result

    @pytest.mark.asyncio
    async def test_propose_final_solution_json_string(self):
        """Verify solution proposal with JSON string input."""
        kernel = MagicMock(spec=Kernel)
        kernel.invoke = AsyncMock(return_value="Solution recorded")

        tools = SherlockTools(kernel)
        solution = json.dumps({"suspect": "Mustard", "weapon": "Knife"})
        result = await tools.propose_final_solution(solution)
        assert "propos\u00e9e avec succ\u00e8s" in result

    @pytest.mark.asyncio
    async def test_propose_final_solution_invalid_json(self):
        """Verify solution proposal handles invalid JSON."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)
        result = await tools.propose_final_solution("not valid json")
        assert "Erreur" in result
        assert "mal format\u00e9e" in result

    @pytest.mark.asyncio
    async def test_propose_final_solution_unsupported_type(self):
        """Verify solution proposal handles unsupported type."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)
        result = await tools.propose_final_solution(12345)
        assert "Erreur" in result
        assert "non support\u00e9" in result

    @pytest.mark.asyncio
    async def test_instant_deduction_json_input(self):
        """Verify instant deduction with JSON input."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)

        elements = json.dumps({
            "suspects": ["Mustard", "Scarlet"],
            "armes": ["Knife", "Revolver"],
            "lieux": ["Kitchen", "Library"]
        })
        result = await tools.instant_deduction(elements)

        deduction = json.loads(result)
        assert "suspect" in deduction
        assert "arme" in deduction
        assert "lieu" in deduction
        assert deduction["method"] == "instant_sherlock_logic"

    @pytest.mark.asyncio
    async def test_instant_deduction_string_input_fallback(self):
        """Verify instant deduction fallback for non-JSON input."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)

        result = await tools.instant_deduction("not json")
        deduction = json.loads(result)
        assert "suspect" in deduction
        # Should use default elements
        assert deduction["suspect"] in ["Colonel Moutarde", "Mme Leblanc", "Mme Pervenche"]

    @pytest.mark.asyncio
    async def test_instant_deduction_logic(self):
        """Verify instant deduction logic selection."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)

        elements = {
            "suspects": ["A", "B", "C"],
            "armes": ["W1", "W2", "W3", "W4"],
            "lieux": ["L1"]
        }
        result = await tools.instant_deduction(json.dumps(elements))
        deduction = json.loads(result)

        # Logic: suspects[-1] = "C"
        assert deduction["suspect"] == "C"
        # Logic: armes[len//2] = armes[2] = "W3"
        assert deduction["arme"] == "W3"
        # Logic: lieux[0] = "L1"
        assert deduction["lieu"] == "L1"

    @pytest.mark.asyncio
    async def test_instant_deduction_empty_elements(self):
        """Verify instant deduction handles empty elements."""
        kernel = MagicMock(spec=Kernel)
        tools = SherlockTools(kernel)

        result = await tools.instant_deduction(json.dumps({}))
        deduction = json.loads(result)
        # Empty dict means .get() returns defaults: ["Suspect Inconnu"], etc.
        # Then selection logic picks from those single-element lists.
        assert deduction["suspect"] == "Suspect Inconnu"
        assert deduction["arme"] == "Arme Inconnue"
        assert deduction["lieu"] == "Lieu Inconnu"


# =====================================================================
# SherlockEnqueteAgent Initialization Tests
# =====================================================================


class TestSherlockEnqueteAgentInitialization:
    """Tests for SherlockEnqueteAgent initialization."""

    def test_default_initialization(self):
        """Verify default initialization."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)
        assert agent.id == "Sherlock"
        assert agent.kernel is kernel
        assert agent._service_id == "chat_completion"
        assert agent.instructions == SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
        assert isinstance(agent._tools, SherlockTools)

    def test_custom_agent_name(self):
        """Verify custom agent name."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel, agent_name="Holmes")
        assert agent.id == "Holmes"

    def test_custom_system_prompt(self):
        """Verify custom system prompt."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        custom_prompt = "You are a detective."
        agent = SherlockEnqueteAgent(kernel, system_prompt=custom_prompt)
        assert agent.instructions == custom_prompt

    def test_custom_service_id(self):
        """Verify custom service ID."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel, service_id="custom_service")
        assert agent._service_id == "custom_service"


# =====================================================================
# SherlockEnqueteAgent Capabilities Tests
# =====================================================================


class TestSherlockEnqueteAgentCapabilities:
    """Tests for SherlockEnqueteAgent capabilities."""

    def test_get_agent_capabilities(self):
        """Verify capabilities dictionary."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)
        caps = agent.get_agent_capabilities()
        assert "get_current_case_description" in caps
        assert "add_new_hypothesis" in caps
        assert "propose_final_solution" in caps
        assert "instant_deduction" in caps


# =====================================================================
# SherlockEnqueteAgent Setup Tests
# =====================================================================


class TestSherlockEnqueteAgentSetup:
    """Tests for SherlockEnqueteAgent setup."""

    def test_setup_agent_components(self):
        """Verify setup stores service ID."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)
        agent.setup_agent_components("test_service_id")
        assert agent._llm_service_id == "test_service_id"


# =====================================================================
# SherlockEnqueteAgent Method Tests
# =====================================================================


class TestSherlockEnqueteAgentMethods:
    """Tests for SherlockEnqueteAgent methods."""

    @pytest.mark.asyncio
    async def test_get_current_case_description(self):
        """Verify case description method."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)
        result = await agent.get_current_case_description()
        assert "Description du cas" in result

    @pytest.mark.asyncio
    async def test_add_new_hypothesis(self):
        """Verify hypothesis addition method."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)
        result = await agent.add_new_hypothesis("Test hypothesis", 0.8)
        assert result["status"] == "success"
        assert result["hypothesis"] == "Test hypothesis"
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_invoke_with_string(self):
        """Verify invoke with string input."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        mock_response = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="Elementary, my dear Watson!",
            name="Sherlock",
        )
        # Use object.__setattr__ to bypass Pydantic V2 validation
        object.__setattr__(agent, "invoke_single", AsyncMock(return_value=mock_response))

        result = await agent.invoke("Analyze the evidence")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].content == "Elementary, my dear Watson!"

    @pytest.mark.asyncio
    async def test_invoke_with_message_history(self):
        """Verify invoke with message history."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        mock_response = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="I see the pattern",
            name="Sherlock",
        )
        # Use object.__setattr__ to bypass Pydantic V2 validation
        object.__setattr__(agent, "invoke_single", AsyncMock(return_value=mock_response))

        messages = [
            ChatMessageContent(role=AuthorRole.USER, content="First message"),
            ChatMessageContent(role=AuthorRole.USER, content="Second message"),
        ]
        result = await agent.invoke(messages)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invoke_stream(self):
        """Verify invoke_stream returns async generator."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        mock_response = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="Streaming response",
        )
        # Use object.__setattr__ to bypass Pydantic V2 validation
        object.__setattr__(agent, "invoke", AsyncMock(return_value=[mock_response]))

        stream = agent.invoke_stream("Test")
        assert hasattr(stream, "__aiter__")

        results = []
        async for item in stream:
            results.extend(item)

        assert len(results) == 1
        assert results[0].content == "Streaming response"

    @pytest.mark.asyncio
    async def test_invoke_single_with_response(self):
        """Verify invoke_single processes messages correctly."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        mock_agent_func = MagicMock()
        kernel.invoke = AsyncMock(return_value="Analysis complete")
        kernel.add_function = MagicMock(return_value=mock_agent_func)

        agent = SherlockEnqueteAgent(kernel)

        messages = [
            ChatMessageContent(role=AuthorRole.USER, content="Analyze this text")
        ]
        result = await agent.invoke_single(messages)

        assert isinstance(result, ChatMessageContent)
        assert result.role == "assistant"
        assert "Analysis complete" in result.content

    @pytest.mark.asyncio
    async def test_invoke_single_no_response(self):
        """Verify invoke_single handles no response."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        mock_agent_func = MagicMock()
        kernel.invoke = AsyncMock(return_value=None)
        kernel.add_function = MagicMock(return_value=mock_agent_func)

        agent = SherlockEnqueteAgent(kernel)

        messages = [ChatMessageContent(role=AuthorRole.USER, content="Test")]
        result = await agent.invoke_single(messages)

        assert result.content == "Je n'ai rien \u00e0 ajouter pour le moment."

    @pytest.mark.asyncio
    async def test_invoke_single_exception_handling(self):
        """Verify invoke_single handles exceptions."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        mock_agent_func = MagicMock()
        kernel.invoke = AsyncMock(side_effect=RuntimeError("Test error"))
        kernel.add_function = MagicMock(return_value=mock_agent_func)

        agent = SherlockEnqueteAgent(kernel)

        messages = [ChatMessageContent(role=AuthorRole.USER, content="Test")]
        result = await agent.invoke_single(messages)

        assert "erreur interne m'emp\u00eache de r\u00e9pondre" in result.content.lower()

    @pytest.mark.asyncio
    async def test_get_response_with_async_generator(self):
        """Verify get_response handles async generator."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        # Create an async generator
        async def mock_stream():
            yield "Response chunk"

        # get_response calls self._get_history which builds a ChatHistory.
        # Provide _get_history via object.__setattr__ since it's not defined on the class.
        mock_history = ChatHistory()
        mock_history.add_user_message("Test")
        object.__setattr__(agent, "_get_history", lambda user_input: mock_history)

        kernel.invoke_stream = MagicMock(return_value=mock_stream())

        result = await agent.get_response("Test")
        assert hasattr(result, "__aiter__")

    @pytest.mark.asyncio
    async def test_get_response_with_mock(self):
        """Verify get_response handles Mock response."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        # Provide _get_history via object.__setattr__ since it's not defined on the class.
        mock_history = ChatHistory()
        mock_history.add_user_message("Test")
        object.__setattr__(agent, "_get_history", lambda user_input: mock_history)

        # Mock invoke_stream returning Mock object
        kernel.invoke_stream = MagicMock(return_value=Mock())

        result = await agent.get_response("Test")
        assert hasattr(result, "__aiter__")


# =====================================================================
# SherlockEnqueteAgent Integration Tests
# =====================================================================


class TestSherlockEnqueteAgentIntegration:
    """Integration tests for SherlockEnqueteAgent."""

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Simulate a full investigation workflow."""
        kernel = _create_mock_kernel()
        kernel.add_plugin = MagicMock()
        kernel.add_function = MagicMock()

        agent = SherlockEnqueteAgent(kernel)

        # Get case description
        case = await agent.get_current_case_description()
        assert case is not None

        # Add hypothesis
        hypothesis_result = await agent.add_new_hypothesis(
            "The killer is Colonel Mustard", 0.85
        )
        assert hypothesis_result["status"] == "success"

        # Invoke with evidence
        mock_response = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="Based on the evidence, I deduce...",
            name="Sherlock",
        )
        # Use object.__setattr__ to bypass Pydantic V2 validation
        object.__setattr__(agent, "invoke_single", AsyncMock(return_value=mock_response))

        result = await agent.invoke("Examine the crime scene")
        assert len(result) == 1
        assert "deduce" in result[0].content.lower()
