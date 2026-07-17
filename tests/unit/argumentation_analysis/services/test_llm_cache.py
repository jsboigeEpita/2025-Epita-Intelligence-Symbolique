"""Tests for LLM response caching layer.

Covers: cache key generation, serialization roundtrip, all three modes
(record, replay, off), LLMCacheMiss on replay miss, env var validation,
and diskcache import fallback.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.services.llm_cache import (
    CACHE_DIR,
    CachedChatCompletion,
    LLMCacheMiss,
    compute_cache_key,
    compute_raw_cache_key,
    cached_raw_chat_completion,
    get_cache_mode,
    get_raw_cache,
    reset_raw_cache,
    _serialize_messages,
    _serialize_response,
    _deserialize_response,
    _serialize_settings,
    OFF,
    RECORD,
    REPLAY,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# --- Helpers ---


def make_history(*messages: tuple) -> ChatHistory:
    """Build a ChatHistory from (role, content) tuples."""
    history = ChatHistory()
    for role, content in messages:
        history.add_message(ChatMessageContent(role=role, content=content))
    return history


def make_response(text: str, role: str = "assistant") -> list:
    """Build a fake response list."""
    return [ChatMessageContent(role=role, content=text)]


class FakeInner:
    """Fake inner service for testing CachedChatCompletion."""

    def __init__(self, response=None):
        self._response = response or make_response("fake response")
        self.calls = []

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        self.calls.append((chat_history, settings, kwargs))
        return self._response


@pytest.fixture
def cache_tmpdir():
    """Provide a temp directory for cache, with proper cleanup for diskcache files."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


# --- Tests ---


class TestGetCacheMode:
    def test_default_is_off(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_CACHE_MODE", None)
            assert get_cache_mode() == OFF

    def test_record(self):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            assert get_cache_mode() == RECORD

    def test_replay(self):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "replay"}):
            assert get_cache_mode() == REPLAY

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "RECORD"}):
            assert get_cache_mode() == RECORD

    def test_invalid_raises(self):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "invalid"}):
            with pytest.raises(ValueError, match="Invalid LLM_CACHE_MODE"):
                get_cache_mode()


class TestComputeCacheKey:
    def test_deterministic(self):
        history = make_history(("user", "hello"))
        key1 = compute_cache_key(history)
        key2 = compute_cache_key(history)
        assert key1 == key2
        assert len(key1) == 64  # sha256 hex

    def test_different_messages_different_keys(self):
        h1 = make_history(("user", "hello"))
        h2 = make_history(("user", "world"))
        assert compute_cache_key(h1) != compute_cache_key(h2)

    def test_settings_affect_key(self):
        history = make_history(("user", "hello"))
        s1 = MagicMock(spec_set=["ai_model_id", "temperature"])
        s1.ai_model_id = "gpt-4"
        s1.temperature = 0.0
        s2 = MagicMock(spec_set=["ai_model_id", "temperature"])
        s2.ai_model_id = "gpt-4"
        s2.temperature = 1.0
        assert compute_cache_key(history, s1) != compute_cache_key(history, s2)

    def test_none_settings_same_as_no_settings(self):
        history = make_history(("user", "hello"))
        assert compute_cache_key(history, None) == compute_cache_key(history)

    def test_empty_history(self):
        history = ChatHistory()
        key = compute_cache_key(history)
        assert len(key) == 64

    def test_tools_in_settings_affect_key(self):
        """Different tool definitions must produce different cache keys."""
        history = make_history(("user", "hello"))
        s1 = MagicMock(spec_set=["ai_model_id", "temperature", "tools"])
        s1.ai_model_id = "gpt-4"
        s1.temperature = 0.0
        s1.tools = [{"type": "function", "function": {"name": "get_weather"}}]
        s2 = MagicMock(spec_set=["ai_model_id", "temperature", "tools"])
        s2.ai_model_id = "gpt-4"
        s2.temperature = 0.0
        s2.tools = [{"type": "function", "function": {"name": "search_web"}}]
        assert compute_cache_key(history, s1) != compute_cache_key(history, s2)

    def test_same_tools_same_key(self):
        """Same tool definitions must produce the same cache key."""
        history = make_history(("user", "hello"))
        tools = [{"type": "function", "function": {"name": "get_weather"}}]
        s1 = MagicMock(spec_set=["ai_model_id", "temperature", "tools"])
        s1.ai_model_id = "gpt-4"
        s1.temperature = 0.0
        s1.tools = tools
        s2 = MagicMock(spec_set=["ai_model_id", "temperature", "tools"])
        s2.ai_model_id = "gpt-4"
        s2.temperature = 0.0
        s2.tools = tools
        assert compute_cache_key(history, s1) == compute_cache_key(history, s2)


class TestSerializeSettings:
    def test_includes_tools_json(self):
        s = MagicMock()
        s.ai_model_id = "gpt-4"
        s.temperature = 0.7
        s.tools = [{"type": "function", "function": {"name": "calc"}}]
        result = _serialize_settings(s)
        assert "tools" in result
        parsed = json.loads(result["tools"])
        assert parsed[0]["function"]["name"] == "calc"

    def test_no_tools_no_key(self):
        s = MagicMock(spec_set=["ai_model_id"])
        s.ai_model_id = "gpt-4"
        result = _serialize_settings(s)
        assert "tools" not in result


class TestSerialization:
    def test_roundtrip(self):
        original = make_response("test content with special chars: éàü")
        serialized = _serialize_response(original)
        deserialized = _deserialize_response(serialized)
        assert len(deserialized) == 1
        assert deserialized[0].content == "test content with special chars: éàü"
        assert deserialized[0].role.value == "assistant"

    def test_metadata_preserved(self):
        msg = ChatMessageContent(role="assistant", content="hi")
        msg.metadata = {"usage": {"tokens": 42}, "model": "gpt-4"}
        serialized = _serialize_response([msg])
        deserialized = _deserialize_response(serialized)
        assert deserialized[0].metadata["usage"]["tokens"] == 42

    def test_metadata_non_serializable_converted(self):
        msg = ChatMessageContent(role="assistant", content="hi")
        msg.metadata = {"obj": object()}  # not JSON-serializable
        serialized = _serialize_response([msg])
        assert isinstance(serialized[0]["metadata"]["obj"], str)

    def test_serialize_messages(self):
        history = make_history(("user", "hello"), ("assistant", "world"))
        msgs = _serialize_messages(history)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hello"
        assert msgs[1]["role"] == "assistant"

    def test_serialize_messages_role_value(self):
        history = make_history(("user", "hello"))
        msgs = _serialize_messages(history)
        assert msgs[0]["role"] == "user"

    def test_null_content_handled(self):
        msg = ChatMessageContent(role="assistant", content=None)
        serialized = _serialize_response([msg])
        deserialized = _deserialize_response(serialized)
        assert deserialized[0].content == ""

    def test_no_metadata(self):
        msg = ChatMessageContent(role="assistant", content="hi")
        serialized = _serialize_response([msg])
        assert "metadata" not in serialized[0]

    def test_function_result_content_serialized(self):
        """Tool call results must be serialized in cache key to avoid collisions."""

        # Use a simple namespace to avoid Pydantic V2 validation on .items
        class FakeItem:
            def __init__(self, fn, plugin, args, result):
                self.function_name = fn
                self.plugin_name = plugin
                self.arguments = args
                self.result = result

        class FakeMsg:
            role = type("R", (), {"value": "assistant"})()
            content = "calling tool"
            items = [
                FakeItem(
                    "get_weather", "weather", "{}", {"temperature": 22, "city": "Paris"}
                )
            ]

        class FakeHistory:
            messages = [FakeMsg()]

        msgs = _serialize_messages(FakeHistory())
        assert len(msgs) == 1
        assert "items" in msgs[0]
        item_data = msgs[0]["items"][0]
        assert "result" in item_data
        result_parsed = json.loads(item_data["result"])
        assert result_parsed["temperature"] == 22

    def test_different_results_different_keys(self):
        """Different tool results should produce different cache keys."""

        class FakeItem:
            def __init__(self, result_value):
                self.function_name = "calc"
                self.plugin_name = "math"
                self.arguments = "{}"
                self.result = result_value

        class FakeMsg:
            role = type("R", (), {"value": "assistant"})()
            content = "tool response"
            items = []

        def make_history_with_result(result_value):
            msg = FakeMsg()
            msg.items = [FakeItem(result_value)]
            history = type("H", (), {"messages": [msg]})()
            return history

        h1 = make_history_with_result({"value": 42})
        h2 = make_history_with_result({"value": 99})
        assert compute_cache_key(h1) != compute_cache_key(h2)


class TestCachedChatCompletion:
    @pytest.mark.asyncio
    async def test_off_mode_passthrough(self):
        inner = FakeInner(make_response("live"))
        cached = CachedChatCompletion(inner, mode=OFF)
        history = make_history(("user", "test"))
        result = await cached.get_chat_message_contents(chat_history=history)
        assert result[0].content == "live"
        assert len(inner.calls) == 1

    @pytest.mark.asyncio
    async def test_record_mode_caches_and_reuses(self, cache_tmpdir):
        inner = FakeInner(make_response("api response"))
        cached = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=RECORD)
        history = make_history(("user", "cache me"))

        # First call: cache miss -> API call
        r1 = await cached.get_chat_message_contents(chat_history=history)
        assert r1[0].content == "api response"
        assert len(inner.calls) == 1

        # Second call: cache hit -> no API call
        r2 = await cached.get_chat_message_contents(chat_history=history)
        assert r2[0].content == "api response"
        assert len(inner.calls) == 1  # still 1, not 2
        cached.close()

    @pytest.mark.asyncio
    async def test_replay_mode_hit(self, cache_tmpdir):
        inner = FakeInner(make_response("cached"))
        # First record
        recorder = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=RECORD)
        history = make_history(("user", "replay test"))
        await recorder.get_chat_message_contents(chat_history=history)
        recorder.close()

        # Now replay
        replay_inner = FakeInner(make_response("should not be called"))
        replayer = CachedChatCompletion(
            replay_inner, cache_dir=cache_tmpdir, mode=REPLAY
        )
        result = await replayer.get_chat_message_contents(chat_history=history)
        assert result[0].content == "cached"
        assert len(replay_inner.calls) == 0
        replayer.close()

    @pytest.mark.asyncio
    async def test_replay_mode_miss_raises(self, cache_tmpdir):
        inner = FakeInner()
        cached = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=REPLAY)
        history = make_history(("user", "never seen before"))
        with pytest.raises(LLMCacheMiss, match="Cache miss in replay mode"):
            await cached.get_chat_message_contents(chat_history=history)
        cached.close()

    def test_mode_property(self):
        inner = FakeInner()
        cached = CachedChatCompletion(inner, mode=REPLAY)
        assert cached.mode == REPLAY

    @pytest.mark.asyncio
    async def test_different_histories_dont_collide(self, cache_tmpdir):
        inner = FakeInner()
        cached = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=RECORD)

        h1 = make_history(("user", "question 1"))
        h2 = make_history(("user", "question 2"))
        inner._response = make_response("answer 1")
        await cached.get_chat_message_contents(chat_history=h1)
        inner._response = make_response("answer 2")
        await cached.get_chat_message_contents(chat_history=h2)
        cached.close()

        # Replay both
        replayer = CachedChatCompletion(
            FakeInner(), cache_dir=cache_tmpdir, mode=REPLAY
        )
        r1 = await replayer.get_chat_message_contents(chat_history=h1)
        r2 = await replayer.get_chat_message_contents(chat_history=h2)
        assert r1[0].content == "answer 1"
        assert r2[0].content == "answer 2"
        replayer.close()

    @pytest.mark.asyncio
    async def test_delegates_attributes(self):
        inner = FakeInner()
        inner.custom_attr = "hello"
        cached = CachedChatCompletion(inner, mode=OFF)
        assert cached.custom_attr == "hello"

    @pytest.mark.asyncio
    async def test_diskcache_missing_falls_back_to_off(self, cache_tmpdir):
        inner = FakeInner(make_response("live"))
        with patch("builtins.__import__", side_effect=ImportError("no diskcache")):
            cached = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=RECORD)
            assert cached.mode == OFF
            result = await cached.get_chat_message_contents(
                chat_history=make_history(("user", "test"))
            )
            assert result[0].content == "live"

    def test_close_idempotent(self, cache_tmpdir):
        inner = FakeInner()
        cached = CachedChatCompletion(inner, cache_dir=cache_tmpdir, mode=RECORD)
        cached.close()
        cached.close()  # should not raise


# --- Raw-path cache (direct OpenAI calls via _guarded_chat_completion) ---
# BO-3 #1473: the CachedChatCompletion class above wraps the SK service, but the
# direct path (_guarded_chat_completion -> client.chat.completions.create) needs
# its own cache at the raw-kwargs level. These guard that cache on the fast gate.


class FakeRawClient:
    """Stand-in for an AsyncOpenAI client. Counts chat.completions.create calls."""

    def __init__(self, response=None):
        from openai.types.chat import ChatCompletion, ChatCompletionMessage
        from openai.types.chat.chat_completion import Choice

        self._response = response or ChatCompletion(
            id="chatcmpl-x",
            object="chat.completion",
            created=1700000000,
            model="gpt-5-mini",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content="live"),
                    finish_reason="stop",
                )
            ],
        )
        self.calls = 0

        async def _create(**kwargs):
            self.calls += 1
            return self._response

        self.chat = type("C", (), {})()
        self.chat.completions = type("P", (), {})()
        self.chat.completions.create = _create


@pytest.fixture
def isolated_raw_cache(cache_tmpdir, monkeypatch):
    """Point the raw cache at a tmpdir + reset the singleton for isolation."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(cache_tmpdir))
    reset_raw_cache()
    yield cache_tmpdir
    reset_raw_cache()


class TestComputeRawCacheKey:
    def test_deterministic(self):
        kw = {"model": "gpt-5-mini", "messages": [{"role": "user", "content": "hi"}]}
        assert compute_raw_cache_key(**kw) == compute_raw_cache_key(**kw)

    def test_different_messages_different_key(self):
        k1 = compute_raw_cache_key(model="m", messages=[{"role": "user", "content": "a"}])
        k2 = compute_raw_cache_key(model="m", messages=[{"role": "user", "content": "b"}])
        assert k1 != k2

    def test_different_model_different_key(self):
        msgs = [{"role": "user", "content": "x"}]
        assert compute_raw_cache_key(model="a", messages=msgs) != compute_raw_cache_key(
            model="b", messages=msgs
        )

    def test_temperature_affects_key(self):
        msgs = [{"role": "user", "content": "x"}]
        k1 = compute_raw_cache_key(model="m", messages=msgs, temperature=0.0)
        k2 = compute_raw_cache_key(model="m", messages=msgs, temperature=1.0)
        assert k1 != k2

    def test_non_deterministic_fields_ignored(self):
        msgs = [{"role": "user", "content": "x"}]
        # `user` (per-request user id) must NOT fragment the key.
        k1 = compute_raw_cache_key(model="m", messages=msgs, user="alice")
        k2 = compute_raw_cache_key(model="m", messages=msgs, user="bob")
        assert k1 == k2


class TestCachedRawChatCompletion:
    @pytest.mark.asyncio
    async def test_off_mode_passthrough(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "off"}):
            reset_raw_cache()
            client = FakeRawClient()
            r = await cached_raw_chat_completion(
                client, model="m", messages=[{"role": "user", "content": "q"}]
            )
            assert r.choices[0].message.content == "live"
            assert client.calls == 1

    @pytest.mark.asyncio
    async def test_record_mode_caches_then_hits(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            client = FakeRawClient()
            kw = {"model": "m", "messages": [{"role": "user", "content": "q"}]}
            r1 = await cached_raw_chat_completion(client, **kw)
            r2 = await cached_raw_chat_completion(client, **kw)
            assert r1.choices[0].message.content == "live"
            assert r2.choices[0].message.content == "live"
            assert client.calls == 1  # second call served from cache

    @pytest.mark.asyncio
    async def test_replay_mode_hit_no_live_call(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            recorder = FakeRawClient()
            kw = {"model": "m", "messages": [{"role": "user", "content": "q"}]}
            await cached_raw_chat_completion(recorder, **kw)
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "replay"}):
            reset_raw_cache()
            replayer = FakeRawClient()
            r = await cached_raw_chat_completion(replayer, **kw)
            assert r.choices[0].message.content == "live"  # served from cache
            assert replayer.calls == 0  # NO live call in replay

    @pytest.mark.asyncio
    async def test_replay_mode_miss_raises_fail_loud(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "replay"}):
            reset_raw_cache()
            client = FakeRawClient()
            with pytest.raises(LLMCacheMiss, match="Raw cache miss in replay mode"):
                await cached_raw_chat_completion(
                    client,
                    model="m",
                    messages=[{"role": "user", "content": "never seen"}],
                )
            assert client.calls == 0  # fail-loud: must NOT silently call the API

    @pytest.mark.asyncio
    async def test_tool_calls_roundtrip(self, isolated_raw_cache):
        """Function-calling responses (tool_calls) must survive the cache."""
        from openai.types.chat import ChatCompletion, ChatCompletionMessage
        from openai.types.chat.chat_completion import Choice

        tc_response = ChatCompletion(
            id="chatcmpl-tc",
            object="chat.completion",
            created=1700000000,
            model="gpt-5-mini",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "extract", "arguments": '{"x":1}'},
                            }
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ],
        )
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            recorder = FakeRawClient(response=tc_response)
            kw = {"model": "m", "messages": [{"role": "user", "content": "call tool"}]}
            await cached_raw_chat_completion(recorder, **kw)
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "replay"}):
            reset_raw_cache()
            replayer = FakeRawClient()
            r = await cached_raw_chat_completion(replayer, **kw)
            assert r.choices[0].message.tool_calls[0].function.name == "extract"
            assert replayer.calls == 0


class TestGetRawCache:
    def test_off_returns_none(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "off"}):
            reset_raw_cache()
            assert get_raw_cache() is None

    def test_record_returns_cache(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            cache = get_raw_cache()
            assert cache is not None

    def test_singleton_reused(self, isolated_raw_cache):
        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            assert get_raw_cache() is get_raw_cache()
