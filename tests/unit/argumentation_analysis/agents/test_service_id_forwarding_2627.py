"""#2627 — the service id a class receives is the one ``BaseAgent`` resolves.

Four classes took a service id and kept it for themselves:
``SherlockEnqueteAgent`` (``service_id``), ``ExtractAgent``
(``llm_service_id``), ``ModalLogicAgent`` (``service_id``) and
``DeepSynthesisAgent`` (``service_id``). ``BaseAgent.__init__`` never saw it and
resolved ``"default"``, so the agent's ``service`` (the one ``AgentGroupChat``
talks through) was the kernel's first service, while the class keyed its own
functions or settings on the id it received. With two services in the kernel,
one agent held two.

The witnesses use a real ``Kernel`` and real OpenAI services built without a
network, so the resolution is Semantic Kernel's, not a double's.
"""

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import (
    ModalLogicAgent,
)
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
    SherlockEnqueteAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)


def _kernel(*service_ids):
    kernel = Kernel()
    for service_id in service_ids:
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=service_id, ai_model_id="gpt-test", api_key="sk-test"
            )
        )
    return kernel


def _sherlock(kernel, service_id):
    return SherlockEnqueteAgent(kernel, service_id=service_id)


def _extract(kernel, service_id):
    return ExtractAgent(kernel, llm_service_id=service_id)


def _modal(kernel, service_id):
    # The bridge is injected so the constructor does not build a TweetyBridge;
    # it only stores it.
    return ModalLogicAgent(kernel, service_id=service_id, tweety_bridge=object())


def _deep_synthesis(kernel, service_id):
    return DeepSynthesisAgent(kernel, service_id=service_id)


BUILDERS = {
    "sherlock": _sherlock,
    "extract": _extract,
    "modal": _modal,
    "deep_synthesis": _deep_synthesis,
}


@pytest.mark.parametrize("build", BUILDERS.values(), ids=BUILDERS.keys())
def test_the_agent_talks_through_the_service_it_was_given(build):
    # svc_b is not the kernel's first service: before the fix the agent's
    # service was svc_a, whatever the class was asked for.
    agent = build(_kernel("svc_a", "svc_b"), "svc_b")
    assert agent.service.service_id == "svc_b"


@pytest.mark.parametrize("build", BUILDERS.values(), ids=BUILDERS.keys())
def test_a_service_id_the_kernel_does_not_hold_raises_at_construction(build):
    with pytest.raises(ValueError) as info:
        build(_kernel("svc_a"), "svc_missing")
    assert "'svc_missing'" in str(info.value)
    assert "['svc_a']" in str(info.value)


def test_sherlock_default_id_is_resolved_not_dropped():
    # Sherlock defaults to "chat_completion" and keys its chat function on it.
    # On a kernel that holds it under a second position, the agent's service
    # is that one.
    agent = SherlockEnqueteAgent(_kernel("svc_a", "chat_completion"))
    assert agent.service.service_id == "chat_completion"


def test_sherlock_refuses_a_second_name_for_the_id():
    # ``llm_service_id`` used to fall into Sherlock's ``**kwargs`` and be dropped,
    # while the agent ran on its default id.
    with pytest.raises(TypeError, match="llm_service_id"):
        SherlockEnqueteAgent(_kernel("svc_a", "svc_b"), llm_service_id="svc_b")


@pytest.mark.parametrize(
    "build", [_modal, _deep_synthesis], ids=["modal", "deep_synthesis"]
)
def test_without_an_id_the_kernel_default_service_is_used(build):
    agent = build(_kernel("svc_a", "svc_b"), None)
    assert agent.service.service_id == "svc_a"


def test_deep_synthesis_without_an_id_keeps_its_llm_paths_off():
    # FB-32 #1112: ``_llm_service_id`` None is how the agent knows it has no
    # LLM path. Forwarding the id to BaseAgent must not turn None into "default".
    agent = DeepSynthesisAgent(_kernel("svc_a"))
    assert agent._llm_service_id is None
