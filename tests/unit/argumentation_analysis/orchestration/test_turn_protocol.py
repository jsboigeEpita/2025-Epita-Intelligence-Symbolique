"""
Tests for orchestration/turn_protocol.py.

Covers TurnResult, ConversationConfig, and TurnStrategy abstractions.
"""

import pytest
from unittest.mock import AsyncMock

from argumentation_analysis.orchestration.turn_protocol import (
    TurnResult,
    ConversationConfig,
    TurnStrategy,
)
from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus


class TestTurnResult:
    """Tests for the TurnResult dataclass."""

    def _make_phase_result(self, status=PhaseStatus.COMPLETED, output=None):
        return PhaseResult(
            phase_name="test_phase",
            status=status,
            capability="test_capability",
            output=output,
        )

    def _make_turn(self, phases=None, confidence=0.9, needs_refinement=False, **kwargs):
        if phases is None:
            phases = {"phase_a": self._make_phase_result()}
        return TurnResult(
            turn_number=1,
            phase_results=phases,
            confidence=confidence,
            needs_refinement=needs_refinement,
            **kwargs,
        )

    def test_basic_construction(self):
        tr = self._make_turn()
        assert tr.turn_number == 1
        assert tr.confidence == 0.9
        assert tr.needs_refinement is False
        assert tr.questions_for_user == []
        assert tr.duration_seconds == 0.0
        assert tr.summary is None

    def test_construction_with_all_fields(self):
        tr = self._make_turn(
            questions_for_user=["q1", "q2"],
            duration_seconds=5.3,
            summary="Done",
        )
        assert tr.questions_for_user == ["q1", "q2"]
        assert tr.duration_seconds == 5.3
        assert tr.summary == "Done"

    # --- is_converged ---

    def test_is_converged_all_completed(self):
        phases = {
            "a": self._make_phase_result(PhaseStatus.COMPLETED),
            "b": self._make_phase_result(PhaseStatus.COMPLETED),
        }
        tr = self._make_turn(phases=phases, needs_refinement=False)
        assert tr.is_converged() is True

    def test_is_converged_with_skipped(self):
        phases = {
            "a": self._make_phase_result(PhaseStatus.COMPLETED),
            "b": self._make_phase_result(PhaseStatus.SKIPPED),
        }
        tr = self._make_turn(phases=phases, needs_refinement=False)
        assert tr.is_converged() is True

    def test_not_converged_when_needs_refinement(self):
        phases = {"a": self._make_phase_result(PhaseStatus.COMPLETED)}
        tr = self._make_turn(phases=phases, needs_refinement=True)
        assert tr.is_converged() is False

    def test_not_converged_when_phase_failed(self):
        phases = {
            "a": self._make_phase_result(PhaseStatus.COMPLETED),
            "b": self._make_phase_result(PhaseStatus.FAILED),
        }
        tr = self._make_turn(phases=phases, needs_refinement=False)
        assert tr.is_converged() is False

    def test_not_converged_when_phase_pending(self):
        phases = {"a": self._make_phase_result(PhaseStatus.PENDING)}
        tr = self._make_turn(phases=phases, needs_refinement=False)
        assert tr.is_converged() is False

    def test_not_converged_when_phase_running(self):
        phases = {"a": self._make_phase_result(PhaseStatus.RUNNING)}
        tr = self._make_turn(phases=phases, needs_refinement=False)
        assert tr.is_converged() is False

    def test_is_converged_empty_phases(self):
        """Empty phases dict: vacuously all completed, no refinement needed."""
        tr = self._make_turn(phases={}, needs_refinement=False)
        assert tr.is_converged() is True

    # --- get_output ---

    def test_get_output_existing_phase(self):
        pr = self._make_phase_result(output={"key": "value"})
        tr = self._make_turn(phases={"my_phase": pr})
        assert tr.get_output("my_phase") == {"key": "value"}

    def test_get_output_missing_phase(self):
        tr = self._make_turn(phases={})
        assert tr.get_output("nonexistent") is None

    def test_get_output_none_output(self):
        pr = self._make_phase_result(output=None)
        tr = self._make_turn(phases={"p": pr})
        assert tr.get_output("p") is None


class TestConversationConfig:
    """Tests for the ConversationConfig dataclass."""

    def test_defaults(self):
        cfg = ConversationConfig()
        assert cfg.max_rounds == 3
        assert cfg.convergence_fn is None
        assert cfg.confidence_threshold == 0.8
        assert cfg.timeout_per_round_seconds is None

    def test_custom_values(self):
        fn = lambda a, b: True
        cfg = ConversationConfig(
            max_rounds=10,
            convergence_fn=fn,
            confidence_threshold=0.95,
            timeout_per_round_seconds=60.0,
        )
        assert cfg.max_rounds == 10
        assert cfg.convergence_fn is fn
        assert cfg.confidence_threshold == 0.95
        assert cfg.timeout_per_round_seconds == 60.0


class TestTurnStrategy:
    """Tests for the TurnStrategy ABC."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            TurnStrategy()

    def test_subclass_must_implement_execute_turn(self):
        class Incomplete(TurnStrategy):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_works(self):
        class ConcreteTurn(TurnStrategy):
            async def execute_turn(self, input_data, context, state=None):
                return TurnResult(
                    turn_number=context.get("turn", 1),
                    phase_results={},
                    confidence=1.0,
                    needs_refinement=False,
                )

        strategy = ConcreteTurn()
        assert isinstance(strategy, TurnStrategy)

    async def test_concrete_execute_turn(self):
        class ConcreteTurn(TurnStrategy):
            async def execute_turn(self, input_data, context, state=None):
                return TurnResult(
                    turn_number=1,
                    phase_results={},
                    confidence=0.95,
                    needs_refinement=False,
                    summary=f"Processed: {input_data}",
                )

        strategy = ConcreteTurn()
        result = await strategy.execute_turn("hello", {"turn": 1})
        assert result.confidence == 0.95
        assert result.summary == "Processed: hello"
        assert result.is_converged() is True
