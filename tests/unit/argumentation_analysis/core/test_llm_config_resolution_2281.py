"""Guards for #2281 — LLM config resolution must be honest and loud.

Modes of trap covered:
1. Silent model/endpoint divergence (no log at startup)
2. Empty-string env vars silently fall back to defaults (empty ≠ absent)
3. Obsolete model substitution without the env-var name in the warning
"""
import os
import pytest
from unittest.mock import patch


class TestResolveChatEndpointHonesty:
    """The resolver must log its effective config and refuse empty strings."""

    def test_logs_resolved_config_openrouter(self, caplog):
        """OpenRouter path: one-line log with endpoint, model, and source."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": "test-or-key",
            "OPENROUTER_CHAT_MODEL_ID": "openai/gpt-5.6-luna",
        }
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level("INFO"):
                api_key, base_url, model_id = resolve_chat_endpoint()
        assert api_key == "test-or-key"
        assert "openrouter" in base_url
        assert model_id == "openai/gpt-5.6-luna"
        assert "LLM config resolved" in caplog.text
        assert "provider=OpenRouter" in caplog.text
        assert "endpoint=https://openrouter.ai/api/v1" in caplog.text
        assert "model=openai/gpt-5.6-luna" in caplog.text
        assert "source=OPENROUTER_API_KEY+OPENROUTER_BASE_URL" in caplog.text

    def test_logs_resolved_config_openai(self, caplog):
        """OpenAI path: one-line log with endpoint, model, and source."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENAI_API_KEY": "test-openai-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-5.6-luna",
        }
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level("INFO"):
                api_key, base_url, model_id = resolve_chat_endpoint()
        assert api_key == "test-openai-key"
        assert "api.openai.com" in base_url
        assert model_id == "gpt-5.6-luna"
        assert "LLM config resolved" in caplog.text
        assert "provider=OpenAI" in caplog.text
        assert "endpoint=https://api.openai.com/v1" in caplog.text
        assert "source=OPENAI_API_KEY" in caplog.text

    def test_empty_openai_api_key_raises(self):
        """OPENAI_API_KEY='' must fail loud — empty is not absent (#2281)."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {"OPENAI_API_KEY": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY.*empty string"):
                resolve_chat_endpoint()

    def test_empty_openai_base_url_raises(self):
        """OPENAI_BASE_URL='' must fail loud — empty is not absent (#2281)."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="OPENAI_BASE_URL.*empty string"):
                resolve_chat_endpoint()

    def test_obsolete_model_substituted_and_logged(self, caplog):
        """gpt-5-mini → gpt-5.6-luna substitution must name the env var."""
        from argumentation_analysis.core.llm_service import resolve_chat_endpoint

        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-5-mini",
        }
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level("WARNING"):
                api_key, base_url, model_id = resolve_chat_endpoint()
        assert model_id == "gpt-5.6-luna"
        assert "OPENAI_CHAT_MODEL_ID" in caplog.text
        assert "gpt-5-mini" in caplog.text
        assert "gpt-5.6-luna" in caplog.text


class TestGetOpenAIClientHonesty:
    """The raw-SDK path must also log and refuse empty strings."""

    def test_empty_openai_api_key_raises(self):
        """_get_openai_client must refuse OPENAI_API_KEY='' (#2281)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_openai_client,
        )

        env = {"OPENAI_API_KEY": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY.*empty string"):
                _get_openai_client()

    def test_logs_resolved_config(self, caplog):
        """_get_openai_client must log its effective config."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _get_openai_client,
        )

        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-5.6-luna",
        }
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level("INFO"):
                client, model_id = _get_openai_client()
        assert client is not None
        assert model_id == "gpt-5.6-luna"
        assert "LLM config resolved" in caplog.text
        assert "provider=OpenAI" in caplog.text
        assert "source=OPENAI_API_KEY" in caplog.text


class TestCreateLlmServiceHonesty:
    """The SK factory path must also log and refuse empty strings."""

    def test_empty_openai_api_key_raises(self):
        """create_llm_service must refuse OPENAI_API_KEY='' (#2281)."""
        from argumentation_analysis.core.llm_service import create_llm_service

        env = {"OPENAI_API_KEY": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY.*empty string"):
                create_llm_service(
                    service_id="test_service",
                    force_authentic=True,
                )

    def test_logs_resolved_config(self, caplog):
        """create_llm_service must log its effective config."""
        from argumentation_analysis.core.llm_service import create_llm_service

        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-5.6-luna",
        }
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level("INFO"):
                service = create_llm_service(
                    service_id="test_service",
                    force_authentic=True,
                )
        assert service is not None
        assert "LLM config resolved" in caplog.text
        assert "provider=OpenAI" in caplog.text
        assert "source=OPENAI_API_KEY" in caplog.text
