"""#3685 — the completion cap is part of the SK cassette key.

Measured on main (issue #3685): the two SK sites pass their cap as
``max_completion_tokens`` — the Sherlock enquiry agent (2000) and the logic
assistant (400) — on ``OpenAIPromptExecutionSettings``. That class keeps
unknown kwargs in ``extension_data``; when the kernel invokes the prompt
function it converts them to ``OpenAIChatPromptExecutionSettings``, where the
cap becomes a declared field and goes to the wire (witnessed below). But
``_serialize_settings`` read only ``max_tokens``: the SK cache key ignored the
cap, so a call capped at 2000 and the same call capped at 400 — or uncapped —
shared one cassette. One of them was answered with the other's recorded
response, and no miss said so.

The witnesses drive the real record/replay wrapper on a tmp diskcache, not the
key helper alone, and the wire witnesses read the request body that actually
went out. Fakes only — no network, no key, zero spend: the one client used
here answers in memory.
"""

import asyncio
import json

import diskcache
import httpx
import pytest
from openai import AsyncOpenAI
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.completion_usage import CompletionUsage
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIChatPromptExecutionSettings,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig

from argumentation_analysis.services.llm_cache import (
    LLMCacheMiss,
    OFF,
    RECORD,
    REPLAY,
    CachedChatCompletion,
    _serialize_response,
    _serialize_settings,
    compute_cache_key,
)

FIELD = "max_completion_tokens"

# The kernel service id the two sites wire their prompt functions to; without
# an explicit id, SK's OpenAI service registers under this same name.
SERVICE_ID = "chat_completion"

# The two production sites' caps (pm/sherlock_enquete_agent.py:282 and
# logic/watson_logic_assistant.py:497).
SHERLOCK_CAP = 2000
WATSON_CAP = 400

# compute_cache_key(_history(), _wrapper_settings()) on the pre-#3685
# derivation (measured on the unfixed tree, identical under SK 1.34.0 and
# 1.44.0): an uncapped call, nothing else in the settings. A cassette recorded
# before #3685 sits under that key.
PRE_3685_KEY_OF_THE_UNCAPPED_CALL = (
    "a89919bfba7e0fdccc8313d386a1b122af013ee858e58d8222935388dbb8e66b"
)

WIRE_ANSWER = {
    "id": "chatcmpl-in-process",
    "object": "chat.completion",
    "created": 0,
    "model": "loopback-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "réponse"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
}


def _site_execution_settings(**overrides):
    """The settings the two production sites write (their class, their kwarg).

    ``max_completion_tokens`` is not a field of this class: SK's
    ``PromptExecutionSettings`` routes the unknown kwarg into
    ``extension_data``, where the kernel conversion finds it.
    """
    return OpenAIPromptExecutionSettings(service_id=SERVICE_ID, **overrides)


def _wrapper_settings(**overrides):
    """The settings the wrapper keys on — the kernel's own conversion.

    Measured on the band's capped lookup (capture, #3685): at
    ``CachedChatCompletion.get_chat_message_contents`` the object is an
    ``OpenAIChatPromptExecutionSettings`` whose ``max_completion_tokens`` is a
    declared field. Building it through the production conversion keeps the
    witness on the real chain instead of a shape invented here.
    """
    return OpenAIChatPromptExecutionSettings.from_prompt_execution_settings(
        _site_execution_settings(**overrides)
    )


def _history() -> ChatHistory:
    return ChatHistory(messages=[ChatMessageContent(role="user", content="q")])


class _CaptureInner(ChatCompletionClientBase):
    """SK inner that answers without a client: enough to record a cassette."""

    def __init__(self) -> None:
        super().__init__(service_id=SERVICE_ID, ai_model_id="loopback-model")

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        msg = ChatMessageContent(role="assistant", content="réponse")
        msg.metadata = {"usage": CompletionUsage(prompt_tokens=1, completion_tokens=1)}
        return [msg]


class _InProcessWire:
    """An OpenAI client whose transport answers in memory and keeps each
    request body it receives (#3685 DoD 3 needs the body, not the settings)."""

    def __init__(self) -> None:
        self.bodies: list = []

    def client(self) -> AsyncOpenAI:
        def answer(request: httpx.Request) -> httpx.Response:
            self.bodies.append(json.loads(request.content))
            return httpx.Response(200, json=WIRE_ANSWER)

        return AsyncOpenAI(
            api_key="sk-in-process-not-a-key",
            base_url="http://llm-double-3685.invalid/v1",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(answer)),
            max_retries=0,
        )


def _call(cache_dir, mode, settings):
    """One SK call through the real wrapper; returns the messages it served."""

    async def run() -> list:
        wrapper = CachedChatCompletion(
            inner=_CaptureInner(), cache_dir=cache_dir, mode=mode
        )
        try:
            return await wrapper.get_chat_message_contents(
                chat_history=_history(), settings=settings
            )
        finally:
            wrapper.close()

    return asyncio.run(run())


@pytest.fixture(autouse=True)
def _off(monkeypatch):
    """No cache from the seat's environment and no run-wide knob: the key of
    a call here is what the call itself carries."""
    monkeypatch.setenv("LLM_CACHE_MODE", OFF)
    from argumentation_analysis.services import llm_cache

    llm_cache._raw_cache = None
    for name in (
        llm_cache._REASONING_EFFORT_ENV,
        llm_cache._ANTHROPIC_THINKING_ENV,
        llm_cache._ENABLE_THINKING_ENV,
    ):
        monkeypatch.delenv(name, raising=False)
    yield llm_cache


class TestTheCapIsPartOfTheRequestIdentity:
    def test_the_sites_settings_carry_the_cap_through_the_conversion(self, _off):
        """The chain the fix stands on, measured at its two ends: the site's
        kwarg lives in ``extension_data`` on its class, and the conversion the
        kernel performs promotes it to a declared field the serializer reads.
        """
        site = _site_execution_settings(**{FIELD: SHERLOCK_CAP})
        assert site.extension_data[FIELD] == SHERLOCK_CAP
        assert (
            _serialize_settings(_wrapper_settings(**{FIELD: SHERLOCK_CAP}))[FIELD]
            == SHERLOCK_CAP
        )

    def test_two_caps_do_not_share_a_cassette(self, _off, tmp_path):
        """A cassette recorded at the Sherlock cap must not answer the same
        call at the Watson cap: two caps are two requests."""
        _call(tmp_path, RECORD, _wrapper_settings(**{FIELD: SHERLOCK_CAP}))
        # Same cap: the cassette is usable.
        _call(tmp_path, REPLAY, _wrapper_settings(**{FIELD: SHERLOCK_CAP}))
        # Other cap: not the same request — the replay must miss.
        with pytest.raises(LLMCacheMiss):
            _call(tmp_path, REPLAY, _wrapper_settings(**{FIELD: WATSON_CAP}))

    def test_a_capped_call_does_not_read_the_uncapped_cassette(self, _off, tmp_path):
        """And the other way round: recorded uncapped, asked capped."""
        _call(tmp_path, RECORD, _wrapper_settings())
        _call(tmp_path, REPLAY, _wrapper_settings())
        with pytest.raises(LLMCacheMiss):
            _call(tmp_path, REPLAY, _wrapper_settings(**{FIELD: SHERLOCK_CAP}))

    def test_a_call_without_the_field_keeps_its_old_key(self, _off, tmp_path):
        """Cassette compatibility: the cap unset adds nothing, so every SK
        cassette recorded without the field keeps its key.

        Two readings: the key of the uncapped call is the one main computed
        (the literal above), and a cassette stored under that key — the way
        the pre-#3685 record wrote it — is served to the uncapped replay.
        """
        assert FIELD not in _serialize_settings(_wrapper_settings())
        old_key = compute_cache_key(_history(), _wrapper_settings())
        assert old_key == PRE_3685_KEY_OF_THE_UNCAPPED_CALL

        response = [ChatMessageContent(role="assistant", content="réponse")]
        with diskcache.Cache(str(tmp_path)) as store:
            store[old_key] = _serialize_response(response)
        served = _call(tmp_path, REPLAY, _wrapper_settings())
        assert [m.content for m in served] == ["réponse"]


class TestTheCapReachesTheWire:
    def test_the_sites_settings_put_the_cap_on_the_wire(self, _off):
        """DoD 3, on the sites' exact form: a prompt function wired the way
        both sites wire it — ``PromptTemplateConfig.execution_settings``
        carrying ``OpenAIPromptExecutionSettings(…, max_completion_tokens=…)``
        — puts the cap in the request body that SK sends.
        """

        async def scenario() -> None:
            wire = _InProcessWire()
            kernel = Kernel()
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id=SERVICE_ID,
                    ai_model_id="loopback-model",
                    async_client=wire.client(),
                )
            )
            kernel.add_function(
                function_name="chat",
                plugin_name="site",
                prompt_template_config=PromptTemplateConfig(
                    template="{{$chat_history}}",
                    template_format="semantic-kernel",
                    input_variables=[
                        InputVariable(
                            name="chat_history", allow_dangerously_set_content=True
                        )
                    ],
                    execution_settings={
                        SERVICE_ID: _site_execution_settings(**{FIELD: SHERLOCK_CAP})
                    },
                ),
            )
            await kernel.invoke(
                plugin_name="site", function_name="chat", chat_history="q"
            )
            assert len(wire.bodies) == 1
            assert wire.bodies[0][FIELD] == SHERLOCK_CAP

        asyncio.run(scenario())

    def test_the_capped_request_is_kept_under_its_own_key(self, _off, tmp_path):
        """The record-side half of the link a cassette rename stands on: in
        record mode the very settings object that computed the key is the one
        handed to the inner service, i.e. to the wire — and the cassette it
        writes answers that cap only.
        """
        wire = _InProcessWire()
        inner = OpenAIChatCompletion(
            service_id=SERVICE_ID,
            ai_model_id="loopback-model",
            async_client=wire.client(),
        )

        async def scenario() -> None:
            settings = _wrapper_settings(**{FIELD: SHERLOCK_CAP})
            recorder = CachedChatCompletion(inner, cache_dir=tmp_path, mode=RECORD)
            try:
                await recorder.get_chat_message_contents(
                    chat_history=_history(), settings=settings
                )
            finally:
                recorder.close()

            assert len(wire.bodies) == 1
            assert wire.bodies[0][FIELD] == SHERLOCK_CAP

            with diskcache.Cache(str(tmp_path)) as store:
                stored = list(store)
            assert stored == [compute_cache_key(_history(), settings)]

            replayer = CachedChatCompletion(inner, cache_dir=tmp_path, mode=REPLAY)
            try:
                served = await replayer.get_chat_message_contents(
                    chat_history=_history(),
                    settings=_wrapper_settings(**{FIELD: SHERLOCK_CAP}),
                )
                with pytest.raises(LLMCacheMiss):
                    await replayer.get_chat_message_contents(
                        chat_history=_history(),
                        settings=_wrapper_settings(**{FIELD: WATSON_CAP}),
                    )
            finally:
                replayer.close()
            assert [m.content for m in served] == ["réponse"]
            # Nothing else went out: both replays read the cassette, or missed.
            assert len(wire.bodies) == 1

        asyncio.run(scenario())
