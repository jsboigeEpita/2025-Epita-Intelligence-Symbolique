"""#3096 item 5 (R1126) — the control the endpoint actually exposes, carried.

Measured (comment 6527232924, 20 direct calls on the OpenAI-compatible
endpoint): thinking is ON by default and **44 % of billed completion tokens
are hidden reasoning**; ``LLM_REASONING_EFFORT`` (#3104) does not move it —
``low`` and ``high`` sit in default's noise, while the manifest stamped the
value as if it controlled something. The control that acts is
``extra_body={"thinking": {"type": "between_tools"}}``: hidden share 246 → 2
tokens. ``{"type": "disabled"}`` is refused by the endpoint (400).

This pins the R1126 plumbing, mirroring #3104's shape:

- ONE run-wide knob (``LLM_ANTHROPIC_THINKING``) carried by BOTH funnels —
  the SK path (the declared ``extra_body`` field) and the raw path — with an
  explicit caller setting winning, an unknown value failing loud, an
  endpoint-refused value failing loud BEFORE a pass spends a call, and the
  value stamped in the run manifest and in the cassette key;
- ``reasoning_effort`` is no longer presented as effective on the route
  where it is measured inert: the call layer does not apply it there, and
  the manifest carries the verdict instead of a bare value.

Anti-pendulum, pinned as a control: the knob COMMANDS, it never decides —
nothing here turns thinking off by default; whether passes should run
without it is the coordinator's paired pass.

Fakes only (loopback captures, no network, no key) — zero spend.
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

from argumentation_analysis.evaluation.env_manifest import (
    environment_manifest,
    render_environment_stamp,
)
from argumentation_analysis.services.llm_cache import OFF, CachedChatCompletion


class _CaptureSKInner(ChatCompletionClientBase):
    """SK inner capturing the settings object each call carried."""

    def __init__(self, model: str = "claude-haiku-5-5") -> None:
        super().__init__(service_id="cap", ai_model_id=model)
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
    """Loopback raw client capturing the kwargs each create() received."""

    def __init__(self):
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


async def _run_raw(client, model: str = "claude-haiku-5-5") -> None:
    from argumentation_analysis.services.llm_cache import cached_raw_chat_completion

    await cached_raw_chat_completion(client, model=model, messages=[])


@pytest.fixture(autouse=True)
def _off(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_MODE", OFF)
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("LLM_ANTHROPIC_THINKING", raising=False)
    from argumentation_analysis.services import llm_cache

    llm_cache._raw_cache = None
    yield llm_cache


class TestRouteDetection:
    def test_the_route_reads_the_model_id(self, _off):
        """Both route forms put a claude-* model id in the call; namespaced
        ids (OpenRouter) never match."""
        from argumentation_analysis.services.llm_cache import anthropic_route

        assert anthropic_route("claude-haiku-5-5")
        assert anthropic_route("claude-sonnet-5-5")
        assert not anthropic_route("gpt-5.6-luna")
        assert not anthropic_route("anthropic/claude-sonnet-5-5")
        assert not anthropic_route(None)
        assert not anthropic_route("")


class TestTheThinkingKnobRidesBothFunnels:
    def test_the_knob_sets_thinking_on_the_sk_path(self, _off, monkeypatch):
        """LLM_ANTHROPIC_THINKING=between_tools → the settings the inner
        service receives carry extra_body.thinking — the measured control."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        inner = _CaptureSKInner()
        _run_sk(inner, _sk_settings())
        assert inner.captured[0].extra_body["thinking"] == {"type": "between_tools"}

    def test_the_knob_sets_thinking_on_the_raw_path(self, _off, monkeypatch):
        """The raw path carries the knob in extra_body — one request field,
        on every direct call, without touching the caller's kwargs."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client)
        )
        assert client.captured["extra_body"]["thinking"] == {"type": "between_tools"}

    def test_unset_knob_injects_nothing(self, _off):
        """Control: no knob, no injection — the request is exactly what the
        caller asked for, on both paths."""
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client)
        )
        assert "extra_body" not in client.captured

        inner = _CaptureSKInner()
        settings = _sk_settings()
        _run_sk(inner, settings)
        assert not getattr(settings, "extra_body", None)

    def test_an_explicit_caller_setting_wins(self, _off, monkeypatch):
        """A caller that chose its thinking keeps it; the knob never
        overrides an explicit decision."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        inner = _CaptureSKInner()
        settings = _sk_settings(extra_body={"thinking": {"type": "caller_choice"}})
        _run_sk(inner, settings)
        assert inner.captured[0].extra_body["thinking"] == {"type": "caller_choice"}

    def test_an_unknown_value_fails_loud(self, _off, monkeypatch):
        """A typo'd value must not run a whole pass with thinking silently
        at the endpoint default — it raises at the first call, naming the
        variable."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "turbo")
        with pytest.raises(ValueError, match="LLM_ANTHROPIC_THINKING"):
            from argumentation_analysis.services.llm_cache import (
                cached_raw_chat_completion_sync,
            )

            client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=MagicMock()))
            )
            cached_raw_chat_completion_sync(
                client, model="claude-haiku-5-5", messages=[]
            )

    def test_an_endpoint_refused_value_fails_before_the_call(self, _off, monkeypatch):
        """``disabled`` is measured REFUSED by the endpoint (400, its own
        message names between_tools as the off-switch). The knob must fail
        loud BEFORE a pass spends a call discovering it — and the error must
        say that, not a generic unknown-value message."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "disabled")
        with pytest.raises(ValueError, match="REFUSES|between_tools"):
            from argumentation_analysis.services.llm_cache import (
                cached_raw_chat_completion_sync,
            )

            client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=MagicMock()))
            )
            cached_raw_chat_completion_sync(
                client, model="claude-haiku-5-5", messages=[]
            )

    def test_the_knob_is_not_applied_off_the_anthropic_route(self, _off, monkeypatch):
        """The knob commands the Anthropic route; on another model it is not
        applied — and that is a NAMED skip, never a silent one (a recorded
        control with no effect was the defect this repairs)."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client, model="gpt-5.6-luna")
        )
        assert "extra_body" not in client.captured


class TestTheEffortIsMeasuredInertOnTheAnthropicRoute:
    """R1126 — ``reasoning_effort`` no longer rides a route it cannot move."""

    def test_the_effort_is_not_applied_on_the_anthropic_route_raw(
        self, _off, monkeypatch
    ):
        """Measured inert (comment 6527232924): applying it would stamp a
        request field that moves nothing. The raw request carries no
        reasoning_effort."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client)
        )
        assert "extra_body" not in client.captured

    def test_the_effort_is_not_applied_on_the_anthropic_route_sk(
        self, _off, monkeypatch
    ):
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        inner = _CaptureSKInner()
        settings = _sk_settings()
        _run_sk(inner, settings)
        assert not getattr(inner.captured[0], "reasoning_effort", None)

    def test_the_effort_still_applies_off_the_anthropic_route(self, _off, monkeypatch):
        """#3104's behaviour is intact where the control is real."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        client = _CaptureRawClient()
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            _run_raw(client, model="gpt-5.6-luna")
        )
        assert client.captured["extra_body"]["reasoning_effort"] == "low"

    def test_a_typo_still_fails_loud_whatever_the_route(self, _off, monkeypatch):
        """Validation precedes the route verdict — a typo'd value never runs
        a pass, on any route."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "turbo")
        with pytest.raises(ValueError, match="LLM_REASONING_EFFORT"):
            from argumentation_analysis.services.llm_cache import (
                cached_raw_chat_completion_sync,
            )

            client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=MagicMock()))
            )
            cached_raw_chat_completion_sync(
                client, model="claude-haiku-5-5", messages=[]
            )


class TestThinkingIsPartOfTheRequestIdentity:
    """R1227 parity — a cassette recorded at one thinking must never answer
    a call at another."""

    def test_the_sk_cassette_does_not_answer_another_thinking(
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

        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        run(CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=RECORD))
        run(CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=REPLAY))
        # Thinking off: not the same request — the replay must miss.
        monkeypatch.delenv("LLM_ANTHROPIC_THINKING", raising=False)
        with pytest.raises(LLMCacheMiss):
            run(
                CachedChatCompletion(_CaptureSKInner(), cache_dir=tmp_path, mode=REPLAY)
            )

    def test_the_raw_cassette_does_not_answer_another_thinking(
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
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        _off._raw_cache = None
        run()
        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        _off._raw_cache = None
        monkeypatch.delenv("LLM_ANTHROPIC_THINKING", raising=False)
        with pytest.raises(LLMCacheMiss):
            run()

    def test_unset_thinking_adds_nothing_to_the_sk_settings(self, _off):
        from argumentation_analysis.services.llm_cache import _serialize_settings

        assert "extra_body" not in _serialize_settings(_sk_settings())


class TestTheKnobIsRecorded:
    def test_the_manifest_carries_the_thinking_knob(self, monkeypatch):
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")
        assert (
            environment_manifest()["overrides"]["pinned_overrides"][
                "LLM_ANTHROPIC_THINKING"
            ]
            == "between_tools"
        ), "the thinking a run commanded must be stamped in its manifest"

    def test_the_effort_carries_its_inert_verdict_on_the_route(self, monkeypatch):
        """Never presented as effective where it is measured inert: on the
        Anthropic route the manifest records value + verdict, not a bare
        pin."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-haiku-5-5")
        entry = environment_manifest()["overrides"]["pinned_overrides"][
            "LLM_REASONING_EFFORT"
        ]
        assert isinstance(entry, dict) and entry["value"] == "low"
        assert "inert" in entry["verdict"]

    def test_the_effort_stands_bare_off_the_route(self, monkeypatch):
        """#3104's record is unchanged where the control is real."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        monkeypatch.delenv("ANTHROPIC_CHAT_MODEL_ID", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")
        assert (
            environment_manifest()["overrides"]["pinned_overrides"][
                "LLM_REASONING_EFFORT"
            ]
            == "low"
        )

    def test_the_thinking_knob_names_the_misroute(self, monkeypatch):
        """Set but no Anthropic route resolved — the manifest says so instead
        of stamping a command nothing obeys."""
        monkeypatch.setenv("LLM_ANTHROPIC_THINKING", "between_tools")
        monkeypatch.delenv("ANTHROPIC_CHAT_MODEL_ID", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")
        entry = environment_manifest()["overrides"]["pinned_overrides"][
            "LLM_ANTHROPIC_THINKING"
        ]
        assert isinstance(entry, dict) and entry["value"] == "between_tools"
        assert "not applied" in entry["verdict"]

    def test_the_stamp_renders_the_verdict(self, monkeypatch):
        """The run-visible surface reads ``k=v (verdict)`` — a reader of the
        signature sees the control is inert, not pinned-and-effective."""
        monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.anthropic.com/v1/")
        stamp = render_environment_stamp(environment_manifest())
        assert "LLM_REASONING_EFFORT=low (measured inert" in stamp

    def test_render_override_bare_value(self):
        # Imported lazily so the behavior witnesses above stay collectable —
        # and meaningfully red — against a tree without the change.
        from argumentation_analysis.evaluation.env_manifest import _render_override

        assert _render_override("low") == "low"
