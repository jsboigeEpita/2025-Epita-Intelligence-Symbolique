# -*- coding: utf-8 -*-
"""#2544: the one Cluedo orchestrator left runs a turn into its state and lets a failure out.

The 2-agent ``cluedo_orchestrator.py`` was retired in #2544. Its loop was a copy
of ``CluedoExtendedOrchestrator.execute_workflow`` that had stopped following
it: it wrote each turn to a name its method never bound, and its ``finally``
ended with ``return``, which turned a failed run into a normal result. #2544
asked, for a repair, for one test that a turn reaches the state and one that a
failure propagates. The module is gone, so both apply to the orchestrator that
carries the Cluedo game.
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from semantic_kernel import Kernel

from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CluedoExtendedOrchestrator,
)


def _one_turn_orchestrator(agent):
    """An orchestrator set up for exactly one turn, taken by ``agent``."""
    orch = CluedoExtendedOrchestrator(
        kernel=create_autospec(Kernel, instance=True), settings=MagicMock()
    )
    orch.orchestration = MagicMock()
    orch.orchestration.active_agents = {agent.name: agent}
    orch.sherlock_agent = agent

    state = MagicMock()
    state.is_solution_proposed = False
    state.final_solution = None
    state.get_solution_secrete.return_value = {}
    state.is_game_solvable_by_elimination.return_value = False
    state.get_oracle_statistics.return_value = {
        "agent_interactions": {"total_turns": 1},
        "workflow_metrics": {"oracle_interactions": 0, "cards_revealed": 0},
        "recent_revelations": [],
    }
    state.get_fluidity_metrics.return_value = {}
    orch.oracle_state = state

    orch.termination_strategy = MagicMock()
    orch.termination_strategy.should_terminate = AsyncMock(side_effect=[False, True])
    orch.selection_strategy = MagicMock()
    orch.selection_strategy.next = AsyncMock(return_value=agent)
    return orch


def _agent(name, invoke):
    agent = MagicMock()
    agent.name = name
    agent.invoke = invoke
    return agent


async def test_a_turn_reaches_the_state():
    sherlock = _agent("Sherlock", AsyncMock(return_value="Nous avancerons pas à pas."))
    orch = _one_turn_orchestrator(sherlock)

    result = await orch.execute_workflow("L'enquête commence.")

    orch.oracle_state.add_conversation_message.assert_called_once()
    written = orch.oracle_state.add_conversation_message.call_args.kwargs
    assert written["agent_name"] == "Sherlock"
    assert written["content"] == "Nous avancerons pas à pas."
    orch.oracle_state.record_agent_turn.assert_called_once()
    assert result["conversation_history"] == [
        {"sender": "Sherlock", "message": "Nous avancerons pas à pas."}
    ]


async def test_a_failed_turn_propagates():
    class TurnFailed(RuntimeError):
        pass

    sherlock = _agent("Sherlock", MagicMock(side_effect=TurnFailed("LLM down")))
    orch = _one_turn_orchestrator(sherlock)

    with pytest.raises(TurnFailed, match="LLM down"):
        await orch.execute_workflow("L'enquête commence.")

    assert orch.end_time is not None, "the finally still stamps the end of the run"
    orch.oracle_state.add_conversation_message.assert_not_called()
