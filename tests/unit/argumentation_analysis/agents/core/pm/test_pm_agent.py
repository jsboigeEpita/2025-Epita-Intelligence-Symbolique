"""
Tests for pm_agent.py (ProjectManagerAgent).
"""

import ast
import asyncio
import inspect
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent


def _create_mock_kernel():
    """Helper to create a mock kernel with a ChatCompletionClientBase service."""
    kernel = MagicMock(spec=Kernel)
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.service_id = "test_service"
    kernel.get_service = MagicMock(return_value=mock_service)
    kernel.services = {"test_service": mock_service}
    return kernel


# =====================================================================
# ProjectManagerAgent Initialization Tests
# =====================================================================


class TestProjectManagerAgentInitialization:
    """Tests for ProjectManagerAgent initialization."""

    def test_default_initialization(self):
        """Verify default initialization."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)
        assert agent.id == "ProjectManagerAgent"
        assert agent.kernel is kernel
        assert agent.instructions is not None

    def test_custom_agent_name(self):
        """Verify custom agent name."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel, agent_name="CustomPM")
        assert agent.id == "CustomPM"

    def test_custom_instructions(self):
        """Verify custom instructions can be provided."""
        kernel = _create_mock_kernel()
        custom_instructions = "Custom PM instructions"
        agent = ProjectManagerAgent(kernel, instructions=custom_instructions)
        assert agent.instructions == custom_instructions


# =====================================================================
# ProjectManagerAgent Capabilities Tests
# =====================================================================


class TestProjectManagerAgentCapabilities:
    """Tests for ProjectManagerAgent capabilities."""

    def test_get_agent_capabilities(self):
        """Verify capabilities dictionary is returned."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)
        caps = agent.get_agent_capabilities()
        assert isinstance(caps, dict)
        assert "define_tasks_and_delegate" in caps
        assert "synthesize_results" in caps
        assert "write_conclusion" in caps
        assert "coordinate_analysis_flow" in caps


# =====================================================================
# ProjectManagerAgent Setup Tests
# =====================================================================


class TestProjectManagerAgentSetup:
    """Tests for ProjectManagerAgent component setup."""

    def test_setup_agent_components_adds_functions(self):
        """Verify setup adds kernel functions."""
        kernel = _create_mock_kernel()
        kernel.add_function = MagicMock()
        agent = ProjectManagerAgent(kernel)
        agent.setup_agent_components("test_service_id")
        assert kernel.add_function.called
        assert kernel.add_function.call_count >= 2

    def test_setup_agent_components_handles_exceptions(self):
        """Verify setup handles exceptions gracefully."""
        kernel = _create_mock_kernel()
        kernel.add_function = MagicMock(side_effect=RuntimeError("Test error"))
        agent = ProjectManagerAgent(kernel)
        # Should not raise exception
        agent.setup_agent_components("test_service_id")


# =====================================================================
# ProjectManagerAgent Method Tests
# =====================================================================


class TestProjectManagerAgentMethods:
    """Tests for ProjectManagerAgent methods."""

    @pytest.mark.asyncio
    async def test_define_tasks_and_delegate_success(self):
        """Verify task definition returns result."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value='{"task": "test_task"}')
        kernel.invoke = AsyncMock(return_value=mock_response)

        result = await agent.define_tasks_and_delegate("snapshot", "raw text")
        assert "task" in result

    @pytest.mark.asyncio
    async def test_define_tasks_and_delegate_error_handling(self):
        """Verify task definition handles errors."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        kernel.invoke = AsyncMock(side_effect=RuntimeError("Test error"))

        result = await agent.define_tasks_and_delegate("snapshot", "raw text")
        assert "ERREUR" in result
        assert "Test error" in result

    @pytest.mark.asyncio
    async def test_write_conclusion_success(self):
        """Verify conclusion writing returns result."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value="Conclusion generated")
        kernel.invoke = AsyncMock(return_value=mock_response)

        result = await agent.write_conclusion("snapshot", "raw text")
        assert "Conclusion" in result

    @pytest.mark.asyncio
    async def test_write_conclusion_error_handling(self):
        """Verify conclusion writing handles errors."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        kernel.invoke = AsyncMock(side_effect=RuntimeError("Test error"))

        result = await agent.write_conclusion("snapshot", "raw text")
        assert "ERREUR" in result
        assert "Test error" in result


# =====================================================================
# ProjectManagerAgent Invocation Tests
# =====================================================================


class TestProjectManagerAgentInvocation:
    """Tests for ProjectManagerAgent invocation methods."""

    @pytest.mark.asyncio
    async def test_invoke_single_returns_list(self):
        """Verify invoke_single returns list of messages via invoke_custom.

        #2339: this test used to call ``invoke_custom`` directly and wrap the
        result by hand, because the surviving ``invoke_single(messages)`` could
        not be called at all. It now exercises ``invoke_single`` itself.
        """
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_content = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="Test response",
            name=agent.name,
        )
        # Use object.__setattr__ to bypass Pydantic V2 validation.
        invoke_custom_mock = AsyncMock(return_value=mock_content)
        object.__setattr__(agent, "invoke_custom", invoke_custom_mock)

        result = await agent.invoke_single(kernel, KernelArguments())

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].content == "Test response"
        invoke_custom_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invoke_custom_with_history(self):
        """Verify invoke_custom processes chat history."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        # Mock state manager plugin
        state_manager = MagicMock()
        snapshot_function = AsyncMock(return_value="state_snapshot")
        state_manager.__getitem__ = MagicMock(return_value=snapshot_function)
        kernel.plugins = MagicMock()
        kernel.plugins.get = MagicMock(return_value=state_manager)

        # Mock define_tasks_and_delegate using object.__setattr__ for Pydantic V2
        object.__setattr__(
            agent,
            "define_tasks_and_delegate",
            AsyncMock(return_value='{"task": "test"}'),
        )

        user_message = ChatMessageContent(
            role=AuthorRole.USER,
            content="Test user message",
        )
        args = KernelArguments(chat_history=[user_message])

        result = await agent.invoke_custom(kernel, args)
        assert isinstance(result, ChatMessageContent)
        assert result.role == AuthorRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_invoke_custom_missing_chat_history(self):
        """Verify invoke_custom handles missing chat history."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        with pytest.raises(ValueError, match="chat_history"):
            await agent.invoke_custom(kernel, None)

    @pytest.mark.asyncio
    async def test_invoke_custom_missing_state_manager(self):
        """Verify invoke_custom handles missing state manager."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        kernel.plugins = MagicMock()
        kernel.plugins.get = MagicMock(return_value=None)

        user_message = ChatMessageContent(
            role=AuthorRole.USER,
            content="Test message",
        )
        args = KernelArguments(chat_history=[user_message])

        with pytest.raises(RuntimeError, match="StateManagerPlugin"):
            await agent.invoke_custom(kernel, args)

    @pytest.mark.asyncio
    async def test_invoke_custom_exception_handling(self):
        """Verify invoke_custom handles exceptions in define_tasks_and_delegate."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        # Mock state manager to succeed (snapshot is outside try/except)
        state_manager = MagicMock()
        snapshot_function = AsyncMock(return_value="state_snapshot")
        state_manager.__getitem__ = MagicMock(return_value=snapshot_function)
        kernel.plugins = MagicMock()
        kernel.plugins.get = MagicMock(return_value=state_manager)

        # Make define_tasks_and_delegate fail (this IS inside the try/except block)
        object.__setattr__(
            agent,
            "define_tasks_and_delegate",
            AsyncMock(side_effect=RuntimeError("Test error")),
        )

        user_message = ChatMessageContent(
            role=AuthorRole.USER,
            content="Test message",
        )
        args = KernelArguments(chat_history=[user_message])

        result = await agent.invoke_custom(kernel, args)
        assert "error" in result.content.lower()

    @pytest.mark.asyncio
    async def test_invoke_stream(self):
        """Verify invoke_stream wraps the single response in a stream.

        #2339: this test used to mock ``agent.invoke`` with an ``AsyncMock``,
        which hid the fact that the removed ``invoke_stream`` override did
        ``await self.invoke(...)`` on an async generator. It now exercises the
        inherited ``BaseAgent.invoke_stream`` against the real ``invoke_single``.
        """
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_content = ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content="Streamed response",
            name=agent.name,
        )
        object.__setattr__(agent, "invoke_custom", AsyncMock(return_value=mock_content))

        results = []
        async for item in agent.invoke_stream(kernel, arguments=KernelArguments()):
            results.append(item)

        # invoke_stream wraps the single invoke_single response in a stream
        assert len(results) == 1
        assert results[0] == [mock_content]


# =====================================================================
# Regression guard for #2339 — invoke_single defined twice
# =====================================================================


class TestInvokeSingleDefinedOnce2339:
    """#2339: ``invoke_single`` was defined twice in ``ProjectManagerAgent``.

    The second definition (``invoke_single(self, messages)``) overwrote the
    contract-honouring one at class creation, and its body delegated to
    ``self.invoke_single(self.kernel, arguments)`` — i.e. to itself, under a
    signature accepting a single positional argument. Measured symptom on
    ``main`` for every entry point below::

        TypeError: ProjectManagerAgent.invoke_single() takes 2 positional
        arguments but 3 were given
    """

    def test_invoke_single_is_defined_exactly_once(self):
        """A second ``def invoke_single`` would silently shadow the first."""
        source = inspect.getsource(ProjectManagerAgent)
        tree = ast.parse(textwrap.dedent(source))
        class_def = tree.body[0]
        assert isinstance(class_def, ast.ClassDef)

        definitions = [
            node
            for node in class_def.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "invoke_single"
        ]
        assert len(definitions) == 1, (
            "ProjectManagerAgent must define invoke_single exactly once; "
            f"found {len(definitions)} definitions "
            f"(lines {[d.lineno for d in definitions]})"
        )

    def test_invoke_single_honours_base_agent_signature(self):
        """The retained definition must accept ``(kernel, arguments)``."""
        params = list(inspect.signature(ProjectManagerAgent.invoke_single).parameters)
        assert params[:3] == ["self", "kernel", "arguments"], (
            "invoke_single must keep the (kernel, arguments) signature used by "
            f"get_response and by the production caller; got {params}"
        )

    @pytest.mark.asyncio
    async def test_invoke_single_delegates_to_invoke_custom_without_recursing(self):
        """Born-red: raised TypeError on main instead of delegating."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_content = ChatMessageContent(
            role=AuthorRole.ASSISTANT, content="Delegated", name=agent.name
        )
        object.__setattr__(agent, "invoke_custom", AsyncMock(return_value=mock_content))

        # Count how many times the body of invoke_single is entered for a
        # single external call: self-delegation would make this > 1.
        entries = []
        original = ProjectManagerAgent.invoke_single

        async def counting_invoke_single(self, *args, **kwargs):
            entries.append((args, kwargs))
            return await original(self, *args, **kwargs)

        with patch.object(ProjectManagerAgent, "invoke_single", counting_invoke_single):
            result = await agent.invoke_single(kernel, KernelArguments())

        assert result == [mock_content]
        assert len(entries) == 1, (
            "invoke_single must delegate to invoke_custom, not to itself; "
            f"body was entered {len(entries)} times"
        )

    @pytest.mark.asyncio
    async def test_get_response_reaches_invoke_custom(self):
        """Born-red: ``get_response`` died in the same TypeError on main."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_content = ChatMessageContent(
            role=AuthorRole.ASSISTANT, content="From get_response", name=agent.name
        )
        invoke_custom_mock = AsyncMock(return_value=mock_content)
        object.__setattr__(agent, "invoke_custom", invoke_custom_mock)

        messages = [ChatMessageContent(role=AuthorRole.USER, content="Bonjour")]
        result = await agent.get_response(
            kernel, KernelArguments(chat_history=messages)
        )

        assert result == [mock_content]
        invoke_custom_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invoke_stream_accepts_the_production_call_shape(self):
        """Born-red: the removed override rejected ``arguments=``.

        Mirrors ``orchestration/enhanced_pm_analysis_runner.py``, which calls
        ``pm_agent.invoke_stream(self.kernel, arguments=arguments)`` and then
        iterates each streamed item as a list of messages.
        """
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        mock_content = ChatMessageContent(
            role=AuthorRole.ASSISTANT, content="Streamed", name=agent.name
        )
        object.__setattr__(agent, "invoke_custom", AsyncMock(return_value=mock_content))

        messages = [ChatMessageContent(role=AuthorRole.USER, content="Bonjour")]
        arguments = KernelArguments(chat_history=messages)

        collected = []
        async for message_list in agent.invoke_stream(kernel, arguments=arguments):
            for msg_content in message_list:
                collected.append(msg_content)

        assert collected == [mock_content]


# =====================================================================
# ProjectManagerAgent Integration Tests
# =====================================================================


class TestProjectManagerAgentIntegration:
    """Integration tests for ProjectManagerAgent."""

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Simulate a full workflow with task definition and conclusion."""
        kernel = _create_mock_kernel()
        agent = ProjectManagerAgent(kernel)

        # Mock task definition
        mock_task_response = MagicMock()
        mock_task_response.__str__ = MagicMock(
            return_value='{"agent": "TestAgent", "task": "Analyze text"}'
        )
        kernel.invoke = AsyncMock(return_value=mock_task_response)

        # Define task
        task_result = await agent.define_tasks_and_delegate("state", "text")
        assert "agent" in task_result

        # Mock conclusion writing
        mock_conclusion_response = MagicMock()
        mock_conclusion_response.__str__ = MagicMock(
            return_value="Analysis complete. Conclusion: Valid argument."
        )
        kernel.invoke = AsyncMock(return_value=mock_conclusion_response)

        # Write conclusion
        conclusion = await agent.write_conclusion("final_state", "text")
        assert "Conclusion" in conclusion
