# -*- coding: utf-8 -*-
"""
Unit tests for the Starlette web application (interface_web/app.py).

Tests the API endpoints by creating a Starlette app with a mock lifespan
that injects a mocked ServiceManager, avoiding heavy LLM/JVM initialization.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.testclient import TestClient


@pytest.fixture
def mock_service_manager():
    """Create a mock ServiceManager with standard async methods."""
    sm = AsyncMock()
    sm.analyze_text = AsyncMock(
        return_value={
            "results": {
                "summary": "Test analysis summary",
                "fallacies": [],
                "arguments": ["arg1", "arg2"],
            }
        }
    )
    sm.analyze_dung_framework = AsyncMock(
        return_value={
            "extensions": {"grounded": ["a"], "preferred": [["a", "b"]]},
            "status": "success",
        }
    )
    return sm


@pytest.fixture
def client(mock_service_manager):
    """Create a Starlette TestClient with mocked ServiceManager."""
    # Import routes and middleware from the real app
    from interface_web.app import routes, middleware

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.service_manager = mock_service_manager
        app.state.nlp_model_manager = None
        yield

    test_app = Starlette(
        debug=True, routes=routes, middleware=middleware, lifespan=test_lifespan
    )
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


# ============================================================
# Health / Status endpoints
# ============================================================


class TestStatusEndpoints:
    """Tests for /api/status and /api/health."""

    def test_status_returns_200(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_status_has_expected_fields(self, client):
        data = client.get("/api/status").json()
        assert "status" in data
        assert "services" in data
        assert "webapp" in data
        assert data["webapp"]["framework"] == "Starlette"

    def test_status_service_manager_active(self, client):
        data = client.get("/api/status").json()
        assert data["services"]["service_manager"] == "active"

    def test_health_alias_works(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# ============================================================
# Examples endpoint
# ============================================================


class TestExamplesEndpoint:
    """Tests for /api/examples."""

    def test_examples_returns_200(self, client):
        response = client.get("/api/examples")
        assert response.status_code == 200

    def test_examples_returns_list(self, client):
        data = client.get("/api/examples").json()
        assert "examples" in data
        assert isinstance(data["examples"], list)
        assert len(data["examples"]) > 0

    def test_examples_have_required_fields(self, client):
        examples = client.get("/api/examples").json()["examples"]
        for ex in examples:
            assert "title" in ex
            assert "text" in ex
            assert "type" in ex


# ============================================================
# Analyze endpoint
# ============================================================


class TestAnalyzeEndpoint:
    """Tests for POST /api/analyze."""

    def test_analyze_success(self, client, mock_service_manager):
        response = client.post("/api/analyze", json={"text": "Test argument text"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "analysis_id" in data
        assert "results" in data
        mock_service_manager.analyze_text.assert_awaited_once()

    def test_analyze_empty_text_returns_400(self, client):
        response = client.post("/api/analyze", json={"text": ""})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_analyze_text_too_long_returns_400(self, client):
        response = client.post("/api/analyze", json={"text": "x" * 10001})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_analyze_invalid_json_returns_400(self, client):
        response = client.post(
            "/api/analyze",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400

    def test_analyze_with_analysis_type(self, client, mock_service_manager):
        response = client.post(
            "/api/analyze",
            json={"text": "Some text", "analysis_type": "fallacy_detection"},
        )
        assert response.status_code == 200
        call_args = mock_service_manager.analyze_text.call_args
        assert call_args[0][1] == "fallacy_detection"

    def test_analyze_metadata_has_duration(self, client):
        response = client.post("/api/analyze", json={"text": "Test"})
        data = response.json()
        assert "metadata" in data
        assert "duration" in data["metadata"]


# ============================================================
# Framework analyze endpoint
# ============================================================


class TestFrameworkAnalyzeEndpoint:
    """Tests for POST /api/v1/framework/analyze."""

    def test_framework_analyze_success(self, client, mock_service_manager):
        response = client.post(
            "/api/v1/framework/analyze",
            json={
                "arguments": ["a", "b", "c"],
                "attacks": [["a", "b"], ["b", "c"]],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "extensions" in data
        mock_service_manager.analyze_dung_framework.assert_awaited_once()

    def test_framework_analyze_missing_arguments(self, client):
        response = client.post(
            "/api/v1/framework/analyze",
            json={"attacks": [["a", "b"]]},
        )
        assert response.status_code == 400

    def test_framework_analyze_invalid_types(self, client):
        response = client.post(
            "/api/v1/framework/analyze",
            json={"arguments": "not a list", "attacks": [["a", "b"]]},
        )
        assert response.status_code == 400


# ============================================================
# ServiceManager unavailable scenario
# ============================================================


class TestServiceManagerUnavailable:
    """Tests for graceful degradation when ServiceManager is None."""

    @pytest.fixture
    def client_no_sm(self):
        from interface_web.app import routes, middleware

        @asynccontextmanager
        async def test_lifespan(app):
            app.state.service_manager = None
            app.state.nlp_model_manager = None
            yield

        test_app = Starlette(
            debug=True, routes=routes, middleware=middleware, lifespan=test_lifespan
        )
        with TestClient(test_app, raise_server_exceptions=False) as c:
            yield c

    def test_status_shows_degraded(self, client_no_sm):
        data = client_no_sm.get("/api/status").json()
        assert data["services"]["service_manager"] == "unavailable"

    def test_analyze_returns_503(self, client_no_sm):
        response = client_no_sm.post(
            "/api/analyze", json={"text": "Test text"}
        )
        assert response.status_code == 503
        assert "indisponible" in response.json()["error"]
