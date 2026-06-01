"""Tests for local_llm state writer and invoke callable enrichment (#834).

Validates:
- _invoke_local_llm writes results to state.local_llm_results
- _invoke_local_llm handles unavailable endpoint gracefully
- _invoke_local_llm handles errors gracefully
- State field local_llm_results exists on UnifiedAnalysisState
- Trace entry is written
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestLocalLLMStateField:
    """Verify local_llm_results field on UnifiedAnalysisState."""

    def test_field_exists(self):
        state = UnifiedAnalysisState("text")
        assert hasattr(state, "local_llm_results"), (
            "UnifiedAnalysisState should have local_llm_results field"
        )

    def test_field_initially_empty(self):
        state = UnifiedAnalysisState("text")
        assert state.local_llm_results == []

    def test_field_accepts_results(self):
        state = UnifiedAnalysisState("text")
        state.local_llm_results.append({"status": "completed", "response": "test"})
        assert len(state.local_llm_results) == 1
        assert state.local_llm_results[0]["status"] == "completed"


class TestInvokeLocalLLMStateWriter:
    """Verify _invoke_local_llm writes to state (#834)."""

    @pytest.mark.asyncio
    async def test_writes_to_state_on_success(self):
        """Successful LLM call should write to state.local_llm_results."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        state = UnifiedAnalysisState("text")

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(return_value="Analysis: 2 arguments found")
        mock_service.model_id = "local-test"

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {"_state_object": state})

        assert result["status"] == "completed"
        assert result["response"] == "Analysis: 2 arguments found"
        assert len(state.local_llm_results) == 1
        assert state.local_llm_results[0]["status"] == "completed"
        # Trace entry should also be written
        assert len(state.analysis_trace) == 1
        assert state.analysis_trace[0]["phase"] == "local_llm"

    @pytest.mark.asyncio
    async def test_writes_to_state_on_unavailable(self):
        """Unavailable endpoint should write skipped status to state."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        state = UnifiedAnalysisState("text")

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=False)

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {"_state_object": state})

        assert result["status"] == "skipped: endpoint_unavailable"
        assert len(state.local_llm_results) == 1
        assert state.local_llm_results[0]["status"] == "skipped: endpoint_unavailable"

    @pytest.mark.asyncio
    async def test_writes_to_state_on_error(self):
        """LLM error should write error status to state."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        state = UnifiedAnalysisState("text")

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(side_effect=RuntimeError("Connection refused"))

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {"_state_object": state})

        assert result["status"] == "error"
        assert "Connection refused" in result["error"]
        assert len(state.local_llm_results) == 1
        assert state.local_llm_results[0]["status"] == "error"

    @pytest.mark.asyncio
    async def test_works_without_state(self):
        """Should work even without state object (graceful degradation)."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(return_value="Response")
        mock_service.model_id = "local"

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test input", {})

        assert result["status"] == "completed"
        assert result["response"] == "Response"

    @pytest.mark.asyncio
    async def test_includes_input_length(self):
        """Result should include input_length metadata."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(return_value=True)
        mock_service.chat_completion = AsyncMock(return_value="OK")
        mock_service.model_id = "local"

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("A" * 100, {})

        assert result["input_length"] == 100

    @pytest.mark.asyncio
    async def test_is_available_exception_handled(self):
        """If is_available raises, should treat as unavailable."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm

        mock_service = MagicMock()
        mock_service.is_available = AsyncMock(side_effect=Exception("DNS error"))

        with patch(
            "argumentation_analysis.services.local_llm_service.LocalLLMService",
            return_value=mock_service,
        ):
            result = await _invoke_local_llm("Test", {})

        assert result["status"] == "skipped: endpoint_unavailable"
