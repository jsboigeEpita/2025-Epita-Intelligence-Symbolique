"""
Tests for the Local LLM Service adapter (integrated from 2.3.6).

Tests validate:
- Module import without errors
- CapabilityRegistry/ServiceDiscovery registration
- Service API contract
- Graceful degradation when endpoint unreachable
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLocalLLMImport:
    """Test that the local LLM service can be imported."""

    def test_import_module(self):
        """Local LLM service imports without errors."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        assert LocalLLMService is not None

    def test_instantiate_service(self):
        """Service can be instantiated with defaults."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService()
        assert service.endpoint == "http://localhost:5001/v1"

    def test_instantiate_custom_endpoint(self):
        """Service accepts custom endpoint configuration."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService(
            endpoint="http://localhost:5002/v1",
            model="GLM-4.7-Flash-AWQ",
        )
        assert "5002" in service.endpoint
        assert service.model == "GLM-4.7-Flash-AWQ"


class TestLocalLLMRegistration:
    """Test ServiceDiscovery registration."""

    def test_register_in_service_discovery(self):
        """Local LLM registers correctly in ServiceDiscovery."""
        from argumentation_analysis.core.capability_registry import (
            ServiceDiscovery,
        )

        sd = ServiceDiscovery()
        sd.register_llm_provider(
            "local_vllm",
            endpoint="http://localhost:5001/v1",
            models=["ZwZ-8B-AWQ"],
            priority=10,
        )

        provider = sd.get_best_provider("llm")
        assert provider is not None
        assert provider.name == "local_vllm"

    def test_register_multiple_providers(self):
        """Multiple local LLM providers can coexist."""
        from argumentation_analysis.core.capability_registry import (
            ServiceDiscovery,
        )

        sd = ServiceDiscovery()
        sd.register_llm_provider(
            "local_mini",
            endpoint="http://localhost:5001/v1",
            priority=5,
        )
        sd.register_llm_provider(
            "local_medium",
            endpoint="http://localhost:5002/v1",
            priority=10,
        )

        best = sd.get_best_provider("llm")
        assert best.name == "local_medium"  # higher priority

    def test_register_in_capability_registry(self):
        """Local LLM registers as a service in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        registry = CapabilityRegistry()
        registry.register_service(
            "local_llm",
            service_class=LocalLLMService,
            capabilities=["local_llm_inference", "chat_completion"],
        )

        providers = registry.find_for_capability("local_llm_inference")
        assert len(providers) == 1
        assert providers[0].name == "local_llm"


class TestLocalLLMServiceAPI:
    """Test the service API contract."""

    def test_get_status_details(self):
        """Status details return expected structure."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService(endpoint="http://localhost:5001/v1", model="test")
        status = service.get_status_details()

        assert status["service"] == "local_llm"
        assert "endpoint" in status
        assert "model" in status

    @pytest.mark.asyncio
    async def test_is_available_unreachable(self):
        """is_available returns False when endpoint unreachable."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService(endpoint="http://localhost:99999/v1")
        available = await service.is_available()
        assert available is False

    @pytest.mark.asyncio
    async def test_chat_completion_unreachable(self):
        """chat_completion returns error when endpoint unreachable."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService(endpoint="http://localhost:99999/v1")
        result = await service.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
        assert "error" in result

    def test_repr(self):
        """repr shows useful debugging info."""
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        service = LocalLLMService(endpoint="http://localhost:5001/v1", model="test")
        repr_str = repr(service)
        assert "LocalLLMService" in repr_str
        assert "5001" in repr_str
