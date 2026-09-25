"""#2641 — the PL adapter calls the logic-agent contract as it is declared.

``PLAgentAdapter.process_task`` called ``generate_queries(belief_set)`` without
the source text, ``interpret_results(belief_set, queries)`` without the text and
the results, and ``execute_query`` / ``is_consistent`` without ``await``. The
first call raised ``TypeError``, which the adapter's ``except`` reported as an
``execution_error`` issue, so no query ever ran.

The double is ``create_autospec`` of the real agent: it binds each call to the
real signature and has the real coroutine-ness, so it cannot accept a call the
agent would refuse.
"""

from unittest.mock import create_autospec

from argumentation_analysis.agents.core.logic.belief_set import (
    PropositionalBeliefSet,
)
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import (
    PLAgentAdapter,
)

_TEXT = "Il pleut, donc la route est mouillée."


async def test_every_contract_call_binds_and_is_awaited():
    belief_set = PropositionalBeliefSet(
        "pluie => mouille\npluie", propositions=["pluie", "mouille"]
    )
    agent = create_autospec(PropositionalLogicAgent, instance=True)
    agent.text_to_belief_set.return_value = (belief_set, "ok")
    agent.generate_queries.return_value = ["mouille"]
    agent.execute_query.return_value = (True, "entailed")
    agent.interpret_results.return_value = "La route est mouillée."
    agent.is_consistent.return_value = (True, "consistent")

    adapter = PLAgentAdapter()
    adapter.agent, adapter.initialized = agent, True

    result = await adapter.process_task(
        {"id": "t1", "text_extracts": [{"content": _TEXT}]}
    )

    assert result["issues"] == [], result["issues"]
    agent.generate_queries.assert_awaited_once_with(_TEXT, belief_set)
    agent.execute_query.assert_awaited_once_with(belief_set, "mouille")
    agent.interpret_results.assert_awaited_once_with(
        _TEXT, belief_set, ["mouille"], [(True, "entailed")]
    )
    agent.is_consistent.assert_awaited_once_with(belief_set)
    assert result["outputs"]["consistency_analysis"][0]["is_consistent"] is True
