"""Tests for argument-level semantic chunking (#174).

Tests the chunk_by_arguments, index_arguments, and search_arguments
methods added to SemanticIndexService.
"""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.services.semantic_index_service import (
    SemanticIndexService,
    SearchResult,
)


class TestChunkByArguments:
    """Test argument-level chunking from fact_extraction output."""

    def test_chunks_from_extraction_output(self):
        """Arguments from fact_extraction are chunked individually."""
        extraction = {
            "arguments": [
                {"text": "The climate is changing due to CO2 emissions", "source_quote": "para 2"},
                {"text": "Renewable energy reduces carbon footprint", "source_quote": "para 5"},
            ],
            "claims": [
                {"text": "We should invest in solar power", "source_quote": "conclusion"},
            ],
        }
        chunks = SemanticIndexService.chunk_by_arguments("raw text", extraction)
        assert len(chunks) == 3
        assert chunks[0]["chunk_type"] == "argument"
        assert chunks[2]["chunk_type"] == "claim"
        assert chunks[0]["source_quote"] == "para 2"

    def test_chunks_from_string_arguments(self):
        """String-format arguments are also chunked."""
        extraction = {
            "arguments": [
                "First argument with enough text",
                "Second argument also long enough",
            ],
            "claims": [],
        }
        chunks = SemanticIndexService.chunk_by_arguments("raw text", extraction)
        assert len(chunks) == 2
        assert chunks[0]["text"] == "First argument with enough text"

    def test_fallback_sentence_splitting(self):
        """Without extraction output, falls back to sentence splitting."""
        text = "First sentence is here now. Second sentence follows after. Third sentence as well."
        chunks = SemanticIndexService.chunk_by_arguments(text)
        assert len(chunks) == 3
        for c in chunks:
            assert c["chunk_type"] == "sentence"

    def test_filters_short_chunks_in_indexing(self):
        """Short arguments are filtered during indexing, not chunking."""
        service = SemanticIndexService()
        uploaded = []
        service.upload_document = lambda name, text, source_type="text", tags=None: (
            uploaded.append(1) or f"doc_{len(uploaded)}"
        )
        doc_ids = service.index_arguments(
            arguments=[{"text": "ok"}, {"text": "This is long enough to be a real argument"}],
            source_name="test",
        )
        # Only the long argument gets indexed (short ones skipped)
        assert len(doc_ids) == 1

    def test_empty_extraction_falls_back(self):
        """Empty extraction output triggers sentence fallback."""
        chunks = SemanticIndexService.chunk_by_arguments(
            "A statement worth indexing here. Another statement also follows.",
            {"arguments": [], "claims": []},
        )
        assert len(chunks) == 2


class TestIndexArguments:
    """Test argument indexing with metadata."""

    def test_index_with_quality_and_fallacy_metadata(self):
        """Arguments indexed with quality scores and fallacy tags."""
        service = SemanticIndexService()
        # Mock upload_document to capture calls
        uploaded = []

        def mock_upload(name, text, source_type="text", tags=None):
            uploaded.append({"name": name, "text": text, "tags": tags or {}})
            return f"doc_{len(uploaded)}"

        service.upload_document = mock_upload

        arguments = [
            {"text": "Climate change is caused by human activity"},
            {"text": "The earth is flat because the horizon looks flat"},
        ]
        quality_scores = {
            "arg_1": {
                "note_finale": 0.85,
                "scores_par_vertu": {"sources": 0.9, "pertinence": 0.8},
            },
            "arg_2": {
                "note_finale": 0.25,
                "scores_par_vertu": {"sources": 0.1, "pertinence": 0.4},
            },
        }
        fallacies = [
            {"argument_index": 1, "fallacy_type": "appeal_to_ignorance"},
        ]

        doc_ids = service.index_arguments(
            arguments=arguments,
            source_name="test_doc",
            quality_scores=quality_scores,
            fallacies=fallacies,
        )
        assert len(doc_ids) == 2
        assert len(uploaded) == 2

        # First argument: high quality, no fallacy
        tags1 = uploaded[0]["tags"]
        assert tags1["chunk_type"] == "argument"
        assert tags1["quality_level"] == "high"
        assert tags1["has_fallacy"] == "false"
        assert tags1["argument_id"] == "arg_1"

        # Second argument: low quality, has fallacy
        tags2 = uploaded[1]["tags"]
        assert tags2["quality_level"] == "low"
        assert tags2["has_fallacy"] == "true"
        assert tags2["fallacy_type"] == "appeal_to_ignorance"
        assert tags2["weakest_virtue"] == "sources"

    def test_index_skips_short_arguments(self):
        """Arguments shorter than 5 chars are skipped."""
        service = SemanticIndexService()
        uploaded = []
        service.upload_document = lambda **kw: uploaded.append(1) or "doc_1"

        doc_ids = service.index_arguments(
            arguments=[{"text": "ok"}, {"text": "A real argument with substance"}],
            source_name="test",
        )
        assert len(doc_ids) == 1

    def test_index_handles_upload_failure(self):
        """Failed uploads are logged but don't crash."""
        service = SemanticIndexService()
        call_count = [0]

        def failing_upload(name, text, source_type="text", tags=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Upload failed")
            return "doc_2"

        service.upload_document = failing_upload

        doc_ids = service.index_arguments(
            arguments=[
                {"text": "First argument that will fail upload"},
                {"text": "Second argument that will succeed"},
            ],
            source_name="test",
        )
        assert len(doc_ids) == 1  # Only second one succeeded

    def test_index_with_string_fallacy_target(self):
        """Fallacy with arg_N target format works."""
        service = SemanticIndexService()
        uploaded = []
        service.upload_document = lambda name, text, source_type="text", tags=None: (
            uploaded.append({"tags": tags or {}}) or f"doc_{len(uploaded)}"
        )

        service.index_arguments(
            arguments=[{"text": "An argument that has a fallacy in it"}],
            fallacies=[{"target_argument_id": "arg_1", "type": "ad_hominem"}],
            source_name="test",
        )
        assert uploaded[0]["tags"]["fallacy_type"] == "ad_hominem"


class TestSearchArguments:
    """Test argument search with metadata filtering."""

    def test_search_builds_filters(self):
        """Search includes metadata filters in API call."""
        service = SemanticIndexService(km_url="http://test:9001")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        service._requests = mock_requests

        service.search_arguments(
            query="climate change",
            fallacy_type="ad_hominem",
            quality_level="high",
            has_fallacy=True,
        )

        # Verify the API call included filters
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert "filters" in payload
        filter_keys = [list(f.keys())[0] for f in payload["filters"]]
        assert "fallacy_type" in filter_keys
        assert "quality_level" in filter_keys
        assert "has_fallacy" in filter_keys
        assert "chunk_type" in filter_keys  # Always filter by argument type
