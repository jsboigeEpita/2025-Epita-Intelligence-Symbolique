"""
RA-6 #1051 — Regression test: PM designation is consumed on the SK-native path.

The conversational orchestrator's _run_phase() creates an AgentGroupChat with
a DelegatingSelectionStrategy that reads state.consume_next_agent_designation().
This test verifies:

1. DelegatingSelectionStrategy honours PM designation (core unit test)
2. The wiring in _run_phase actually passes selection_strategy to AgentGroupChat
3. PM designation is consumed (not left dangling) after selection

These tests run WITHOUT API keys (mock agents, real state).
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


class TestDelegatingSelectionHonoursPM:
    """Core: DelegatingSelectionStrategy consumes PM designation."""

    @pytest.fixture
    def strategy_components(self):
        try:
            from argumentation_analysis.core.strategies import (
                DelegatingSelectionStrategy,
            )
            from argumentation_analysis.core.shared_state import (
                RhetoricalAnalysisState,
            )
        except ImportError:
            pytest.skip("DelegatingSelectionStrategy or RhetoricalAnalysisState not importable")

        state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")

        pm = MagicMock()
        pm.name = "ProjectManager"

        extract = MagicMock()
        extract.name = "ExtractAgent"

        informal = MagicMock()
        informal.name = "InformalAnalysisAgent"

        agents = [pm, extract, informal]
        strategy = DelegatingSelectionStrategy(agents, state)
        return state, strategy, agents, pm, extract, informal

    def test_designation_consumed_by_strategy(self, strategy_components):
        """PM designates ExtractAgent → strategy returns ExtractAgent → designation consumed."""
        state, strategy, agents, pm, extract, _ = strategy_components

        # PM designates ExtractAgent
        state.designate_next_agent("ExtractAgent")
        assert state._next_agent_designated == "ExtractAgent"

        # Strategy reads and consumes the designation
        selected = asyncio.run(strategy.next(agents, []))
        assert selected == extract, f"Expected ExtractAgent, got {selected.name}"

        # Designation consumed (no leak to next turn)
        assert state.consume_next_agent_designation() is None

    def test_no_designation_falls_to_default(self, strategy_components):
        """Without designation, strategy returns the default PM agent."""
        state, strategy, agents, pm, _, _ = strategy_components

        # No designation set
        assert state._next_agent_designated is None

        selected = asyncio.run(strategy.next(agents, []))
        assert selected == pm, f"Expected PM, got {selected.name}"

    def test_designation_consumed_after_single_read(self, strategy_components):
        """After one selection, the designation is cleared (no double-read)."""
        state, strategy, agents, pm, extract, _ = strategy_components

        state.designate_next_agent("ExtractAgent")

        # First read: returns ExtractAgent
        first = asyncio.run(strategy.next(agents, []))
        assert first == extract

        # Second read: designation consumed, returns PM default
        second = asyncio.run(strategy.next(agents, []))
        assert second == pm


class TestRunPhaseWiring:
    """Verify _run_phase wires DelegatingSelectionStrategy into AgentGroupChat."""

    def test_run_phase_creates_strategy_when_state_available(self):
        """_run_phase should pass selection_strategy to AgentGroupChat when state is available."""
        try:
            from argumentation_analysis.core.shared_state import (
                RhetoricalAnalysisState,
            )
        except ImportError:
            pytest.skip("RhetoricalAnalysisState not importable")

        state = RhetoricalAnalysisState("Test text")
        pm = MagicMock()
        pm.name = "ProjectManager"
        extract = MagicMock()
        extract.name = "ExtractAgent"
        agents = [pm, extract]

        captured_strategy = None

        async def mock_add_chat_message(msg):
            pass

        async def mock_invoke():
            return
            yield  # Make it an async generator

        class MockAgentGroupChat:
            def __init__(self, *args, **kwargs):
                nonlocal captured_strategy
                captured_strategy = kwargs.get("selection_strategy")
                self.agents = args[0] if args else kwargs.get("agents", [])

            async def add_chat_message(self, msg):
                pass

            async def invoke(self):
                return
                yield

        # Patch the import that _run_phase uses: it does
        #   from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            MockAgentGroupChat,
        ):
            try:
                asyncio.run(self._call_run_phase(agents, state))
            except Exception:
                pass  # We only care about the strategy being passed

        # Verify strategy was captured and is correct type
        if captured_strategy is not None:
            from argumentation_analysis.core.strategies import (
                DelegatingSelectionStrategy,
            )

            assert isinstance(
                captured_strategy, DelegatingSelectionStrategy
            ), f"Expected DelegatingSelectionStrategy, got {type(captured_strategy)}"
        else:
            pytest.fail("selection_strategy was not passed to AgentGroupChat")

    async def _call_run_phase(self, agents, state):
        """Helper to call _run_phase with minimal args."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        return await _run_phase(
            agents=agents,
            initial_prompt="Test prompt",
            max_turns=1,
            phase_name="test",
            state=state,
            enable_growth_validation=False,
        )


class TestDesignationIntegration:
    """Integration: state → designation → strategy → correct agent selected."""

    def test_full_designation_round_trip(self):
        """Simulate a complete PM designation round-trip with real state."""
        try:
            from argumentation_analysis.core.strategies import (
                DelegatingSelectionStrategy,
            )
            from argumentation_analysis.core.shared_state import (
                RhetoricalAnalysisState,
            )
        except ImportError:
            pytest.skip("Required classes not importable")

        state = RhetoricalAnalysisState("Le texte source de l'analyse.")

        agents = [MagicMock(name=f"Agent{i}") for i in range(4)]
        agents[0].name = "ProjectManager"
        agents[1].name = "ExtractAgent"
        agents[2].name = "InformalAnalysisAgent"
        agents[3].name = "SherlockEnqueteAgent"

        strategy = DelegatingSelectionStrategy(agents, state)

        # Turn 1: PM designates InformalAnalysisAgent
        state.designate_next_agent("InformalAnalysisAgent")
        selected = asyncio.run(strategy.next(agents, []))
        assert selected.name == "InformalAnalysisAgent"
        assert state._next_agent_designated is None  # consumed

        # Turn 2: PM designates SherlockEnqueteAgent
        state.designate_next_agent("SherlockEnqueteAgent")
        selected = asyncio.run(strategy.next(agents, []))
        assert selected.name == "SherlockEnqueteAgent"
        assert state._next_agent_designated is None  # consumed

        # Turn 3: No designation → PM default
        selected = asyncio.run(strategy.next(agents, []))
        assert selected.name == "ProjectManager"
