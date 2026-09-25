"""#2627 — un agent parle avec le service qu'on lui demande, ou il refuse.

``BaseAgent.__init__`` remplaçait en silence un ``llm_service_id`` absent du
kernel par le premier service du kernel. Quatre appelants passaient l'objet
``AppSettings`` à ``AgentFactory`` au lieu de l'id, et ce repli les laissait
tourner. Ces témoins utilisent un vrai ``Kernel`` et de vrais services
OpenAI construits sans réseau, pour que la résolution soit celle de Semantic
Kernel et non celle d'une doublure.
"""

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.factory import AgentFactory
from argumentation_analysis.config.settings import AppSettings


class _Agent(BaseAgent):
    def get_agent_capabilities(self):
        return {}

    async def get_response(self, *args, **kwargs):
        return None

    async def invoke_single(self, *args, **kwargs):
        return None


def _kernel(*service_ids):
    kernel = Kernel()
    for service_id in service_ids:
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=service_id, ai_model_id="gpt-test", api_key="sk-test"
            )
        )
    return kernel


def test_a_missing_explicit_id_raises_and_names_the_held_ids():
    kernel = _kernel("svc_a")
    with pytest.raises(ValueError) as info:
        _Agent(kernel, "Witness", llm_service_id="chat_completion")
    message = str(info.value)
    assert "'chat_completion'" in message
    assert "['svc_a']" in message


def test_a_missing_id_is_not_swapped_for_another_service():
    # Avec deux services, le repli choisissait le premier : un modèle que
    # personne n'avait demandé.
    kernel = _kernel("svc_a", "svc_b")
    with pytest.raises(ValueError):
        _Agent(kernel, "Witness", llm_service_id="svc_c")


def test_an_explicit_id_selects_that_service():
    kernel = _kernel("svc_a", "svc_b")
    agent = _Agent(kernel, "Witness", llm_service_id="svc_b")
    assert agent.service.service_id == "svc_b"


def test_without_an_id_the_kernel_default_service_is_used():
    # "default" est résolu par Semantic Kernel lui-même : c'est son contrat,
    # pas un repli de BaseAgent.
    kernel = _kernel("svc_a")
    agent = _Agent(kernel, "Witness")
    assert agent.service.service_id == "svc_a"


def test_the_factory_refuses_the_settings_in_place_of_the_service_id():
    with pytest.raises(TypeError, match="AppSettings"):
        AgentFactory(_kernel("svc_a"), AppSettings())
