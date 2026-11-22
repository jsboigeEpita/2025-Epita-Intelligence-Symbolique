"""#3667 ask 1 — the resolver names an absent embedding route BEFORE any call.

On the named Anthropic chat route (#3096 item 6) there is no ``/v1/embeddings``
endpoint: c21 measured 8 documents of HTTP 404 while the phase table read
``completed``. The resolver must answer ``None`` from the ROUTE IDENTITY
(``_resolve_named_anthropic_route``), never from the model name, and a declared
``SEMANTIC_INDEX_EMBEDDING_*`` pair still wins. Seat-free: fakes only.
"""

from __future__ import annotations

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.services import semantic_retrieval as sr

_NAMED_ROUTE_ENV = {
    "ANTHROPIC_CHAT_MODEL_ID": "claude-fake-0",
    "ANTHROPIC_API_KEY": "test-key-not-a-secret",
}


def _clear_embedding_pair(monkeypatch):
    monkeypatch.delenv(sr.EMBEDDING_KEY_ENV, raising=False)
    monkeypatch.delenv(sr.EMBEDDING_URL_ENV, raising=False)
    monkeypatch.delenv(sr.EMBEDDING_MODEL_ENV, raising=False)


def _counting_post_embeddings(calls):
    def _fake(route, texts):
        calls.append(list(texts))
        return [[0.0, 1.0] for _ in texts]

    return _fake


def test_named_anthropic_route_yields_no_embedding_route(monkeypatch):
    _clear_embedding_pair(monkeypatch)
    for name, value in _NAMED_ROUTE_ENV.items():
        monkeypatch.setenv(name, value)
    route, reason = sr.resolve_embedding_route()
    assert route is None
    assert "Anthropic" in reason
    assert sr.EMBEDDING_KEY_ENV in reason


async def test_phase_skips_without_any_embedding_call(monkeypatch):
    """The DoD witness: the phase answers skipped: no_embedding_route and
    _post_embeddings is never called."""
    _clear_embedding_pair(monkeypatch)
    for name, value in _NAMED_ROUTE_ENV.items():
        monkeypatch.setenv(name, value)
    calls = []
    monkeypatch.setattr(sr, "_post_embeddings", _counting_post_embeddings(calls))
    result = await ic._invoke_semantic_index("a text long enough to chunk" * 20, {})
    assert result["status"] == "skipped: no_embedding_route"
    assert calls == []


def test_declared_pair_still_wins_on_the_named_route(monkeypatch):
    """The DoD control: with the pair declared, the fake _post_embeddings IS
    called — the guard refuses the provider fallback only, never the pair."""
    for name, value in _NAMED_ROUTE_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://127.0.0.1:8005/v1")
    monkeypatch.setenv(sr.EMBEDDING_MODEL_ENV, "local-embed")
    route, reason = sr.resolve_embedding_route()
    assert route is not None and reason == ""
    assert route.source == "declared"
    calls = []
    monkeypatch.setattr(sr, "_post_embeddings", _counting_post_embeddings(calls))
    vectors = sr._post_embeddings(route, ["one chunk"])
    assert len(calls) == 1
    assert vectors == [[0.0, 1.0]]


def test_no_named_route_keeps_the_provider_fallback(monkeypatch):
    """Without the named route, the one provider resolver still answers."""
    _clear_embedding_pair(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_CHAT_MODEL_ID", raising=False)
    monkeypatch.setattr(
        "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
        lambda: ("k", "http://provider/v1", "chat-model"),
    )
    route, reason = sr.resolve_embedding_route()
    assert route is not None and reason == ""
    assert route.source == "provider"
    assert route.base_url == "http://provider/v1"
