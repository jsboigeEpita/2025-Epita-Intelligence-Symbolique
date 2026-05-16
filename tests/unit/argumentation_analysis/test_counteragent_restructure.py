"""Tests for CounterAgent restructure — #551.

Validates:
- CounterAgent instructions reference fallacy targeting
- CounterAgent instructions reference quality score targeting
- CounterAgent instructions reference strategy-per-weakness mapping
- CounterAgent instructions specify quantity target (>= 10)
- Synthesis & Debate phase has max_turns >= 10
"""

import pytest

from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_CONFIG,
)


class TestCounterAgentInstructions:
    """Test CounterAgent instructions target fallacious arguments."""

    def test_instructions_reference_fallacies(self):
        """CounterAgent must target fallacious arguments specifically."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        assert "fallacieux" in instructions.lower() or "fallacy" in instructions.lower()

    def test_instructions_reference_quality_scores(self):
        """CounterAgent must target weak arguments by quality score."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        assert "qualite" in instructions.lower() or "quality" in instructions.lower()
        assert "score" in instructions.lower() or "score" in instructions.lower()

    def test_instructions_reference_strategy_mapping(self):
        """CounterAgent must map strategy to weakness type."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        # Check at least one strategy mapping
        assert "reductio" in instructions.lower() or "reformulation" in instructions.lower()
        assert "contre-exemple" in instructions.lower() or "distinction" in instructions.lower()

    def test_instructions_specify_quantity_target(self):
        """CounterAgent must aim for at least 10 counter-arguments."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        assert "10" in instructions

    def test_instructions_specify_per_target(self):
        """CounterAgent must produce per-target counter-arguments."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        assert "CHAQUE" in instructions or "chaque" in instructions.lower()

    def test_instructions_reference_state_read(self):
        """CounterAgent must read state snapshot."""
        instructions = AGENT_CONFIG["CounterAgent"]["instructions"]
        assert "get_current_state_snapshot" in instructions


class TestSynthesisPhaseConfig:
    """Test Synthesis & Debate phase configuration."""

    def test_synthesis_max_turns_at_least_10(self):
        """Synthesis phase must have >= 10 turns for exhaustive counter-argumentation."""
        # The phase configs are built with hardcoded values in the function
        # We check by reading the relevant section
        import inspect
        from argumentation_analysis.orchestration import conversational_orchestrator as co

        source = inspect.getsource(co.run_conversational_analysis)
        # Look for the Synthesis & Debate max_turns
        assert "max_turns\": 10" in source or "max_turns\": 10" in source
