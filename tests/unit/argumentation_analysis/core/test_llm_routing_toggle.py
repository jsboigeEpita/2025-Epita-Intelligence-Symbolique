# -*- coding: utf-8 -*-
"""
Tests for the OpenRouter routing toggle (RA anti-théâtre #1079).

Two layers:
1. ``resolve_chat_endpoint`` — the canonical resolver in ``core.llm_service``.
   Env-injected, $0-API: proves the OPENROUTER_* toggle is consulted and that
   OPENAI_* is the fallback.
2. Site wiring — proves each production bypass site (router,
   collaborative_debate, judge, french_fallacy_adapter) now routes the resolved
   ``base_url`` into its ``AsyncOpenAI`` client instead of hardcoding the
   official endpoint.

These are the regression guards for the #1079 fix track (leaks surfaced by the
AUDIT-LLM-ROUTING sweep #1078).
"""

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# 1. Canonical resolver
# ---------------------------------------------------------------------------


class TestResolveChatEndpoint:
    """resolve_chat_endpoint honors the OPENROUTER_* toggle."""

    def test_openrouter_toggle_on_routes_to_openrouter(self):
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True):
            api_key, base_url, model_id = resolve_chat_endpoint()
        assert api_key == "sk-or-test"
        assert base_url == "https://openrouter.ai/api/v1"
        assert model_id == "openai/gpt-5-mini"

    def test_openrouter_model_falls_back_to_openai_chat_model(self):
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENAI_CHAT_MODEL_ID": "gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True):
            _, _, model_id = resolve_chat_endpoint()
        assert model_id == "gpt-5-mini"

    def test_no_openrouter_falls_back_to_openai_official(self):
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {"OPENAI_API_KEY": "sk-test", "OPENAI_CHAT_MODEL_ID": "gpt-5-mini"}
        with patch.dict("os.environ", env, clear=True):
            api_key, base_url, model_id = resolve_chat_endpoint()
        assert api_key == "sk-test"
        assert base_url == "https://api.openai.com/v1"
        assert model_id == "gpt-5-mini"

    def test_no_key_returns_empty(self):
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        with patch.dict("os.environ", {}, clear=True):
            api_key, base_url, model_id = resolve_chat_endpoint()
        assert api_key == ""
        assert base_url == "https://api.openai.com/v1"
        assert model_id == "gpt-5-mini"  # default

    def test_partial_openrouter_falls_back_to_openai(self):
        """Key without base_url (or vice-versa) must NOT enable the toggle."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENROUTER_API_KEY": "sk-or-test",  # no OPENROUTER_BASE_URL
            "OPENAI_API_KEY": "sk-openai",
        }
        with patch.dict("os.environ", env, clear=True):
            api_key, _, _ = resolve_chat_endpoint()
        assert api_key == "sk-openai"  # toggle OFF → OpenAI fallback


# ---------------------------------------------------------------------------
# 2. Production sites route the resolved base_url into their client
# ---------------------------------------------------------------------------


class TestSitesConsultToggle:
    """Each #1079 bypass site passes the OpenRouter base_url to its client."""

    async def test_collaborative_debate_uses_openrouter_base_url(self):
        from argumentation_analysis.orchestration.collaborative_debate import (
            _invoke_collaborative_analysis,
        )

        captured = {}

        class _FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        return _mock_completion()

            def __init__(self, **kwargs):
                captured.update(kwargs)

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True), patch(
            "openai.AsyncOpenAI", side_effect=_FakeClient
        ):
            await _invoke_collaborative_analysis("some text", {})
        # The client must target OpenRouter, not the official OpenAI endpoint.
        assert captured.get("base_url") == "https://openrouter.ai/api/v1"
        assert captured.get("api_key") == "sk-or-test"

    async def test_router_builds_client_with_toggle_base_url(self):
        from argumentation_analysis.orchestration.router import TextAnalysisRouter

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True):
            router = TextAnalysisRouter()
        # __init__ must derive the endpoint from the toggle.
        assert router._api_key == "sk-or-test"
        assert router._base_url == "https://openrouter.ai/api/v1"
        assert router._model == "openai/gpt-5-mini"

    async def test_french_fallacy_adapter_get_client_uses_toggle(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        captured = {}

        class _FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True), patch(
            "openai.AsyncOpenAI", side_effect=_FakeAsyncOpenAI
        ):
            client, model = LLMFallacyDetector()._get_openai_client()
        assert client is not None
        assert captured.get("base_url") == "https://openrouter.ai/api/v1"
        assert model == "openai/gpt-5-mini"

    async def test_judge_routes_through_toggle(self):
        from argumentation_analysis.evaluation.judge import LLMJudge

        captured = {}

        class _FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        return _mock_completion(
                            content='{"completeness": 3, "accuracy": 3, "depth": 3, '
                            '"coherence": 3, "actionability": 3, "overall": 3, '
                            '"reasoning": "ok"}'
                        )

            def __init__(self, **kwargs):
                captured.update(kwargs)

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "sk-or-test",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5-mini",
        }
        with patch.dict("os.environ", env, clear=True), patch(
            "openai.AsyncOpenAI", side_effect=_FakeClient
        ):
            await LLMJudge().evaluate("text", "standard", {})
        assert captured.get("base_url") == "https://openrouter.ai/api/v1"
        assert captured.get("api_key") == "sk-or-test"

    async def test_fallacy_adapter_emits_degraded_signal_on_failure(self):
        """#1019: an API failure sets last_degraded (no silent [])."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        class _FailingClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        raise RuntimeError("upstream 429")

            def __init__(self, **kwargs):
                pass

        env = {"OPENAI_API_KEY": "sk-test"}
        detector = LLMFallacyDetector()
        with patch.dict("os.environ", env, clear=True), patch(
            "openai.AsyncOpenAI", side_effect=_FailingClient
        ):
            result = await detector.detect_async("some text")
        assert result == []  # return type preserved (tier-fallback contract)
        assert detector.last_degraded is True  # observable signal present
        assert "429" in (detector._last_error or "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_completion(
    content: str = '{"capabilities": [], "workflow_complexity": "standard"}',
):
    """Build a minimal mock OpenAI chat completion response."""
    from unittest.mock import MagicMock

    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response
