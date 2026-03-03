"""
Tests for CyclicSelectionStrategy and OracleTerminationStrategy.

These tests validate:
- CyclicSelectionStrategy: cyclic agent ordering, fallback, reset, adaptive mode, context injection
- OracleTerminationStrategy: turn/cycle limits, solution detection, elimination detection, summary
- Base classes: Agent, SelectionStrategy, TerminationStrategy abstract contracts
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List

from semantic_kernel.contents import ChatMessageContent
from argumentation_analysis.orchestration.base import (
    Agent,
    SelectionStrategy,
    TerminationStrategy,
)
from argumentation_analysis.orchestration.strategies import (
    CyclicSelectionStrategy,
    OracleTerminationStrategy,
)


# ---------------------------------------------------------------------------
# Helpers: concrete Agent subclass (Agent is abstract)
# ---------------------------------------------------------------------------

class ConcreteAgent(Agent):
    """Minimal concrete Agent for testing purposes."""

    async def invoke(self, history: List[ChatMessageContent]) -> ChatMessageContent:
        return ChatMessageContent(role="assistant", content=f"Response from {self.name}")


def _make_agents(*names: str) -> List[ConcreteAgent]:
    """Create a list of ConcreteAgent instances from names."""
    return [ConcreteAgent(name=n) for n in names]


def _make_oracle_state(
    is_solution_proposed: bool = False,
    final_solution: dict = None,
    secret_solution: dict = None,
    solvable_by_elimination: bool = False,
):
    """Create a mock CluedoOracleState with the specified behavior."""
    state = MagicMock()
    state.is_solution_proposed = is_solution_proposed
    state.final_solution = final_solution
    state.get_solution_secrete = Mock(return_value=secret_solution)
    state.is_game_solvable_by_elimination = Mock(return_value=solvable_by_elimination)
    state.get_contextual_prompt_addition = Mock(return_value="")
    return state


# ===========================================================================
# Tests for base classes
# ===========================================================================

class TestBaseAgent:
    """Tests for the abstract Agent base class."""

    def test_agent_is_abstract(self):
        """Agent cannot be instantiated directly because invoke() is abstract."""
        with pytest.raises(TypeError):
            Agent(name="test")

    def test_concrete_agent_instantiation(self):
        """A concrete subclass of Agent can be instantiated."""
        agent = ConcreteAgent(name="Sherlock")
        assert agent.name == "Sherlock"

    async def test_concrete_agent_invoke(self):
        """invoke() returns a ChatMessageContent with the agent's name."""
        agent = ConcreteAgent(name="Watson")
        result = await agent.invoke([])
        assert isinstance(result, ChatMessageContent)
        assert "Watson" in str(result.content)


class TestBaseSelectionStrategy:
    """Tests for the abstract SelectionStrategy base class."""

    def test_selection_strategy_is_abstract(self):
        """SelectionStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SelectionStrategy()

    def test_reset_is_noop_by_default(self):
        """The base reset() does nothing (no-op)."""
        # CyclicSelectionStrategy inherits and overrides reset, so test
        # that the base class method exists and is callable indirectly.
        strategy = CyclicSelectionStrategy(agents=_make_agents("A"))
        # This should not raise
        strategy.reset()


class TestBaseTerminationStrategy:
    """Tests for the abstract TerminationStrategy base class."""

    def test_termination_strategy_is_abstract(self):
        """TerminationStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TerminationStrategy()


# ===========================================================================
# Tests for CyclicSelectionStrategy
# ===========================================================================

class TestCyclicSelectionStrategyInit:
    """Tests for CyclicSelectionStrategy initialization."""

    def test_init_with_agents(self):
        """Strategy initializes with the correct agent order."""
        agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(agents=agents)

        assert strategy.agent_order == ["Sherlock", "Watson", "Moriarty"]
        assert strategy.current_index == 0
        assert strategy.turn_count == 0

    def test_init_single_agent(self):
        """Strategy works with a single agent."""
        agents = _make_agents("Solo")
        strategy = CyclicSelectionStrategy(agents=agents)

        assert strategy.agent_order == ["Solo"]
        assert strategy.current_index == 0

    def test_init_adaptive_selection_default_false(self):
        """adaptive_selection defaults to False."""
        strategy = CyclicSelectionStrategy(agents=_make_agents("A"))
        assert strategy.adaptive_selection is False

    def test_init_adaptive_selection_explicit_true(self):
        """adaptive_selection can be set to True."""
        strategy = CyclicSelectionStrategy(
            agents=_make_agents("A"),
            adaptive_selection=True,
        )
        assert strategy.adaptive_selection is True

    def test_init_oracle_state_default_none(self):
        """oracle_state defaults to None."""
        strategy = CyclicSelectionStrategy(agents=_make_agents("A"))
        assert strategy.oracle_state is None

    def test_init_oracle_state_provided(self):
        """oracle_state can be passed at initialization."""
        mock_state = _make_oracle_state()
        strategy = CyclicSelectionStrategy(
            agents=_make_agents("A"),
            oracle_state=mock_state,
        )
        assert strategy.oracle_state is mock_state

    def test_init_stores_agents_reference(self):
        """The agents list itself is stored in __dict__."""
        agents = _make_agents("X", "Y")
        strategy = CyclicSelectionStrategy(agents=agents)
        assert strategy.agents is agents


class TestCyclicSelectionStrategyNext:
    """Tests for CyclicSelectionStrategy.next() behavior."""

    async def test_first_call_selects_first_agent(self):
        """First call to next() returns the first agent in order."""
        agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(agents=agents)

        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"

    async def test_cyclic_order_three_agents(self):
        """Agents are selected in cyclic order: first -> second -> third -> first."""
        agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(agents=agents)

        names = []
        for _ in range(6):
            selected = await strategy.next(agents, [])
            names.append(selected.name)

        assert names == [
            "Sherlock", "Watson", "Moriarty",
            "Sherlock", "Watson", "Moriarty",
        ]

    async def test_cyclic_order_two_agents(self):
        """Cyclic selection works correctly with two agents."""
        agents = _make_agents("Alpha", "Beta")
        strategy = CyclicSelectionStrategy(agents=agents)

        names = []
        for _ in range(4):
            selected = await strategy.next(agents, [])
            names.append(selected.name)

        assert names == ["Alpha", "Beta", "Alpha", "Beta"]

    async def test_single_agent_always_selected(self):
        """With a single agent, next() always returns that agent."""
        agents = _make_agents("Solo")
        strategy = CyclicSelectionStrategy(agents=agents)

        for _ in range(3):
            selected = await strategy.next(agents, [])
            assert selected.name == "Solo"

    async def test_empty_agents_raises_value_error(self):
        """Passing an empty agents list to next() raises ValueError."""
        init_agents = _make_agents("Sherlock")
        strategy = CyclicSelectionStrategy(agents=init_agents)

        with pytest.raises(ValueError, match="Aucun agent disponible"):
            await strategy.next([], [])

    async def test_agent_not_found_falls_back_to_first(self):
        """When the expected agent is not in the passed list, fallback to first available."""
        init_agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(agents=init_agents)

        # The strategy expects "Sherlock" first, but we pass different agents
        runtime_agents = _make_agents("Alpha", "Beta")
        selected = await strategy.next(runtime_agents, [])

        # Should fallback to the first runtime agent
        assert selected.name == "Alpha"

    async def test_agent_not_found_after_advance(self):
        """After advancing past the first agent, fallback still returns first available."""
        init_agents = _make_agents("A", "B", "C")
        strategy = CyclicSelectionStrategy(agents=init_agents)

        # First call selects "A" (present)
        full_agents = _make_agents("A", "B", "C")
        await strategy.next(full_agents, [])

        # Second call should look for "B", but we pass agents without "B"
        partial_agents = _make_agents("X", "Y")
        selected = await strategy.next(partial_agents, [])
        assert selected.name == "X"

    async def test_turn_count_increments(self):
        """turn_count increments on each call to next()."""
        agents = _make_agents("A", "B")
        strategy = CyclicSelectionStrategy(agents=agents)

        assert strategy.turn_count == 0
        await strategy.next(agents, [])
        assert strategy.turn_count == 1
        await strategy.next(agents, [])
        assert strategy.turn_count == 2
        await strategy.next(agents, [])
        assert strategy.turn_count == 3

    async def test_current_index_wraps_around(self):
        """current_index wraps around to 0 after reaching the end."""
        agents = _make_agents("A", "B", "C")
        strategy = CyclicSelectionStrategy(agents=agents)

        await strategy.next(agents, [])  # index: 0 -> 1
        assert strategy.current_index == 1
        await strategy.next(agents, [])  # index: 1 -> 2
        assert strategy.current_index == 2
        await strategy.next(agents, [])  # index: 2 -> 0
        assert strategy.current_index == 0

    async def test_adaptive_selection_returns_default_agent(self):
        """With adaptive_selection=True, _apply_contextual_adaptations returns the default agent (Phase 1)."""
        agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(
            agents=agents,
            adaptive_selection=True,
        )

        # The adaptive method currently returns the default agent unchanged
        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"

    async def test_adaptive_selection_preserves_cyclic_order(self):
        """adaptive_selection=True still follows the cyclic order (Phase 1 stub)."""
        agents = _make_agents("A", "B")
        strategy = CyclicSelectionStrategy(agents=agents, adaptive_selection=True)

        names = []
        for _ in range(4):
            selected = await strategy.next(agents, [])
            names.append(selected.name)

        assert names == ["A", "B", "A", "B"]


class TestCyclicSelectionStrategyContextInjection:
    """Tests for context injection when oracle_state is present."""

    async def test_context_injected_when_oracle_state_and_attr_present(self):
        """Context is injected into agent when oracle_state and _context_enhanced_prompt attr exist."""
        mock_state = _make_oracle_state()
        mock_state.get_contextual_prompt_addition = Mock(return_value="Extra context info")

        agents = _make_agents("Sherlock", "Watson")
        # Add the attribute that triggers context injection
        agents[0]._context_enhanced_prompt = True

        strategy = CyclicSelectionStrategy(agents=agents, oracle_state=mock_state)
        selected = await strategy.next(agents, [])

        assert selected.name == "Sherlock"
        mock_state.get_contextual_prompt_addition.assert_called_once_with("Sherlock")
        assert selected._current_context == "Extra context info"

    async def test_no_context_injection_without_oracle_state(self):
        """No context injection happens when oracle_state is None."""
        agents = _make_agents("Sherlock")
        agents[0]._context_enhanced_prompt = True

        strategy = CyclicSelectionStrategy(agents=agents, oracle_state=None)
        selected = await strategy.next(agents, [])

        assert not hasattr(selected, "_current_context")

    async def test_no_context_injection_without_attr(self):
        """No context injection when agent lacks _context_enhanced_prompt."""
        mock_state = _make_oracle_state()
        agents = _make_agents("Sherlock")

        strategy = CyclicSelectionStrategy(agents=agents, oracle_state=mock_state)
        selected = await strategy.next(agents, [])

        # get_contextual_prompt_addition should NOT be called
        mock_state.get_contextual_prompt_addition.assert_not_called()

    async def test_empty_context_not_injected(self):
        """When contextual addition is empty string, attribute is still set (the code sets it regardless)."""
        mock_state = _make_oracle_state()
        mock_state.get_contextual_prompt_addition = Mock(return_value="")

        agents = _make_agents("Sherlock")
        agents[0]._context_enhanced_prompt = True

        strategy = CyclicSelectionStrategy(agents=agents, oracle_state=mock_state)
        selected = await strategy.next(agents, [])

        # Empty string is falsy, so the `if contextual_addition:` guard prevents injection
        assert not hasattr(selected, "_current_context")


class TestCyclicSelectionStrategyReset:
    """Tests for CyclicSelectionStrategy.reset()."""

    async def test_reset_restores_index_to_zero(self):
        """reset() sets current_index back to 0."""
        agents = _make_agents("A", "B", "C")
        strategy = CyclicSelectionStrategy(agents=agents)

        await strategy.next(agents, [])
        await strategy.next(agents, [])
        assert strategy.current_index == 2

        strategy.reset()
        assert strategy.current_index == 0

    async def test_reset_restores_turn_count_to_zero(self):
        """reset() sets turn_count back to 0."""
        agents = _make_agents("A", "B")
        strategy = CyclicSelectionStrategy(agents=agents)

        await strategy.next(agents, [])
        await strategy.next(agents, [])
        assert strategy.turn_count == 2

        strategy.reset()
        assert strategy.turn_count == 0

    async def test_reset_allows_fresh_cycle(self):
        """After reset(), the cycle restarts from the first agent."""
        agents = _make_agents("Sherlock", "Watson", "Moriarty")
        strategy = CyclicSelectionStrategy(agents=agents)

        # Advance to Watson
        await strategy.next(agents, [])
        await strategy.next(agents, [])

        # Reset
        strategy.reset()

        # Should start from Sherlock again
        selected = await strategy.next(agents, [])
        assert selected.name == "Sherlock"


# ===========================================================================
# Tests for OracleTerminationStrategy
# ===========================================================================

class TestOracleTerminationStrategyInit:
    """Tests for OracleTerminationStrategy initialization."""

    def test_default_values(self):
        """Default initialization sets max_turns=15, max_cycles=5."""
        strategy = OracleTerminationStrategy()
        assert strategy.max_turns == 15
        assert strategy.max_cycles == 5
        assert strategy.turn_count == 0
        assert strategy.cycle_count == 0
        assert strategy.is_solution_found is False
        assert strategy.oracle_state is None

    def test_custom_max_turns(self):
        """max_turns can be set to a custom value."""
        strategy = OracleTerminationStrategy(max_turns=30)
        assert strategy.max_turns == 30

    def test_custom_max_cycles(self):
        """max_cycles can be set to a custom value."""
        strategy = OracleTerminationStrategy(max_cycles=10)
        assert strategy.max_cycles == 10

    def test_custom_oracle_state(self):
        """oracle_state can be provided at initialization."""
        mock_state = _make_oracle_state()
        strategy = OracleTerminationStrategy(oracle_state=mock_state)
        assert strategy.oracle_state is mock_state

    def test_custom_all_parameters(self):
        """All parameters can be provided together."""
        mock_state = _make_oracle_state()
        strategy = OracleTerminationStrategy(
            max_turns=20,
            max_cycles=7,
            oracle_state=mock_state,
        )
        assert strategy.max_turns == 20
        assert strategy.max_cycles == 7
        assert strategy.oracle_state is mock_state


class TestOracleTerminationStrategyShouldTerminate:
    """Tests for OracleTerminationStrategy.should_terminate()."""

    async def test_does_not_terminate_before_limits(self):
        """should_terminate() returns False when no conditions are met."""
        strategy = OracleTerminationStrategy(max_turns=10, max_cycles=5)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False

    async def test_turn_count_increments(self):
        """Each call to should_terminate() increments turn_count."""
        strategy = OracleTerminationStrategy(max_turns=100)
        agent = ConcreteAgent(name="Watson")

        assert strategy.turn_count == 0
        await strategy.should_terminate(agent, [])
        assert strategy.turn_count == 1
        await strategy.should_terminate(agent, [])
        assert strategy.turn_count == 2

    async def test_terminates_at_max_turns(self):
        """should_terminate() returns True when turn_count reaches max_turns."""
        strategy = OracleTerminationStrategy(max_turns=3, max_cycles=100)
        agent = ConcreteAgent(name="Watson")

        # Turns 1, 2 should not terminate
        assert await strategy.should_terminate(agent, []) is False
        assert await strategy.should_terminate(agent, []) is False
        # Turn 3 hits the limit
        assert await strategy.should_terminate(agent, []) is True

    async def test_terminates_at_max_cycles(self):
        """should_terminate() returns True when cycle_count reaches max_cycles."""
        strategy = OracleTerminationStrategy(max_turns=100, max_cycles=2)
        sherlock = ConcreteAgent(name="Sherlock")
        watson = ConcreteAgent(name="Watson")

        # Cycle 1: Sherlock increments cycle_count to 1
        assert await strategy.should_terminate(sherlock, []) is False
        assert await strategy.should_terminate(watson, []) is False

        # Cycle 2: Sherlock increments cycle_count to 2 -> reaches max_cycles
        assert await strategy.should_terminate(sherlock, []) is True

    async def test_cycle_count_only_increments_on_sherlock(self):
        """cycle_count only increments when the agent's name is 'Sherlock'."""
        strategy = OracleTerminationStrategy(max_turns=100, max_cycles=100)
        watson = ConcreteAgent(name="Watson")
        moriarty = ConcreteAgent(name="Moriarty")

        await strategy.should_terminate(watson, [])
        await strategy.should_terminate(moriarty, [])
        await strategy.should_terminate(watson, [])

        assert strategy.cycle_count == 0

    async def test_cycle_count_increments_each_sherlock_turn(self):
        """Each Sherlock turn increments the cycle count by 1."""
        strategy = OracleTerminationStrategy(max_turns=100, max_cycles=100)
        sherlock = ConcreteAgent(name="Sherlock")
        watson = ConcreteAgent(name="Watson")

        await strategy.should_terminate(sherlock, [])  # cycle 1
        await strategy.should_terminate(watson, [])
        await strategy.should_terminate(sherlock, [])  # cycle 2
        await strategy.should_terminate(watson, [])
        await strategy.should_terminate(sherlock, [])  # cycle 3

        assert strategy.cycle_count == 3

    async def test_terminates_when_solution_found(self):
        """should_terminate() returns True when oracle_state has a correct proposed solution."""
        solution = {"suspect": "Colonel Mustard", "weapon": "Candlestick", "room": "Library"}
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=solution,
            secret_solution=solution,  # same = correct
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.is_solution_found is True

    async def test_does_not_terminate_on_wrong_solution(self):
        """should_terminate() returns False when proposed solution does not match secret."""
        proposed = {"suspect": "Colonel Mustard", "weapon": "Candlestick", "room": "Library"}
        secret = {"suspect": "Miss Scarlet", "weapon": "Rope", "room": "Kitchen"}
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=proposed,
            secret_solution=secret,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False
        assert strategy.is_solution_found is False

    async def test_does_not_terminate_when_no_solution_proposed(self):
        """should_terminate() returns False when is_solution_proposed is False."""
        mock_state = _make_oracle_state(
            is_solution_proposed=False,
            final_solution=None,
            secret_solution={"suspect": "A", "weapon": "B", "room": "C"},
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False

    async def test_terminates_on_elimination_complete(self):
        """should_terminate() returns True when oracle_state reports solvable by elimination."""
        mock_state = _make_oracle_state(
            is_solution_proposed=False,
            solvable_by_elimination=True,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True

    async def test_does_not_terminate_when_elimination_not_complete(self):
        """should_terminate() returns False when elimination is not yet complete."""
        mock_state = _make_oracle_state(
            is_solution_proposed=False,
            solvable_by_elimination=False,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is False

    async def test_solution_check_takes_priority_over_elimination(self):
        """Solution found terminates before elimination check is evaluated."""
        solution = {"suspect": "A", "weapon": "B", "room": "C"}
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=solution,
            secret_solution=solution,
            solvable_by_elimination=True,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.is_solution_found is True

    async def test_no_oracle_state_no_solution_or_elimination(self):
        """Without oracle_state, solution and elimination checks both return False."""
        strategy = OracleTerminationStrategy(max_turns=100, max_cycles=100)
        agent = ConcreteAgent(name="Watson")

        # Should only terminate by turn/cycle limits
        result = await strategy.should_terminate(agent, [])
        assert result is False

    async def test_termination_order_solution_before_max_turns(self):
        """Solution found terminates even if max_turns is not yet reached."""
        solution = {"suspect": "A", "weapon": "B", "room": "C"}
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=solution,
            secret_solution=solution,
        )
        strategy = OracleTerminationStrategy(
            oracle_state=mock_state, max_turns=100, max_cycles=100
        )
        agent = ConcreteAgent(name="Watson")

        result = await strategy.should_terminate(agent, [])
        assert result is True
        assert strategy.turn_count == 1  # only 1 turn used

    async def test_full_workflow_simulation(self):
        """Simulate a full 3-agent workflow until max_turns."""
        strategy = OracleTerminationStrategy(max_turns=6, max_cycles=100)
        sherlock = ConcreteAgent(name="Sherlock")
        watson = ConcreteAgent(name="Watson")
        moriarty = ConcreteAgent(name="Moriarty")

        agents_cycle = [sherlock, watson, moriarty]
        results = []
        for i in range(6):
            agent = agents_cycle[i % 3]
            result = await strategy.should_terminate(agent, [])
            results.append(result)

        # First 5 turns should be False, last should be True (turn 6 == max_turns)
        assert results == [False, False, False, False, False, True]
        assert strategy.turn_count == 6
        assert strategy.cycle_count == 2  # Sherlock appeared at turns 0, 3


class TestOracleTerminationStrategySummary:
    """Tests for OracleTerminationStrategy.get_termination_summary()."""

    def test_summary_initial_state(self):
        """Summary reflects initial state with all counters at zero."""
        strategy = OracleTerminationStrategy()
        summary = strategy.get_termination_summary()

        assert summary["turn_count"] == 0
        assert summary["cycle_count"] == 0
        assert summary["max_turns"] == 15
        assert summary["max_cycles"] == 5
        assert summary["is_solution_found"] is False
        assert summary["solution_proposed"] is False
        assert summary["elimination_possible"] is False

    async def test_summary_after_turns(self):
        """Summary reflects updated turn and cycle counts after calls."""
        strategy = OracleTerminationStrategy(max_turns=100, max_cycles=100)
        sherlock = ConcreteAgent(name="Sherlock")
        watson = ConcreteAgent(name="Watson")

        await strategy.should_terminate(sherlock, [])
        await strategy.should_terminate(watson, [])
        await strategy.should_terminate(sherlock, [])

        summary = strategy.get_termination_summary()
        assert summary["turn_count"] == 3
        assert summary["cycle_count"] == 2

    def test_summary_with_oracle_state_solution_proposed(self):
        """Summary shows solution_proposed from oracle_state."""
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            solvable_by_elimination=False,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state)
        summary = strategy.get_termination_summary()

        assert summary["solution_proposed"] is True
        assert summary["elimination_possible"] is False

    def test_summary_with_elimination_possible(self):
        """Summary shows elimination_possible from oracle_state."""
        mock_state = _make_oracle_state(
            is_solution_proposed=False,
            solvable_by_elimination=True,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state)
        summary = strategy.get_termination_summary()

        assert summary["solution_proposed"] is False
        assert summary["elimination_possible"] is True

    async def test_summary_after_solution_found(self):
        """Summary reflects is_solution_found=True after a correct solution terminates."""
        solution = {"suspect": "A", "weapon": "B", "room": "C"}
        mock_state = _make_oracle_state(
            is_solution_proposed=True,
            final_solution=solution,
            secret_solution=solution,
        )
        strategy = OracleTerminationStrategy(oracle_state=mock_state, max_turns=100)
        agent = ConcreteAgent(name="Watson")

        await strategy.should_terminate(agent, [])

        summary = strategy.get_termination_summary()
        assert summary["is_solution_found"] is True
        assert summary["turn_count"] == 1

    def test_summary_without_oracle_state(self):
        """Summary handles missing oracle_state gracefully."""
        strategy = OracleTerminationStrategy()
        summary = strategy.get_termination_summary()

        assert summary["solution_proposed"] is False
        assert summary["elimination_possible"] is False

    def test_summary_custom_limits(self):
        """Summary reflects custom max_turns and max_cycles."""
        strategy = OracleTerminationStrategy(max_turns=42, max_cycles=7)
        summary = strategy.get_termination_summary()

        assert summary["max_turns"] == 42
        assert summary["max_cycles"] == 7

    def test_summary_returns_dict(self):
        """get_termination_summary() returns a dictionary."""
        strategy = OracleTerminationStrategy()
        summary = strategy.get_termination_summary()
        assert isinstance(summary, dict)

    def test_summary_has_expected_keys(self):
        """Summary contains all expected keys."""
        strategy = OracleTerminationStrategy()
        summary = strategy.get_termination_summary()
        expected_keys = {
            "turn_count", "cycle_count", "max_turns", "max_cycles",
            "is_solution_found", "solution_proposed", "elimination_possible",
        }
        assert set(summary.keys()) == expected_keys
