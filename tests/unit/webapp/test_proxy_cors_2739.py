"""The frontend proxy uses the backend's explicit browser-origin policy."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / "services" / "web_api" / "interface-web-argumentative" / "build"
pytestmark = pytest.mark.skipif(
    not BUILD.exists(), reason="React build prerequisite absent"
)


def test_proxy_preflight_rejects_foreign_origin_and_accepts_configured_origin():
    from interface_web.app import app

    with TestClient(app) as client:
        headers = {"Access-Control-Request-Method": "POST"}
        foreign = client.options(
            "/api/analyze",
            headers={**headers, "Origin": "https://foreign.example.test"},
        )
        allowed = client.options(
            "/api/analyze",
            headers={**headers, "Origin": "http://localhost:3000"},
        )

    assert foreign.status_code == 400
    assert "access-control-allow-origin" not in foreign.headers
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_proxy_origin_policy_matches_api(monkeypatch):
    from api.factory import allowed_frontend_origins, create_app
    from interface_web.app import app

    configured_origins = next(
        m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    ).kwargs["allow_origins"]
    monkeypatch.setenv("FRONTEND_URL", configured_origins[0])
    api = create_app("test", "origin policy", "1")
    api_cors = next(
        m for m in api.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    proxy_cors = next(
        m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    assert api_cors.kwargs["allow_origins"] == allowed_frontend_origins()
    assert proxy_cors.kwargs["allow_origins"] == allowed_frontend_origins()

    monkeypatch.setenv("FRONTEND_URL", "https://frontend.example.test")
    assert allowed_frontend_origins()[0] == "https://frontend.example.test"


def test_cors_is_not_authentication_for_a_direct_request():
    from interface_web.app import app

    with TestClient(app) as client:
        response = client.get(
            "/api/examples", headers={"Origin": "https://foreign.example.test"}
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
