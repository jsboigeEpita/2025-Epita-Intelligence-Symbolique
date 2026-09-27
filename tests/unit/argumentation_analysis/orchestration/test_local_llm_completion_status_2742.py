"""A healthy model listing cannot hide a failed local completion (#2742)."""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import _invoke_local_llm


@pytest.mark.parametrize("completion_fails", [True, False])
async def test_local_completion_status_follows_the_completion(completion_fails):
    requests = []

    async def respond(request):
        requests.append(request.url.path)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "synthetic-model"}]})
        assert request.url.path.endswith("/chat/completions")
        if completion_fails:
            return httpx.Response(503, json={"error": "synthetic service unavailable"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "synthetic response"}}]},
        )

    real_client = httpx.AsyncClient

    def local_client(*args, **kwargs):
        return real_client(transport=httpx.MockTransport(respond), **kwargs)

    state = UnifiedAnalysisState("synthetic input")
    with patch("httpx.AsyncClient", side_effect=local_client):
        result = await _invoke_local_llm("synthetic input", {"_state_object": state})

    assert requests == ["/v1/models", "/v1/chat/completions"]
    assert state.local_llm_results == [result]
    assert len(state.analysis_trace) == 1
    trace = state.analysis_trace[0]
    assert trace["phase"] == "local_llm"
    if completion_fails:
        assert result["status"] == "error"
        assert "503" in result["error"]
        assert "error" in trace["summary"]
        assert "503" in trace["summary"]
        assert "response" not in result
    else:
        assert result["status"] == "completed"
        assert "synthetic response" in result["response"]
        assert "completed" in trace["summary"]


async def test_raised_completion_failure_is_traced():
    service = MagicMock()
    service.is_available = AsyncMock(return_value=True)
    service.chat_completion = AsyncMock(side_effect=RuntimeError("synthetic failure"))
    state = UnifiedAnalysisState("synthetic input")

    with patch(
        "argumentation_analysis.services.local_llm_service.LocalLLMService",
        return_value=service,
    ):
        result = await _invoke_local_llm("synthetic input", {"_state_object": state})

    assert result == {"status": "error", "error": "synthetic failure"}
    assert state.local_llm_results == [result]
    assert len(state.analysis_trace) == 1
    assert "synthetic failure" in state.analysis_trace[0]["summary"]
