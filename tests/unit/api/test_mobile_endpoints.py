"""Tests for the mobile API endpoints.

Validates:
- POST /api/mobile/analyze — argument analysis
- POST /api/mobile/fallacies — fallacy detection
- POST /api/mobile/validate — logical validation
- POST /api/mobile/chat — chat assistant
- Input validation (text too short)
- Graceful error handling when pipeline unavailable
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ──── Analyze Endpoint ────


class TestMobileAnalyze:
    def test_analyze_returns_200(self, client):
        resp = client.post(
            "/api/mobile/analyze",
            json={"text": "All men are mortal. Socrates is a man. Therefore Socrates is mortal."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "arguments" in data
        assert "overall_quality" in data

    def test_analyze_validation_short_text(self, client):
        resp = client.post("/api/mobile/analyze", json={"text": "hi"})
        assert resp.status_code == 422  # text too short (min 5)

    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_analyze_with_pipeline_results(self, mock_run, client):
        mock_run.return_value = {
            "identified_arguments": {"arg1": "Main argument about climate change"},
            "identified_fallacies": {},
            "overall_quality": 0.8,
            "summary": "Argument analysis complete",
        }
        resp = client.post(
            "/api/mobile/analyze",
            json={"text": "Climate change is real because scientists agree."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["arguments"]) >= 1
        assert data["overall_quality"] == 0.8

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
        assert data["overall_quality"] == 0.0
        assert any("error" in arg["id"].lower() or "unavailable" in arg["text"].lower()
                    for arg in data["arguments"])


# ──── Fallacies Endpoint ────


class TestMobileFallacies:
    def test_fallacies_returns_200(self, client):
        resp = client.post(
            "/api/mobile/fallacies",
            json={"text": "Everyone agrees with me, so I must be right."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "fallacies" in data
        assert "execution_time" in data

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
        assert data["fallacies"] == []
        assert data["execution_time"] >= 0


# ──── Validate Endpoint ────


class TestMobileValidate:
    def test_validate_returns_200(self, client):
        resp = client.post(
            "/api/mobile/validate",
            json={"text": "If it rains then the road is wet. It rains. Therefore the road is wet."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data
        assert "formalization" in data
        assert "explanation" in data

    def test_validate_short_text_rejected(self, client):
        resp = client.post("/api/mobile/validate", json={"text": "hi"})
        assert resp.status_code == 422


# ──── Chat Endpoint ────


class TestMobileChat:
    def test_chat_returns_200(self, client):
        resp = client.post(
            "/api/mobile/chat",
            json={"message": "What is a logical fallacy?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "timestamp" in data
        assert len(data["message"]) > 0

    def test_chat_empty_message_rejected(self, client):
        resp = client.post("/api/mobile/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message(self, client):
        resp = client.post("/api/mobile/chat", json={})
        assert resp.status_code == 422


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

        assert isinstance(data["text"], str)
        assert isinstance(data["arguments"], list)
        assert isinstance(data["overall_quality"], (int, float))
        if data["arguments"]:
            arg = data["arguments"][0]
            assert "id" in arg
            assert "text" in arg

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

        assert isinstance(data["text"], str)
        assert isinstance(data["fallacies"], list)
        assert isinstance(data["execution_time"], (int, float))
        if data["fallacies"]:
            f = data["fallacies"][0]
            assert "type" in f
            assert "confidence" in f
            assert "explanation" in f
