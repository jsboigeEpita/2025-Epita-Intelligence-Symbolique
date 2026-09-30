"""#2711 B: Azure is built from Azure's own configuration, in the factory.

Before this slice, ``create_llm_service(service_type="AzureChatCompletion")``
resolved the OpenAI or OpenRouter key first and handed it to Azure. It used the
OpenAI model id as the deployment name, and it refused a seat where only Azure
was configured. The one correct Azure configuration in the tree was
``KernelBuilder``'s, which had no caller. It now lives in the factory.

These tests build the real ``AzureChatCompletion`` (no double) and read what it
carries: the key its client sends, the endpoint and the deployment.
"""

import pytest
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
)

from argumentation_analysis.core.llm_service import create_llm_service

_SEAT_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
    "OPENAI_ORG_ID",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_CHAT_MODEL_ID",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    "LLM_CACHE_MODE",
)

AZURE_KEY = "azure-key-not-a-real-key"
AZURE_ENDPOINT = "https://resource-2711.openai.azure.com/"
AZURE_DEPLOYMENT = "deployment-2711"
OPENAI_KEY = "sk-openai-not-a-real-key"
OPENROUTER_KEY = "sk-or-not-a-real-key"


@pytest.fixture
def seat(monkeypatch, tmp_path):
    """An empty seat: no route or Azure variable, and no ``.env`` in reach.

    ``AzureOpenAISettings`` also reads ``.env`` from the working directory, so a
    developer's own file would otherwise decide what these tests see.
    """
    for var in _SEAT_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return monkeypatch


@pytest.fixture
def azure_seat(seat):
    seat.setenv("AZURE_OPENAI_API_KEY", AZURE_KEY)
    seat.setenv("AZURE_OPENAI_ENDPOINT", AZURE_ENDPOINT)
    seat.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", AZURE_DEPLOYMENT)
    return seat


def _azure_service(**kwargs):
    return create_llm_service(
        "azure_svc",
        service_type="AzureChatCompletion",
        force_authentic=True,
        **kwargs,
    )


def test_an_azure_only_seat_gets_its_service(azure_seat):
    """The seat ``.env.example`` documents for Azure: no OpenAI key at all."""
    service = _azure_service()

    # #2849: the service is always wrapped in the accounting envelope; the
    # Azure wiring this test pins lives on the inner SK service (the wrapped
    # cache test below asserts the envelope half).
    inner = getattr(service, "_inner", service)
    assert isinstance(inner, AzureChatCompletion)
    assert inner.service_id == "azure_svc"
    assert inner.client.api_key == AZURE_KEY
    assert str(inner.client.base_url).startswith(AZURE_ENDPOINT)
    assert inner.ai_model_id == AZURE_DEPLOYMENT


def test_the_openai_key_never_reaches_azure(azure_seat):
    """With both keys set, Azure carries its own key and its own deployment."""
    azure_seat.setenv("OPENAI_API_KEY", OPENAI_KEY)
    azure_seat.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")

    service = _azure_service()

    assert service.client.api_key == AZURE_KEY
    assert service.ai_model_id == AZURE_DEPLOYMENT


def test_the_openrouter_toggle_does_not_reroute_azure(azure_seat):
    azure_seat.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    azure_seat.setenv("OPENROUTER_API_KEY", OPENROUTER_KEY)

    service = _azure_service()

    assert service.client.api_key == AZURE_KEY
    assert str(service.client.base_url).startswith(AZURE_ENDPOINT)


def test_an_explicit_deployment_wins_over_the_setting(azure_seat):
    service = _azure_service(model_id="caller-deployment")

    assert service.ai_model_id == "caller-deployment"


def test_a_deployment_name_is_not_substituted_like_a_model_id(azure_seat):
    """The #1930 table replaces retired OpenAI model ids. A tenant may name a
    deployment after one; the name must reach Azure unchanged."""
    azure_seat.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-mini")

    service = _azure_service()

    assert service.ai_model_id == "gpt-5-mini"


def test_the_azure_service_goes_through_the_llm_cache(azure_seat):
    """Record/replay covers Azure like OpenAI: the kernel path is wrapped."""
    from argumentation_analysis.services.llm_cache import REPLAY, CachedChatCompletion

    azure_seat.setenv("LLM_CACHE_MODE", REPLAY)

    service = _azure_service()

    assert isinstance(service, CachedChatCompletion)
    assert isinstance(service._inner, AzureChatCompletion)
    assert service._inner.client.api_key == AZURE_KEY


@pytest.mark.parametrize(
    "absent",
    [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    ],
)
def test_each_missing_azure_variable_is_named(azure_seat, absent):
    """An OpenAI key and model id are present, and neither stands in for Azure's."""
    azure_seat.setenv("OPENAI_API_KEY", OPENAI_KEY)
    azure_seat.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")
    azure_seat.delenv(absent)

    with pytest.raises(ValueError, match=absent):
        _azure_service()


def test_the_openai_path_is_unchanged(azure_seat):
    """Control: the default service type still builds OpenAI from the OpenAI key,
    whatever Azure configuration the seat also carries."""
    azure_seat.setenv("OPENAI_API_KEY", OPENAI_KEY)

    service = create_llm_service("openai_svc", force_authentic=True)

    # #2849: unwrap the always-on accounting envelope (see above).
    inner = getattr(service, "_inner", service)
    assert isinstance(inner, OpenAIChatCompletion)
    assert inner.client.api_key == OPENAI_KEY
