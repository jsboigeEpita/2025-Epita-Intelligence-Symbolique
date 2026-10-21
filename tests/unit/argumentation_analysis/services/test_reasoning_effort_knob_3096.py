"""#3096 item 5 — the run path can set reasoning effort explicitly, and says so.

Measured on the doc_A pass: Claude completion tokens run 3-8× the GPT figure
for comparable rendered output — hidden reasoning tokens billed as output are
suspected, not measured. The endpoint accepts ``reasoning_effort`` (probe
20/10: 200; low cut one question's completion tokens by 20 %). The repair
this pins: ONE run-wide knob (``LLM_REASONING_EFFORT``) carried by BOTH LLM
funnels — the SK path (SK's own ``reasoning_effort`` setting) and the raw
path (``extra_body``) — recorded in the run's environment manifest, with an
explicit caller setting always winning and an unknown value failing loud.

Fakes only — no network, no key, zero spend.
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.completion_usage import CompletionUsage
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.evaluation.env_manifest import environment_manifest
from argumentation_analysis.services.llm_cache import CachedChatCompletion, OFF


class _CaptureSKInner(ChatCompletionClientBase):
    """SK inner capturing the settings object each call carried."""

    def __init__(self) -> None:
        super().__init__(service_id="cap", ai_model_id="claude-haiku-5-5")
        self._captured = []

    @property
    def captured(self):
        return self._captured

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        self._captured.append(settings)
        msg = ChatMessageContent(role="assistant", content="réponse")
        msg.metadata = {"usage": CompletionUsage(prompt_tokens=1, completion_tokens=1)}
        return [msg]


class _CaptureRawClient:
    """Raw client capturing the kwargs each create() received."""

    def __init__(self) -> None:
        self.captured = {}
        create = AsyncMock(side_effect=self._capture)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    async def _capture(self, **kwargs):
        self.captured.update(kwargs)
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            choices=[SimpleNamespace(message=SimpleNamespace(content="r"))],
        )


def _sk_settings(**overrides):
    from semantic_kernel.connectors.ai.open_ai import (
        OpenAIChatPromptExecutionSettings,
    )

    return OpenAIChatPromptExecutionSettings(**overrides)


def _history() -> ChatHistory:
    return ChatHistory(messages=[ChatMessageContent(role="user", content="q")])


def _run_sk(inner, settings) -> None:
    import asyncio

    wrapper = CachedChatCompletion(inner=inner, mode=OFF)
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        wrapper.get_chat_message_contents(chat_history=_history(), settings=settings)
    )


async def _run_raw(client) -> None:
    from argumentation_analysis.services.llm_cache import cached_raw_chat_completion

    await cached_raw_chat_completion(client, model="claude-haiku-5-5", messages=[])


@pytest.fixture(autouse=True)
def _off(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_MODE", OFF)
    from argumentation_analysis.services import llm_cache

    llm_cache._raw_cache = None
    yield llm_cache


class TestTheKnobRidesBothFunnels:
    def test_the_knob_sets_effort_on_the_sk_path(self, _off, monkeypatch):
        """LLM_REASONING_EFFORT=low → the settings the inner service receives
        carry reasoning_effort=low (SK declares the field natively)."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        inner = _CaptureSKInner()
        _run_sk(inner, _sk_settings())
        assert inner.captured[0].reasoning_effort == "low"

    def test_the_knob_sets_effort_on_the_raw_path(self, _off, monkeypatch):
        """The raw path carries the knob in extra_body — one request field,
        sent on every direct call, without touching the caller's kwargs."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client)
        )
        assert client.captured["extra_body"]["reasoning_effort"] == "low"

    def test_unset_knob_injects_nothing(self, _off, monkeypatch):
        """Control: no knob, no injection — the request is exactly what the
        caller asked for, on both paths."""
        monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client)
        )
        assert "extra_body" not in client.captured

        inner = _CaptureSKInner()
        settings = _sk_settings()
        _run_sk(inner, settings)
        assert settings.reasoning_effort is None

    def test_an_explicit_caller_setting_wins(self, _off, monkeypatch):
        """A caller that chose its effort keeps it; the knob never overrides
        an explicit decision."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        inner = _CaptureSKInner()
        settings = _sk_settings(reasoning_effort="high")
        _run_sk(inner, settings)
        assert inner.captured[0].reasoning_effort == "high"

    def test_an_unknown_value_fails_loud(self, _off, monkeypatch):
        """A typo'd effort must not run a whole pass at the endpoint default —
        it raises at the first call, naming the variable."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "turbo")
        with pytest.raises(ValueError, match="LLM_REASONING_EFFORT"):
            from argumentation_analysis.services.llm_cache import (
                cached_raw_chat_completion_sync,
            )

            client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=MagicMock()))
            )
            cached_raw_chat_completion_sync(client, model="m", messages=[])


class TestTheEffortIsPartOfTheRequestIdentity:
    """R1227 review — a cassette recorded at one effort must never answer a
    call at another effort.

    Measured defect before the fix: the SK path computed its cache key BEFORE
    applying the knob, and the raw path's key tuple ignored ``extra_body``.
    Two efforts therefore shared one cassette: a replay at ``high`` served the
    answer recorded at ``low`` without a miss. The witnesses below drive the
    REAL record/replay wrappers on a tmp diskcache and pin the consequence
    (miss/ hit), not the key helper alone.
    """

    def test_the_sk_cassette_does_not_answer_another_effort(
        self, _off, monkeypatch, tmp_path
    ):
        from argumentation_analysis.services.llm_cache import (
            LLMCacheMiss,
            RECORD,
            REPLAY,
        )

        def run(wrapper) -> None:
            import asyncio

            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                wrapper.get_chat_message_contents(
                    chat_history=_history(), settings=_sk_settings()
                )
            )

        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        run(CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=RECORD))
        # Same effort: the cassette is usable (the knob did not invalidate it).
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        run(CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=REPLAY))
        # Other effort: the request is not the same one — the replay must miss.
        monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
        with pytest.raises(LLMCacheMiss):
            run(
                CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=REPLAY)
            )

    def test_the_raw_cassette_does_not_answer_another_effort(
        self, _off, monkeypatch, tmp_path
    ):
        import asyncio

        from argumentation_analysis.services.llm_cache import LLMCacheMiss

        def run() -> None:
            client = _CaptureRawClient()
            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                _run_raw(client)
            )

        monkeypatch.setenv("LLM_CACHE_MODE", "record")
        monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        _off._raw_cache = None
        run()
        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        _off._raw_cache = None
        monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
        with pytest.raises(LLMCacheMiss):
            run()

    def test_unset_effort_leaves_the_raw_key_identity_untouched(self, _off):
        """Cassette compatibility: with no knob, the request carries no
        ``extra_body`` and the key is the pre-#3096 one."""
        from argumentation_analysis.services.llm_cache import (
            _apply_effort_to_raw_kwargs,
            compute_raw_cache_key,
        )

        caller = {"model": "m", "messages": []}
        assert _apply_effort_to_raw_kwargs(dict(caller), None) == caller
        assert compute_raw_cache_key(**caller) == compute_raw_cache_key(
            **_apply_effort_to_raw_kwargs(dict(caller), None)
        )

    def test_unset_effort_adds_nothing_to_the_sk_settings(self, _off):
        from argumentation_analysis.services.llm_cache import _serialize_settings

        assert "reasoning_effort" not in _serialize_settings(_sk_settings())


class TestTheKnobIsRecorded:
    def test_the_manifest_carries_the_knob(self, monkeypatch):
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        manifest = environment_manifest()
        assert (
            manifest["overrides"]["pinned_overrides"]["LLM_REASONING_EFFORT"] == "low"
        ), "the effort a run used must be stamped in its environment manifest"

    def test_the_manifest_carries_the_named_route_model(self, monkeypatch):
        """Parity with OPENAI/OPENROUTER_CHAT_MODEL_ID: the named Anthropic
        route's model id is a pin a reader of the signature must see."""
        monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")
        manifest = environment_manifest()
        assert (
            manifest["overrides"]["pinned_overrides"]["ANTHROPIC_CHAT_MODEL_ID"]
            == "claude-haiku-5-5"
        )

    def test_no_knob_no_override_entry(self, monkeypatch):
        monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
        assert (
            "LLM_REASONING_EFFORT"
            not in environment_manifest()["overrides"]["pinned_overrides"]
        )
