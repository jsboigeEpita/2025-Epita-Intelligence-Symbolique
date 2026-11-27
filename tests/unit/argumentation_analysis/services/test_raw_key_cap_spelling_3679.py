"""The raw cache key carries the completion cap under its second spelling (#3679).

``client.chat.completions.create`` takes ``max_tokens`` on the OpenAI spelling
of a model and ``max_completion_tokens`` on the reasoning-model spelling; the
raw seam sends the second for the first reading, the personas and the shield
validator. Only the first was in the key. Measured on main ``de05227f3``: one
request, and the same request capped at 64 under the second spelling, hashed
to one key. So a call capped at 200 could replay the answer recorded for a
call capped at 1024 — an answer the capped call cannot receive.

Same rule as ``extra_body`` (#3096 item 5): unset adds nothing, so every
cassette recorded without the field keeps its key. The two digests pinned
below were computed under the formula as it stood before the change.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from argumentation_analysis.services.llm_cache import (
    LLMCacheMiss,
    cached_raw_chat_completion,
    compute_raw_cache_key,
    reset_raw_cache,
)

MODEL = "m"
MESSAGES = [{"role": "user", "content": "one request"}]
KEY_WITHOUT_CAP = "bbf9d8c7e7e98cfb8f5276b22ee456886deeeb30ceba0939ecc0d271a05eb4d8"
KEY_WITH_MAX_TOKENS_64 = (
    "c00d187a08415d02e096cfd4835afef771ea6bc50afa39909e67cc5cf3441cfb"
)


def _key(**fields) -> str:
    return compute_raw_cache_key(model=MODEL, messages=MESSAGES, **fields)


class TestTheCapIsPartOfTheKeyWhateverItsSpelling:
    def test_a_capped_call_no_longer_shares_the_uncapped_key(self):
        assert _key(max_completion_tokens=64) != _key()

    def test_two_calls_differing_only_by_the_cap_get_two_keys(self):
        assert _key(max_completion_tokens=200) != _key(max_completion_tokens=1024)

    def test_the_two_spellings_are_two_requests(self):
        assert _key(max_tokens=64) != _key(max_completion_tokens=64)

    def test_a_call_without_it_keeps_its_old_key(self):
        assert _key() == KEY_WITHOUT_CAP
        # Unset adds nothing; an explicit None is the same absence.
        assert _key(max_completion_tokens=None) == KEY_WITHOUT_CAP

    def test_the_first_spelling_keeps_its_key_too(self):
        assert _key(max_tokens=64) == KEY_WITH_MAX_TOKENS_64
        assert _key(max_tokens=200) != _key(max_tokens=1024)


class _FakeClient:
    """Stand-in for an OpenAI client. Counts chat.completions.create calls."""

    def __init__(self, content: str):
        from openai.types.chat import ChatCompletion, ChatCompletionMessage
        from openai.types.chat.chat_completion import Choice

        self._content = content
        self.calls = 0

        async def _create(**kwargs):
            self.calls += 1
            return ChatCompletion(
                id="chatcmpl-x",
                object="chat.completion",
                created=1700000000,
                model=kwargs.get("model", "m"),
                choices=[
                    Choice(
                        index=0,
                        message=ChatCompletionMessage(
                            role="assistant", content=self._content
                        ),
                        finish_reason="stop",
                    )
                ],
            )

        self.chat = type("C", (), {})()
        self.chat.completions = type("P", (), {})()
        self.chat.completions.create = _create


@pytest.fixture
def isolated_raw_cache(tmp_path: Path, monkeypatch):
    """One cache directory per test, and no open handle left behind."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
    reset_raw_cache()
    yield tmp_path
    reset_raw_cache()


class TestACassetteAnswersOnlyUnderItsCap:
    async def test_a_replay_under_another_cap_misses_instead_of_answering(
        self, isolated_raw_cache
    ):
        request = {"model": MODEL, "messages": MESSAGES}

        with patch.dict(os.environ, {"LLM_CACHE_MODE": "record"}):
            reset_raw_cache()
            recorder = _FakeClient("recorded under 1024")
            await cached_raw_chat_completion(
                recorder, **request, max_completion_tokens=1024
            )
            assert recorder.calls == 1

        with patch.dict(os.environ, {"LLM_CACHE_MODE": "replay"}):
            reset_raw_cache()
            replayer = _FakeClient("live")
            served = await cached_raw_chat_completion(
                replayer, **request, max_completion_tokens=1024
            )
            assert served.choices[0].message.content == "recorded under 1024"

            # The same request under another cap, and uncapped: no cassette
            # of theirs exists, so the replay says so. It never hands them the
            # 1024 answer.
            with pytest.raises(LLMCacheMiss, match="Raw cache miss in replay mode"):
                await cached_raw_chat_completion(
                    replayer, **request, max_completion_tokens=200
                )
            with pytest.raises(LLMCacheMiss, match="Raw cache miss in replay mode"):
                await cached_raw_chat_completion(replayer, **request)
            assert replayer.calls == 0  # a miss never becomes a live call
