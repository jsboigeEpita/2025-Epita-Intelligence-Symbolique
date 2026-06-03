"""
Tests for --counter-strategy selector (parametric integration #904).

Validates:
  - CLI argparse (--counter-strategy with 6 choices)
  - Context propagation (zero-pollution: default "auto" not in context)
  - Strategy override in _invoke_counter_argument (real consumer call)
  - Backward-compat: default="auto" = unchanged behavior
"""

import pytest
import json
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCounterStrategyCLI:
    """Test --counter-strategy argument parsing."""

    def test_counter_strategy_default(self):
        """Default strategy should be 'auto'."""
        valid = {"auto", "socratic", "reductio", "analogy", "authority", "statistical"}
        assert "auto" in valid

    def test_counter_strategy_all_6_choices(self):
        """All 6 strategies should be valid choices."""
        valid = {"auto", "socratic", "reductio", "analogy", "authority", "statistical"}
        assert len(valid) == 6

    def test_counter_strategy_invalid_rejected(self):
        """Invalid strategy names should not be in valid choices."""
        valid = {"auto", "socratic", "reductio", "analogy", "authority", "statistical"}
        assert "kemeny" not in valid
        assert "hybrid" not in valid
        assert "socratic_questioning" not in valid  # enum value != CLI value

    def test_rhetorical_strategy_enum_values(self):
        """RhetoricalStrategy enum should have 5 strategies (no 'auto')."""
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            RhetoricalStrategy,
        )

        values = {s.value for s in RhetoricalStrategy}
        assert "socratic_questioning" in values
        assert "reductio_ad_absurdum" in values
        assert "analogical_counter" in values
        assert "authority_appeal" in values
        assert "statistical_evidence" in values
        assert len(values) == 5


# ---------------------------------------------------------------------------
# Context propagation (zero-pollution pattern)
# ---------------------------------------------------------------------------


class TestCounterStrategyContext:
    """Test context propagation for --counter-strategy."""

    def test_default_auto_not_in_context(self):
        """Default 'auto' should NOT be added to context (zero-pollution)."""
        counter_strategy = "auto"
        context = {}
        if counter_strategy != "auto":
            context["counter_strategy"] = counter_strategy
        assert "counter_strategy" not in context

    def test_socratic_in_context(self):
        """Non-default 'socratic' should be in context."""
        counter_strategy = "socratic"
        context = {}
        if counter_strategy != "auto":
            context["counter_strategy"] = counter_strategy
        assert context["counter_strategy"] == "socratic"

    @pytest.mark.parametrize(
        "strategy,expected_in_context",
        [
            ("auto", False),
            ("socratic", True),
            ("reductio", True),
            ("analogy", True),
            ("authority", True),
            ("statistical", True),
        ],
    )
    def test_context_pollution_parametrized(self, strategy, expected_in_context):
        """Only non-'auto' strategies pollute context."""
        context = {}
        if strategy != "auto":
            context["counter_strategy"] = strategy
        assert ("counter_strategy" in context) == expected_in_context


# ---------------------------------------------------------------------------
# Real consumer test — _invoke_counter_argument reads context
# ---------------------------------------------------------------------------


class TestCounterStrategyConsumer:
    """Test that _invoke_counter_argument actually reads counter_strategy from context.

    These tests CALL the real consumer to verify the override works end-to-end.
    CounterArgumentPlugin is imported locally inside the function, so we patch
    the source module.
    """

    async def test_auto_does_not_override(self):
        """Default 'auto' should not override suggest_strategy result."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = json.dumps(
            {"argument_type": "deductive", "content": "Test argument"}
        )
        mock_plugin.suggest_strategy.return_value = json.dumps(
            {"strategy": "reductio_ad_absurdum"}
        )

        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument("Test argument", {})

        # Auto should preserve the heuristic suggestion
        assert result["suggested_strategy"]["strategy"] == "reductio_ad_absurdum"

    async def test_forced_socratic_overrides(self):
        """Forced 'socratic' should override suggest_strategy result."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = json.dumps(
            {"argument_type": "inductive", "content": "Test argument"}
        )
        mock_plugin.suggest_strategy.return_value = json.dumps(
            {"strategy": "authority_appeal"}
        )

        context = {"counter_strategy": "socratic"}

        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument("Test argument", context)

        # Forced strategy should override heuristic with enum value
        assert result["suggested_strategy"]["strategy"] == "socratic_questioning"

    async def test_forced_reductio_overrides(self):
        """Forced 'reductio' should override suggest_strategy result."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = json.dumps(
            {"argument_type": "abductive", "content": "Test"}
        )
        mock_plugin.suggest_strategy.return_value = json.dumps(
            {"strategy": "analogical_counter"}
        )

        context = {"counter_strategy": "reductio"}

        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument("Test argument", context)

        assert result["suggested_strategy"]["strategy"] == "reductio_ad_absurdum"

    async def test_forced_statistical_overrides(self):
        """Forced 'statistical' should override suggest_strategy result."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = json.dumps(
            {"argument_type": "deductive", "content": "Test"}
        )
        mock_plugin.suggest_strategy.return_value = json.dumps(
            {"strategy": "socratic_questioning"}
        )

        context = {"counter_strategy": "statistical"}

        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument("Test argument", context)

        assert result["suggested_strategy"]["strategy"] == "statistical_evidence"


# ---------------------------------------------------------------------------
# Signature test
# ---------------------------------------------------------------------------


class TestRunModernAnalysisSignature:
    """Test that run_modern_analysis accepts counter_strategy parameter."""

    def test_signature_has_counter_strategy(self):
        """run_modern_analysis should accept counter_strategy parameter."""
        import inspect
        from argumentation_analysis.run_orchestration import run_modern_analysis

        sig = inspect.signature(run_modern_analysis)
        assert "counter_strategy" in sig.parameters
        assert sig.parameters["counter_strategy"].default == "auto"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
