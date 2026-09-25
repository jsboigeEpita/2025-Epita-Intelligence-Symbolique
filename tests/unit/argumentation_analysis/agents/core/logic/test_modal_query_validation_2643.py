"""#2643 — a modal query is validated against the belief set it runs on.

``ModalLogicAgent.generate_queries`` validated each query with
``validate_modal_formula``, which parses the formula alone. MlParser checks a
formula's predicates against the signature it holds from earlier parses, so a
query on the belief set's own atoms was refused unless some earlier call in the
process had parsed that belief set (a rebuilt belief set, a restarted service).

The atoms below are used nowhere else, so no earlier parse in the session can
have declared them: each test sees the state a fresh process would.
"""

import sys
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked, reason="#2643 needs the real JVM (jpype is mocked)"
    ),
]

KB = "type(rainqvx)\ntype(wetqvx)\n\n[](rainqvx => wetqvx)\nrainqvx"
QUERIES = ["[](wetqvx)", "<>(rainqvx)", "wetqvx && rainqvx", "[](wetqvx"]


@pytest.fixture(scope="module")
def handler():
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    if not initialize_jvm():
        pytest.skip("the JVM does not start on this seat")
    return TweetyBridge().modal_handler


def test_a_query_on_the_belief_sets_own_atoms_validates_before_any_parse(handler):
    is_valid, message = handler.validate_query(KB, "[](wetqvx)")

    assert is_valid, message


@pytest.mark.parametrize("query", QUERIES)
def test_validation_agrees_with_execution(handler, query):
    is_valid, _ = handler.validate_query(KB, query)
    executed = handler.execute_modal_query(KB, query)

    assert is_valid == (not executed.startswith("FUNC_ERROR")), executed


# Atoms of their own: the tests above parse ``KB``, this one needs a belief set
# that nothing in the session has parsed, as after a rebuild.
REBUILT = "type(rainqvy)\ntype(wetqvy)\n\n[](rainqvy => wetqvy)\nrainqvy"


async def test_the_agent_generates_a_query_on_a_rebuilt_belief_set(
    handler, monkeypatch
):
    import semantic_kernel as sk
    from unittest.mock import AsyncMock
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from semantic_kernel.contents import ChatMessageContent
    from semantic_kernel.contents.utils.author_role import AuthorRole

    from argumentation_analysis.agents.core.logic.belief_set import ModalBeliefSet
    from argumentation_analysis.agents.core.logic.logic_factory import (
        LogicAgentFactory,
    )

    reply = '{"query_ideas": [{"formula": "[](wetqvy)"}]}'
    chat = AsyncMock(
        return_value=[ChatMessageContent(role=AuthorRole.ASSISTANT, content=reply)]
    )
    monkeypatch.setattr(OpenAIChatCompletion, "get_chat_message_contents", chat)
    kernel = sk.Kernel()
    service = OpenAIChatCompletion(
        service_id="default", ai_model_id="gpt-test", api_key="sk-test"
    )
    kernel.add_service(service)
    agent = LogicAgentFactory.create_agent("modal", kernel, service)

    queries = await agent.generate_queries("Il pleut.", ModalBeliefSet(REBUILT))

    assert chat.await_count == 1
    assert queries == ["[](wetqvy)"]
