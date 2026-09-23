# -*- coding: utf-8 -*-
"""
#2447 (items 1 and 2) — ``FOLAnalysisResult.consistency_check`` is a verdict
only when a solver decided.

On ``main``:

- with no Tweety bridge, ``_analyze_with_tweety`` set ``consistency_check =
  True`` ("Assume consistent si pas de vérification");
- a solver that did not decide (``(None, reason)``) went to the ``else``
  branch and added "Formules incohérentes détectées";
- the LLM enhancement step replaced the verdict with the model's own
  ``consistency`` opinion;
- the field defaulted to ``False``, so the error path of ``analyze()``
  reported "inconsistent".

The conversational orchestrator's ``fol_logic`` adapter mapped anything but
``True`` to 0.5, defaulted ``satisfiable`` to ``True``, counted every
``validation_errors`` entry as a contradiction, and turned a dataclass result
into ``{"raw": str(...)}``.

No LLM is called: the kernel holds a fake chat service. No JVM: the bridge is
a double, or its construction is patched to fail.
"""

import json
from typing import Any, List

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic import fol_logic_agent
from argumentation_analysis.agents.core.logic.fol_logic_agent import (
    FOLAnalysisResult,
    FOLLogicAgent,
)
from argumentation_analysis.orchestration.conversation_orchestrator import (
    AnalysisState,
    ConversationOrchestrator,
)

SERVICE_ID = "fol_verdict_2447"
TEXT = "Tous les hommes sont mortels. Socrate est un homme."


class _FakeChat(ChatCompletionClientBase):
    """Answers every prompt with one formula and a model opinion that the KB
    is consistent. Calls no LLM."""

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        return [
            ChatMessageContent(
                role="assistant",
                content=json.dumps(
                    {"formulas": ["Mortel(socrate)"], "consistency": True}
                ),
                ai_model_id=self.ai_model_id,
            )
        ]


class _Bridge:
    """A bridge double answering one fixed consistency verdict."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def check_consistency(self, content: str, logic_type: str):
        self.calls.append((content, logic_type))
        return self.verdict


def _kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    kernel.add_service(_FakeChat(ai_model_id="fake-2447", service_id=SERVICE_ID))
    return kernel


def _agent_with(bridge) -> FOLLogicAgent:
    return FOLLogicAgent(kernel=_kernel(), service_id=SERVICE_ID, tweety_bridge=bridge)


def _raise_bridge(*_args, **_kwargs):
    raise RuntimeError("no JVM here (2447)")


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------


async def test_no_bridge_is_no_consistency_verdict(monkeypatch):
    monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _raise_bridge)
    agent = FOLLogicAgent(kernel=_kernel(), service_id=SERVICE_ID)
    agent.setup_agent_components(llm_service_id=SERVICE_ID)
    assert agent.tweety_bridge is None

    result = await agent.analyze(TEXT)

    assert result.consistency_check is None, result
    assert "bridge" in result.consistency_message
    assert (
        "tweety_bridge" in result.consistency_message
    ), "the message should carry the setup failure that explains the absence"


async def test_an_undecided_solver_is_no_inconsistency():
    bridge = _Bridge((None, "Degraded: timeout"))
    result = await _agent_with(bridge).analyze(TEXT)

    assert bridge.calls, "the bridge double was never asked"
    assert result.consistency_check is None
    assert "Formules incohérentes détectées" not in result.validation_errors
    assert result.consistency_message == "Degraded: timeout"


@pytest.mark.parametrize("verdict", [True, False])
async def test_a_decided_verdict_is_kept(verdict):
    """Non-vacuity: a solver's answer reaches the result, ``False`` included."""
    message = "consistent" if verdict else "inconsistent"
    result = await _agent_with(_Bridge((verdict, message))).analyze(TEXT)

    assert result.consistency_check is verdict
    assert result.consistency_message == message
    incoherent = "Formules incohérentes détectées" in result.validation_errors
    assert incoherent is (not verdict)


async def test_the_llm_opinion_does_not_replace_the_verdict():
    """The fake model says ``"consistency": true``; the solver said
    "undecided". The verdict stays undecided, and the opinion is kept,
    labelled, in the reasoning steps."""
    result = await _agent_with(_Bridge((None, "Degraded: timeout"))).analyze(TEXT)

    assert result.consistency_check is None
    assert any("Avis du LLM" in step for step in result.reasoning_steps)


def test_the_default_result_claims_no_verdict():
    """The error path of ``analyze()`` builds a default result."""
    assert FOLAnalysisResult().consistency_check is None


async def test_the_statistics_do_not_count_undecided_as_inconsistent():
    agent = _agent_with(_Bridge((None, "Degraded: timeout")))
    await agent.analyze(TEXT)

    stats = agent.get_analysis_summary()
    assert stats["consistency_rate"] is None
    assert stats["consistency_undetermined"] == 1


# ---------------------------------------------------------------------------
# The conversational orchestrator's fol_logic adapter
# ---------------------------------------------------------------------------


@pytest.fixture
def orch():
    return ConversationOrchestrator(mode="demo")


def test_the_adapter_reads_the_dataclass_the_agent_returns(orch):
    """The agent returns a dataclass, not a dict."""
    raw = FOLAnalysisResult(
        formulas=["P(a)", "Q(a)"], consistency_check=True, confidence_score=0.9
    )
    adapted = orch._adapt_real_result("fol_logic", raw)

    assert adapted["formulas_count"] == 2
    assert adapted["consistency"] == 1.0
    assert adapted["logical_score"] == 0.9


def test_the_adapter_maps_undetermined_to_undetermined(orch):
    raw = FOLAnalysisResult(
        formulas=["P(a)"],
        consistency_check=None,
        consistency_message="Degraded: timeout",
        validation_errors=["Erreur Tweety: timeout"],
    )
    adapted = orch._adapt_real_result("fol_logic", raw)

    assert adapted["consistency"] is None
    assert adapted["consistency_undetermined"] is True
    assert adapted["satisfiable"] is None
    assert adapted["contradictions"] == 0, "an analysis error is no contradiction"
    assert adapted["consistency_message"] == "Degraded: timeout"


def test_the_adapter_counts_a_decided_inconsistency(orch):
    raw = FOLAnalysisResult(
        consistency_check=False,
        validation_errors=["Formules incohérentes détectées"],
    )
    adapted = orch._adapt_real_result("fol_logic", raw)

    assert adapted["consistency"] == 0.0
    assert adapted["satisfiable"] is False
    assert adapted["contradictions"] == 1


def test_the_state_keeps_an_undetermined_score():
    state = AnalysisState()
    state.update_from_modal({"propositions_count": 1, "consistency": None})

    assert state.to_dict()["consistency_score"] is None
