"""#2648: a deep-synthesis settings lookup that fails raises; a failed chat
call still degrades.

``grounded_transversal_synthesis``, ``_llm_convergence_prose`` and
``_llm_synthesis`` looked up their service's prompt settings inside the ``try``
that covers the chat call. A service id the kernel does not hold (a
calling-code defect) was therefore recorded as "LLM unavailable", at ``DEBUG``
for the convergence prose. The lookup now sits before that ``try``.

Real ``Kernel`` holding one service, ``"default"``; the agent is given
``service_id="absent"``. ``BaseAgent`` resolves ``"default"`` and the agent
builds (the id is not forwarded — #2627's open item). Only the synthesis
methods read the absent id.
"""

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.semantic_setup import SemanticSetupError
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _agent(service_id):
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(service_id="default", ai_model_id="m", api_key="dummy")
    )
    return DeepSynthesisAgent(kernel, service_id=service_id)


def _state():
    state = UnifiedAnalysisState("A short discourse with two claims.")
    state.add_argument("first claim")
    state.add_argument("second claim")
    state.add_fallacy("false_dilemma", "either/or framing", "arg_2")
    return state


class TestAMisnamedServiceRaises:
    async def test_grounded_transversal_synthesis(self):
        agent = _agent("absent")
        # The lookup follows the briefing guard: the state must be citable.
        assert DeepSynthesisAgent.build_artifact_briefing(_state()).count("\n") >= 1
        with pytest.raises(SemanticSetupError, match="'absent'"):
            await agent.grounded_transversal_synthesis(_state(), None)

    async def test_convergence_prose(self):
        with pytest.raises(SemanticSetupError, match="'absent'"):
            await _agent("absent")._llm_convergence_prose(_state())

    async def test_llm_synthesis(self):
        with pytest.raises(SemanticSetupError, match="'absent'"):
            await _agent("absent")._llm_synthesis(None)


class TestAFailedChatCallStillDegrades:
    """Anti-pendulum: the value of a chat call comes from the model or the
    network, so its failure keeps degrading to the section's empty value."""

    @pytest.fixture
    def chat_down(self, monkeypatch):
        calls = []

        async def _down(self, *args, **kwargs):
            calls.append(kwargs.get("function_name"))
            raise RuntimeError("LLM down (#2648)")

        monkeypatch.setattr(Kernel, "invoke_prompt", _down)
        return calls

    async def test_grounded_transversal_synthesis(self, chat_down):
        result = await _agent("default").grounded_transversal_synthesis(_state(), None)
        assert result == ""
        assert chat_down == ["deep_synthesis_grounded_transversal"]
