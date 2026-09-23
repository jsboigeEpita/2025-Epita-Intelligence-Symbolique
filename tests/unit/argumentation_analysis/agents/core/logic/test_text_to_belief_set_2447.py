# -*- coding: utf-8 -*-
"""
#2447 item 5 — ``FOLLogicAgent.text_to_belief_set`` asks the LLM.

On ``main`` it returned ``_basic_fol_conversion(text)`` directly: the LLM was
never called, and placeholder formulas (``P0(a)``) came back as the text's
belief set, with the status "Converted to N FOL formulas". Measured on the
real-JVM module: ``test_end_to_end_fol_syllogism_with_llm`` passed with 0
watched LLM requests.

Now the conversion is ``_convert_to_fol``'s. The LLM's formulas become the
belief set, with the sort and predicate declarations the parser needs. When
only the heuristic can run, there is no belief set, and the status names why.

No LLM is called: the kernel holds a fake chat service. No JVM: the agent
gets a bridge double, which ``text_to_belief_set`` does not use (the setup
would otherwise build a real ``TweetyBridge``).
"""

import json
from typing import Any, List

import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent

SERVICE_ID = "fol_text_to_belief_set_2447"
TEXT = "Tous les hommes sont mortels. Socrate est un homme."
LLM_FORMULAS = ["forall X: (Homme(X) => Mortel(X))", "Homme(socrate)"]


class _FakeChat(ChatCompletionClientBase):
    """Answers every prompt with ``answer`` and counts the calls."""

    answer: str = ""
    calls: int = 0

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        self.calls += 1
        return [
            ChatMessageContent(
                role="assistant", content=self.answer, ai_model_id=self.ai_model_id
            )
        ]


def _agent(answer: str):
    chat = _FakeChat(ai_model_id="fake-2447", service_id=SERVICE_ID, answer=answer)
    kernel = sk.Kernel()
    kernel.add_service(chat)
    agent = FOLLogicAgent(kernel=kernel, service_id=SERVICE_ID, tweety_bridge=object())
    return agent, chat


async def test_the_llm_formulas_become_the_belief_set():
    agent, chat = _agent(json.dumps({"formulas": LLM_FORMULAS}))

    belief_set, status = await agent.text_to_belief_set(TEXT)

    assert chat.calls == 1, "the conversion did not ask the LLM"
    assert belief_set is not None, status
    assert belief_set.content == chr(10).join(
        FOLLogicAgent.build_signature_prefixed_formulas(LLM_FORMULAS)
    )
    assert "type(Mortel(thing))" in belief_set.content
    assert status == "Converted to 2 FOL formulas (llm)"


async def test_a_failed_llm_conversion_is_no_belief_set():
    """The model answers in prose: ``json.loads`` raises, and only the
    heuristic could run. Its placeholder formulas translate nothing."""
    agent, chat = _agent("Voici les formules : …")

    belief_set, status = await agent.text_to_belief_set(TEXT)

    assert chat.calls == 1
    assert belief_set is None
    assert "aucune formule traduite du texte" in status
    assert "JSONDecodeError" in status


async def test_an_empty_llm_conversion_is_no_belief_set():
    agent, _ = _agent(json.dumps({"formulas": []}))

    belief_set, status = await agent.text_to_belief_set(TEXT)

    assert belief_set is None
    assert "no formulas" in status
