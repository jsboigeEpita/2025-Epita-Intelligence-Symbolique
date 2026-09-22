"""Non-vacuity controls for the LLM egress counter (#1787).

The counter's success value is 0 — exactly what it reads when unwired. These
controls are therefore part of the instrument, not optional coverage: each
emits ONE request through a covered path (via httpx.MockTransport — zero real
network) and asserts the session counter sees exactly one.

They also cover BOTH production paths named in the DoD:
- raw path: direct ``AsyncOpenAI`` → ``client.chat.completions.create``
  (the extract/governance/quality/fallacy/counter-arg funnel)
- SK path: ``CachedChatCompletion`` wrapping an SK ``OpenAIChatCompletion``
  (the kernel/agents funnel — conversational & cluedo modes)

Because these tests run inside the gate, every gate report self-attests the
counter is live: this file's rows must appear in the per-test breakdown.
"""

import httpx
import pytest
from openai import AsyncOpenAI

from tests.llm_egress_counter import get_counter

FAKE_OPENAI_HOST = "https://api.openai.com/v1"
NON_LLM_URL = "https://example.com/ping"

_CHAT_COMPLETION_PAYLOAD = {
    "id": "chatcmpl-egress-control",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-5-mini",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "ok"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_CHAT_COMPLETION_PAYLOAD)

    return httpx.MockTransport(handler)


def _session_counter():
    counter = get_counter()
    assert counter is not None, (
        "session counter not activated — tests/conftest.py pytest_configure "
        "must call activate() (#1787)"
    )
    return counter


async def test_counter_sees_raw_openai_sdk_request():
    """Chemin brut: 1 request via direct AsyncOpenAI → counter +1 (not 0, not 2)."""
    counter = _session_counter()
    client = AsyncOpenAI(
        api_key="sk-egress-control",
        base_url=FAKE_OPENAI_HOST,
        http_client=httpx.AsyncClient(transport=_mock_transport()),
    )
    before = counter.total()
    response = await client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "egress control"}],
    )
    assert response.choices[0].message.content == "ok"
    assert counter.total() == before + 1, (
        f"non-vacuity FAILED on the raw path: expected {before + 1}, "
        f"counter reads {counter.total()} — the counter is blind to the "
        "direct AsyncOpenAI path"
    )


async def test_counter_sees_sk_wrapper_request():
    """Chemin SK: 1 request via CachedChatCompletion(OpenAIChatCompletion) → counter +1."""
    pytest.importorskip("semantic_kernel")
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    from argumentation_analysis.services.llm_cache import CachedChatCompletion

    counter = _session_counter()
    inner = OpenAIChatCompletion(
        ai_model_id="gpt-5-mini",
        api_key="sk-egress-control",
        async_client=AsyncOpenAI(
            api_key="sk-egress-control",
            base_url=FAKE_OPENAI_HOST,
            http_client=httpx.AsyncClient(transport=_mock_transport()),
        ),
    )
    wrapped = CachedChatCompletion(inner=inner, mode="off")

    from semantic_kernel.connectors.ai.prompt_execution_settings import (
        PromptExecutionSettings,
    )
    from semantic_kernel.contents import ChatHistory

    history = ChatHistory()
    history.add_user_message("egress control")
    before = counter.total()
    result = await wrapped.get_chat_message_contents(
        chat_history=history,
        settings=PromptExecutionSettings(ai_model_id="gpt-5-mini"),
    )
    assert result and getattr(result[0], "content", None) == "ok"
    assert counter.total() == before + 1, (
        f"non-vacuity FAILED on the SK wrapper path: expected {before + 1}, "
        f"counter reads {counter.total()} — the counter is blind to the "
        "CachedChatCompletion/kernel path"
    )


async def test_counter_sees_bare_httpx_request():
    """Transport floor: a bare httpx request to an LLM host is counted."""
    counter = _session_counter()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        before = counter.total()
        await client.post(
            f"{FAKE_OPENAI_HOST}/chat/completions", json={"probe": "egress"}
        )
    assert counter.total() == before + 1


async def test_counter_ignores_non_llm_host():
    """Specificity + 3-state vision (#1591): a request to an unwatched host
    leaves the LLM count unchanged AND surfaces in the unknown bucket — an
    absent endpoint env var must produce "unknown host seen", not silence."""
    counter = _session_counter()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        before = counter.total()
        await client.get(NON_LLM_URL)
    assert counter.total() == before, "a non-watched host must not count as LLM egress"
    snap = counter.snapshot()
    unknown_hits = [
        r
        for r in snap["requests"]
        if r["host"] == "example.com"
        and r["class"] == "unknown"
        and r["test"].endswith("test_counter_ignores_non_llm_host")
    ]
    assert unknown_hits, (
        "3-state vision failed: the example.com request must be visible in "
        "the unknown bucket (class='unknown'), not silently dropped"
    )


async def test_counter_classifies_asgi_testserver_nonllm():
    """The ASGI TestClient host is known test infra, not an unknown host (#1591):
    141 in-process "testserver" requests drowned the unknown bucket in the
    first 3-state CI run — unknown must stay a signal, not the default."""
    counter = _session_counter()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        before = counter.total()
        await client.get("https://testserver/api/egress-control")
    assert counter.total() == before
    snap = counter.snapshot()
    seen = [
        r
        for r in snap["requests"]
        if r["host"] == "testserver" and r["test"].endswith(
            "test_counter_classifies_asgi_testserver_nonllm"
        )
    ]
    assert seen and all(r["class"] == "nonllm" for r in seen), (
        "testserver (ASGI TestClient) must classify as nonllm, not unknown"
    )


async def test_counter_sees_httpx2_request():
    """openai>=3.x transport coverage (#1591 livrable 0): openai 3.1 (what CI
    resolves from the unpinned environment.yml) sends via httpx2, not httpx.
    The counter must patch it too, or every default-client SDK call is
    invisible — CI read a false 0 this way (run 32048104455). Skipped where
    httpx2 is absent (local envs run openai <3); CI is where this control
    earns its keep."""
    httpx2 = pytest.importorskip("httpx2")
    counter = _session_counter()

    def handler(request) -> "httpx2.Response":
        return httpx2.Response(200, json=_CHAT_COMPLETION_PAYLOAD)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        before = counter.total()
        await client.post(f"{FAKE_OPENAI_HOST}/chat/completions", json={"p": 1})
    assert counter.total() == before + 1, (
        f"non-vacuity FAILED on the httpx2 path: expected {before + 1}, "
        f"counter reads {counter.total()} — the counter is blind to "
        "httpx2, the transport openai>=3.x uses in CI (false-zero family "
        "#1556: an unpatched transport reads exactly like a clean gate)"
    )
    assert "httpx2" in counter.snapshot()["transports_patched"]
    # #2391: the outcome rides on httpx2 entries too (the transport CI's SDK uses).
    entries = _this_test_llm_entries(counter, "test_counter_sees_httpx2_request")
    assert [r.get("status") for r in entries] == [200], entries


def _this_test_llm_entries(counter, test_name: str):
    return [
        r
        for r in counter.snapshot()["requests"]
        if r["class"] == "llm" and r["test"].endswith(test_name)
    ]


async def test_counter_records_the_response_status():
    """#2391 : the report says how a request came back, not only that it left.

    A 400 answered to every tool-carrying call was visible only when a test
    FAILED and pytest printed its captured log; in a passing test the same 400
    left no trace in the report. The status now rides on the request's entry.
    """
    counter = _session_counter()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "egress control"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await client.post(f"{FAKE_OPENAI_HOST}/chat/completions", json={"p": 1})

    entries = _this_test_llm_entries(
        counter, "test_counter_records_the_response_status"
    )
    assert [r.get("status") for r in entries] == [400], entries
    snap = counter.snapshot()
    assert snap["llm_outcomes"].get("400", 0) >= 1
    assert any(
        t.endswith("test_counter_records_the_response_status")
        for t in snap["per_test_llm_not_ok"]
    ), snap["per_test_llm_not_ok"]


async def test_counter_records_a_transport_error_and_lets_it_propagate():
    """An exception in the send is recorded by type, and still reaches the caller."""
    counter = _session_counter()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("egress control", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ConnectError):
            await client.post(f"{FAKE_OPENAI_HOST}/chat/completions", json={"p": 1})

    entries = _this_test_llm_entries(
        counter, "test_counter_records_a_transport_error_and_lets_it_propagate"
    )
    assert [r.get("error") for r in entries] == ["ConnectError"], entries
    assert all("status" not in r for r in entries)


async def test_a_successful_llm_response_is_not_counted_as_not_ok():
    """Agreement control: a 200 lands in the 2xx outcomes, not in the not-ok map."""
    counter = _session_counter()
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        await client.post(f"{FAKE_OPENAI_HOST}/chat/completions", json={"p": 1})

    entries = _this_test_llm_entries(
        counter, "test_a_successful_llm_response_is_not_counted_as_not_ok"
    )
    assert [r.get("status") for r in entries] == [200], entries
    assert not any(
        t.endswith("test_a_successful_llm_response_is_not_counted_as_not_ok")
        for t in counter.snapshot()["per_test_llm_not_ok"]
    )
