"""BO-3 #1473 PR2 (SK-path wiring) — unit tests, no network.

``create_llm_service`` is the canonical factory for every SK-native chat service
(the conversational ``AgentGroupChat`` / ``ChatCompletionAgent`` path, the cluedo
orchestrator, the CLI). PR2 wraps its returned service with
``CachedChatCompletion`` so SK-native calls are replayed from the same disk cache
as the direct path (PR1, ``_guarded_chat_completion``). These tests assert the
wiring CONTRACT with ``OpenAIChatCompletion`` patched out (no API key needed):

- off mode  → wrapped for usage accounting only (#2849): live-only passthrough,
              the cache stays inert (no read, no write)
- record    → wrapped with CachedChatCompletion(mode=record)
- replay    → wrapped with CachedChatCompletion(mode=replay)
- mock path → NOT wrapped (mocks are deterministic by nature; they return early)

The end-to-end live proof (record → replay → 0 live API call, identical output,
fail-loud on miss) lives in
``tests/integration/orchestration/test_replay_cache_sk_path.py``.
"""

from typing import List
from unittest.mock import patch

import pytest

from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.services.llm_cache import (
    OFF,
    RECORD,
    REPLAY,
    CachedChatCompletion,
)


@pytest.fixture(autouse=True)
def _cache_env(monkeypatch):
    """Isolate LLM_CACHE_* + provider env per test; reset the raw-cache singleton."""
    monkeypatch.delenv("LLM_CACHE_MODE", raising=False)
    monkeypatch.delenv("LLM_CACHE_DIR", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-not-used")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from argumentation_analysis.services import llm_cache as lc

    lc.reset_raw_cache()
    yield
    lc.reset_raw_cache()


class _FakeOpenAIChatCompletion:
    """Stand-in for the real SK service; only construction matters here."""

    def __init__(self, *args, **kwargs):
        self.service_id = kwargs.get("service_id")
        self.ai_model_id = kwargs.get("ai_model_id")


def _build(monkeypatch, tmp_path, mode):
    """Build an authentic service with OpenAIChatCompletion patched (no network)."""
    monkeypatch.setenv("LLM_CACHE_MODE", mode)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "sk_cache"))
    with patch(
        "argumentation_analysis.core.llm_service.OpenAIChatCompletion",
        _FakeOpenAIChatCompletion,
    ):
        from argumentation_analysis.core.llm_service import create_llm_service

        return create_llm_service(
            service_id="test", model_id="gpt-test", force_authentic=True
        )


def test_off_mode_wraps_for_accounting_without_caching(monkeypatch, tmp_path):
    """#2849: off mode wraps too — the envelope is a live-only passthrough
    that accounts token usage; the old OFF hole meant cache-off runs were paid
    but never counted. The cache itself stays inert in off mode (no read, no
    write — pinned end-to-end in test_llm_usage_accounting_2849.py)."""
    service = _build(monkeypatch, tmp_path, OFF)
    assert isinstance(
        service, CachedChatCompletion
    ), "off mode must wrap the SK service for usage accounting (#2849)"
    assert service.mode == OFF


def test_record_mode_wraps(monkeypatch, tmp_path):
    service = _build(monkeypatch, tmp_path, RECORD)
    assert isinstance(
        service, CachedChatCompletion
    ), "record mode must wrap the SK service with CachedChatCompletion (PR2)"
    assert service.mode == RECORD


def test_replay_mode_wraps(monkeypatch, tmp_path):
    service = _build(monkeypatch, tmp_path, REPLAY)
    assert isinstance(service, CachedChatCompletion)
    assert service.mode == REPLAY


def test_mock_path_not_wrapped(monkeypatch):
    """Test-env mock branch returns early → never wrapped."""
    monkeypatch.setenv("LLM_CACHE_MODE", REPLAY)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-not-used")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "unit::test::mock_path (call)")
    from argumentation_analysis.core.llm_service import create_llm_service

    service = create_llm_service(service_id="test", model_id="m")
    assert not isinstance(service, CachedChatCompletion)


# ─── #2853 review item 1 — the wrapper must stream in off mode ────────────
#
# Measured offline by the coordinator: ``get_streaming_chat_message_contents``
# is defined on ``ChatCompletionClientBase``, so it resolves on the wrapper
# BEFORE ``__getattr__`` and raises NotImplementedError. Real runs stream
# through it (Sherlock ``kernel.invoke_stream``, the agent channels'
# ``agent.invoke_stream``) — an "inert passthrough" that cannot stream breaks
# every off-mode run.


class _StreamingFakeInner(ChatCompletionClientBase):
    """Inner SK service with a measurable streaming implementation."""

    SUPPORTS_FUNCTION_CALLING = True

    def __init__(self, chunks: List[str]) -> None:
        super().__init__(service_id="fake-streaming", ai_model_id="fake-model")
        object.__setattr__(self, "_chunks", chunks)
        object.__setattr__(self, "stream_calls", 0)

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        return [ChatMessageContent(role="assistant", content="".join(self._chunks))]

    async def _inner_get_streaming_chat_message_contents(
        self, chat_history, settings=None, **kwargs
    ):
        object.__setattr__(self, "stream_calls", self.stream_calls + 1)
        for chunk in self._chunks:
            yield [ChatMessageContent(role="assistant", content=chunk)]

    @classmethod
    def get_prompt_execution_settings_class(cls):
        from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
            OpenAIChatPromptExecutionSettings,
        )

        return OpenAIChatPromptExecutionSettings


async def test_the_wrapper_streams_what_the_inner_streams():
    """#2853: the streaming override must delegate to the inner service —
    the call must NOT resolve on the base class and raise NotImplementedError."""
    inner = _StreamingFakeInner(["chunk-un", "chunk-deux"])
    wrapper = CachedChatCompletion(inner=inner, mode=OFF)

    from semantic_kernel.connectors.ai.prompt_execution_settings import (
        PromptExecutionSettings,
    )

    history = ChatHistory(
        messages=[ChatMessageContent(role="user", content="question")]
    )
    streamed = []
    async for group in wrapper.get_streaming_chat_message_contents(
        chat_history=history, settings=PromptExecutionSettings()
    ):
        streamed.extend(m.content for m in group)

    assert streamed == ["chunk-un", "chunk-deux"]
    assert inner.stream_calls == 1, "the inner service must have been streamed"


def test_the_wrapper_forwards_the_inner_class_contract():
    """#2853 item 2: two class-level attributes the agents read must not flip
    behind the wrapper — ``SUPPORTS_FUNCTION_CALLING`` and the settings class."""
    inner = _StreamingFakeInner(["x"])
    wrapper = CachedChatCompletion(inner=inner, mode=OFF)
    assert wrapper.SUPPORTS_FUNCTION_CALLING is inner.SUPPORTS_FUNCTION_CALLING
    assert (
        wrapper.get_prompt_execution_settings_class()
        is inner.get_prompt_execution_settings_class()
    )
