"""KernelBuilder — the provider branch each ``default_llm_service_id`` selects.

The azure branch of ``create_kernel`` read ``settings.azure_openai``, a name
``AppSettings`` does not carry: the field was declared inside ``JVMSettings``
(``config/settings.py``), so the attribute access raised ``AttributeError``
before the branch's own "key not configured" guard. Selecting azure could
therefore never work — the exception surfaced as "the Azure key is missing"
no matter what the environment held (#2115).
"""

from pydantic import SecretStr

from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.kernel.kernel_builder import KernelBuilder


def _settings_with_provider(provider: str) -> AppSettings:
    base = AppSettings()
    return base.model_copy(
        update={
            "service_manager": base.service_manager.model_copy(
                update={"default_llm_service_id": provider}
            )
        }
    )


def test_azure_provider_builds_the_azure_service():
    """Selecting azure reaches AzureChatCompletion, not an AttributeError."""
    base = AppSettings()
    azure = base.jvm.azure_openai.model_copy(
        update={
            "api_key": SecretStr("test-key"),
            "endpoint": "https://example.openai.azure.com/",
            "deployment_name": "test-deployment",
        }
    )
    settings = base.model_copy(
        update={
            "service_manager": base.service_manager.model_copy(
                update={"default_llm_service_id": "azure"}
            ),
            "jvm": base.jvm.model_copy(update={"azure_openai": azure}),
        }
    )

    kernel = KernelBuilder.create_kernel(settings)

    service = kernel.get_service("azure")
    assert service is not None, (
        "the azure branch produced no service — check that it reads the block "
        "where it actually lives (settings.jvm.azure_openai, #2115)"
    )


def test_openai_provider_still_builds_the_openai_service():
    """Control: the openai path (the one that always worked) is unaffected."""
    base = AppSettings()
    if not base.openai.api_key:
        base = base.model_copy(
            update={
                "openai": base.openai.model_copy(
                    update={"api_key": SecretStr("test-key")}
                )
            }
        )
    settings = _settings_with_provider("openai")

    kernel = KernelBuilder.create_kernel(settings)

    assert kernel.get_service("openai") is not None


def test_unknown_provider_still_fails_loud():
    """The else branch keeps naming the unknown provider."""
    import pytest

    with pytest.raises(ValueError, match="inconnu"):
        KernelBuilder.create_kernel(_settings_with_provider("not-a-provider"))
