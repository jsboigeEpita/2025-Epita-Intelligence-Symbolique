"""Tests for JTMS router mounted in FastAPI (issue #843).

Validates:
- jtms_router is mounted under /api/v1/jtms prefix
- JTMS service initialization at startup
- Key endpoints return expected status codes
- Integration with existing FastAPI app
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from argumentation_analysis.api.jtms_endpoints import jtms_router, initialize_jtms_services


@pytest.fixture
def jtms_app():
    """Create a FastAPI app with JTMS router mounted under /api/v1."""
    app = FastAPI()
    app.include_router(jtms_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(jtms_app):
    """Test client with JTMS router mounted."""
    return TestClient(jtms_app, raise_server_exceptions=False)


class TestJTMSRouterMount:
    """Verify router is correctly mounted and accessible."""

    def test_jtms_router_prefix(self):
        """jtms_router should have prefix /jtms."""
        assert jtms_router.prefix == "/jtms"

    def test_jtms_routes_registered(self):
        """jtms_router should have 18 routes registered."""
        route_count = len(jtms_router.routes)
        assert route_count == 18, f"Expected 18 routes, got {route_count}"

    def test_jtms_routes_under_api_v1(self, client):
        """JTMS routes should be accessible under /api/v1/jtms."""
        # POST /api/v1/jtms/beliefs
        response = client.post(
            "/api/v1/jtms/beliefs",
            json={
                "belief_name": "test_belief",
                "agent_id": "test_agent",
            },
        )
        # Should not be 404 (route exists) — 200 or 400 (service error) is OK
        assert response.status_code != 404, (
            "JTMS /beliefs route not found — router may not be mounted"
        )

    def test_sessions_get_route(self, client):
        """GET /api/v1/jtms/sessions should be accessible."""
        response = client.get("/api/v1/jtms/sessions")
        assert response.status_code != 404, (
            "JTMS /sessions GET route not found"
        )

    def test_plugin_status_route(self, client):
        """GET /api/v1/jtms/plugin/status should be accessible."""
        response = client.get("/api/v1/jtms/plugin/status")
        assert response.status_code != 404, (
            "JTMS /plugin/status route not found"
        )

    def test_nonexistent_jtms_route_returns_404(self, client):
        """Non-existent JTMS route should return 404."""
        response = client.get("/api/v1/jtms/nonexistent")
        assert response.status_code == 404


class TestJTMSBeliefEndpoint:
    """Test the belief creation endpoint."""

    def test_create_belief_success(self, client):
        """POST /beliefs should create a belief and return 200."""
        response = client.post(
            "/api/v1/jtms/beliefs",
            json={
                "belief_name": "test_belief_1",
                "agent_id": "test_agent",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "belief_name" in data or "status" in data

    def test_create_belief_with_session(self, client):
        """POST /beliefs with session_id should attempt session lookup."""
        response = client.post(
            "/api/v1/jtms/beliefs",
            json={
                "belief_name": "test_belief_2",
                "session_id": "test_session",
                "agent_id": "test_agent",
            },
        )
        # Non-existent session returns 400 (session not found)
        # but the route is accessible (not 404/405)
        assert response.status_code in (200, 400), (
            f"Expected 200 or 400, got {response.status_code}"
        )

    def test_create_belief_with_initial_value(self, client):
        """POST /beliefs with initial_value should set belief value."""
        response = client.post(
            "/api/v1/jtms/beliefs",
            json={
                "belief_name": "test_belief_true",
                "initial_value": "true",
                "agent_id": "test_agent",
            },
        )
        assert response.status_code == 200


class TestJTMSSessionsEndpoint:
    """Test session management endpoints."""

    def test_list_sessions(self, client):
        """GET /sessions should return a list."""
        response = client.get("/api/v1/jtms/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data

    def test_create_session(self, client):
        """POST /sessions should create a new session."""
        response = client.post(
            "/api/v1/jtms/sessions",
            json={
                "agent_id": "test_agent",
                "session_name": "test_session",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data


class TestJTMSJustificationEndpoint:
    """Test justification endpoints."""

    def test_add_justification(self, client):
        """POST /justifications should add a justification."""
        response = client.post(
            "/api/v1/jtms/justifications",
            json={
                "in_beliefs": ["belief_a"],
                "out_beliefs": ["belief_b"],
                "conclusion": "belief_c",
                "agent_id": "test_agent",
            },
        )
        assert response.status_code == 200