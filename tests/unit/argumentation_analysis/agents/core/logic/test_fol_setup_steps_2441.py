# -*- coding: utf-8 -*-
"""
#2441 — FOL setup: one step failing no longer skips the others, and the
failure is readable from the agent.

``FOLLogicAgent.setup_agent_components`` ran three independent steps in one
``try`` (parent setup, ``TweetyBridge()``, registration of the ``fol_logic``
plugin) and logged "Configuration composants FOL partielle" on any
exception. A bridge failure therefore skipped the plugin registration, and
``analyze()`` marked the agent initialized whatever happened, so the plugin
stayed absent for the life of the agent. That ``try`` had already hidden
#2360 (the registration called a method that does not exist) for months.

The decision per step follows where the failing value comes from:

- the bridge is an environment dependency (JVM, jars) the agent can run
  without: its failure degrades **by name** into ``agent.setup_failures``
  and into ``FOLAnalysisResult.setup_failures``;
- the plugin registration is configuration: its failure raises, and the
  lazy setup of ``analyze()`` retries it on the next call.

The factory side: the third parameter of ``LogicAgentFactory.create_agent``
is the LLM **service**. The factory read ``llm_service.service_id`` only
when present, so a ``str`` id (three production callers passed one) was
dropped without a trace. It now refuses an argument it cannot read.

No LLM is called: the kernel holds a fake chat service that answers every
prompt locally. The bridge is patched or injected; no JVM is needed.
"""

import asyncio
import json
from typing import Any, List

import pytest
import semantic_kernel as sk
from pydantic import Field
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.core.logic import fol_logic_agent
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

SERVICE_ID = "fol_setup_2441"
BRIDGE_CAUSE = "fabricated JVM failure 2441"
REGISTRATION_CAUSE = "fabricated registration failure 2441"


class _FakeChat(ChatCompletionClientBase):
    """Answers every prompt with one fabricated formula; calls no LLM."""

    prompts: List[str] = Field(default_factory=list)

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        self.prompts.append(str(chat_history))
        return [
            ChatMessageContent(
                role="assistant",
                content=json.dumps({"formulas": ["Gravat(pierre)"]}),
                ai_model_id=self.ai_model_id,
            )
        ]


class _InjectedBridge:
    """A bridge double: consistent, no inference, no model."""

    def check_consistency(self, content: str, logic_type: str):
        return True, "consistent"


def _kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    kernel.add_service(_FakeChat(ai_model_id="fake-2441", service_id=SERVICE_ID))
    return kernel


def _raise_bridge(*_args, **_kwargs):
    raise RuntimeError(BRIDGE_CAUSE)


def _fol_plugin_functions(kernel: sk.Kernel):
    plugin = kernel.plugins.get("fol_logic")
    return sorted(plugin.functions) if plugin is not None else None


# ---------------------------------------------------------------------------
# Step 2 (bridge) cannot skip step 3 (plugin); its failure is in the state
# ---------------------------------------------------------------------------


def test_bridge_failure_does_not_skip_the_plugin(monkeypatch):
    """Born red: on main the plugin is absent after a bridge failure."""
    monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _raise_bridge)
    kernel = _kernel()
    agent = LogicAgentFactory.create_agent("first_order", kernel)
    assert agent is not None

    agent.setup_agent_components(llm_service_id=SERVICE_ID)

    assert _fol_plugin_functions(kernel) == ["analyze_fol", "convert_to_fol"], (
        "the fol_logic plugin is missing: the bridge failure skipped its "
        "registration, which does not need the bridge"
    )
    assert agent.setup_failures == {"tweety_bridge": f"RuntimeError: {BRIDGE_CAUSE}"}
    assert agent.tweety_bridge is None


def test_bridge_failure_reaches_the_analysis_result(monkeypatch):
    """The reader of the result sees why the formal check did not run."""
    monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _raise_bridge)
    agent = FOLLogicAgent(kernel=_kernel(), service_id=SERVICE_ID)

    result = asyncio.run(agent.analyze("Texte fabriqué 2441 sur des gravats."))

    assert result.setup_failures == {"tweety_bridge": f"RuntimeError: {BRIDGE_CAUSE}"}


def test_a_successful_setup_reports_no_failure():
    """Non-vacuity: an injected bridge and a working kernel give {}."""
    kernel = _kernel()
    agent = FOLLogicAgent(
        kernel=kernel, service_id=SERVICE_ID, tweety_bridge=_InjectedBridge()
    )

    agent.setup_agent_components(llm_service_id=SERVICE_ID)

    assert agent.setup_failures == {}
    assert _fol_plugin_functions(kernel) == ["analyze_fol", "convert_to_fol"]


def test_a_bridge_that_comes_back_clears_its_failure(monkeypatch):
    """The state names the current failure, not a past one."""
    monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _raise_bridge)
    agent = FOLLogicAgent(kernel=_kernel(), service_id=SERVICE_ID)
    agent.setup_agent_components()
    assert "tweety_bridge" in agent.setup_failures

    monkeypatch.setattr(fol_logic_agent, "TweetyBridge", _InjectedBridge)
    agent.setup_agent_components()

    assert agent.setup_failures == {}
    assert isinstance(agent.tweety_bridge, _InjectedBridge)


# ---------------------------------------------------------------------------
# Step 3 (plugin) is configuration: it raises, and analyze() retries it
# ---------------------------------------------------------------------------


def _failing_registration(self):
    raise ValueError(REGISTRATION_CAUSE)


def test_plugin_registration_failure_is_not_swallowed(monkeypatch):
    """Born red: on main the exception is logged and setup returns."""
    monkeypatch.setattr(
        FOLLogicAgent, "_register_fol_semantic_functions", _failing_registration
    )
    agent = FOLLogicAgent(
        kernel=_kernel(), service_id=SERVICE_ID, tweety_bridge=_InjectedBridge()
    )

    with pytest.raises(ValueError, match=REGISTRATION_CAUSE):
        agent.setup_agent_components(llm_service_id=SERVICE_ID)


def test_analyze_retries_a_failed_registration(monkeypatch):
    """Born red: on main analyze() marked the agent initialized after the
    swallowed failure, so the second call never registered the plugin."""
    original = FOLLogicAgent._register_fol_semantic_functions
    calls = []

    def fail_once(self):
        calls.append(len(calls))
        if len(calls) == 1:
            raise ValueError(REGISTRATION_CAUSE)
        return original(self)

    monkeypatch.setattr(FOLLogicAgent, "_register_fol_semantic_functions", fail_once)
    kernel = _kernel()
    agent = FOLLogicAgent(
        kernel=kernel, service_id=SERVICE_ID, tweety_bridge=_InjectedBridge()
    )

    first = asyncio.run(agent.analyze("Premier texte fabriqué 2441."))
    assert any(
        REGISTRATION_CAUSE in e for e in first.validation_errors
    ), f"the failed registration is not named in the result: {first}"
    assert _fol_plugin_functions(kernel) is None

    asyncio.run(agent.analyze("Second texte fabriqué 2441."))

    assert len(calls) == 2, "analyze() did not retry the failed setup"
    assert _fol_plugin_functions(kernel) == ["analyze_fol", "convert_to_fol"]


# ---------------------------------------------------------------------------
# Factory: the third argument is a service, not its id
# ---------------------------------------------------------------------------


def test_factory_refuses_a_service_id_string():
    """Born red: on main the str was dropped and the agent got the default id."""
    with pytest.raises(TypeError, match="service_id"):
        LogicAgentFactory.create_agent("first_order", _kernel(), SERVICE_ID)


def test_factory_passes_the_service_id_of_a_service_object():
    """Non-vacuity: the service object is read, its id reaches the agent."""
    kernel = _kernel()
    service = kernel.get_service(SERVICE_ID)

    agent = LogicAgentFactory.create_agent("first_order", kernel, service)

    assert agent is not None
    assert agent._llm_service_id == SERVICE_ID
