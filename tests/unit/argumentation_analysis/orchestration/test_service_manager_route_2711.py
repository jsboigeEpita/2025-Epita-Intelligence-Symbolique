# -*- coding: utf-8 -*-
"""#2711 A2: the service manager takes its LLM route from the resolver.

``initialize()`` used to decide "with or without an LLM service" on
``settings.openai.api_key``, and the tactical and operational analyses
refused to run on the same field. That field is not the factory's source:
``create_llm_service`` follows ``resolve_chat_endpoint``, which reads the
environment and honours the OpenRouter toggle. Each test below is born red
on ``d7b97bf0d``:

- an OpenRouter-only seat got no service from ``initialize()``;
- a seat whose settings hold a key the environment does not (another
  ``.env``, or #2713's dummy default) got a service the factory would refuse;
- on an OpenRouter-only seat, the two analyses refused a kernel that held
  their service;
- on a kernel without the service, the two analyses called it anyway and
  failed on ``No service found`` instead of naming what was missing.
"""

import types

import pytest
from pydantic import SecretStr
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent

import argumentation_analysis.orchestration.service_manager as sm
from argumentation_analysis.agents.core.informal import informal_definitions

_SERVICE_ID = "route-2711"
_METHODS = ("_run_tactical_analysis", "_run_operational_analysis")


class _FakeChat(ChatCompletionClientBase):
    """A chat service that answers without a network call."""

    async def _inner_get_chat_message_contents(self, chat_history, settings):
        return [
            ChatMessageContent(
                role="assistant", content="{}", ai_model_id=self.ai_model_id
            )
        ]


def _settings(openai_key):
    """What ``settings`` says. The manager must not decide on ``openai``."""
    return types.SimpleNamespace(
        openai=types.SimpleNamespace(api_key=openai_key),
        service_manager=types.SimpleNamespace(
            default_llm_service_id=_SERVICE_ID,
            enable_communication_middleware=False,
            enable_hierarchical=False,
            enable_specialized_orchestrators=False,
        ),
    )


@pytest.fixture
def bare_manager(monkeypatch):
    monkeypatch.setattr(sm, "initialize_project_environment", lambda: object())
    monkeypatch.setattr(
        informal_definitions, "setup_informal_kernel", lambda **kw: None
    )
    return sm.OrchestrationServiceManager(enable_logging=False)


def _analysis_manager(kernel):
    mgr = sm.OrchestrationServiceManager(enable_logging=False)
    mgr.kernel = kernel
    mgr.llm_service_id = _SERVICE_ID
    mgr.tactical_manager = object()
    mgr.operational_manager = object()
    return mgr


async def test_an_openrouter_only_seat_gets_its_service(
    monkeypatch, llm_route_seat, bare_manager
):
    llm_route_seat(openrouter_key="sk-or-test-2711")
    monkeypatch.setattr(sm, "settings", _settings(None))

    assert await bare_manager.initialize() is True
    assert _SERVICE_ID in bare_manager.kernel.services, (
        "an OpenRouter-only seat has a route; the manager built no service "
        f"(setup_failures={bare_manager.setup_failures})"
    )
    assert "informal_plugin" not in bare_manager.setup_failures


async def test_a_key_only_the_settings_hold_builds_no_service(
    monkeypatch, llm_route_seat, bare_manager
):
    llm_route_seat()
    monkeypatch.setattr(
        sm, "settings", _settings(SecretStr("sk-only-in-another-env-file"))
    )

    assert await bare_manager.initialize() is True
    assert _SERVICE_ID not in bare_manager.kernel.services, (
        "the environment has no route, so the factory refuses this seat; "
        "a service built on the settings' key is one no real run can use"
    )
    reason = bare_manager.setup_failures.get("informal_plugin", "")
    assert "clé" in reason and "OPENROUTER_API_KEY" in reason, reason


@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_analyses_run_on_an_openrouter_only_seat(
    monkeypatch, llm_route_seat, method_name
):
    llm_route_seat(openrouter_key="sk-or-test-2711")
    monkeypatch.setattr(sm, "settings", _settings(None))
    kernel = Kernel()
    kernel.add_service(_FakeChat(ai_model_id="model-2711", service_id=_SERVICE_ID))

    result = await getattr(_analysis_manager(kernel), method_name)("texte", None)

    assert result["status"] == "completed", result


def _empty_kernel():
    return Kernel()


def _kernel_with_another_service():
    """The pinned id is what counts: a kernel that is not empty is not enough."""
    kernel = Kernel()
    kernel.add_service(_FakeChat(ai_model_id="model-other", service_id="other"))
    return kernel


@pytest.mark.parametrize("make_kernel", [_empty_kernel, _kernel_with_another_service])
@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_analyses_name_the_service_the_kernel_lacks(
    monkeypatch, method_name, make_kernel
):
    monkeypatch.setattr(sm, "settings", _settings(SecretStr("sk-test-2711")))

    result = await getattr(_analysis_manager(make_kernel()), method_name)("texte", None)

    assert result["status"] == "error", result
    assert f"aucun service LLM '{_SERVICE_ID}'" in result.get("message", ""), result
