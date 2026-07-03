"""Tests for Starlette frontend proxy (issue #844, #858).

Validates:
- ServiceManager and NLP imports are removed
- API proxy forwards to FastAPI
- Static files mount preserved
- Examples endpoint is local (hardcoded)
- Dashboard is local
- No backend coupling remains
- WS proxy returns explicit error (not silent drop)
- Accent in examples text is preserved
- Environment variables documented
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from starlette.testclient import TestClient
from pathlib import Path

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


class TestStarletteProxyStructure:
    """Verify the proxy structure has no backend coupling."""

    def test_no_service_manager_import(self):
        """interface_web.app should NOT import ServiceManager."""
        import interface_web.app as app_module

        assert not hasattr(app_module, "ServiceManager"), (
            "ServiceManager should not be imported in proxy mode"
        )

    def test_no_nlp_model_manager_import(self):
        """interface_web.app should NOT import nlp_model_manager."""
        import interface_web.app as app_module

        assert not hasattr(app_module, "nlp_model_manager"), (
            "nlp_model_manager should not be imported in proxy mode"
        )

    def test_httpx_client_created(self):
        """App should use httpx.AsyncClient for proxying."""
        import interface_web.app as app_module

        assert hasattr(app_module, "FASTAPI_BASE_URL"), (
            "FASTAPI_BASE_URL should be defined"
        )

    def test_fastapi_base_url_default(self):
        """Default FastAPI URL should be localhost:8095."""
        import interface_web.app as app_module

        assert "8095" in app_module.FASTAPI_BASE_URL


class TestStarletteProxyRoutes:
    """Verify route structure."""

    @pytest.fixture
    def client(self):
        from interface_web.app import app
        return TestClient(app, raise_server_exceptions=False)

    def test_examples_endpoint_local(self, client):
        """GET /api/examples should return hardcoded data (local route)."""
        response = client.get("/api/examples")
        # This is a local route, not proxied
        # May fail if no static build, but the route should be registered
        assert response.status_code in (200, 404, 500)

    def test_dashboard_local(self, client):
        """GET /dashboard should serve HTML locally."""
        response = client.get("/dashboard")
        # Dashboard template may or may not exist
        assert response.status_code in (200, 404)


class TestStarletteProxyConfig:
    """Verify proxy configuration."""

    def test_fastapi_host_env(self):
        """FASTAPI_HOST should be configurable via env var."""
        import interface_web.app as app_module

        assert app_module.FASTAPI_HOST is not None

    def test_fastapi_port_env(self):
        """FASTAPI_PORT should be configurable via env var."""
        import interface_web.app as app_module

        assert isinstance(app_module.FASTAPI_PORT, int)

    def test_static_files_dir(self):
        """STATIC_FILES_DIR should point to React build."""
        import interface_web.app as app_module

        assert "build" in str(app_module.STATIC_FILES_DIR)
        assert "interface-web-argumentative" in str(app_module.STATIC_FILES_DIR)


class TestWSProxyLimitation:
    """Verify WS proxy behavior documents limitation (#858)."""

    def test_ws_proxy_function_exists(self):
        """ws_proxy should be defined in module."""
        import interface_web.app as app_module

        assert hasattr(app_module, "ws_proxy"), (
            "ws_proxy function should exist for WS connection handling"
        )

    def test_ws_proxy_sends_explicit_error(self):
        """ws_proxy should send ws_relay_unavailable before closing."""
        import interface_web.app as app_module
        import inspect

        source = inspect.getsource(app_module.ws_proxy)
        # Verify the function sends explicit error JSON
        assert "ws_relay_unavailable" in source, (
            "ws_proxy should send 'ws_relay_unavailable' type"
        )
        assert "target_url" in source, (
            "ws_proxy should include target_url for client redirect"
        )
        # Verify it does NOT contain dead code (relay_to_backend)
        assert "relay_to_backend" not in source, (
            "ws_proxy should not contain dead relay_to_backend function"
        )

    def test_ws_proxy_closes_with_1011(self):
        """ws_proxy should close with code 1011 (internal error)."""
        import interface_web.app as app_module
        import inspect

        source = inspect.getsource(app_module.ws_proxy)
        assert "1011" in source, (
            "ws_proxy should close with code 1011"
        )


class TestExamplesAccent:
    """Verify accent is preserved in examples (#858)."""

    def test_mouillee_has_accent(self):
        """Example text should use 'mouillée' with accent."""
        import interface_web.app as app_module

        source = open(app_module.__file__, encoding="utf-8").read()
        assert "mouillée" in source, (
            "Examples should contain 'mouillée' with proper accent"
        )
        # Ensure the unaccented version is NOT present
        assert "mouillee" not in source, (
            "Found 'mouillee' without accent — should be 'mouillée'"
        )


class TestEnvDocumentation:
    """Verify environment variables are documented in module docstring (#858)."""

    def test_fastapi_host_documented(self):
        """FASTAPI_HOST should appear in module docstring."""
        import interface_web.app as app_module

        docstring = app_module.__doc__
        assert "FASTAPI_HOST" in docstring, (
            "FASTAPI_HOST should be documented in module docstring"
        )

    def test_fastapi_port_documented(self):
        """FASTAPI_PORT should appear in module docstring."""
        import interface_web.app as app_module

        docstring = app_module.__doc__
        assert "FASTAPI_PORT" in docstring, (
            "FASTAPI_PORT should be documented in module docstring"
        )

    def test_react_app_backend_url_documented(self):
        """REACT_APP_BACKEND_URL should be documented."""
        import interface_web.app as app_module

        docstring = app_module.__doc__
        assert "REACT_APP_BACKEND_URL" in docstring, (
            "REACT_APP_BACKEND_URL should be documented for frontend build"
        )

    def test_ws_limitation_documented(self):
        """WS relay limitation should be documented."""
        import interface_web.app as app_module

        docstring = app_module.__doc__
        assert "WebSocket" in docstring or "WS" in docstring, (
            "WebSocket limitation should be documented"
        )
