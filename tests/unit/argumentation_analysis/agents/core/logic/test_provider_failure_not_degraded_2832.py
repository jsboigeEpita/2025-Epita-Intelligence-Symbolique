# -*- coding: utf-8 -*-
"""#2832 — a provider failure is not "the model said nothing".

The logic agents degrade on any exception: ``text_to_belief_set`` returns
``(None, message)`` and ``generate_queries`` returns ``[]``. That is the right
answer for a model whose *output* cannot be used. It is the wrong answer for a
*provider* failure: a rejected key, a rate limit, a timeout or a 5xx is raised by
the SDK, and collapsing it into an empty result made five authentic tests pass or
skip on a dead provider (one passed on ``[]``, four skipped on ``None`` —
measured on ai-01 with a dummy key, #2832).

These four tests are the born-red pair of the four repaired surfaces: on ``main``
each one fails with "DID NOT RAISE", because the agent returned its degraded
value instead of letting the provider failure out. No LLM is called and no JVM is
needed — the kernel holds a fake chat service, and the bridge double is never
reached (the provider failure happens first).

The two controls hold the other side: an exception that is *not* a provider
failure keeps degrading exactly as before (#1019 — an input from calling code
fails loud, a model output degrades in the state).
"""

from types import SimpleNamespace
from typing import Any, List

import httpx
import openai
import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.belief_set import (
    ModalBeliefSet,
    PropositionalBeliefSet,
)
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.core.llm_errors import provider_failure

SERVICE_ID = "provider_failure_2832"
TEXT = "S'il pleut, la route est mouillée. Or il pleut."
MODAL_KB = "p1\ntype(p1)\np2\ntype(p2)"
PL_KB = "p1\np2"
# ``generate_queries`` returns [] before calling the LLM when the belief set
# declares no proposition (propositional_logic_agent.py:640-647). Without this
# list both PL query tests would measure that guard instead of the call.
PL_PROPOSITIONS = ["p1", "p2"]


def _rejected_request() -> openai.APIConnectionError:
    """The failure a rejected key produced on this seat (po-2023, measured).

    The fleet gateway refuses the connection instead of answering 401, so the
    family — not a status code — is what the discriminator has to recognise.
    """
    return openai.APIConnectionError(
        request=httpx.Request("POST", "https://provider.invalid/v1/chat/completions")
    )


class _ProviderFails(ChatCompletionClientBase):
    """Every call dies the way a rejected key dies."""

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        raise _rejected_request()


class _UnexpectedFailure(ChatCompletionClientBase):
    """Every call dies for a reason that is not the provider's."""

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        raise RuntimeError("unexpected non-provider failure")


class _ConcreteModalAgent(ModalLogicAgent):
    """The authentic tests' shape: the base class is abstract."""


def _service(cls):
    return cls(ai_model_id="fake-2832", service_id=SERVICE_ID)


def _bridge_double():
    """``setup_agent_components`` asks the bridge only whether the JVM is ready
    (``propositional_logic_agent.py:323``); everything past that is a handler
    call, and no test here reaches one — the provider failure happens at the LLM
    call, before any Tweety use."""
    return SimpleNamespace(initializer=SimpleNamespace(is_jvm_ready=lambda: True))


def _modal_agent(cls):
    kernel = sk.Kernel()
    kernel.add_service(_service(cls))
    agent = _ConcreteModalAgent(
        kernel=kernel,
        agent_name="ModalLogicAgent",
        service_id=SERVICE_ID,
        tweety_bridge=_bridge_double(),
    )
    agent.setup_agent_components(SERVICE_ID)
    return agent


def _pl_agent(cls):
    kernel = sk.Kernel()
    kernel.add_service(_service(cls))
    agent = PropositionalLogicAgent(
        kernel=kernel, service_id=SERVICE_ID, tweety_bridge=_bridge_double()
    )
    agent.setup_agent_components(SERVICE_ID)
    return agent


# ── the discriminator itself ──────────────────────────────────────────


def test_the_discriminator_finds_the_provider_failure_in_the_chain():
    """The measured chain is KernelInvokeException → FunctionExecutionException
    → APIConnectionError; the walker must find the provider member, not the wrapper."""
    from semantic_kernel.exceptions import (
        FunctionExecutionException,
        KernelInvokeException,
    )

    provider = _rejected_request()
    inner = FunctionExecutionException("the function raised")
    inner.__cause__ = provider
    outer = KernelInvokeException("the kernel invoke failed")
    outer.__cause__ = inner

    assert provider_failure(outer) is provider
    assert provider_failure(provider) is provider, "the leaf itself must match"
    assert provider_failure(RuntimeError("boom")) is None
    assert provider_failure(ValueError("not a provider problem")) is None


# ── the four repaired surfaces (born-red on main) ─────────────────────


async def test_modal_text_to_belief_set_raises_on_a_provider_failure():
    agent = _modal_agent(_ProviderFails)

    with pytest.raises(Exception) as excinfo:
        await agent.text_to_belief_set(TEXT)

    assert (
        provider_failure(excinfo.value) is not None
    ), "the provider failure was degraded into (None, message) instead of raised"


async def test_modal_generate_queries_raises_on_a_provider_failure():
    agent = _modal_agent(_ProviderFails)

    with pytest.raises(Exception) as excinfo:
        await agent.generate_queries(TEXT, ModalBeliefSet(MODAL_KB))

    assert (
        provider_failure(excinfo.value) is not None
    ), "the provider failure was degraded into [] instead of raised"


async def test_pl_text_to_belief_set_raises_on_a_provider_failure():
    agent = _pl_agent(_ProviderFails)

    with pytest.raises(Exception) as excinfo:
        await agent.text_to_belief_set(TEXT)

    assert (
        provider_failure(excinfo.value) is not None
    ), "the provider failure was degraded into (None, message) instead of raised"


async def test_pl_generate_queries_raises_on_a_provider_failure():
    agent = _pl_agent(_ProviderFails)

    with pytest.raises(Exception) as excinfo:
        await agent.generate_queries(
            TEXT, PropositionalBeliefSet(PL_KB, propositions=PL_PROPOSITIONS)
        )

    assert (
        provider_failure(excinfo.value) is not None
    ), "the provider failure was degraded into [] instead of raised"


# ── the controls: a non-provider failure keeps degrading (#1019) ──────


async def test_modal_text_to_belief_set_still_degrades_on_another_failure():
    agent = _modal_agent(_UnexpectedFailure)

    belief_set, status = await agent.text_to_belief_set(TEXT)

    assert belief_set is None
    assert "Erreur inattendue" in status


async def test_modal_generate_queries_still_degrades_on_another_failure():
    agent = _modal_agent(_UnexpectedFailure)

    queries = await agent.generate_queries(TEXT, ModalBeliefSet(MODAL_KB))

    assert queries == []


async def test_pl_text_to_belief_set_still_degrades_on_another_failure():
    agent = _pl_agent(_UnexpectedFailure)

    belief_set, status = await agent.text_to_belief_set(TEXT)

    assert belief_set is None
    assert status, "the degradation must stay traced"


async def test_pl_generate_queries_still_degrades_on_another_failure():
    agent = _pl_agent(_UnexpectedFailure)

    queries = await agent.generate_queries(
        TEXT, PropositionalBeliefSet(PL_KB, propositions=PL_PROPOSITIONS)
    )

    assert queries == []
