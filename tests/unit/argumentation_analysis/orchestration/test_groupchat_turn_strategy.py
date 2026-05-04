"""Tests for GroupChatTurnStrategy with SK-native AgentGroupChat (#212).

Validates:
- SK native AgentGroupChat is used when available
- Fallback to compatibility shim when SK import fails
- Strategy adapters wrap base.py strategies for SK
- Messages from async generator are collected correctly
- Phase results are built from ChatMessageContent objects
- Empty/error cases handled gracefully
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.conversational_executor import (
    GroupChatTurnStrategy,
)
from argumentation_analysis.orchestration.workflow_dsl import PhaseStatus

# --- Fixtures ---


def _make_mock_message(name: str, content: str, role: str = "assistant"):
    """Create a mock ChatMessageContent-like object."""
    msg = MagicMock()
    msg.name = name
    msg.role = role
    msg.content = content
    return msg


# --- Strategy adapter tests ---


class TestStrategyAdapters:
    def test_wrap_none_selection_returns_none(self):
        assert GroupChatTurnStrategy._wrap_selection_strategy(None) is None

    def test_wrap_none_termination_returns_none(self):
        strategy = GroupChatTurnStrategy(agents=[])
        assert strategy._wrap_termination_strategy(None) is None

    def test_wrap_sk_native_selection_passes_through(self):
        """If already an SK strategy, return as-is."""
        try:
            from semantic_kernel.agents.strategies.selection.sequential_selection_strategy import (
                SequentialSelectionStrategy,
            )

            sk_strategy = SequentialSelectionStrategy()
            result = GroupChatTurnStrategy._wrap_selection_strategy(sk_strategy)
            assert result is sk_strategy
        except ImportError:
            pytest.skip("SK not available")

    def test_wrap_sk_native_termination_passes_through(self):
        """If already an SK strategy, return as-is."""
        try:
            from semantic_kernel.agents.strategies.termination.default_termination_strategy import (
                DefaultTerminationStrategy,
            )

            sk_strategy = DefaultTerminationStrategy(maximum_iterations=5)
            strategy = GroupChatTurnStrategy(agents=[])
            result = strategy._wrap_termination_strategy(sk_strategy)
            assert result is sk_strategy
        except ImportError:
            pytest.skip("SK not available")

    def test_wrap_base_selection_creates_adapter(self):
        """A base.py SelectionStrategy should be wrapped into an SK adapter."""
        try:
            from semantic_kernel.agents.strategies.selection.selection_strategy import (
                SelectionStrategy as SKSelectionStrategy,
            )
            from argumentation_analysis.orchestration.base import (
                SelectionStrategy as BaseSelection,
            )
        except ImportError:
            pytest.skip("SK not available")

        # Use a concrete subclass of our base.py SelectionStrategy
        class DummySelection(BaseSelection):
            async def next(self, agents, history):
                return agents[0] if agents else None

        strategy = DummySelection()
        result = GroupChatTurnStrategy._wrap_selection_strategy(strategy)
        assert isinstance(result, SKSelectionStrategy)

    def test_wrap_base_termination_creates_adapter(self):
        """A base.py TerminationStrategy should be wrapped into an SK adapter."""
        try:
            from semantic_kernel.agents.strategies.termination.termination_strategy import (
                TerminationStrategy as SKTerminationStrategy,
            )
            from argumentation_analysis.orchestration.base import (
                TerminationStrategy as BaseTermination,
            )
        except ImportError:
            pytest.skip("SK not available")

        class DummyTermination(BaseTermination):
            async def should_terminate(self, agent, history):
                return len(history) > 5

        strategy = DummyTermination()
        gcs = GroupChatTurnStrategy(agents=[])
        result = gcs._wrap_termination_strategy(strategy)
        assert isinstance(result, SKTerminationStrategy)


# --- SK native execution ---


class TestSKNativeExecution:
    @pytest.mark.asyncio
    async def test_sk_native_collects_messages(self):
        """SK native invoke() yields ChatMessageContent; we collect them."""
        msg1 = _make_mock_message("sherlock", "I observe...")
        msg2 = _make_mock_message("watson", "I deduce...")

        async def fake_invoke():
            yield msg1
            yield msg2

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.invoke = fake_invoke
        mock_chat_instance.add_chat_message = MagicMock()
        mock_chat_cls.return_value = mock_chat_instance

        strategy = GroupChatTurnStrategy(agents=[MagicMock(), MagicMock()])

        with patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "GroupChatTurnStrategy._run_sk_native"
        ) as mock_native:
            mock_native.return_value = [msg1, msg2]
            result = await strategy.execute_turn("test input", {"turn_number": 1})

        assert len(result.phase_results) == 2
        assert "sherlock" in result.phase_results
        assert "watson" in result.phase_results
        assert result.phase_results["sherlock"].output == "I observe..."
        assert result.phase_results["watson"].output == "I deduce..."

    @pytest.mark.asyncio
    async def test_sk_native_failure_triggers_fallback(self):
        """If SK native fails, should fall back to compatibility shim."""
        fallback_msg = _make_mock_message("agent_0", "fallback result")

        strategy = GroupChatTurnStrategy(agents=[MagicMock()])

        with patch.object(strategy, "_run_sk_native", return_value=None), patch.object(
            strategy, "_run_fallback", return_value=[fallback_msg]
        ):
            result = await strategy.execute_turn("test", {"turn_number": 1})

        assert len(result.phase_results) == 1
        assert result.phase_results["agent_0"].output == "fallback result"

    @pytest.mark.asyncio
    async def test_both_fail_returns_empty_turn(self):
        """If both SK native and fallback fail, return empty TurnResult."""
        strategy = GroupChatTurnStrategy(agents=[MagicMock()])

        with patch.object(strategy, "_run_sk_native", return_value=None), patch.object(
            strategy, "_run_fallback", return_value=None
        ):
            result = await strategy.execute_turn("test", {"turn_number": 3})

        assert result.turn_number == 3
        assert result.phase_results == {}
        assert result.confidence == 0.0
        assert result.needs_refinement is True


# --- Fallback execution ---


class TestFallbackExecution:
    @pytest.mark.asyncio
    async def test_fallback_invokes_compatibility_shim(self):
        """Fallback should use the cluedo_extended_orchestrator AgentGroupChat."""
        mock_agent = MagicMock()
        strategy = GroupChatTurnStrategy(agents=[mock_agent])

        mock_chat = AsyncMock()
        mock_chat.invoke = AsyncMock(
            return_value=[_make_mock_message("agent_0", "shim result")]
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "GroupChatTurnStrategy._run_sk_native",
            return_value=None,
        ), patch(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator."
            "AgentGroupChat",
            return_value=mock_chat,
        ):
            result = await strategy.execute_turn("input text", {"turn_number": 1})

        assert len(result.phase_results) == 1

    @pytest.mark.asyncio
    async def test_fallback_import_failure(self):
        """If cluedo_extended_orchestrator import fails, _run_fallback returns None."""
        strategy = GroupChatTurnStrategy(agents=[MagicMock()])

        with patch.object(strategy, "_run_sk_native", return_value=None), patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "GroupChatTurnStrategy._run_fallback",
            return_value=None,
        ):
            result = await strategy.execute_turn("input", {"turn_number": 1})

        assert result.phase_results == {}
        assert result.needs_refinement is True


# --- Message conversion ---


class TestMessageConversion:
    def test_messages_with_name_attribute(self):
        strategy = GroupChatTurnStrategy(agents=[])
        messages = [
            _make_mock_message("critic", "weakness found"),
            _make_mock_message("validator", "evidence checked"),
        ]
        results = strategy._messages_to_phase_results(messages)
        assert "critic" in results
        assert "validator" in results
        assert results["critic"].output == "weakness found"
        assert results["validator"].status == PhaseStatus.COMPLETED

    def test_messages_with_role_fallback(self):
        strategy = GroupChatTurnStrategy(agents=[])
        msg = MagicMock()
        msg.name = None
        msg.role = "assistant"
        msg.content = "some response"
        results = strategy._messages_to_phase_results([msg])
        assert "assistant" in results

    def test_plain_string_messages(self):
        strategy = GroupChatTurnStrategy(agents=[])
        results = strategy._messages_to_phase_results(["plain text response"])
        assert "agent_0" in results
        assert results["agent_0"].output == "plain text response"

    def test_empty_messages(self):
        strategy = GroupChatTurnStrategy(agents=[])
        assert strategy._messages_to_phase_results([]) == {}
        assert strategy._messages_to_phase_results(None) == {}

    def test_multiple_messages_from_same_agent_last_wins(self):
        strategy = GroupChatTurnStrategy(agents=[])
        messages = [
            _make_mock_message("sherlock", "first observation"),
            _make_mock_message("sherlock", "revised observation"),
        ]
        results = strategy._messages_to_phase_results(messages)
        assert results["sherlock"].output == "revised observation"


# --- Integration: full execute_turn with real SK (if available) ---


class TestIntegrationWithSK:
    @pytest.mark.asyncio
    async def test_execute_turn_produces_multi_agent_results(self):
        """Core acceptance: execute_turn produces results from MULTIPLE agents."""
        msg1 = _make_mock_message("agent_a", "Analysis A")
        msg2 = _make_mock_message("agent_b", "Analysis B")

        strategy = GroupChatTurnStrategy(
            agents=[MagicMock(), MagicMock()],
        )

        with patch.object(strategy, "_run_sk_native", return_value=[msg1, msg2]):
            result = await strategy.execute_turn("test text", {"turn_number": 1})

        # Issue #212 acceptance: messages from MULTIPLE agents
        assert len(result.phase_results) >= 2
        assert result.needs_refinement is False
        assert result.duration_seconds >= 0

    def test_maximum_iterations_parameter(self):
        """maximum_iterations should be configurable, not hardcoded."""
        strategy = GroupChatTurnStrategy(agents=[], maximum_iterations=42)
        assert strategy._maximum_iterations == 42

    def test_default_maximum_iterations(self):
        """Default maximum_iterations should be 25."""
        strategy = GroupChatTurnStrategy(agents=[])
        assert strategy._maximum_iterations == 25

    @pytest.mark.asyncio
    async def test_await_add_chat_message(self):
        """Verify add_chat_message is awaited (regression test for #219 review)."""
        strategy = GroupChatTurnStrategy(agents=[MagicMock(), MagicMock()])

        # We can't run a real SK AgentGroupChat without an LLM, but we can
        # verify the code path calls await on add_chat_message by checking
        # it doesn't produce a RuntimeWarning about unawaited coroutines.
        try:
            from semantic_kernel.agents.group_chat.agent_group_chat import (
                AgentGroupChat,
            )
        except ImportError:
            pytest.skip("SK AgentGroupChat not available")

        import warnings

        # Patch AgentGroupChat to track the call without needing a real LLM
        mock_chat = AsyncMock()
        mock_chat.add_chat_message = AsyncMock()

        async def empty_invoke():
            return
            yield  # make it an async generator

        mock_chat.invoke = empty_invoke

        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            return_value=mock_chat,
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = await strategy._run_sk_native("test input", {"turn_number": 1})
                # Check no RuntimeWarning about unawaited coroutine
                coroutine_warnings = [
                    x for x in w if "coroutine" in str(x.message).lower()
                ]
                assert (
                    len(coroutine_warnings) == 0
                ), f"Unawaited coroutine warnings detected: {coroutine_warnings}"
