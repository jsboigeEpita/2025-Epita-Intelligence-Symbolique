"""#2849 — token-usage accounting point: every chat completion counts.

Born-red contract: on main at issue-filing time, nothing counts. The run log of
the #2841 pass (49 docs, 1.65 M lines) carried usage for only 44 client-direct
calls — every SK call logged nothing, and the pipeline's total token spend was
unknowable. These guards fail until the accounting point exists and rises by
EXACTLY the usage a fake service reports (never an estimate, never 0-fabricated).

The accounting lives at the live round-trips of the two funnels
(``CachedChatCompletion`` for the SK path, ``cached_raw_chat_completion`` /
``cached_raw_chat_completion_sync`` for the direct path): a replayed (cached)
response is NOT a live spend and must not count.
"""

import types
from unittest.mock import AsyncMock

import pytest

from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.completion_usage import CompletionUsage
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.services.llm_cache import (
    OFF,
    CachedChatCompletion,
    cached_raw_chat_completion,
    cached_raw_chat_completion_sync,
)

# ─── Fakes ──────────────────────────────────────────────────────────────


class _FakeSKInner(ChatCompletionClientBase):
    """Inner SK service whose every response carries a measured usage."""

    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        super().__init__(service_id="fake-inner", ai_model_id="fake-model")
        self._usage = CompletionUsage(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        msg = ChatMessageContent(role="assistant", content="réponse")
        msg.metadata = {"usage": self._usage}
        return [msg]

    async def get_chat_message_content(self, chat_history, settings=None, **kwargs):
        msgs = await self.get_chat_message_contents(chat_history, settings, **kwargs)
        return msgs[0]


def _fake_raw_response(prompt_tokens: int, completion_tokens: int, cost=None):
    """Duck-typed OpenAI ChatCompletion: ``.usage`` carries the measurements."""
    usage = types.SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    if cost is not None:
        usage.cost = cost
    choice = types.SimpleNamespace(message=types.SimpleNamespace(content="réponse"))
    return types.SimpleNamespace(usage=usage, choices=[choice])


class _FakeRawClient:
    """``client.chat.completions.create`` returning a measured fake response.

    ``sync=False`` serves the async funnel (an awaitable create); ``sync=True``
    serves the sync twin (create returns the response directly).
    """

    def __init__(self, response, *, sync: bool = False) -> None:
        if sync:
            from unittest.mock import MagicMock

            create = MagicMock(return_value=response)
        else:
            create = AsyncMock(return_value=response)
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=create)
        )


def _history(prompt: str = "question") -> ChatHistory:
    return ChatHistory(messages=[ChatMessageContent(role="user", content=prompt)])


@pytest.fixture()
def usage_counter():
    from argumentation_analysis.services.llm_cache import (
        reset_usage_stats,
        get_usage_stats,
    )

    reset_usage_stats()
    yield get_usage_stats
    reset_usage_stats()


# ─── DoD 1+4: the accounting point rises by exactly the reported usage ──


class TestSkPathAccounting:
    def test_fake_sk_service_usage_rises_exactly(self, usage_counter, monkeypatch):
        """Born-red (#2849 DoD 4): a fake SK service returning ``metadata.usage``
        makes the per-run counter rise by exactly that amount."""
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.services import llm_cache

        llm_cache._raw_cache = None  # isolate from any module-level cache
        inner = _FakeSKInner(prompt_tokens=100, completion_tokens=23)
        wrapper = CachedChatCompletion(inner=inner, mode=OFF)

        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            wrapper.get_chat_message_contents(chat_history=_history())
        )

        stats = usage_counter()
        assert stats["(unattributed)"]["prompt_tokens"] == 100
        assert stats["(unattributed)"]["completion_tokens"] == 23
        assert stats["(unattributed)"]["calls"] == 1

    def test_phase_attribution_lands_under_the_phase_key(
        self, usage_counter, monkeypatch
    ):
        """A call made inside a phase context is attributed to that phase."""
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.services import llm_cache

        llm_cache._raw_cache = None
        inner = _FakeSKInner(prompt_tokens=10, completion_tokens=4)
        wrapper = CachedChatCompletion(inner=inner, mode=OFF)

        import asyncio

        with llm_cache.llm_usage_phase("fact_extraction"):
            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                wrapper.get_chat_message_contents(chat_history=_history())
            )

        stats = usage_counter()
        assert stats["fact_extraction"]["prompt_tokens"] == 10
        assert "(unattributed)" not in stats or stats["(unattributed)"]["calls"] == 0

    def test_off_mode_sk_service_is_always_wrapped(self, monkeypatch):
        """The accounting point must see every SK call — including when the
        cache is off (a real paid run), which is exactly when main skips the
        wrapper today."""
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.core.llm_service import _wrap_with_llm_cache

        class _Anything(ChatCompletionClientBase):
            def __init__(self):
                super().__init__(service_id="x", ai_model_id="m")

        wrapped = _wrap_with_llm_cache(_Anything())
        assert isinstance(wrapped, CachedChatCompletion)


class TestDirectPathAccounting:
    def test_raw_async_usage_rises_exactly(self, usage_counter, monkeypatch):
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.services import llm_cache

        llm_cache._raw_cache = None
        client = _FakeRawClient(
            _fake_raw_response(prompt_tokens=150, completion_tokens=7)
        )

        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            cached_raw_chat_completion(
                client, model="m", messages=[{"role": "user", "content": "q"}]
            )
        )

        stats = usage_counter()
        assert stats["(unattributed)"]["prompt_tokens"] == 150
        assert stats["(unattributed)"]["completion_tokens"] == 7
        assert stats["(unattributed)"]["calls"] == 1

    def test_raw_sync_usage_rises_exactly(self, usage_counter, monkeypatch):
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.services import llm_cache

        llm_cache._raw_cache = None
        client = _FakeRawClient(
            _fake_raw_response(prompt_tokens=50, completion_tokens=2), sync=True
        )

        cached_raw_chat_completion_sync(
            client, model="m", messages=[{"role": "user", "content": "q"}]
        )

        stats = usage_counter()
        assert stats["(unattributed)"]["prompt_tokens"] == 50
        assert stats["(unattributed)"]["calls"] == 1

    def test_dollar_counted_only_when_provider_reports_one(
        self, usage_counter, monkeypatch
    ):
        """A dollar figure exists only when the provider returned one; absence
        is None (rendered "not reported"), never 0."""
        monkeypatch.setenv("LLM_CACHE_MODE", OFF)
        from argumentation_analysis.services import llm_cache

        llm_cache._raw_cache = None
        with_cost = _FakeRawClient(_fake_raw_response(10, 1, cost=0.0123), sync=True)
        without_cost = _FakeRawClient(_fake_raw_response(10, 1), sync=True)

        cached_raw_chat_completion_sync(
            with_cost, model="m", messages=[{"role": "user", "content": "q"}]
        )
        cached_raw_chat_completion_sync(
            without_cost, model="m", messages=[{"role": "user", "content": "q2"}]
        )

        stats = usage_counter()
        assert stats["cost_usd"] == pytest.approx(0.0123)


class TestReplayIsNotLiveSpend:
    def test_cached_response_does_not_count(self, usage_counter, monkeypatch, tmp_path):
        """A replayed response was paid at record time, not now — the live-run
        counter must stay flat (cost honesty of the accounting point)."""
        import asyncio

        monkeypatch.setenv("LLM_CACHE_MODE", "record")
        from argumentation_analysis.services import llm_cache

        llm_cache.reset_raw_cache()
        cache_dir = tmp_path / "cache"  # explicit: CACHE_DIR is module-import-time
        inner = _FakeSKInner(prompt_tokens=100, completion_tokens=23)
        wrapper = CachedChatCompletion(inner=inner, mode="record", cache_dir=cache_dir)
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            wrapper.get_chat_message_contents(chat_history=_history("première"))
        )
        assert usage_counter()["(unattributed)"]["prompt_tokens"] == 100  # live miss

        from argumentation_analysis.services.llm_cache import reset_usage_stats

        reset_usage_stats()

        replay = CachedChatCompletion(inner=inner, mode="replay", cache_dir=cache_dir)
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            replay.get_chat_message_contents(chat_history=_history("première"))
        )
        stats = usage_counter()
        assert stats == {"cost_usd": None} or all(
            v.get("calls", 0) == 0 for v in stats.values() if isinstance(v, dict)
        )
        llm_cache.reset_raw_cache()
