# -*- coding: utf-8 -*-
"""
#2447 (item 3) — ``validate_argument`` asks the solver the question it
answers, and raises when nothing was checked.

On ``main``:

- ``FOLLogicAgent.validate_argument`` awaited ``check_consistency`` with a
  list and no ``logic_type``. The bridge method is sync and takes a string, so
  the call failed, the error was caught, and the method returned ``False``
  ("invalid") for every argument. It also returned ``False`` with no bridge.
  Its negation, ``not (…)``, is not Tweety syntax (``!``).
- ``ModalLogicAgent.validate_argument`` returned ``not is_consistent``. For a
  solver that did not decide (``None``, for example a formula Tweety cannot
  parse) that is ``True``: "valid".

No LLM and no JVM: the kernel holds a fake chat service and the bridge is a
double. The real-JVM check is ``test_validate_argument_on_the_real_solver``
in ``tests/integration/workers/test_worker_fol_tweety.py``.
"""

from typing import Any, List

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import (
    ModalLogicAgent,
)

SERVICE_ID = "validate_argument_2447"
PREMISES = ["forall X: (Man(X) => Mortal(X))", "Man(socrate)"]
CONCLUSION = "Mortal(socrate)"


class _FakeChat(ChatCompletionClientBase):
    """A chat service the agents' constructors accept. Never called here."""

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        raise AssertionError("validate_argument must not call the model")


def _kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    kernel.add_service(_FakeChat(ai_model_id="fake-2447", service_id=SERVICE_ID))
    return kernel


class _FolBridge:
    """Records the call with the real bridge's signature and answers a fixed
    verdict."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def check_consistency(self, belief_set, logic_type="propositional"):
        self.calls.append((belief_set, logic_type))
        return self.verdict


class _ModalHandler:
    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def is_modal_kb_consistent(self, belief_set):
        self.calls.append(belief_set)
        return self.verdict


class _ModalBridge:
    def __init__(self, verdict):
        self.modal_handler = _ModalHandler(verdict)


def _fol(bridge) -> FOLLogicAgent:
    return FOLLogicAgent(kernel=_kernel(), service_id=SERVICE_ID, tweety_bridge=bridge)


def _modal(bridge) -> ModalLogicAgent:
    agent = ModalLogicAgent(kernel=_kernel(), service_id=SERVICE_ID)
    agent._tweety_bridge = bridge
    return agent


# ---------------------------------------------------------------------------
# FOLLogicAgent
# ---------------------------------------------------------------------------


async def test_fol_calls_the_bridge_with_a_string_and_first_order():
    bridge = _FolBridge((False, "inconsistent"))

    assert await _fol(bridge).validate_argument(PREMISES, CONCLUSION) is True

    assert len(bridge.calls) == 1, bridge.calls
    belief_set, logic_type = bridge.calls[0]
    assert isinstance(belief_set, str), type(belief_set)
    assert logic_type == "first_order"
    lines = belief_set.splitlines()
    assert "!(Mortal(socrate))" in lines, "Tweety negation is '!'"
    assert "type(Mortal(thing))" in lines, "the parser needs the signature"
    assert "thing = {socrate}" in lines
    for premise in PREMISES:
        assert premise in lines


async def test_fol_premises_compatible_with_the_negation_are_invalid():
    """Non-vacuity: the other decided verdict."""
    bridge = _FolBridge((True, "consistent"))

    assert await _fol(bridge).validate_argument(PREMISES, "Man(platon)") is False


async def test_fol_an_undecided_solver_raises():
    bridge = _FolBridge((None, "Degraded: timeout"))

    with pytest.raises(RuntimeError, match="Degraded: timeout"):
        await _fol(bridge).validate_argument(PREMISES, CONCLUSION)


async def test_fol_no_bridge_raises():
    agent = _fol(None)
    assert agent.tweety_bridge is None

    with pytest.raises(RuntimeError, match="bridge"):
        await agent.validate_argument(PREMISES, CONCLUSION)


# ---------------------------------------------------------------------------
# ModalLogicAgent (same method, same defect in the other direction)
# ---------------------------------------------------------------------------


async def test_modal_an_undecided_solver_is_not_valid():
    bridge = _ModalBridge((None, "Modal KB parse error"))

    with pytest.raises(RuntimeError, match="parse error"):
        await _modal(bridge).validate_argument(["[](p => q"], "[](q)")
    assert bridge.modal_handler.calls, "the handler double was never asked"


@pytest.mark.parametrize("consistent, valid", [(False, True), (True, False)])
async def test_modal_a_decided_verdict_is_kept(consistent, valid):
    bridge = _ModalBridge((consistent, "decided"))

    result = await _modal(bridge).validate_argument(["[](p => q)", "[](p)"], "[](q)")

    assert result is valid


async def test_modal_no_bridge_raises():
    agent = _modal(None)

    with pytest.raises(RuntimeError, match="bridge"):
        await agent.validate_argument(["[](p)"], "[](p)")
