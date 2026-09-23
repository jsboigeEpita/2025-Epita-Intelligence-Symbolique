# -*- coding: utf-8 -*-
"""
#2456 — the conversational real mode runs its FOL step, and the report
prints only a consistency value that an agent produced.

On ``main`` the ``fol_logic`` step was in ``run_orchestration_async``'s
order and had a result adapter, but ``_setup_real_agents`` registered no
FOL agent, so the step was skipped on every run ("Agent 'fol_logic' not
available"). Had one been registered, ``_invoke_real_agent`` would have
called ``analyze_text``, which ``FOLLogicAgent`` does not have. The report
then printed ``Cohérence logique: 0.00/1.0``, the initial value of
``AnalysisState.consistency_score``, as if a check had found it. The micro
mode printed the same line: its modal agent was never dispatched
(``SimulatedAgent.analyze`` answered ``Unknown agent type``).

The informal step ran, but the orchestrator never called the agent's
``setup_agent_components``: every analysis answered "Plugin 'InformalAnalyzer'
not found", and the adapter counted that error entry as a fallacy ("1
sophisme détecté", type "unknown").

The kernel holds a fake chat service, and the Tweety bridge is a double
that records its calls. No LLM and no JVM are used.
"""

import json

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic import fol_logic_agent
from argumentation_analysis.orchestration.conversation_orchestrator import (
    AnalysisState,
    ConversationOrchestrator,
)

TEXT = "Tous les hommes sont mortels. Socrate est un homme."
FORMULAS = ["forall X: (Homme(X) => Mortel(X))", "Homme(socrate)"]
FALLACIES = [{"fallacy_type": "ad_hominem", "confidence": 0.9}]


class _FakeChat(ChatCompletionClientBase):
    """Answers the FOL prompts with the conversion prompt's own example, and
    the informal agent's prompt with one fallacy."""

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        prompt = chr(10).join(str(m.content) for m in chat_history.messages)
        answer = {"formulas": FORMULAS} if "FOL" in prompt else {"sophismes": FALLACIES}
        return [
            ChatMessageContent(
                role="assistant",
                content=json.dumps(answer),
                ai_model_id=self.ai_model_id,
            )
        ]


@pytest.fixture
def real_orchestrator(monkeypatch):
    """``ConversationOrchestrator(mode="real")`` on a kernel with a fake chat
    service. The FOL agent's setup builds its bridge from the module's
    ``TweetyBridge``, replaced by a double answering ``verdict``."""

    def build(verdict):
        calls = []

        class _Bridge:
            def check_consistency(self, content, logic_type):
                calls.append((content, logic_type))
                return verdict, "bridge double"

        monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _Bridge)
        kernel = sk.Kernel()
        kernel.add_service(_FakeChat(ai_model_id="fake-2456", service_id="fake"))
        return ConversationOrchestrator(mode="real", kernel=kernel), calls

    return build


def _report_line(report, label):
    lines = [line for line in report.splitlines() if label in line]
    assert len(lines) == 1, lines
    return lines[0]


def _consistency_line(report):
    return _report_line(report, "Cohérence logique")


def _fallacies_line(report):
    return _report_line(report, "Sophismes détectés:**")


@pytest.mark.parametrize(
    "verdict, consistency, printed",
    [(True, 1.0, "1.00/1.0"), (None, None, "non déterminée")],
)
async def test_the_real_mode_runs_the_fol_step(
    real_orchestrator, verdict, consistency, printed
):
    orch, calls = real_orchestrator(verdict)
    assert orch.mode == "real"
    assert "fol_logic" in orch._real_agents, orch.real_agent_setup_failures

    report = await orch.run_orchestration_async(TEXT)

    assert len(calls) == 1 and calls[0][1] == "first_order", calls
    fol = orch.state.agent_results["fol_logic"]
    assert fol["consistency"] == consistency
    assert fol["satisfiable"] is verdict
    assert "modal" not in orch.state.agent_results
    assert orch.state.consistency_score == consistency
    assert _consistency_line(report).endswith(printed)

    informal = orch.state.agent_results["informal"]
    assert informal["fallacies_count"] == 1
    assert informal["main_issues"] == ["ad_hominem"]
    assert "analysis_errors" not in informal
    assert _fallacies_line(report).endswith("** 1")


async def test_a_report_without_a_fol_result_prints_no_consistency_value():
    """The real mode with the informal agent only (the FOL step produced
    nothing): the report does not print the initial ``0.00``."""
    orch = ConversationOrchestrator(mode="demo")
    orch.mode = "real"

    class _Informal:
        name = "InformalAnalysisAgent"

        async def perform_complete_analysis(self, text):
            return {"fallacies": []}

    orch._real_agents = {"informal": _Informal()}

    report = await orch.run_orchestration_async(TEXT)

    assert orch.state.consistency_score is None
    assert _consistency_line(report).endswith("non déterminée")


async def test_a_failed_informal_analysis_is_no_fallacy():
    """``analyze_fallacies`` reports a failure as an ``"error"`` entry in the
    list. The count and the report do not read it as a fallacy."""
    orch = ConversationOrchestrator(mode="demo")
    orch.mode = "real"

    class _Informal:
        name = "InformalAnalysisAgent"

        async def perform_complete_analysis(self, text):
            return {"fallacies": [{"error": "Plugin 'InformalAnalyzer' not found"}]}

    orch._real_agents = {"informal": _Informal()}

    report = await orch.run_orchestration_async(TEXT)

    informal = orch.state.agent_results["informal"]
    assert informal["fallacies_count"] == 0
    assert informal["analysis_errors"] == ["Plugin 'InformalAnalyzer' not found"]
    assert "sophistication_score" not in informal
    assert orch.state.fallacies_detected == 0
    assert orch.state.score == 0.0
    assert _fallacies_line(report).endswith(
        "non déterminé (analyse en échec : Plugin 'InformalAnalyzer' not found)"
    )


async def test_a_report_without_any_analysis_prints_no_value():
    orch = ConversationOrchestrator(mode="demo")
    orch.mode = "real"
    orch._real_agents = {}

    report = await orch.run_orchestration_async(TEXT)

    assert _fallacies_line(report).endswith("non déterminé (aucune analyse informelle)")
    assert _consistency_line(report).endswith("non déterminée")


def test_no_consistency_before_an_agent_produces_one():
    state = AnalysisState()
    assert state.consistency_score is None
    assert state.to_dict()["consistency_score"] is None


async def test_the_fol_step_calls_the_agents_analyze():
    orch = ConversationOrchestrator(mode="demo")
    seen = []

    class _Fol:
        async def analyze(self, text, context=None):
            seen.append(text)
            return {"consistency_check": False}

    assert await orch._invoke_real_agent("fol_logic", _Fol(), TEXT) == {
        "consistency_check": False
    }
    assert seen == [TEXT]


def test_the_demo_fol_step_lands_under_its_own_name():
    orch = ConversationOrchestrator(mode="demo")
    orch.run_orchestration(TEXT)

    assert "fol_logic" in orch.state.agent_results
    assert "modal" not in orch.state.agent_results


def test_the_micro_mode_runs_its_modal_agent():
    orch = ConversationOrchestrator(mode="micro")
    report = orch.run_orchestration(TEXT)

    modal = orch.state.agent_results["modal"]
    assert "error" not in modal, modal
    assert orch.state.agents_active == 2
    assert _consistency_line(report).endswith(f"{modal['consistency']:.2f}/1.0")
