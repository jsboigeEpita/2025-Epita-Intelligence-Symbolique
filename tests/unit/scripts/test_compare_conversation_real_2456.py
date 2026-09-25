# -*- coding: utf-8 -*-
"""
#2456 — the conversational real mode has a caller: ``conversation_real`` in
``scripts/compare_orchestration_modes.py``.

``ConversationOrchestrator(mode="real")`` was built by no tracked module, so
the agents #2466 wired into it never ran outside a test. The comparison
instrument (#1735) now runs it under its own key, next to
``conversation_deterministic`` (same engine, simulated agents).

The runner must not report what the mode did not do:
- the orchestrator falls back to demo mode when its kernel has no LLM
  service, and those rows must not appear under ``conversation_real``;
- a step whose agent could not be built, or whose analysis failed, is not a
  completed step, and the error says which one and why;
- ``fallacy_count`` is ``None`` when no informal analysis decided, and the
  consistency is ``None`` when no solver decided.

The kernel holds a fake chat service and the Tweety bridge is a double.
No LLM and no JVM are used.
"""

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.informal import informal_agent
from argumentation_analysis.agents.core.logic import fol_logic_agent, logic_factory
from argumentation_analysis.orchestration.conversation_orchestrator import (
    AnalysisState,
)

HARNESS_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "compare_orchestration_modes.py"
)
TEXT = "Tous les hommes sont mortels. Socrate est un homme."
FORMULAS = ["forall X: (Homme(X) => Mortel(X))", "Homme(socrate)"]
FALLACIES = [{"nom": "ad-hominem", "confidence": 0.9}]


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "compare_orchestration_modes", str(HARNESS_PATH)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load_harness()


class _FakeChat(ChatCompletionClientBase):
    """Answers the FOL prompts with two formulas and the informal prompt with
    one fallacy. ``fol_delay`` stalls the FOL answer, for the budget test."""

    fol_delay: float = 0.0

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        prompt = chr(10).join(str(m.content) for m in chat_history.messages)
        if "FOL" in prompt:
            if self.fol_delay:
                await asyncio.sleep(self.fol_delay)
            answer = {"formulas": FORMULAS}
        else:
            answer = {"sophismes": FALLACIES}
        return [
            ChatMessageContent(
                role="assistant",
                content=json.dumps(answer),
                ai_model_id=self.ai_model_id,
            )
        ]


@pytest.fixture
def fake_kernel(monkeypatch):
    """A kernel factory with the fake chat service. The FOL agent builds its
    bridge from the module's ``TweetyBridge``, replaced by a double."""

    def build(verdict=True, fol_delay=0.0):
        class _Bridge:
            def check_consistency(self, content, logic_type):
                return verdict, "bridge double"

        monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _Bridge)

        def factory():
            kernel = sk.Kernel()
            kernel.add_service(
                _FakeChat(
                    ai_model_id="fake-2456",
                    service_id="fake",
                    fol_delay=fol_delay,
                )
            )
            return kernel

        return factory

    return build


def test_the_real_mode_is_a_key_of_the_default_sweep():
    assert harness.MODE_RUNNERS["conversation_real"] is (
        harness.run_conversation_real_mode
    )
    assert "conversation_real" in harness.default_modes()
    assert "conversation_real" in harness.MODE_SCOPE_DESCRIPTIONS
    rows = {r.mode: r for r in harness.compute_depth_parity()}
    assert rows["conversation_real"].depth_count == 2


@pytest.mark.parametrize("verdict, consistency", [(True, 1.0), (None, None)])
async def test_a_real_run_reports_both_steps(fake_kernel, verdict, consistency):
    result = await harness.run_conversation_real_mode(
        TEXT, "corpus_A", kernel_factory=fake_kernel(verdict)
    )

    assert result.mode == "conversation_real"
    assert result.success, result.error
    assert result.error is None
    assert (result.phases_completed, result.phases_total) == (2, 2)
    assert result.fallacy_count == 1
    assert result.state_fill_rate is None
    extra = result.extra_metrics
    assert extra["steps_completed"] == ["informal", "fol_logic"]
    assert extra["real_agent_setup_failures"] == {}
    # None = no solver decided (#2447); the step still ran.
    assert extra["consistency"] == consistency
    assert extra["formulas_count"] == len(FORMULAS)
    assert harness._compute_decides(result) is True


async def test_a_kernel_without_llm_is_a_failed_run_not_a_demo_row():
    """The orchestrator falls back to demo mode on a kernel with no chat
    service; the SimulatedAgent output must not become a real-mode row."""
    result = await harness.run_conversation_real_mode(
        TEXT, "corpus_A", kernel_factory=sk.Kernel
    )

    assert result.success is False
    assert "fell back to 'demo' mode" in result.error
    assert result.phases_completed == 0
    assert result.fallacy_count is None
    assert result.extra_metrics == {}


async def test_a_kernel_that_cannot_be_built_is_named():
    def factory():
        raise ValueError("OPENAI_API_KEY is not set")

    result = await harness.run_conversation_real_mode(
        TEXT, "corpus_A", kernel_factory=factory
    )

    assert result.success is False
    assert result.error == "setup failed: OPENAI_API_KEY is not set"


async def test_a_step_whose_agent_was_not_built_is_named(fake_kernel, monkeypatch):
    """#2649 : la doublure lève comme le fait désormais un vrai constructeur.

    Elle rendait ``None`` — un retour que la fabrique n'a plus : avec la garde
    disparue, l'orchestrateur enregistrait ``None`` comme agent. La propriété
    défendue ne change pas : l'étape est nommée avec sa cause, jamais
    silencieusement sautée.
    """
    from argumentation_analysis.agents.core.semantic_setup import SemanticSetupError

    def _cannot_build(*args, **kwargs):
        raise SemanticSetupError("settings du service LLM introuvables")

    monkeypatch.setattr(
        logic_factory.LogicAgentFactory, "create_agent", staticmethod(_cannot_build)
    )

    result = await harness.run_conversation_real_mode(
        TEXT, "corpus_A", kernel_factory=fake_kernel()
    )

    assert result.success is False
    assert result.extra_metrics["steps_completed"] == ["informal"]
    assert (result.phases_completed, result.phases_total) == (1, 2)
    assert result.error.startswith("fol_logic: SemanticSetupError: ")
    assert result.extra_metrics["consistency"] is None
    assert result.fallacy_count == 1


async def test_a_failed_informal_analysis_is_no_step_and_no_count(
    fake_kernel, monkeypatch
):
    """``analyze_fallacies`` reports a failure as an ``"error"`` entry; the
    runner counts neither the step nor a fallacy total."""

    async def failing(self, text, *args, **kwargs):
        return {"fallacies": [{"error": "Plugin 'InformalAnalyzer' not found"}]}

    monkeypatch.setattr(
        informal_agent.InformalAnalysisAgent, "perform_complete_analysis", failing
    )

    result = await harness.run_conversation_real_mode(
        TEXT, "corpus_A", kernel_factory=fake_kernel()
    )

    assert result.success is False
    assert result.fallacy_count is None
    assert result.extra_metrics["steps_completed"] == ["fol_logic"]
    assert result.error == (
        "informal: analysis failed: Plugin 'InformalAnalyzer' not found"
    )


async def test_a_budget_breach_keeps_the_steps_that_finished(fake_kernel):
    result = await harness.run_conversation_real_mode(
        TEXT,
        "corpus_A",
        max_wall_seconds=2.0,
        kernel_factory=fake_kernel(fol_delay=30.0),
    )

    assert result.terminated_by_budget is True
    assert result.success is False
    assert result.error == "Wall-clock budget (>=2s)"
    assert result.extra_metrics["steps_completed"] == ["informal"]
    assert result.phases_completed == 1
    assert result.fallacy_count == 1
    assert result.extra_metrics["consistency"] is None


def test_a_modal_result_without_consistency_leaves_it_undetermined():
    state = AnalysisState()
    state.update_from_modal({"propositions_count": 2})
    assert state.consistency_score is None
