"""
Tests for multi-turn conversational pipeline (Issue #68).

Covers:
- TurnResult dataclass
- ConversationConfig dataclass
- ConversationalPipeline (multi-turn loop)
- WorkflowTurnStrategy (DAG-based turns)
- GroupChatTurnStrategy (AgentGroupChat turns)
- Convergence logic
- Confidence extraction
- Edge cases
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.orchestration.turn_protocol import (
    ConversationConfig,
    TurnResult,
    TurnStrategy,
)
from argumentation_analysis.orchestration.conversational_executor import (
    ConversationalPipeline,
    GroupChatTurnStrategy,
    WorkflowTurnStrategy,
    _extract_confidence,
    _extract_questions,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeRegistration:
    """Mimics ComponentRegistration for tests."""

    name: str
    invoke: Optional[Any] = None


def make_registry(*capabilities_map):
    """Build a mock registry from (capability, provider_name, invoke_fn) tuples."""
    registry = MagicMock()
    mapping = {}
    for cap, name, fn in capabilities_map:
        mapping.setdefault(cap, []).append(FakeRegistration(name=name, invoke=fn))

    def find(cap):
        return mapping.get(cap, [])

    registry.find_for_capability = MagicMock(side_effect=find)
    return registry


def make_phase_result(name, status=PhaseStatus.COMPLETED, output=None):
    """Quick PhaseResult creation."""
    return PhaseResult(
        phase_name=name,
        status=status,
        capability="test_cap",
        output=output,
    )


class MockTurnStrategy(TurnStrategy):
    """Test strategy that returns pre-configured TurnResults."""

    def __init__(self, results: List[TurnResult]):
        self._results = results
        self._call_count = 0
        self.contexts_received = []

    async def execute_turn(self, input_data, context, state=None):
        self.contexts_received.append(dict(context))
        idx = min(self._call_count, len(self._results) - 1)
        result = self._results[idx]
        self._call_count += 1
        return result


class FailingTurnStrategy(TurnStrategy):
    """Strategy that raises on the Nth call."""

    def __init__(self, fail_on: int = 1):
        self._fail_on = fail_on
        self._call_count = 0

    async def execute_turn(self, input_data, context, state=None):
        self._call_count += 1
        if self._call_count >= self._fail_on:
            raise RuntimeError("Strategy failed")
        return TurnResult(
            turn_number=context.get("turn_number", 1),
            phase_results={"p1": make_phase_result("p1")},
            confidence=0.5,
            needs_refinement=True,
        )


# ===========================================================================
# TestTurnResult
# ===========================================================================


class TestTurnResult:
    """Tests for TurnResult dataclass."""

    def test_creation(self):
        tr = TurnResult(
            turn_number=1,
            phase_results={"p1": make_phase_result("p1")},
            confidence=0.7,
            needs_refinement=False,
        )
        assert tr.turn_number == 1
        assert tr.confidence == 0.7
        assert not tr.needs_refinement

    def test_is_converged_true(self):
        tr = TurnResult(
            turn_number=2,
            phase_results={"p1": make_phase_result("p1", PhaseStatus.COMPLETED)},
            confidence=0.9,
            needs_refinement=False,
        )
        assert tr.is_converged() is True

    def test_is_converged_false_needs_refinement(self):
        tr = TurnResult(
            turn_number=1,
            phase_results={"p1": make_phase_result("p1")},
            confidence=0.9,
            needs_refinement=True,
        )
        assert tr.is_converged() is False

    def test_get_output(self):
        tr = TurnResult(
            turn_number=1,
            phase_results={
                "p1": make_phase_result("p1", output={"data": "value"}),
                "p2": make_phase_result("p2", output=42),
            },
            confidence=0.5,
            needs_refinement=False,
        )
        assert tr.get_output("p1") == {"data": "value"}
        assert tr.get_output("p2") == 42
        assert tr.get_output("missing") is None

    def test_defaults(self):
        tr = TurnResult(
            turn_number=1,
            phase_results={},
            confidence=0.5,
            needs_refinement=False,
        )
        assert tr.questions_for_user == []
        assert tr.duration_seconds == 0.0
        assert tr.summary is None


# ===========================================================================
# TestConversationConfig
# ===========================================================================


class TestConversationConfig:
    """Tests for ConversationConfig dataclass."""

    def test_defaults(self):
        cfg = ConversationConfig()
        assert cfg.max_rounds == 3
        assert cfg.convergence_fn is None
        assert cfg.confidence_threshold == 0.8
        assert cfg.timeout_per_round_seconds is None

    def test_custom_values(self):
        fn = lambda prev, curr: True
        cfg = ConversationConfig(
            max_rounds=10,
            convergence_fn=fn,
            confidence_threshold=0.95,
            timeout_per_round_seconds=30.0,
        )
        assert cfg.max_rounds == 10
        assert cfg.convergence_fn is fn

    def test_convergence_fn_callable(self):
        cfg = ConversationConfig(
            convergence_fn=lambda p, c: p.confidence == c.confidence
        )
        tr1 = TurnResult(1, {}, 0.5, False)
        tr2 = TurnResult(2, {}, 0.5, False)
        assert cfg.convergence_fn(tr1, tr2) is True


# ===========================================================================
# TestConversationalPipeline
# ===========================================================================


class TestConversationalPipeline:
    """Tests for the multi-turn ConversationalPipeline."""

    async def test_single_round_high_confidence(self):
        """Single round with high confidence exits immediately."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {"p1": make_phase_result("p1")}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(
            strategy, ConversationConfig(max_rounds=5, confidence_threshold=0.8)
        )
        result = await pipeline.execute("test input")
        assert result["status"] == "high_confidence"
        assert len(result["rounds"]) == 1
        assert result["final_turn_result"].confidence == 0.9

    async def test_multi_round_reaches_max(self):
        """Low confidence rounds hit max_rounds."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {"p1": make_phase_result("p1")}, 0.3, True),
                TurnResult(2, {"p1": make_phase_result("p1")}, 0.4, True),
                TurnResult(3, {"p1": make_phase_result("p1")}, 0.5, True),
            ]
        )
        pipeline = ConversationalPipeline(
            strategy, ConversationConfig(max_rounds=3, confidence_threshold=0.8)
        )
        result = await pipeline.execute("test")
        assert result["status"] == "max_rounds"
        assert len(result["rounds"]) == 3

    async def test_convergence_stops_early(self):
        """Custom convergence function stops execution."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {"p1": make_phase_result("p1")}, 0.5, True),
                TurnResult(2, {"p1": make_phase_result("p1")}, 0.5, True),
            ]
        )
        pipeline = ConversationalPipeline(
            strategy,
            ConversationConfig(
                max_rounds=5,
                confidence_threshold=0.99,
                convergence_fn=lambda prev, curr: prev.confidence == curr.confidence,
            ),
        )
        result = await pipeline.execute("test")
        assert result["status"] == "converged"
        assert len(result["rounds"]) == 2

    async def test_context_carries_turn_number(self):
        """Each round receives incrementing turn_number in context."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {}, 0.3, True),
                TurnResult(2, {}, 0.3, True),
                TurnResult(3, {}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(strategy, ConversationConfig(max_rounds=3))
        await pipeline.execute("test")
        assert strategy.contexts_received[0]["turn_number"] == 1
        assert strategy.contexts_received[1]["turn_number"] == 2
        assert strategy.contexts_received[2]["turn_number"] == 3

    async def test_previous_outputs_in_context(self):
        """Subsequent rounds get previous_outputs from prior turn."""
        strategy = MockTurnStrategy(
            [
                TurnResult(
                    1, {"p1": make_phase_result("p1", output={"score": 5})}, 0.3, True
                ),
                TurnResult(
                    2, {"p1": make_phase_result("p1", output={"score": 8})}, 0.9, False
                ),
            ]
        )
        pipeline = ConversationalPipeline(strategy, ConversationConfig(max_rounds=3))
        await pipeline.execute("test")
        # First round: no previous
        assert strategy.contexts_received[0].get("previous_outputs") is None
        # Second round: has previous outputs
        assert strategy.contexts_received[1]["previous_outputs"]["p1"] == {"score": 5}

    async def test_failed_round(self):
        """Strategy exception produces failed status."""
        strategy = FailingTurnStrategy(fail_on=1)
        pipeline = ConversationalPipeline(strategy, ConversationConfig(max_rounds=3))
        result = await pipeline.execute("test")
        assert result["status"] == "failed"
        assert "Strategy failed" in result["summary"]

    async def test_convergence_fn_exception_continues(self):
        """Convergence function error doesn't crash — continues looping."""

        def bad_convergence(prev, curr):
            raise ValueError("convergence boom")

        strategy = MockTurnStrategy(
            [
                TurnResult(1, {}, 0.3, True),
                TurnResult(2, {}, 0.3, True),
                TurnResult(3, {}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(
            strategy,
            ConversationConfig(max_rounds=3, convergence_fn=bad_convergence),
        )
        result = await pipeline.execute("test")
        # Convergence fn always fails → reaches round 3 where confidence hits threshold
        assert result["status"] == "high_confidence"

    async def test_result_dict_structure(self):
        """Verify complete result dict structure."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {"p1": make_phase_result("p1")}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(strategy)
        result = await pipeline.execute("test")
        assert "status" in result
        assert "rounds" in result
        assert "final_turn_result" in result
        assert "total_duration" in result
        assert "summary" in result
        assert isinstance(result["total_duration"], float)


# ===========================================================================
# TestWorkflowTurnStrategy
# ===========================================================================


class TestWorkflowTurnStrategy:
    """Tests for WorkflowTurnStrategy."""

    async def test_executes_workflow(self):
        invoke_fn = AsyncMock(return_value={"result": "ok", "confidence": 0.7})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("test_wf").add_phase("p1", capability="cap_a").build()
        strategy = WorkflowTurnStrategy(wf, registry)

        result = await strategy.execute_turn("input", {"turn_number": 1})
        assert isinstance(result, TurnResult)
        assert result.phase_results["p1"].status == PhaseStatus.COMPLETED
        invoke_fn.assert_called_once()

    async def test_extracts_confidence_from_output(self):
        invoke_fn = AsyncMock(return_value={"confidence": 0.85})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("test_wf").add_phase("p1", capability="cap_a").build()
        strategy = WorkflowTurnStrategy(wf, registry)

        result = await strategy.execute_turn("input", {"turn_number": 1})
        assert result.confidence == 0.85

    async def test_failed_phase_sets_needs_refinement(self):
        registry = make_registry()  # no providers → FAILED
        wf = WorkflowBuilder("test_wf").add_phase("p1", capability="cap_a").build()
        strategy = WorkflowTurnStrategy(wf, registry)

        result = await strategy.execute_turn("input", {"turn_number": 1})
        assert result.needs_refinement is True

    async def test_state_passed_through(self):
        mock_state = MagicMock()
        invoke_fn = AsyncMock(return_value={"confidence": 0.6})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("test_wf").add_phase("p1", capability="cap_a").build()
        strategy = WorkflowTurnStrategy(wf, registry)

        await strategy.execute_turn("input", {"turn_number": 1}, state=mock_state)
        # State should be accessible in the invoke context
        call_args = invoke_fn.call_args
        ctx = call_args[0][1]  # second positional arg is context
        assert ctx.get("unified_state") is mock_state

    async def test_multi_phase_workflow(self):
        invoke_a = AsyncMock(return_value={"confidence": 0.6})
        invoke_b = AsyncMock(return_value={"confidence": 0.8})
        registry = make_registry(
            ("cap_a", "prov_a", invoke_a),
            ("cap_b", "prov_b", invoke_b),
        )
        wf = (
            WorkflowBuilder("multi")
            .add_phase("p1", capability="cap_a")
            .add_phase("p2", capability="cap_b", depends_on=["p1"])
            .build()
        )
        strategy = WorkflowTurnStrategy(wf, registry)
        result = await strategy.execute_turn("input", {"turn_number": 1})

        assert len(result.phase_results) == 2
        # Average confidence: (0.6 + 0.8) / 2 = 0.7
        assert abs(result.confidence - 0.7) < 0.01

    async def test_turn_number_from_context(self):
        invoke_fn = AsyncMock(return_value={"confidence": 0.5})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("test_wf").add_phase("p1", capability="cap_a").build()
        strategy = WorkflowTurnStrategy(wf, registry)

        result = await strategy.execute_turn("input", {"turn_number": 42})
        assert result.turn_number == 42


# ===========================================================================
# TestGroupChatTurnStrategy
# ===========================================================================


class TestGroupChatTurnStrategy:
    """Tests for GroupChatTurnStrategy."""

    async def test_creates_and_invokes_group_chat(self):
        mock_agent = MagicMock()
        mock_agent.name = "agent1"

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.invoke = AsyncMock(return_value=["response_1"])
        mock_chat_cls.return_value = mock_chat_instance

        strategy = GroupChatTurnStrategy(agents=[mock_agent])

        with patch(
            "argumentation_analysis.orchestration.conversational_executor.GroupChatTurnStrategy.execute_turn",
            wraps=strategy.execute_turn,
        ):
            with patch(
                "argumentation_analysis.orchestration.cluedo_extended_orchestrator.AgentGroupChat",
                mock_chat_cls,
            ):
                result = await strategy.execute_turn("test", {"turn_number": 1})

        assert isinstance(result, TurnResult)

    async def test_handles_empty_chat(self):
        """Empty agent list produces empty results."""
        strategy = GroupChatTurnStrategy(agents=[])
        result = await strategy.execute_turn("test", {"turn_number": 1})
        assert isinstance(result, TurnResult)
        # Either empty phase_results or needs_refinement
        assert result.needs_refinement or len(result.phase_results) == 0

    async def test_messages_to_phase_results(self):
        """Test message-to-PhaseResult conversion."""
        strategy = GroupChatTurnStrategy(agents=[])

        # Simulate messages with name/content attributes
        msg1 = MagicMock()
        msg1.name = "Watson"
        msg1.content = "Analysis complete"

        msg2 = MagicMock()
        msg2.name = "Sherlock"
        msg2.content = "I concur"

        results = strategy._messages_to_phase_results([msg1, msg2])
        assert "Watson" in results
        assert "Sherlock" in results
        assert results["Watson"].output == "Analysis complete"
        assert results["Sherlock"].status == PhaseStatus.COMPLETED

    async def test_selection_strategy_passed(self):
        """Selection strategy is passed to AgentGroupChat."""
        mock_selection = MagicMock()
        mock_agent = MagicMock()

        mock_chat_cls = MagicMock()
        mock_chat_instance = MagicMock()
        mock_chat_instance.invoke = AsyncMock(return_value=[])
        mock_chat_cls.return_value = mock_chat_instance

        strategy = GroupChatTurnStrategy(
            agents=[mock_agent], selection_strategy=mock_selection
        )

        with patch(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator.AgentGroupChat",
            mock_chat_cls,
        ):
            await strategy.execute_turn("test", {"turn_number": 1})

        mock_chat_cls.assert_called_once_with(
            agents=[mock_agent],
            selection_strategy=mock_selection,
            termination_strategy=None,
        )

    async def test_extracts_confidence_from_dict_messages(self):
        """When agent returns dict with confidence, it's extracted."""
        strategy = GroupChatTurnStrategy(agents=[])

        msg = MagicMock()
        msg.name = "analyst"
        msg.content = {"confidence": 0.75, "analysis": "complete"}

        results = strategy._messages_to_phase_results([msg])
        conf = _extract_confidence(results)
        assert conf == 0.75


# ===========================================================================
# TestConfidenceExtraction
# ===========================================================================


class TestConfidenceExtraction:
    """Tests for _extract_confidence helper."""

    def test_extracts_from_dict(self):
        results = {
            "p1": make_phase_result("p1", output={"confidence": 0.8}),
        }
        assert _extract_confidence(results) == 0.8

    def test_averages_multiple(self):
        results = {
            "p1": make_phase_result("p1", output={"confidence": 0.6}),
            "p2": make_phase_result("p2", output={"confidence": 0.8}),
        }
        assert abs(_extract_confidence(results) - 0.7) < 0.01

    def test_ignores_non_dict(self):
        results = {
            "p1": make_phase_result("p1", output="just a string"),
        }
        assert _extract_confidence(results) == 0.5  # default

    def test_ignores_missing_confidence_key(self):
        results = {
            "p1": make_phase_result("p1", output={"other": "data"}),
        }
        assert _extract_confidence(results) == 0.5

    def test_handles_failed_phases(self):
        results = {
            "p1": make_phase_result(
                "p1", PhaseStatus.FAILED, output={"confidence": 0.9}
            ),
        }
        assert _extract_confidence(results) == 0.5  # failed phases ignored


# ===========================================================================
# TestQuestionExtraction
# ===========================================================================


class TestQuestionExtraction:
    """Tests for _extract_questions helper."""

    def test_extracts_questions(self):
        results = {
            "p1": make_phase_result(
                "p1", output={"user_question": "What do you mean?"}
            ),
        }
        questions = _extract_questions(results)
        assert questions == ["What do you mean?"]

    def test_empty_when_no_questions(self):
        results = {
            "p1": make_phase_result("p1", output={"data": "value"}),
        }
        assert _extract_questions(results) == []

    def test_handles_non_string_question(self):
        results = {
            "p1": make_phase_result("p1", output={"user_question": 123}),
        }
        assert _extract_questions(results) == []  # non-string ignored


# ===========================================================================
# TestSummary
# ===========================================================================


class TestSummary:
    """Tests for summary generation."""

    async def test_summary_format(self):
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {"p1": make_phase_result("p1")}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(strategy)
        result = await pipeline.execute("test")
        assert "1 round(s)" in result["summary"]
        assert "high_confidence" in result["summary"]

    async def test_multi_round_summary(self):
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {}, 0.3, True),
                TurnResult(2, {}, 0.4, True),
                TurnResult(3, {}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(strategy, ConversationConfig(max_rounds=3))
        result = await pipeline.execute("test")
        assert "3 round(s)" in result["summary"]


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Edge case tests."""

    async def test_empty_workflow_strategy(self):
        """Empty workflow with no phases."""
        registry = make_registry()
        wf = WorkflowBuilder("empty").build()
        strategy = WorkflowTurnStrategy(wf, registry)
        result = await strategy.execute_turn("test", {"turn_number": 1})
        assert isinstance(result, TurnResult)
        assert len(result.phase_results) == 0

    async def test_both_strategies_produce_compatible_results(self):
        """WorkflowTurnStrategy and GroupChatTurnStrategy both return TurnResult."""
        # Workflow strategy
        invoke_fn = AsyncMock(return_value={"confidence": 0.7})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("wf").add_phase("p1", capability="cap_a").build()
        wf_strategy = WorkflowTurnStrategy(wf, registry)
        wf_result = await wf_strategy.execute_turn("test", {"turn_number": 1})

        # GroupChat strategy
        gc_strategy = GroupChatTurnStrategy(agents=[])
        gc_result = await gc_strategy.execute_turn("test", {"turn_number": 1})

        # Both produce TurnResult
        assert isinstance(wf_result, TurnResult)
        assert isinstance(gc_result, TurnResult)
        assert hasattr(wf_result, "confidence")
        assert hasattr(gc_result, "confidence")

    async def test_pipeline_with_base_context(self):
        """Base context is merged into each round's context."""
        strategy = MockTurnStrategy(
            [
                TurnResult(1, {}, 0.9, False),
            ]
        )
        pipeline = ConversationalPipeline(strategy)
        await pipeline.execute("test", context={"custom_key": "custom_value"})
        assert strategy.contexts_received[0]["custom_key"] == "custom_value"
        assert strategy.contexts_received[0]["turn_number"] == 1
