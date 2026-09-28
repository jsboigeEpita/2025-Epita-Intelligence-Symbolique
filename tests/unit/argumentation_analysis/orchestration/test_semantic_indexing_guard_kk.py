"""Tests for semantic_indexing is_available() guard (Track KK #700).

Verifies that _invoke_semantic_index consults is_available() and returns
an explicit status instead of silently skipping. #2618 moved the endpoint-up
branch to the argument contract: ``index_arguments`` then ``search_arguments``
(#174), results serialized to ``{id, score, snippet, ...}``.
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
        mock_service.index_arguments.assert_not_called()
        mock_service.search_arguments.assert_not_called()

    async def test_endpoint_up_returns_ran(self):
        """When is_available() is True, indexes then searches, returns ran."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.index_arguments.return_value = ["pipeline__arg_1"]
        hit = MagicMock()
        hit.document_id = "pipeline__arg_1"
        hit.relevance = 0.9
        hit.text = "argument synthetique"
        hit.source_name = "pipeline"
        hit.tags = {"tags": ["chunk_type:argument"]}
        mock_service.search_arguments.return_value = [hit]

        # #2763: the no-input branch returns ``skipped: no_input_arguments``
        # before reaching the service — this guard's branch needs arguments.
        context = {
            "phase_extract_output": {
                "arguments": [{"text": "argument synthetique", "source_quote": "q1"}]
            }
        }

        with patch(_SERVICE_PATH, return_value=mock_service), patch(
            "asyncio.to_thread", side_effect=lambda fn, *a, **kw: fn(*a, **kw)
        ):
            result = await mod._invoke_semantic_index("some text", context)

        assert result["status"] == "ran"
        assert result["indexed_count"] == 1
        assert result["results"][0]["id"] == "pipeline__arg_1"
        assert result["results"][0]["score"] == 0.9
        mock_service.index_arguments.assert_called_once()
        mock_service.search_arguments.assert_called_once()
