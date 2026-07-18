"""BO-3 #1473 PR3 (monitoring) — unit tests for the shared CacheStats counters.

No network, no API key. Asserts the counters increment correctly per mode for
BOTH cache layers (CachedChatCompletion SK layer + cached_raw_chat_completion
direct layer), and that the anti-théâtre invariant holds: in replay mode the
``live`` counter never increments (a miss raises instead).

The end-to-end batch proof (record N → replay N → live == 0, latency table)
lives in ``tests/integration/orchestration/test_replay_cache_profiling_batch.py``.
"""

import pytest

from argumentation_analysis.services import llm_cache as lc
from argumentation_analysis.services.llm_cache import (
    OFF,
    RECORD,
    REPLAY,
    CachedChatCompletion,
    get_cache_stats,
    reset_cache_stats,
)


@pytest.fixture(autouse=True)
def _reset_stats():
    reset_cache_stats()
    yield
    reset_cache_stats()


# ── direct layer (cached_raw_chat_completion) ──


class _FakeAsyncClient:
    """Minimal stand-in: chat.completions.create returns a canned response.

    Tracks live calls so a test can prove the API was NOT reached in replay.
    """

    def __init__(self):
        self.calls = 0

        class _Completions:
            async def create(_self, **kwargs):  # noqa: N805
                self.calls += 1
                return {"_fallback": "live-response"}

        self.chat = type("C", (), {"completions": _Completions()})()


def _fake_client():
    return _FakeAsyncClient()


@pytest.mark.asyncio
async def test_off_mode_counts_live(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_CACHE_MODE", OFF)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "c"))
    lc.reset_raw_cache()
    client = _fake_client()
    await lc.cached_raw_chat_completion(client, model="m", messages=[{"role": "user", "content": "hi"}])
    stats = get_cache_stats()
    assert stats["live"] == 1, "off-mode passthrough must count as live"
    assert stats["hit"] == 0 and stats["miss_record"] == 0 and stats["miss_replay"] == 0


@pytest.mark.asyncio
async def test_record_miss_then_hit_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_CACHE_MODE", RECORD)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "c"))
    lc.reset_raw_cache()
    client = _fake_client()
    # 1st call: miss → API + store
    await lc.cached_raw_chat_completion(client, model="m", messages=[{"role": "user", "content": "q"}])
    # 2nd identical call: hit
    await lc.cached_raw_chat_completion(client, model="m", messages=[{"role": "user", "content": "q"}])
    stats = get_cache_stats()
    assert stats["miss_record"] == 1, "first record call is a miss"
    assert stats["live"] == 1, "the miss reached the API"
    assert stats["hit"] == 1, "second identical call is a hit"
    assert stats["miss_replay"] == 0


@pytest.mark.asyncio
async def test_replay_hit_no_live(monkeypatch, tmp_path):
    # Seed the cache in record mode first.
    monkeypatch.setenv("LLM_CACHE_MODE", RECORD)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "c"))
    lc.reset_raw_cache()
    client = _fake_client()
    await lc.cached_raw_chat_completion(client, model="m", messages=[{"role": "user", "content": "q"}])
    # Switch to replay: same key → hit, NO live call.
    monkeypatch.setenv("LLM_CACHE_MODE", REPLAY)
    reset_cache_stats()
    client2 = _fake_client()
    await lc.cached_raw_chat_completion(client2, model="m", messages=[{"role": "user", "content": "q"}])
    stats = get_cache_stats()
    assert stats["hit"] == 1
    assert stats["live"] == 0, "replay hit must NOT reach the API (anti-théâtre)"
    assert client2.calls == 0


@pytest.mark.asyncio
async def test_replay_miss_counts_miss_replay_and_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_CACHE_MODE", REPLAY)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "c"))
    lc.reset_raw_cache()
    client = _fake_client()
    with pytest.raises(lc.LLMCacheMiss):
        await lc.cached_raw_chat_completion(
            client, model="m", messages=[{"role": "user", "content": "unseen"}]
        )
    stats = get_cache_stats()
    assert stats["miss_replay"] == 1, "replay miss increments miss_replay"
    assert stats["live"] == 0, "replay miss must NOT fall through to the API"
    assert stats["hit"] == 0


# ── SK layer (CachedChatCompletion) ──


class _FakeInner:
    """Stand-in for an SK ChatCompletionClientBase."""

    async def get_chat_message_contents(self, chat_history, settings, **kwargs):
        from semantic_kernel.contents.chat_message_content import ChatMessageContent

        return [ChatMessageContent(role="assistant", content="sk-live")]


@pytest.mark.asyncio
async def test_sk_layer_record_then_replay_stats(monkeypatch, tmp_path):
    from semantic_kernel.contents.chat_history import ChatHistory

    monkeypatch.setattr(lc, "CACHE_DIR", tmp_path / "sk")
    history = ChatHistory()
    history.add_user_message("probe")

    # RECORD: miss → live, then store
    monkeypatch.setenv("LLM_CACHE_MODE", RECORD)
    svc = CachedChatCompletion(inner=_FakeInner(), mode=RECORD)
    await svc.get_chat_message_contents(history, settings=None)
    assert get_cache_stats() == {"hit": 0, "miss_record": 1, "miss_replay": 0, "live": 1}

    # REPLAY: hit, no live
    monkeypatch.setenv("LLM_CACHE_MODE", REPLAY)
    reset_cache_stats()
    svc2 = CachedChatCompletion(inner=_FakeInner(), mode=REPLAY)
    await svc2.get_chat_message_contents(history, settings=None)
    stats = get_cache_stats()
    assert stats["hit"] == 1 and stats["live"] == 0 and stats["miss_replay"] == 0


def test_reset_cache_stats_zeros_all():
    # dirty the counters, then reset
    lc._cache_stats.hit = 5
    lc._cache_stats.live = 3
    lc._cache_stats.miss_record = 2
    lc._cache_stats.miss_replay = 1
    reset_cache_stats()
    assert get_cache_stats() == {"hit": 0, "miss_record": 0, "miss_replay": 0, "live": 0}
