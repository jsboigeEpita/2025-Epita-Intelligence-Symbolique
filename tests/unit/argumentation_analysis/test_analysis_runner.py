# -*- coding: utf-8 -*-
"""
Tests of ``AnalysisRunnerV2`` on a real kernel and a real OpenAI service whose
chat call is mocked (#2630): no network, no key.

The test that stood here patched ``AgentFactory`` and ``AgentGroupChat``, and
asserted that ``invoke`` was awaited once per phase. Awaiting ``invoke`` is
the defect itself: it is an async generator, so every phase raised. The test
stayed green while the runner could not get past its setup.
"""

import ast
import inspect
from unittest.mock import AsyncMock

import pytest
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

import argumentation_analysis.core.state_manager_plugin as state_plugin_module
import argumentation_analysis.orchestration.analysis_runner_v2 as runner_module
from argumentation_analysis.orchestration.analysis_runner_v2 import AnalysisRunnerV2

TEXT = "Il pleut, donc la route est mouillée."

# Who speaks in each phase, written out here rather than read from the runner.
CASTING = [
    ["ProjectManager", "ExtractAgent", "InformalAgent"],
    ["ProjectManager", "FormalAgent", "QualityAgent"],
    ["ProjectManager", "DebateAgent", "CounterAgent", "GovernanceAgent"],
]
TURNS_PER_PHASE = 5


def _service(chat=None):
    svc = OpenAIChatCompletion(
        service_id="caller_svc", ai_model_id="gpt-test", api_key="sk-test"
    )
    if chat is None:
        # A fresh message per call: the agent stamps its name on what it gets.
        chat = AsyncMock(
            side_effect=lambda *a, **k: [
                ChatMessageContent(role=AuthorRole.ASSISTANT, content="Tour traité.")
            ]
        )
    object.__setattr__(svc, "get_chat_message_contents", chat)
    return svc, chat


@pytest.fixture(autouse=True)
def _no_trace_file(monkeypatch):
    # A run saves its trace report under <repo>/logs; the tests do not.
    monkeypatch.setattr(runner_module, "save_enhanced_pm_report", lambda path: True)


async def test_setup_builds_every_agent_on_the_callers_service():
    svc, _ = _service()
    runner = AnalysisRunnerV2(llm_service=svc)

    await runner._setup_orchestration(TEXT, svc)

    assert {name for phase in CASTING for name in phase} <= set(runner.agents)
    assert all(agent.service is svc for agent in runner.agent_list)


def _state_methods_the_plugin_calls():
    tree = ast.parse(inspect.getsource(state_plugin_module))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "_state"
    }


async def test_the_state_carries_every_method_the_agents_plugin_calls():
    # The agents write through StateManagerPlugin; a method it calls that the
    # state lacks turns into a FUNC_ERROR the LLM reads, and the run goes on.
    svc, _ = _service()
    runner = AnalysisRunnerV2(llm_service=svc)
    await runner._setup_orchestration(TEXT, svc)

    called = _state_methods_the_plugin_calls()
    assert len(called) > 10  # the scan found the plugin's calls
    assert sorted(n for n in called if not hasattr(runner.shared_state, n)) == []


async def test_run_analysis_runs_the_three_phases_with_their_casting():
    svc, chat = _service()
    runner = AnalysisRunnerV2(llm_service=svc)

    result = await runner.run_analysis(text_content=TEXT)

    assert result["status"] == "success"
    assert runner.phase_counter == 3
    speakers = [
        m["author_name"] for m in result["history"] if m["author_role"] == "assistant"
    ]
    expected = [
        phase[turn % len(phase)] for phase in CASTING for turn in range(TURNS_PER_PHASE)
    ]
    assert speakers == expected
    assert chat.await_count == 3 * TURNS_PER_PHASE


async def test_a_failing_run_raises_instead_of_returning_an_error_result():
    svc, _ = _service(AsyncMock(side_effect=RuntimeError("chat call failed")))
    runner = AnalysisRunnerV2(llm_service=svc)

    with pytest.raises(Exception, match="chat call failed"):
        await runner.run_analysis(text_content=TEXT)
