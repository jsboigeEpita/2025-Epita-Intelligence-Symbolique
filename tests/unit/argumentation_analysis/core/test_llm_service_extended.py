"""
Extended tests for core/llm_service.py.

Covers mock/authentic branching, model substitution, Azure path,
unsupported service type, LLMService class, and error handling.
All tests use mocks — no real API calls.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, PropertyMock


class TestCreateLlmServiceMocking:
    """Tests for create_llm_service mock/authentic branching."""

    def _import_create(self):
        from argumentation_analysis.core.llm_service import create_llm_service
        return create_llm_service

    def test_force_mock_returns_mock_service(self):
        """force_mock=True returns MockChatCompletion."""
        create = self._import_create()
        with patch("argumentation_analysis.core.llm_service.logger"):
            service = create("test_svc", force_mock=True)
        assert type(service).__name__ == "MockChatCompletion"

    def test_test_env_returns_mock(self):
        """PYTEST_CURRENT_TEST in env triggers mock path."""
        create = self._import_create()
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_file::test_fn"}):
            service = create("test_svc")
        assert type(service).__name__ == "MockChatCompletion"

    def test_force_authentic_overrides_test_env(self):
        """force_authentic=True bypasses mock even in test env."""
        create = self._import_create()
        with patch.dict(os.environ, {
            "PYTEST_CURRENT_TEST": "test_file::test_fn",
            "OPENAI_API_KEY": "sk-test-fake-key",
            "OPENAI_CHAT_MODEL_ID": "gpt-5-mini",
        }):
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI") as mock_client:
                with patch("argumentation_analysis.core.llm_service.OpenAIChatCompletion") as mock_oai:
                    mock_oai.return_value = MagicMock()
                    service = create("svc", force_authentic=True)
        assert service is not None
        mock_oai.assert_called_once()

    def test_missing_api_key_raises(self):
        """Missing OPENAI_API_KEY raises ValueError."""
        create = self._import_create()
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        env.pop("PYTEST_CURRENT_TEST", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                create("svc", force_authentic=True)


class TestCreateLlmServiceModelSubstitution:
    """Tests for automatic model substitution."""

    def test_gpt4_32k_substituted(self):
        """gpt-4-32k is automatically replaced by gpt-5-mini."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
        }):
            # Remove PYTEST_CURRENT_TEST to avoid mock path
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI"):
                with patch("argumentation_analysis.core.llm_service.OpenAIChatCompletion") as mock_oai:
                    mock_oai.return_value = MagicMock()
                    create_llm_service(
                        "svc",
                        model_id="gpt-4-32k",
                        force_authentic=True,
                    )
            # Verify the substituted model was used
            call_kwargs = mock_oai.call_args
            assert call_kwargs[1]["ai_model_id"] == "gpt-5-mini"

    def test_default_model_from_env(self):
        """When model_id is None, reads from OPENAI_CHAT_MODEL_ID."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_CHAT_MODEL_ID": "custom-model",
        }):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI"):
                with patch("argumentation_analysis.core.llm_service.OpenAIChatCompletion") as mock_oai:
                    mock_oai.return_value = MagicMock()
                    create_llm_service("svc", force_authentic=True)
            call_kwargs = mock_oai.call_args
            assert call_kwargs[1]["ai_model_id"] == "custom-model"


class TestCreateLlmServiceAzure:
    """Tests for Azure service creation path."""

    def test_azure_missing_endpoint_raises(self):
        """Azure path without AZURE_OPENAI_ENDPOINT raises ValueError."""
        from argumentation_analysis.core.llm_service import create_llm_service

        env = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
                create_llm_service(
                    "svc",
                    model_id="gpt-4",
                    service_type="AzureChatCompletion",
                    force_authentic=True,
                )

    def test_azure_success(self):
        """Azure path with endpoint creates AzureChatCompletion."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "AZURE_OPENAI_ENDPOINT": "https://my-resource.openai.azure.com",
        }):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AzureChatCompletion") as mock_azure:
                mock_azure.return_value = MagicMock()
                service = create_llm_service(
                    "svc",
                    model_id="gpt-4",
                    service_type="AzureChatCompletion",
                    force_authentic=True,
                )
            assert service is not None
            mock_azure.assert_called_once()


class TestCreateLlmServiceErrors:
    """Tests for error handling."""

    def test_unsupported_service_type(self):
        """Unsupported service_type raises ValueError."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with pytest.raises(ValueError, match="non supporté"):
                create_llm_service(
                    "svc",
                    model_id="m",
                    service_type="UnknownService",
                    force_authentic=True,
                )

    def test_openai_constructor_exception_wraps_in_runtime(self):
        """Generic exception during OpenAI creation is wrapped in RuntimeError."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI"):
                with patch(
                    "argumentation_analysis.core.llm_service.OpenAIChatCompletion",
                    side_effect=Exception("connection failed"),
                ):
                    with pytest.raises(RuntimeError, match="Impossible de configurer"):
                        create_llm_service("svc", model_id="m", force_authentic=True)

    def test_org_id_passed_to_client(self):
        """OPENAI_ORG_ID is forwarded to AsyncOpenAI."""
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_ORG_ID": "org-12345",
        }):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI") as mock_client:
                with patch("argumentation_analysis.core.llm_service.OpenAIChatCompletion") as mock_oai:
                    mock_oai.return_value = MagicMock()
                    create_llm_service("svc", model_id="m", force_authentic=True)
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs["organization"] == "org-12345"


class TestLLMServiceClass:
    """Tests for the LLMService wrapper class."""

    def test_llm_property(self):
        from argumentation_analysis.core.llm_service import LLMService

        mock_instance = MagicMock()
        svc = LLMService(mock_instance)
        assert svc.llm is mock_instance
