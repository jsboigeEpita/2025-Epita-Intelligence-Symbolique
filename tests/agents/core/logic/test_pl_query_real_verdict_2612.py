"""#2612: the PL query paths return a real entailment verdict on a real JVM.

``TweetyBridge.execute_pl_query`` delegated to a ``PLHandler.execute_pl_query``
that never existed, and ``PropositionalLogicAgent.execute_query`` called the
wrapper with keywords outside its signature — the ``TypeError`` fired before
the ``AttributeError`` ever surfaced. On main, every PL query therefore came
back ``(None, "FUNC_ERROR: ...")``: no verdict, on both production call paths
(the agent and the ``LogicAgentPlugin`` kernel function).
"""

import json
from unittest.mock import patch

import pytest

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


def _pl_agent(bridge: TweetyBridge) -> PropositionalLogicAgent:
    """Agent PL sur un service jamais appelé — ``execute_query`` ne touche
    pas le LLM, seulement le pont Tweety injecté."""
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="keyless_2612", ai_model_id="keyless", api_key="keyless"
        )
    )
    agent = PropositionalLogicAgent(
        kernel=kernel, agent_name="PlRealVerdict2612", service_id="keyless_2612"
    )
    agent._tweety_bridge = bridge
    return agent


@pytest.mark.jpype
async def test_agent_query_returns_real_verdicts(tweety_bridge_fixture):
    """La barrière 1 (kwargs hors signature) et la barrière 2 (méthode
    PLHandler inexistante) sont franchies toutes les deux : requête entraînée
    → True, requête non entraînée → False, aucun FUNC_ERROR."""
    if not tweety_bridge_fixture.initializer.is_jvm_ready():
        pytest.skip("JVM Tweety indisponible")

    agent = _pl_agent(tweety_bridge_fixture)
    belief_set = PropositionalBeliefSet("(a => b) & a")

    entailed, message = await agent.execute_query(belief_set, "b")
    assert entailed is True
    assert "FUNC_ERROR" not in message

    rejected, message_rejected = await agent.execute_query(belief_set, "c")
    assert rejected is False
    assert "FUNC_ERROR" not in message_rejected


@pytest.mark.jpype
def test_plugin_query_returns_real_verdict(tweety_bridge_fixture):
    """Le kernel function du plugin rend un verdict d'entraînement réel,
    pas un JSON d'erreur (AttributeError avalé par le except du plugin)."""
    if not tweety_bridge_fixture.initializer.is_jvm_ready():
        pytest.skip("JVM Tweety indisponible")

    from argumentation_analysis.plugins.logic_agent_plugin import LogicAgentPlugin

    plugin = LogicAgentPlugin()
    payload = json.dumps({"belief_set": "(a => b) & a", "query": "b"})
    with patch(
        "argumentation_analysis.plugins.logic_agent_plugin._jvm_available",
        return_value=True,
    ):
        result = json.loads(plugin.execute_pl_query(payload))

    assert result.get("accepted") is True
    assert "error" not in result


def test_bridge_wrapper_is_deleted():
    """Le wrapper déléguant à une méthode inexistante ne revient pas."""
    assert not hasattr(TweetyBridge, "execute_pl_query")


def test_no_plhandler_method_named_after_the_wrapper():
    """DoD 3 : aucune méthode n'est ajoutée à PLHandler pour satisfaire le
    nom du wrapper."""
    from argumentation_analysis.agents.core.logic.pl_handler import PLHandler

    assert not hasattr(PLHandler, "execute_pl_query")
