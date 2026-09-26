"""#2346: ``TracedAgent`` called itself a proxy but only had ``invoke``.

Its one in-tree caller, the validation demo, calls ``invoke_single`` and died
with ``AttributeError`` before anything was traced (4 scenarios out of 4,
measured on ``main`` ``5e4cd3788``). The proxy now traces ``invoke_single``
too. It still has no ``__getattr__``: relaying every attribute would let an
untraced call through without a line in the trace.

The agent is the real one, built by the real factory on the mock LLM service
the demo's ``--integration-test`` mode uses. No network, no credit.
"""

import pytest
import semantic_kernel as sk
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.agents.utils.tracer import TracedAgent
from argumentation_analysis.core.llm_service import create_llm_service

TEXT = "TEXT_UNDER_ANALYSIS_2346"


def _traced(tmp_path):
    kernel = sk.Kernel()
    service = create_llm_service(service_id="default", model_id="mock", force_mock=True)
    kernel.add_service(service)
    trace = tmp_path / "trace.log"
    traced = AgentFactory(kernel, service.service_id).create_informal_fallacy_agent(
        config_name="simple", trace_log_path=str(trace)
    )
    assert isinstance(traced, TracedAgent)
    return kernel, traced, trace


def _history():
    history = ChatHistory()
    history.add_user_message(TEXT)
    return history


async def test_invoke_single_is_traced_and_returns_the_agent_answer(tmp_path):
    kernel, traced, trace = _traced(tmp_path)
    try:
        result = await traced.invoke_single(text_to_analyze=TEXT, history=_history())
        direct = await traced.agent.invoke_single(
            text_to_analyze=TEXT, history=_history()
        )
    finally:
        traced.close()
    assert str(result) == str(direct)
    content = trace.read_text(encoding="utf-8")
    start = content.index("--- START INVOKE_SINGLE on Fallacy_Analyst ---")
    assert content.index(f"text_to_analyze={TEXT}") > start
    answer = content.index("--- RESULT for Fallacy_Analyst ---")
    assert content.index(str(result), answer) > answer
    assert content.index("--- FINAL HISTORY for Fallacy_Analyst ---") > answer


async def test_a_failing_call_is_traced_then_raised(tmp_path):
    kernel, traced, trace = _traced(tmp_path)
    kernel.remove_all_services()
    try:
        with pytest.raises(Exception) as raised:
            await traced.invoke_single(text_to_analyze=TEXT, history=_history())
    finally:
        traced.close()
    content = trace.read_text(encoding="utf-8")
    assert "--- INVOKE_SINGLE FAILED on Fallacy_Analyst ---" in content
    assert type(raised.value).__name__ in content
    assert "--- RESULT for" not in content


def test_an_untraced_entry_point_is_not_relayed(tmp_path):
    """No ``__getattr__``: ``get_response`` exists on the agent, not on the proxy."""
    kernel, traced, trace = _traced(tmp_path)
    try:
        assert hasattr(traced.agent, "get_response")
        assert "__getattr__" not in vars(TracedAgent)
        with pytest.raises(AttributeError):
            traced.get_response
    finally:
        traced.close()
