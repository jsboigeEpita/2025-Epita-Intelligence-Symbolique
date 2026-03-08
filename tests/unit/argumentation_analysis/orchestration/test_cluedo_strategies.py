"""
Unit tests for argumentation_analysis/orchestration/cluedo_components/strategies.py

Covers:
- CyclicSelectionStrategy: init, cyclic next(), reset, fallback, adaptive, context injection
- OracleTerminationStrategy: init, should_terminate (all 4 criteria), _check_solution_found,
  _check_elimination_complete, get_termination_summary
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_agent(name: str, has_context_enhanced=False):
    """Create a minimal mock Agent with a .name attribute."""
    agent = MagicMock()
    agent.name = name
    if has_context_enhanced:
        agent._context_enhanced_prompt = True
    else:
        # Ensure hasattr(..., "_context_enhanced_prompt") returns False
        del agent._context_enhanced_prompt
    return agent


def _make_agents(names=("Sherlock", "Watson", "Moriarty"), context_enhanced=False):
    return [_make_mock_agent(n, has_context_enhanced=context_enhanced) for n in names]


def _make_oracle_state(**overrides):
    state = MagicMock()
    state.is_solution_proposed = overrides.get("is_solution_proposed", False)
    state.final_solution = overrides.get("final_solution", None)
    state.get_solution_secrete = MagicMock(
        return_value=overrides.get("secret", {"suspect": "Moutarde", "arme": "Chandelier", "lieu": "Salon"})
    )
    state.is_game_solvable_by_elimination = MagicMock(
        return_value=overrides.get("solvable_by_elimination", False)
    )
    state.get_contextual_prompt_addition = MagicMock(
        return_value=overrides.get("contextual_prompt", "")
    )
    return state


# ============================================================================
# CyclicSelectionStrategy
# ============================================================================

class TestCyclicSelectionStrategy:
    """Tests for CyclicSelectionStrategy."""

    def _make_strategy(self, agents=None, adaptive=False, oracle_state=None):
        from argumentation_analysis.orchestration.cluedo_components.strategies import (
            CyclicSelectionStrategy,
        )
        if agents is None:
            agents = _make_agents()
        return CyclicSelectionStrategy(
            agents=agents,
            adaptive_selection=adaptive,
            oracle_state=oracle_state,
        )

    # -- Construction --

    def test_init_stores_agent_order(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)
        assert strategy.agent_order == ["Sherlock", "Watson", "Moriarty"]
        assert strategy.current_index == 0
        assert strategy.turn_count == 0
        assert strategy.adaptive_selection is False
        assert strategy.oracle_state is None

    def test_init_with_adaptive_and_oracle(self):
        state = _make_oracle_state()
        strategy = self._make_strategy(adaptive=True, oracle_state=state)
        assert strategy.adaptive_selection is True
        assert strategy.oracle_state is state

    def test_init_single_agent(self):
        agents = [_make_mock_agent("Solo")]
        strategy = self._make_strategy(agents=agents)
        assert strategy.agent_order == ["Solo"]

    # -- next() basic cyclic --

    async def test_next_cycles_through_agents(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)

        first = await strategy.next(agents, [])
        assert first.name == "Sherlock"
        assert strategy.current_index == 1
        assert strategy.turn_count == 1

        second = await strategy.next(agents, [])
        assert second.name == "Watson"
        assert strategy.current_index == 2
        assert strategy.turn_count == 2

        third = await strategy.next(agents, [])
        assert third.name == "Moriarty"
        assert strategy.current_index == 0  # wraps around
        assert strategy.turn_count == 3

    async def test_next_wraps_around_after_full_cycle(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)

        for _ in range(3):
            await strategy.next(agents, [])

        # Now back to index 0
        fourth = await strategy.next(agents, [])
        assert fourth.name == "Sherlock"
        assert strategy.turn_count == 4

    async def test_next_empty_agents_raises(self):
        strategy = self._make_strategy()
        with pytest.raises(ValueError, match="Aucun agent disponible"):
            await strategy.next([], [])

    # -- next() fallback when agent not found --

    async def test_next_fallback_when_agent_missing(self):
        """If the expected agent is not in the provided list, select first available."""
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)

        # Provide only Watson and Moriarty (no Sherlock)
        partial_agents = [_make_mock_agent("Watson"), _make_mock_agent("Moriarty")]
        selected = await strategy.next(partial_agents, [])
        # Sherlock is at index 0 but not in partial_agents -> fallback to first
        assert selected.name == "Watson"

    # -- next() with oracle_state context injection --

    async def test_next_injects_context_when_oracle_and_enhanced(self):
        """When oracle_state is set and agent has _context_enhanced_prompt, inject context."""
        state = _make_oracle_state(contextual_prompt="Extra context for investigation")
        agents = _make_agents(context_enhanced=True)
        strategy = self._make_strategy(agents=agents, oracle_state=state)

        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"
        state.get_contextual_prompt_addition.assert_called_once_with("Sherlock")
        assert selected._current_context == "Extra context for investigation"

    async def test_next_no_injection_when_no_context_enhanced_prompt(self):
        """No injection if agent lacks _context_enhanced_prompt."""
        state = _make_oracle_state(contextual_prompt="Some context")
        agents = _make_agents(context_enhanced=False)
        strategy = self._make_strategy(agents=agents, oracle_state=state)

        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"
        state.get_contextual_prompt_addition.assert_not_called()

    async def test_next_no_injection_when_contextual_prompt_empty(self):
        """No injection if contextual prompt is empty string."""
        state = _make_oracle_state(contextual_prompt="")
        agents = _make_agents(context_enhanced=True)
        strategy = self._make_strategy(agents=agents, oracle_state=state)

        selected = await strategy.next(agents, [])
        # get_contextual_prompt_addition called but returned "", so no _current_context set
        state.get_contextual_prompt_addition.assert_called_once_with("Sherlock")
        assert not hasattr(selected, "_current_context") or getattr(selected, "_current_context", None) != ""

    # -- next() with adaptive selection --

    async def test_next_with_adaptive_calls_adaptations(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents, adaptive=True)

        selected = await strategy.next(agents, [])
        # _apply_contextual_adaptations just returns default agent in Phase 1
        assert selected.name == "Sherlock"

    # -- _apply_contextual_adaptations --

    async def test_apply_contextual_adaptations_returns_default(self):
        """Phase 1 implementation just returns the default agent."""
        from argumentation_analysis.orchestration.cluedo_components.strategies import (
            CyclicSelectionStrategy,
        )
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)
        default = agents[0]
        result = await strategy._apply_contextual_adaptations(default, agents, [])
        assert result is default

    # -- reset() --

    def test_reset_clears_index_and_count(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)
        # Simulate some turns
        strategy.__dict__["current_index"] = 2
        strategy.__dict__["turn_count"] = 7

        strategy.reset()

        assert strategy.current_index == 0
        assert strategy.turn_count == 0

    async def test_reset_then_next_restarts_cycle(self):
        agents = _make_agents()
        strategy = self._make_strategy(agents=agents)

        # Advance two steps
        await strategy.next(agents, [])
        await strategy.next(agents, [])
        assert strategy.current_index == 2

        strategy.reset()

        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"
        assert strategy.turn_count == 1


# ============================================================================
# OracleTerminationStrategy
# ============================================================================

class TestOracleTerminationStrategy:
    """Tests for OracleTerminationStrategy."""

    def _make_strategy(self, max_turns=15, max_cycles=5, oracle_state=None):
        from argumentation_analysis.orchestration.cluedo_components.strategies import (
            OracleTerminationStrategy,
        )
        return OracleTerminationStrategy(
            max_turns=max_turns,
            max_cycles=max_cycles,
            oracle_state=oracle_state,
        )

    # -- Construction --

    def test_init_defaults(self):
        strategy = self._make_strategy()
        assert strategy.max_turns == 15
        assert strategy.max_cycles == 5
        assert strategy.turn_count == 0
        assert strategy.cycle_count == 0
        assert strategy.is_solution_found is False
        assert strategy.oracle_state is None

    def test_init_custom_values(self):
        state = _make_oracle_state()
        strategy = self._make_strategy(max_turns=10, max_cycles=3, oracle_state=state)
        assert strategy.max_turns == 10
        assert strategy.max_cycles == 3
        assert strategy.oracle_state is state

    # -- should_terminate: no termination --

    async def test_should_not_terminate_early(self):
        strategy = self._make_strategy(max_turns=15, max_cycles=5)
        agent = _make_mock_agent("Watson")
        result = await strategy.should_terminate(agent, [])
        assert result is False
        assert strategy.turn_count == 1

    async def test_should_not_terminate_no_oracle_state(self):
        strategy = self._make_strategy()
        agent = _make_mock_agent("Watson")
        result = await strategy.should_terminate(agent, [])
        assert result is False

    # -- should_terminate: max_turns reached --

    async def test_terminates_at_max_turns(self):
        strategy = self._make_strategy(max_turns=3, max_cycles=100)
        agent = _make_mock_agent("Watson")

        for _ in range(2):
            result = await strategy.should_terminate(agent, [])
            assert result is False

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.turn_count == 3

    # -- should_terminate: max_cycles reached --

    async def test_terminates_at_max_cycles(self):
        strategy = self._make_strategy(max_turns=100, max_cycles=2)
        sherlock = _make_mock_agent("Sherlock")

        # Each Sherlock turn increments cycle_count
        result = await strategy.should_terminate(sherlock, [])
        assert result is False
        assert strategy.cycle_count == 1

        result = await strategy.should_terminate(sherlock, [])
        assert result is True
        assert strategy.cycle_count == 2

    async def test_non_sherlock_does_not_increment_cycle(self):
        strategy = self._make_strategy(max_turns=100, max_cycles=100)
        watson = _make_mock_agent("Watson")

        await strategy.should_terminate(watson, [])
        assert strategy.cycle_count == 0

    # -- should_terminate: solution found --

    async def test_terminates_when_correct_solution_proposed(self):
        secret = {"suspect": "Moutarde", "arme": "Chandelier", "lieu": "Salon"}
        state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=secret,
            secret=secret,
        )
        strategy = self._make_strategy(oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.is_solution_found is True

    async def test_does_not_terminate_when_wrong_solution(self):
        secret = {"suspect": "Moutarde", "arme": "Chandelier", "lieu": "Salon"}
        wrong = {"suspect": "Rose", "arme": "Poignard", "lieu": "Cuisine"}
        state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=wrong,
            secret=secret,
        )
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False
        assert strategy.is_solution_found is False

    async def test_does_not_terminate_when_solution_not_proposed(self):
        state = _make_oracle_state(is_solution_proposed=False)
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False

    # -- should_terminate: elimination complete --

    async def test_terminates_when_elimination_complete(self):
        state = _make_oracle_state(solvable_by_elimination=True)
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True

    async def test_does_not_terminate_when_elimination_incomplete(self):
        state = _make_oracle_state(solvable_by_elimination=False)
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False

    # -- should_terminate: agent=None --

    async def test_should_terminate_with_none_agent(self):
        strategy = self._make_strategy(max_turns=100, max_cycles=100)
        result = await strategy.should_terminate(None, [])
        assert result is False
        assert strategy.cycle_count == 0  # None agent does not increment cycle

    # -- _check_solution_found --

    def test_check_solution_no_oracle_state(self):
        strategy = self._make_strategy()
        assert strategy._check_solution_found() is False

    def test_check_solution_not_proposed(self):
        state = _make_oracle_state(is_solution_proposed=False)
        strategy = self._make_strategy(oracle_state=state)
        assert strategy._check_solution_found() is False

    def test_check_solution_correct(self):
        secret = {"suspect": "X", "arme": "Y", "lieu": "Z"}
        state = _make_oracle_state(is_solution_proposed=True, final_solution=secret, secret=secret)
        strategy = self._make_strategy(oracle_state=state)
        assert strategy._check_solution_found() is True

    def test_check_solution_incorrect(self):
        secret = {"suspect": "X", "arme": "Y", "lieu": "Z"}
        wrong = {"suspect": "A", "arme": "B", "lieu": "C"}
        state = _make_oracle_state(is_solution_proposed=True, final_solution=wrong, secret=secret)
        strategy = self._make_strategy(oracle_state=state)
        assert strategy._check_solution_found() is False

    # -- _check_elimination_complete --

    def test_check_elimination_no_oracle_state(self):
        strategy = self._make_strategy()
        assert strategy._check_elimination_complete() is False

    def test_check_elimination_complete_true(self):
        state = _make_oracle_state(solvable_by_elimination=True)
        strategy = self._make_strategy(oracle_state=state)
        assert strategy._check_elimination_complete() is True

    def test_check_elimination_complete_false(self):
        state = _make_oracle_state(solvable_by_elimination=False)
        strategy = self._make_strategy(oracle_state=state)
        assert strategy._check_elimination_complete() is False

    # -- get_termination_summary --

    def test_get_termination_summary_no_oracle(self):
        strategy = self._make_strategy()
        summary = strategy.get_termination_summary()
        assert summary["turn_count"] == 0
        assert summary["cycle_count"] == 0
        assert summary["max_turns"] == 15
        assert summary["max_cycles"] == 5
        assert summary["is_solution_found"] is False
        assert summary["solution_proposed"] is False
        assert summary["elimination_possible"] is False

    def test_get_termination_summary_with_oracle(self):
        state = _make_oracle_state(
            is_solution_proposed=True,
            solvable_by_elimination=True,
        )
        strategy = self._make_strategy(max_turns=10, max_cycles=3, oracle_state=state)
        strategy.turn_count = 7
        strategy.cycle_count = 2
        strategy.is_solution_found = True

        summary = strategy.get_termination_summary()
        assert summary["turn_count"] == 7
        assert summary["cycle_count"] == 2
        assert summary["max_turns"] == 10
        assert summary["max_cycles"] == 3
        assert summary["is_solution_found"] is True
        assert summary["solution_proposed"] is True
        assert summary["elimination_possible"] is True

    async def test_termination_priority_solution_before_timeout(self):
        """Solution found should terminate even if turns/cycles are under limit."""
        secret = {"suspect": "X", "arme": "Y", "lieu": "Z"}
        state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=secret,
            secret=secret,
        )
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.turn_count == 1  # only 1 turn, well under max

    async def test_termination_priority_elimination_before_timeout(self):
        """Elimination complete should terminate before hitting timeout."""
        state = _make_oracle_state(solvable_by_elimination=True)
        strategy = self._make_strategy(max_turns=100, max_cycles=100, oracle_state=state)
        agent = _make_mock_agent("Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.turn_count == 1

    async def test_multiple_turns_accumulate(self):
        """Turn and cycle counts accumulate across calls."""
        strategy = self._make_strategy(max_turns=100, max_cycles=100)
        sherlock = _make_mock_agent("Sherlock")
        watson = _make_mock_agent("Watson")
        moriarty = _make_mock_agent("Moriarty")

        await strategy.should_terminate(sherlock, [])  # cycle 1, turn 1
        await strategy.should_terminate(watson, [])    # turn 2
        await strategy.should_terminate(moriarty, [])  # turn 3
        await strategy.should_terminate(sherlock, [])  # cycle 2, turn 4

        assert strategy.turn_count == 4
        assert strategy.cycle_count == 2
