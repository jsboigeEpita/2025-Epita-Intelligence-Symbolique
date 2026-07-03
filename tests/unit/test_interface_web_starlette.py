# -*- coding: utf-8 -*-
"""
Unit tests for the Starlette web application (interface_web/app.py).

Tests the frontend proxy mode (issue #844):
- Starlette serves React SPA + proxies /api/* to FastAPI
- No ServiceManager, no NLP, no JVM in Starlette process
- Proxy behavior with mocked httpx.AsyncClient

Previous version (ServiceManager-backed) is superseded by the proxy architecture.
Old tests archived at test_interface_web_starlette_legacy.py (if needed).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

import httpx

# The Starlette app mounts StaticFiles(directory=.../build) at module import
# (interface_web/app.py: app = Starlette(routes=[Mount(app=StaticFiles(...))])).
# The React build is a gitignored npm artifact (CLAUDE.md) not provisioned on
# CI, so importing the app raises "RuntimeError: Directory '...build' does not
# exist" there. Skip the whole module when the build is absent — conditional on
# the artifact, not unconditional (anti-pendule). On a machine WITH the build
# (local dev) all tests run. Tracked in #1362 (real fix = npm step in ci.yml,
# owner decision).
_REPO_ROOT = Path(__file__).resolve()
while _REPO_ROOT.parent != _REPO_ROOT and not (_REPO_ROOT / "pytest.ini").exists():
    _REPO_ROOT = _REPO_ROOT.parent
_BUILD_DIR = (
    _REPO_ROOT / "services" / "web_api" / "interface-web-argumentative" / "build"
)
pytestmark = pytest.mark.skipif(
    not _BUILD_DIR.exists(),
    reason=(
        "React build artifact absent (not in git) — prerequisite: npm run build in "
        "services/web_api/interface-web-argumentative/ (CLAUDE.md). Tracked in #1362."
    ),
)


def _build_test_routes():
    """Build fresh API routes for testing, excluding the StaticFiles mount."""
    from interface_web.app import (
        api_proxy,
        examples_endpoint,
        dashboard_endpoint,
    )

    return [
        Route("/dashboard", endpoint=dashboard_endpoint, methods=["GET"]),
        Route("/api/examples", endpoint=examples_endpoint, methods=["GET"]),
        Route(
            "/api/{path:path}",
            endpoint=api_proxy,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        ),
    ]


def _build_test_middleware():
    """Build fresh middleware list for testing."""
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]


@pytest.fixture
def mock_http_client():
    """Create a mock httpx.AsyncClient for proxy tests."""
    client = AsyncMock(spec=httpx.AsyncClient)

    # Default: return a 200 response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b'{"status": "ok"}'
    mock_response.headers = httpx.Headers({"content-type": "application/json"})

    client.request = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def client(mock_http_client):
    """Create a Starlette TestClient with mocked httpx client."""
    from interface_web.app import api_proxy

    # Rebuild routes with the mocked endpoint
    from interface_web.app import examples_endpoint, dashboard_endpoint

    test_routes = [
        Route("/dashboard", endpoint=dashboard_endpoint, methods=["GET"]),
        Route("/api/examples", endpoint=examples_endpoint, methods=["GET"]),
        Route(
            "/api/{path:path}",
            endpoint=api_proxy,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        ),
    ]

    @asynccontextmanager
    async def test_lifespan(app):
        app.state.http_client = mock_http_client
        yield

    test_app = Starlette(
        debug=True,
        routes=test_routes,
        middleware=_build_test_middleware(),
        lifespan=test_lifespan,
    )
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


# ============================================================
# Structure verification
# ============================================================


class TestProxyStructure:
    """Verify the proxy has no backend coupling."""

    def test_no_service_manager(self):
        import interface_web.app as mod

        assert not hasattr(mod, "ServiceManager")

    def test_no_nlp_model_manager(self):
        import interface_web.app as mod

        assert not hasattr(mod, "nlp_model_manager")

    def test_has_fastapi_base_url(self):
        import interface_web.app as mod

        assert hasattr(mod, "FASTAPI_BASE_URL")
        assert "8095" in mod.FASTAPI_BASE_URL


# ============================================================
# Examples endpoint (local, hardcoded)
# ============================================================


class TestExamplesEndpoint:
    """Tests for /api/examples (local route, not proxied)."""

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
# Proxy behavior
# ============================================================


class TestApiProxy:
    """Tests for the /api/* proxy to FastAPI."""

    def test_proxy_forwards_get(self, client, mock_http_client):
        response = client.get("/api/status")
        assert response.status_code == 200
        mock_http_client.request.assert_awaited()

    def test_proxy_forwards_post(self, client, mock_http_client):
        response = client.post("/api/analyze", json={"text": "Test"})
        assert response.status_code == 200
        mock_http_client.request.assert_awaited()

    def test_proxy_forwards_to_correct_path(self, client, mock_http_client):
        client.get("/api/v1/jtms/sessions")
        call_args = mock_http_client.request.call_args
        assert "/api/v1/jtms/sessions" in call_args[1].get("url", "") or \
               "/api/v1/jtms/sessions" in str(call_args)

    def test_proxy_returns_502_on_connect_error(self, client, mock_http_client):
        mock_http_client.request.side_effect = httpx.ConnectError("Connection refused")
        response = client.get("/api/status")
        assert response.status_code == 502
        assert "indisponible" in response.json()["error"]

    def test_proxy_returns_504_on_timeout(self, client, mock_http_client):
        mock_http_client.request.side_effect = httpx.TimeoutException("Timeout")
        response = client.get("/api/status")
        assert response.status_code == 504


# ============================================================
# Dashboard (local)
# ============================================================


class TestDashboardEndpoint:
    """Tests for /dashboard (local route)."""

    def test_dashboard_returns_html_or_404(self, client):
        response = client.get("/dashboard")
        assert response.status_code in (200, 404)
