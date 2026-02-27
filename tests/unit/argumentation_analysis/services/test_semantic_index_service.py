"""
Tests for SemanticIndexService adapter (Arg_Semantic_Index integration).

Tests validate:
- Module and class imports
- Data class creation (SearchResult, AskResult)
- Service initialization with defaults and custom config
- format_doc_id slug generation
- HTTP calls mocked for upload, search, ask
- Availability check against KM service
- CapabilityRegistry registration
- Graceful handling of missing KM service
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestImports:
    """Test that service classes are importable."""

    def test_import_service(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        assert SemanticIndexService is not None

    def test_import_data_classes(self):
        from argumentation_analysis.services.semantic_index_service import (
            SearchResult,
            AskResult,
        )

        assert SearchResult is not None
        assert AskResult is not None


class TestSearchResult:
    """Test SearchResult data class."""

    def test_creation(self):
        from argumentation_analysis.services.semantic_index_service import (
            SearchResult,
        )

        r = SearchResult(text="hello", relevance=0.95, document_id="doc1")
        assert r.text == "hello"
        assert r.relevance == 0.95
        assert r.document_id == "doc1"
        assert r.tags == {}

    def test_defaults(self):
        from argumentation_analysis.services.semantic_index_service import (
            SearchResult,
        )

        r = SearchResult(text="x", relevance=0.5)
        assert r.document_id == ""
        assert r.source_name == ""


class TestAskResult:
    """Test AskResult data class."""

    def test_creation(self):
        from argumentation_analysis.services.semantic_index_service import (
            AskResult,
            SearchResult,
        )

        r = AskResult(
            answer="Paris is the capital",
            sources=[SearchResult(text="France...", relevance=0.9)],
        )
        assert r.answer == "Paris is the capital"
        assert len(r.sources) == 1

    def test_empty_result(self):
        from argumentation_analysis.services.semantic_index_service import (
            AskResult,
        )

        r = AskResult(answer="")
        assert r.answer == ""
        assert r.sources == []
        assert r.raw_response is None


class TestServiceConfig:
    """Test service initialization and configuration."""

    def test_default_url(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService()
        assert "9001" in svc._km_url

    def test_custom_url(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService(km_url="http://my-km:9002")
        assert svc._km_url == "http://my-km:9002"

    def test_env_url(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        with patch.dict(os.environ, {"KERNEL_MEMORY_URL": "http://env-km:9003"}):
            svc = SemanticIndexService()
            assert svc._km_url == "http://env-km:9003"

    def test_custom_api_key(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService(api_key="test-key")
        headers = svc._headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_no_api_key(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService(api_key=None)
        svc._api_key = None
        headers = svc._headers()
        assert "Authorization" not in headers


class TestFormatDocId:
    """Test document ID generation."""

    def test_simple_name(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        assert SemanticIndexService.format_doc_id("My Document") == "my_document"

    def test_accented_name(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        result = SemanticIndexService.format_doc_id("Débat Lincoln-Douglas")
        assert "debat" in result
        assert "lincoln" in result

    def test_special_chars(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        result = SemanticIndexService.format_doc_id("Test (1) & More!")
        assert result == "test_1_more"


class TestServiceAvailability:
    """Test service health check."""

    def test_unavailable_when_no_service(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService(km_url="http://nonexistent:9999")
        assert svc.is_available() is False

    def test_available_with_mock(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            svc._available = None
            assert svc.is_available() is True


class TestSearch:
    """Test semantic search with mocked HTTP."""

    def test_search_returns_results(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "documentId": "doc1",
                    "partitions": [{"text": "Found text", "relevance": 0.85}],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            results = svc.search("test query")

        assert len(results) == 1
        assert results[0].text == "Found text"
        assert results[0].relevance == 0.85
        assert results[0].document_id == "doc1"


class TestAsk:
    """Test RAG question answering with mocked HTTP."""

    def test_ask_returns_answer(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "The answer is 42",
            "relevantSources": [
                {
                    "documentId": "doc1",
                    "partitions": [{"text": "Source text", "relevance": 0.9}],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = svc.ask("What is the answer?")

        assert result.answer == "The answer is 42"
        assert len(result.sources) == 1
        assert result.raw_response is not None


class TestStatusDetails:
    """Test status details reporting."""

    def test_status_details(self):
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        svc = SemanticIndexService(km_url="http://test:9001")
        svc._available = True
        details = svc.get_status_details()
        assert details["service_type"] == "SemanticIndexService"
        assert details["km_url"] == "http://test:9001"
        assert details["available"] is True


class TestCapabilityRegistration:
    """Test CapabilityRegistry integration."""

    def test_register_semantic_index(self):
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.services.semantic_index_service import (
            SemanticIndexService,
        )

        registry = CapabilityRegistry()
        registry.register_service(
            "semantic_index",
            SemanticIndexService,
            capabilities=["semantic_search", "document_indexing", "rag_qa"],
        )
        services = registry.find_services_for_capability("semantic_search")
        assert len(services) == 1
        assert services[0].name == "semantic_index"
