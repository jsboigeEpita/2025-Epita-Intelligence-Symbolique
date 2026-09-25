"""#2645 — every logic agent's ``interpret_results`` returns the interpretation text.

The modal agent returned ``result.value`` of its prompt function. For a chat
prompt that value is the list of ``ChatMessageContent``, so the answer the query
task recorded was the repr of a list of objects. Its unit tests stood in for the
result with a double whose ``.value`` was already the text, which hid it.

Here the kernel is real and only the chat call is mocked: Semantic Kernel
itself builds the ``FunctionResult``, as on a real run.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked, reason="#2645 builds the agents on the real JVM"
    ),
]

TEXT = "Il pleut, donc la route est mouillée."
REPLY = "La route est nécessairement mouillée."
CASES = {
    "propositional": ("pluie => mouille\npluie", ["mouille"], [(True, "entailed")]),
    "modal": (
        "type(pluie)\ntype(mouille)\n\n[](pluie => mouille)\npluie",
        ["[](mouille)"],
        [(True, "ACCEPTED")],
    ),
    "first_order": (
        "forall X: (Homme(X) => Mortel(X))\nHomme(socrate)",
        ["consistency_check"],
        [(True, "consistent")],
    ),
}


@pytest.fixture(scope="module")
def jvm():
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    if not initialize_jvm():
        pytest.skip("the JVM does not start on this seat")


@pytest.fixture
def chat(monkeypatch):
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from semantic_kernel.contents import ChatMessageContent
    from semantic_kernel.contents.utils.author_role import AuthorRole

    mock = AsyncMock(
        return_value=[ChatMessageContent(role=AuthorRole.ASSISTANT, content=REPLY)]
    )
    monkeypatch.setattr(OpenAIChatCompletion, "get_chat_message_contents", mock)
    return mock


def _agent(logic_type):
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    from argumentation_analysis.agents.core.logic.logic_factory import (
        LogicAgentFactory,
    )

    kernel = sk.Kernel()
    service = OpenAIChatCompletion(
        service_id="default", ai_model_id="gpt-test", api_key="sk-test"
    )
    kernel.add_service(service)
    return LogicAgentFactory.create_agent(logic_type, kernel, service)


@pytest.mark.parametrize("logic_type", sorted(CASES))
async def test_interpret_results_returns_text(jvm, chat, logic_type):
    from argumentation_analysis.agents.core.logic.belief_set import BeliefSet

    content, queries, results = CASES[logic_type]
    belief_set = BeliefSet.from_dict({"logic_type": logic_type, "content": content})

    interpretation = await _agent(logic_type).interpret_results(
        TEXT, belief_set, queries, results
    )

    assert isinstance(interpretation, str), type(interpretation)
    if chat.await_count:  # FOL interprets by rule, without the LLM
        assert interpretation == REPLY


async def test_the_modal_prompt_calls_read_the_reply_text(jvm, chat):
    # The two other prompt calls of the modal agent went through the same
    # expression, and worked only because the JSON extractor joined a list.
    # They run in pipeline order: the belief set is built, then queried.
    from semantic_kernel.contents import ChatMessageContent
    from semantic_kernel.contents.utils.author_role import AuthorRole

    replies = [
        '{"propositions": ["pluie", "mouille"], '
        '"modal_formulas": ["[](pluie => mouille)", "pluie"]}',
        '{"query_ideas": [{"formula": "[](mouille)"}]}',
    ]
    chat.return_value = None
    chat.side_effect = [
        [ChatMessageContent(role=AuthorRole.ASSISTANT, content=r)] for r in replies
    ]
    agent = _agent("modal")

    belief_set, message = await agent.text_to_belief_set(TEXT)
    assert belief_set is not None, message
    assert "[](pluie => mouille)" in belief_set.content

    queries = await agent.generate_queries(TEXT, belief_set)
    assert queries == ["[](mouille)"]
