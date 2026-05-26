"""Tests for semantic_indexing is_available() guard (Track KK #700).

Verifies that _invoke_semantic_index consults is_available() and returns
an explicit status instead of silently skipping.
"""

from unittest.mock import MagicMock, patch

import argumentation_analysis.orchestration.invoke_callables as mod

_SERVICE_PATH = (
    "argumentation_analysis.services.semantic_index_service.SemanticIndexService"
)


class TestSemanticIndexGuard:
    """_invoke_semantic_index branches on is_available()."""

    async def test_endpoint_down_returns_explicit_skip(self):
        """When is_available() is False, returns skipped: endpoint_unavailable."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = False

        with patch(_SERVICE_PATH, return_value=mock_service):
            result = await mod._invoke_semantic_index("some text", {})

        assert result["status"] == "skipped: endpoint_unavailable"
        assert "not reachable" in result["reason"]
        mock_service.search.assert_not_called()

    async def test_endpoint_up_returns_ran(self):
        """When is_available() is True, runs search and returns ran."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.search.return_value = [{"doc_id": "test", "relevance": 0.9}]

        with patch(_SERVICE_PATH, return_value=mock_service), patch(
            "asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)
        ):
            result = await mod._invoke_semantic_index("some text", {})

        assert result["status"] == "ran"
        assert result["results"] == [{"doc_id": "test", "relevance": 0.9}]
