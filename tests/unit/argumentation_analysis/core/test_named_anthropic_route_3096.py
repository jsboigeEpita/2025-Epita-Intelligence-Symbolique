"""#3096 item 6 — a NAMED provider route that never overwrites the others.

Today the Claude route works only if the caller overwrites ``OPENAI_*``
(measured on the doc_A pass: the caller set ``OPENAI_BASE_URL`` /
``OPENAI_API_KEY`` / ``OPENAI_CHAT_MODEL_ID`` to Anthropic's compatible
endpoint and emptied the OpenRouter triple). This witness pins the named
route: ``ANTHROPIC_CHAT_MODEL_ID`` + ``ANTHROPIC_API_KEY`` select Anthropic
without touching a single ``OPENAI_*`` value, the run log names the provider,
and both routes stay available on the same machine.

The model id, not the key, selects the route: an ambient ``ANTHROPIC_API_KEY``
(unrelated tooling exports one) must never reroute a pipeline, and a model id
without a key is an explicit declaration that cannot be honoured — it raises
rather than falling back silently (#2322's spirit).

Env only, no client built against the network; zero spend, opaque ids only.
"""

import logging
from types import SimpleNamespace

import pytest

from argumentation_analysis.core import llm_service
from argumentation_analysis.core.llm_service import (
    LLMRouteDivergenceError,
    assert_declared_route,
    classify_route,
    resolve_chat_endpoint,
)

_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CHAT_MODEL_ID",
    "LLM_EXPECTED_ROUTE",
)


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)


def _openai_sentinels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-sentinel")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.invalid/v1")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "openai-sentinel-model")


def test_the_named_route_wins_without_overwriting_openai_settings(monkeypatch):
    """The born-red shape: with every OPENAI_* set to sentinels, naming the
    Anthropic route must resolve to Anthropic — and leave OPENAI_* untouched."""
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sentinel")
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")

    api_key, base_url, model_id = resolve_chat_endpoint()

    assert (api_key, model_id) == ("sk-ant-sentinel", "claude-haiku-5-5")
    assert base_url == "https://api.anthropic.com/v1"
    # Both routes stay available: the OpenAI settings are exactly as set.
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-openai-sentinel"
    assert os.environ["OPENAI_BASE_URL"] == "https://openai.invalid/v1"
    assert os.environ["OPENAI_CHAT_MODEL_ID"] == "openai-sentinel-model"


def test_without_the_model_id_the_openai_route_is_unchanged(monkeypatch):
    """Control: the same machine, no ANTHROPIC_CHAT_MODEL_ID — the OpenAI
    route resolves exactly as before (both routes available)."""
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sentinel")

    api_key, base_url, model_id = resolve_chat_endpoint()

    assert (api_key, base_url, model_id) == (
        "sk-openai-sentinel",
        "https://openai.invalid/v1",
        "openai-sentinel-model",
    )


def test_an_ambient_key_alone_never_reroutes(monkeypatch):
    """ANTHROPIC_API_KEY is commonly present for unrelated tooling: it is not
    a route selection, so the OpenAI route stands."""
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-ambient")

    assert resolve_chat_endpoint()[1] == "https://openai.invalid/v1"


def test_a_model_id_without_a_key_raises_naming_the_variable(monkeypatch):
    """An explicit declaration that cannot be honoured fails loud — it never
    falls back to another provider."""
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        resolve_chat_endpoint()


def test_the_log_names_the_anthropic_provider(monkeypatch, caplog):
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sentinel")
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")

    with caplog.at_level(
        logging.INFO, logger="argumentation_analysis.core.llm_service"
    ):
        resolve_chat_endpoint()

    config_lines = [
        r.message for r in caplog.records if "LLM config resolved" in r.message
    ]
    assert any(
        "provider=Anthropic" in line for line in config_lines
    ), f"the run log must name the provider; got {config_lines}"


def test_classify_route_and_the_declared_route_understand_anthropic(monkeypatch):
    """The declared-route guard can pin the Anthropic route like the others."""
    _clean_env(monkeypatch)
    assert classify_route("https://api.anthropic.com/v1") == "anthropic"
    assert classify_route("https://openrouter.ai/api/v1") == "openrouter"
    assert classify_route("https://openai.invalid/v1") == "openai"

    monkeypatch.setenv("LLM_EXPECTED_ROUTE", "anthropic:claude-haiku-5-5")
    assert_declared_route("https://api.anthropic.com/v1", "claude-haiku-5-5", "test")
    with pytest.raises(LLMRouteDivergenceError):
        assert_declared_route("https://openai.invalid/v1", "gpt-5.6-luna", "test")


def test_the_kernel_factory_builds_the_named_route(monkeypatch):
    """create_llm_service (the kernel path: most calls) must also take the
    named route, with its own base_url — not the OpenAI default."""
    _clean_env(monkeypatch)
    _openai_sentinels(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sentinel")
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")
    monkeypatch.setenv("LLM_CACHE_MODE", "off")

    captured = {}

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

    class _FakeOpenAIChatCompletion:
        def __init__(self, **kwargs):
            captured["service_kwargs"] = kwargs

    monkeypatch.setattr(llm_service, "AsyncOpenAI", _FakeAsyncOpenAI)
    monkeypatch.setattr(llm_service, "OpenAIChatCompletion", _FakeOpenAIChatCompletion)
    monkeypatch.setattr(
        llm_service, "get_resilient_async_client", lambda: SimpleNamespace()
    )

    llm_service.create_llm_service(force_authentic=True)

    assert captured["client_kwargs"]["api_key"] == "sk-ant-sentinel"
    assert captured["client_kwargs"]["base_url"] == "https://api.anthropic.com/v1"
    assert captured["service_kwargs"]["ai_model_id"] == "claude-haiku-5-5"
