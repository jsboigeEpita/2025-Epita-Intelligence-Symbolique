"""BO-3 #1473 PR2 (SK-path wiring) — unit tests, no network.

``create_llm_service`` is the canonical factory for every SK-native chat service
(the conversational ``AgentGroupChat`` / ``ChatCompletionAgent`` path, the cluedo
orchestrator, the CLI). PR2 wraps its returned service with
``CachedChatCompletion`` so SK-native calls are replayed from the same disk cache
as the direct path (PR1, ``_guarded_chat_completion``). These tests assert the
wiring CONTRACT with ``OpenAIChatCompletion`` patched out (no API key needed):

- off mode  → service returned UNWRAPPED (zero behavior change)
- record    → wrapped with CachedChatCompletion(mode=record)
- replay    → wrapped with CachedChatCompletion(mode=replay)
- mock path → NOT wrapped (mocks are deterministic by nature; they return early)

The end-to-end live proof (record → replay → 0 live API call, identical output,
fail-loud on miss) lives in
``tests/integration/orchestration/test_replay_cache_sk_path.py``.
"""

from unittest.mock import patch

import pytest

from argumentation_analysis.services.llm_cache import (
    OFF,
    RECORD,
    REPLAY,
    CachedChatCompletion,
)


@pytest.fixture(autouse=True)
def _cache_env(monkeypatch):
    """Isolate LLM_CACHE_* + provider env per test; reset the raw-cache singleton."""
    monkeypatch.delenv("LLM_CACHE_MODE", raising=False)
    monkeypatch.delenv("LLM_CACHE_DIR", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-not-used")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from argumentation_analysis.services import llm_cache as lc

    lc.reset_raw_cache()
    yield
    lc.reset_raw_cache()


class _FakeOpenAIChatCompletion:
    """Stand-in for the real SK service; only construction matters here."""

    def __init__(self, *args, **kwargs):
        self.service_id = kwargs.get("service_id")
        self.ai_model_id = kwargs.get("ai_model_id")


def _build(monkeypatch, tmp_path, mode):
    """Build an authentic service with OpenAIChatCompletion patched (no network)."""
    monkeypatch.setenv("LLM_CACHE_MODE", mode)
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "sk_cache"))
    with patch(
        "argumentation_analysis.core.llm_service.OpenAIChatCompletion",
        _FakeOpenAIChatCompletion,
    ):
        from argumentation_analysis.core.llm_service import create_llm_service

        return create_llm_service(
            service_id="test", model_id="gpt-test", force_authentic=True
        )


def test_off_mode_no_wrapping(monkeypatch, tmp_path):
    service = _build(monkeypatch, tmp_path, OFF)
    assert not isinstance(service, CachedChatCompletion), (
        "off mode must NOT wrap the SK service (zero behavior change)"
    )


def test_record_mode_wraps(monkeypatch, tmp_path):
    service = _build(monkeypatch, tmp_path, RECORD)
    assert isinstance(service, CachedChatCompletion), (
        "record mode must wrap the SK service with CachedChatCompletion (PR2)"
    )
    assert service.mode == RECORD


def test_replay_mode_wraps(monkeypatch, tmp_path):
    service = _build(monkeypatch, tmp_path, REPLAY)
    assert isinstance(service, CachedChatCompletion)
    assert service.mode == REPLAY


def test_mock_path_not_wrapped(monkeypatch):
    """Test-env mock branch returns early → never wrapped."""
    monkeypatch.setenv("LLM_CACHE_MODE", REPLAY)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-not-used")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "unit::test::mock_path (call)")
    from argumentation_analysis.core.llm_service import create_llm_service

    service = create_llm_service(service_id="test", model_id="m")
    assert not isinstance(service, CachedChatCompletion)
