"""Tests for the mobile API endpoints.

Validates:
- POST /api/mobile/analyze — argument analysis
- POST /api/mobile/fallacies — fallacy detection
- POST /api/mobile/validate — logical validation
- POST /api/mobile/chat — chat assistant
- Input validation (text too short)
- Error handling with specific assertions (no broad try/except masking)
- Response contracts match TypeScript frontend types

Fixes #848: Tests use specific assertions and fail on real bugs.
Fixes #846: Tests verify create_llm_service is called with service_id.
Fixes #847: Tests verify Toulmin fields are serialized as strings.

Note: These tests construct a standalone FastAPI app with just the mobile
router (avoids torch DLL crash from api.main import chain on Windows).
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.mobile_endpoints import mobile_router


@pytest.fixture
def app():
    """Create a minimal FastAPI app with just the mobile router."""
    _app = FastAPI()
    _app.include_router(mobile_router, prefix="/api")
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ──── Analyze Endpoint ────


class TestMobileAnalyze:
    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_analyze_returns_200_with_pipeline(self, mock_run, client):
        mock_run.return_value = {
            "identified_arguments": {"arg1": "Main argument about climate"},
            "identified_fallacies": {},
            "overall_quality": 0.8,
            "summary": "Analysis complete",
        }
        resp = client.post(
            "/api/mobile/analyze",
            json={"text": "Climate change is real because scientists agree."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Climate change is real because scientists agree."
        assert len(data["arguments"]) >= 1
        assert data["arguments"][0]["id"] == "arg1"
        assert data["overall_quality"] == 0.8

    def test_analyze_validation_short_text(self, client):
        resp = client.post("/api/mobile/analyze", json={"text": "hi"})
        assert resp.status_code == 422  # text too short (min 5)

    @patch(
        "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
        side_effect=RuntimeError("Pipeline down"),
    )
    def test_analyze_handles_pipeline_failure(self, mock_run, client):
        resp = client.post(
            "/api/mobile/analyze",
            json={"text": "Test fallback when pipeline fails"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Specific: quality should be 0.0 on failure (#848)
        assert data["overall_quality"] == 0.0
        # Specific: error argument should be present
        assert any(
            "error" in arg["id"].lower() or "unavailable" in arg["text"].lower()
            for arg in data["arguments"]
        )


# ──── Fallacies Endpoint ────


class TestMobileFallacies:
    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_fallacies_with_results(self, mock_run, client):
        mock_run.return_value = {
            "identified_fallacies": {
                "f1": {"type": "ad_populum", "justification": "Appeal to majority"}
            }
        }
        resp = client.post(
            "/api/mobile/fallacies",
            json={"text": "Everyone agrees so it must be true."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["fallacies"]) == 1
        assert data["fallacies"][0]["type"] == "ad_populum"

    @patch(
        "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
        side_effect=RuntimeError("Pipeline error"),
    )
    def test_fallacies_handles_failure(self, mock_run, client):
        resp = client.post(
            "/api/mobile/fallacies",
            json={"text": "Test fallacy detection failure handling"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Specific: fallacies should be empty list, not None (#848)
        assert isinstance(data["fallacies"], list)
        assert len(data["fallacies"]) == 0
        assert data["execution_time"] >= 0


# ──── Validate Endpoint ────


class TestMobileValidate:
    def test_validate_short_text_rejected(self, client):
        resp = client.post("/api/mobile/validate", json={"text": "hi"})
        assert resp.status_code == 422

    @patch(
        "argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer.SemanticArgumentAnalyzer.run"
    )
    def test_validate_toulmin_fields_are_strings(self, mock_run, client):
        """Validate endpoint must return Toulmin fields as strings (#847)."""
        from argumentation_analysis.core.models.toulmin_model import (
            ToulminAnalysisResult,
            ToulminComponent,
        )

        mock_run.return_value = ToulminAnalysisResult(
            claim=ToulminComponent(text="The road is wet", confidence_score=0.9, source_sentences=[0]),
            data=[
                ToulminComponent(text="It rains", confidence_score=0.8, source_sentences=[0]),
                ToulminComponent(text="Rain causes wetness", confidence_score=0.7, source_sentences=[0]),
            ],
            warrant=ToulminComponent(text="Rain causes wet roads", confidence_score=0.85, source_sentences=[0]),
            qualifier=ToulminComponent(text="certainly", confidence_score=0.9, source_sentences=[0]),
        )

        resp = client.post(
            "/api/mobile/validate",
            json={"text": "If it rains then the road is wet. It rains. Therefore the road is wet."},
        )
        assert resp.status_code == 200
        data = resp.json()
        form = data["formalization"]

        # #847: all fields must be strings per mobile contract
        assert isinstance(form["conclusion"], str), f"conclusion should be str, got {type(form['conclusion'])}"
        assert form["conclusion"] == "The road is wet"
        assert isinstance(form["rule"], str), f"rule should be str, got {type(form['rule'])}"
        assert form["rule"] == "Rain causes wet roads"
        assert isinstance(data["explanation"], str), f"explanation should be str, got {type(data['explanation'])}"
        assert data["explanation"] == "certainly"
        # Premises must be a list of strings
        assert isinstance(form["premises"], list)
        for p in form["premises"]:
            assert isinstance(p, str), f"premise should be str, got {type(p)}: {p}"
        assert form["premises"] == ["It rains", "Rain causes wetness"]

    @patch(
        "argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer.SemanticArgumentAnalyzer.run",
        side_effect=RuntimeError("Analyzer error"),
    )
    def test_validate_handles_failure(self, mock_run, client):
        resp = client.post(
            "/api/mobile/validate",
            json={"text": "Test validation failure handling."},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Specific: valid should be False on failure
        assert data["valid"] is False


# ──── Chat Endpoint ────


class TestMobileChat:
    def test_chat_empty_message_rejected(self, client):
        resp = client.post("/api/mobile/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message(self, client):
        resp = client.post("/api/mobile/chat", json={})
        assert resp.status_code == 422

    @patch("argumentation_analysis.core.llm_service.create_llm_service")
    def test_chat_calls_create_llm_service_with_service_id(self, mock_create, client):
        """create_llm_service must be called with service_id parameter (#846)."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="A fallacy is a flaw in reasoning.")
        mock_create.return_value = mock_llm

        resp = client.post(
            "/api/mobile/chat",
            json={"message": "What is a logical fallacy?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "timestamp" in data
        # #846: verify create_llm_service was called with service_id
        mock_create.assert_called_once_with(service_id="mobile_chat")

    @patch("argumentation_analysis.core.llm_service.create_llm_service", return_value=None)
    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_chat_fallback_when_llm_unavailable(self, mock_pipeline, mock_create, client):
        """When LLM service is None, falls back to pipeline."""
        mock_pipeline.return_value = {
            "summary": "Analysis result from pipeline fallback",
        }
        resp = client.post(
            "/api/mobile/chat",
            json={"message": "Tell me about fallacies"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert len(data["message"]) > 0


# ──── Response Contract ────


class TestResponseContract:
    """Verify response shapes match the mobile app's TypeScript types."""

    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_analyze_response_shape(self, mock_run, client):
        mock_run.return_value = {
            "identified_arguments": {"arg1": "Test argument"},
            "identified_fallacies": {},
            "summary": "Done",
        }
        data = client.post(
            "/api/mobile/analyze",
            json={"text": "Test the response contract shape"},
        ).json()

        # Specific type assertions
        assert isinstance(data["text"], str)
        assert isinstance(data["arguments"], list)
        assert isinstance(data["overall_quality"], (int, float))
        if data["arguments"]:
            arg = data["arguments"][0]
            assert isinstance(arg["id"], str)
            assert isinstance(arg["text"], str)

    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_fallacy_response_shape(self, mock_run, client):
        mock_run.return_value = {
            "identified_fallacies": {
                "f1": {"type": "straw_man", "justification": "Misrepresentation"}
            }
        }
        data = client.post(
            "/api/mobile/fallacies",
            json={"text": "Test the fallacy response shape"},
        ).json()

        # Specific type assertions
        assert isinstance(data["text"], str)
        assert isinstance(data["fallacies"], list)
        assert isinstance(data["execution_time"], (int, float))
        if data["fallacies"]:
            f = data["fallacies"][0]
            assert isinstance(f["type"], str)
            assert isinstance(f["confidence"], (int, float))
            assert isinstance(f["explanation"], str)
