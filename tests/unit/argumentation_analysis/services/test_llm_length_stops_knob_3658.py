"""#3658 — a reply cut at the token cap is named; a switch turns thinking off.

Measured (issue #3658, R1202, one panel document on the claudish/MiniMax
OpenAI-compatible route): five phases stop at exactly a round token count
(``finish_reason: "length"`` — the model spent ``max_tokens`` reasoning
before it finished writing), two of them fail to parse, three leave no usage
at all — and the runner says PASS because nothing records the stop. The
control that route exposes is ``extra_body={"enable_thinking": false}``.

Born-red contract, mirroring #2849/#3096's shapes:

- the two accounting points record ``length_stops`` per phase (the calls
  whose finish reason is ``"length"``); a call that reports NO finish reason
  is counted apart (``calls_without_finish_reason``), never as 0 — the way
  ``calls_without_usage`` is (#2853). A reply cut at the cap is model
  output: it is recorded, never raised (value-provenance rule);
- ``LLM_ENABLE_THINKING=false`` sends ``extra_body={"enable_thinking":
  False}`` on both funnels — the OpenAI-compatible twin of
  ``LLM_ANTHROPIC_THINKING``, with no route gate (never inferred from the
  model name), an explicit caller ``extra_body`` winning, an unknown value
  failing loud at the first call.

Fakes only (loopback captures, no network, no key, no corpus) — zero spend.
"""

import asyncio
import types
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import pytest
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.completion_usage import CompletionUsage
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.services.llm_cache import (
    OFF,
    UNATTRIBUTED_PHASE,
    CachedChatCompletion,
)


class _FinishReason(str, Enum):
    """SK's finish reason is a str-enum comparing equal to its value."""

    STOP = "stop"
    LENGTH = "length"


class _CaptureSKInner(ChatCompletionClientBase):
    """Inner SK service whose response carries usage and a finish reason —
    the shape a cut reply has on the OpenAI-compatible route."""

    def __init__(self, finish_reason=None, model: str = "gpt-5.6-luna") -> None:
        super().__init__(service_id="cap", ai_model_id=model)
        self._finish = finish_reason
        self._captured = []

    @property
    def captured(self):
        return self._captured

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        self.captured.append(settings)
        msg = ChatMessageContent(role="assistant", content="réponse")
        msg.metadata = {"usage": CompletionUsage(prompt_tokens=1, completion_tokens=1)}
        if self._finish is not None:
            msg.finish_reason = self._finish
        return [msg]


class _CaptureRawClient:
    """Loopback raw client capturing the kwargs each create() received."""

    def __init__(self, finish_reason=None):
        self.captured = {}
        self._finish = finish_reason
        create = AsyncMock(side_effect=self._capture)
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=create)
        )

    async def _capture(self, **kwargs):
        self.captured.update(kwargs)
        choice = types.SimpleNamespace(
            message=types.SimpleNamespace(content="r"),
            finish_reason=self._finish,
        )
        return types.SimpleNamespace(
            usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            choices=[choice],
        )


def _sk_settings(**overrides):
    from semantic_kernel.connectors.ai.open_ai import (
        OpenAIChatPromptExecutionSettings,
    )

    return OpenAIChatPromptExecutionSettings(**overrides)


def _history() -> ChatHistory:
    return ChatHistory(messages=[ChatMessageContent(role="user", content="q")])


def _run_sk(inner, settings) -> None:
    wrapper = CachedChatCompletion(inner=inner, mode=OFF)
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        wrapper.get_chat_message_contents(chat_history=_history(), settings=settings)
    )


def _run_raw(client, model: str = "gpt-5.6-luna") -> None:
    from argumentation_analysis.services.llm_cache import cached_raw_chat_completion

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        cached_raw_chat_completion(client, model=model, messages=[])
    )


@pytest.fixture(autouse=True)
def _clean_knobs(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_MODE", OFF)
    for var in (
        "LLM_REASONING_EFFORT",
        "LLM_ANTHROPIC_THINKING",
        "LLM_ENABLE_THINKING",
    ):
        monkeypatch.delenv(var, raising=False)
    from argumentation_analysis.services import llm_cache

    llm_cache._raw_cache = None
    llm_cache.reset_usage_stats()
    yield llm_cache
    llm_cache.reset_usage_stats()


@pytest.fixture()
def usage_counter(_clean_knobs):
    return _clean_knobs.get_usage_stats


# ─── Ask 1: the stop reason is recorded at the two accounting points ─────


class TestLengthStopsAreAccounted:
    def test_an_sk_reply_cut_at_the_cap_counts_in_its_phase(self, usage_counter):
        """Born red: on main the bucket has no ``length_stops`` at all — a
        cut reply was indistinguishable from a whole one (#3658 ask 1)."""
        from argumentation_analysis.services import llm_cache

        msg = types.SimpleNamespace(
            metadata={
                "usage": CompletionUsage(prompt_tokens=1, completion_tokens=8192)
            },
            finish_reason=_FinishReason.LENGTH,
        )
        with llm_cache.llm_usage_phase("first_reading"):
            llm_cache._account_sk_usage([msg], model="m")
        bucket = usage_counter()["first_reading"]
        assert bucket["length_stops"] == 1
        assert bucket["calls_without_finish_reason"] == 0

    def test_a_well_ended_sk_reply_leaves_the_count_at_zero(self, usage_counter):
        """``stop`` is a measurement too: the key exists at 0, it is not
        absent — 0 says the phase answered and none of its replies was cut."""
        from argumentation_analysis.services import llm_cache

        msg = types.SimpleNamespace(
            metadata={"usage": CompletionUsage(prompt_tokens=1, completion_tokens=1)},
            finish_reason=_FinishReason.STOP,
        )
        with llm_cache.llm_usage_phase("strategist"):
            llm_cache._account_sk_usage([msg], model="m")
        bucket = usage_counter()["strategist"]
        assert bucket["length_stops"] == 0
        assert bucket["calls_without_finish_reason"] == 0

    def test_an_sk_call_without_finish_reason_is_counted_apart(self, usage_counter):
        """A response that reports no finish reason is never merged into 0
        (#2853's rule, applied to the stop reason)."""
        from argumentation_analysis.services import llm_cache

        msg = types.SimpleNamespace(
            metadata={"usage": CompletionUsage(prompt_tokens=1, completion_tokens=1)},
        )
        with llm_cache.llm_usage_phase("aspic_analysis"):
            llm_cache._account_sk_usage([msg], model="m")
        bucket = usage_counter()["aspic_analysis"]
        assert bucket["length_stops"] == 0
        assert bucket["calls_without_finish_reason"] == 1

    def test_the_raw_path_reads_the_first_choice_finish_reason(self, usage_counter):
        from argumentation_analysis.services import llm_cache

        response = types.SimpleNamespace(
            usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=4096),
            choices=[types.SimpleNamespace(finish_reason="length")],
        )
        with llm_cache.llm_usage_phase("act2_narrative"):
            llm_cache._account_raw_usage(response, model="m")
        bucket = usage_counter()["act2_narrative"]
        assert bucket["length_stops"] == 1
        assert bucket["calls_without_finish_reason"] == 0

    def test_the_raw_path_without_a_finish_reason_counts_the_call_apart(
        self, usage_counter
    ):
        from argumentation_analysis.services import llm_cache

        response = types.SimpleNamespace(
            usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            choices=[types.SimpleNamespace(finish_reason=None)],
        )
        with llm_cache.llm_usage_phase("delp_reasoning"):
            llm_cache._account_raw_usage(response, model="m")
        bucket = usage_counter()["delp_reasoning"]
        assert bucket["length_stops"] == 0
        assert bucket["calls_without_finish_reason"] == 1

    def test_a_live_sk_call_cut_at_the_cap_is_accounted(self, usage_counter):
        """Through the real wrapper (off mode): the accounting rides the live
        round-trip, outside any phase scope."""
        inner = _CaptureSKInner(_FinishReason.LENGTH)
        _run_sk(inner, _sk_settings())
        bucket = usage_counter()[UNATTRIBUTED_PHASE]
        assert bucket["length_stops"] == 1

    def test_a_live_raw_call_cut_at_the_cap_is_accounted(self, usage_counter):
        client = _CaptureRawClient(finish_reason="length")
        _run_raw(client)
        bucket = usage_counter()[UNATTRIBUTED_PHASE]
        assert bucket["length_stops"] == 1


# ─── Ask 3: the OpenAI-compatible thinking switch ─────────────────────────


class TestTheOpenAICompatibleThinkingSwitch:
    def test_false_sends_enable_thinking_false_on_the_sk_path(
        self, _clean_knobs, monkeypatch
    ):
        """The measured remedy, carried by the SK funnel — a settings field
        the inner service actually receives."""
        monkeypatch.setenv("LLM_ENABLE_THINKING", "false")
        inner = _CaptureSKInner()
        _run_sk(inner, _sk_settings())
        assert inner.captured[0].extra_body["enable_thinking"] is False

    def test_false_sends_enable_thinking_false_on_the_raw_path(
        self, _clean_knobs, monkeypatch
    ):
        monkeypatch.setenv("LLM_ENABLE_THINKING", "false")
        client = _CaptureRawClient()
        _run_raw(client)
        assert client.captured["extra_body"]["enable_thinking"] is False

    def test_true_sends_enable_thinking_true(self, _clean_knobs, monkeypatch):
        """A two-call probe answered in both modes (#3658): the knob is a
        boolean switch, not an off-only flag."""
        monkeypatch.setenv("LLM_ENABLE_THINKING", "true")
        client = _CaptureRawClient()
        _run_raw(client)
        assert client.captured["extra_body"]["enable_thinking"] is True

    def test_unset_injects_nothing(self, _clean_knobs):
        """Control: no knob, no injection — the request is exactly what the
        caller asked for, on both paths. The value is never inferred from the
        model name."""
        client = _CaptureRawClient()
        _run_raw(client)
        assert "extra_body" not in client.captured

        inner = _CaptureSKInner()
        settings = _sk_settings()
        _run_sk(inner, settings)
        assert not getattr(inner.captured[0], "extra_body", None)

    def test_an_explicit_caller_setting_wins(self, _clean_knobs, monkeypatch):
        monkeypatch.setenv("LLM_ENABLE_THINKING", "false")
        client = _CaptureRawClient()
        from argumentation_analysis.services.llm_cache import (
            cached_raw_chat_completion,
        )

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            cached_raw_chat_completion(
                client,
                model="gpt-5.6-luna",
                messages=[],
                extra_body={"enable_thinking": True},
            )
        )
        assert client.captured["extra_body"]["enable_thinking"] is True

    def test_the_switch_has_no_route_gate(self, _clean_knobs, monkeypatch):
        """Unlike ``LLM_ANTHROPIC_THINKING``, this knob commands whatever
        OpenAI-compatible call it rides — the operator said it, the request
        carries it, whatever the model id."""
        monkeypatch.setenv("LLM_ENABLE_THINKING", "false")
        client = _CaptureRawClient()
        _run_raw(client, model="claude-haiku-5-5")
        assert client.captured["extra_body"]["enable_thinking"] is False

    def test_an_unknown_value_fails_loud(self, _clean_knobs, monkeypatch):
        """A typo'd value must not run a whole pass with thinking silently
        at the route default — it raises at the first call, naming the
        variable."""
        monkeypatch.setenv("LLM_ENABLE_THINKING", "maybe")
        with pytest.raises(ValueError, match="LLM_ENABLE_THINKING"):
            from argumentation_analysis.services.llm_cache import (
                cached_raw_chat_completion_sync,
            )

            client = types.SimpleNamespace(
                chat=types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=MagicMock())
                )
            )
            cached_raw_chat_completion_sync(client, model="gpt-5.6-luna", messages=[])
