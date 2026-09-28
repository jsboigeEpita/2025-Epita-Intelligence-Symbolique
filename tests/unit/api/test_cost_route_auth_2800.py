"""Every API POST has an explicit cost classification and billed calls require auth."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.agent_routes import agent_router
from api.endpoints import framework_router, informal_router, router
from api.frontend_endpoints import frontend_router
from api.mobile_endpoints import mobile_router
from api.proposal_endpoints import proposal_router
from api.shield_endpoints import shield_router


@pytest.fixture(autouse=True)
def closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHIELD_ALLOW_ANONYMOUS", raising=False)
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)


ROUTERS = (
    (agent_router, ""),
    (router, "/api"),
    (framework_router, ""),
    (informal_router, ""),
    (frontend_router, "/api"),
    (mobile_router, "/api"),
    (proposal_router, "/api"),
    (shield_router, "/api"),
)


def _app() -> FastAPI:
    app = FastAPI()
    for route, prefix in ROUTERS:
        app.include_router(route, prefix=prefix)
    return app


def _assert_post_cost_policy(app: FastAPI) -> None:
    # OpenAPI includes mounted routes even on FastAPI versions where app.routes
    # omits include_router additions (#1853).
    posts = [
        (path, methods["post"])
        for path, methods in app.openapi()["paths"].items()
        if "post" in methods and not path.startswith("/api/v1/jtms/")
    ]
    assert len(posts) >= 20  # 19 audited POSTs plus the Shield route
    for path, operation in posts:
        local = operation.get("x-cost-class") in {"local", "local-model"}
        token_header = any(
            parameter.get("name") == "X-Shield-Token"
            and parameter.get("in") == "header"
            for parameter in operation.get("parameters", [])
        )
        assert (
            local != token_header
        ), f"Unclassified or contradictory POST route: {path}"


def test_all_post_routes_are_classified_and_cost_routes_are_guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    _assert_post_cost_policy(app)
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "synthetic-token")
    client = TestClient(app, raise_server_exceptions=False)
    for path, methods in app.openapi()["paths"].items():
        if "post" not in methods or path.startswith("/api/v1/jtms/"):
            continue
        if methods["post"].get("x-cost-class") in {"local", "local-model"}:
            continue
        response = client.post(path, json={})
        assert response.status_code == 401, f"Unguarded POST route: {path}"


def test_new_post_without_guard_fails_census() -> None:
    app = _app()

    @app.post("/api/new-billed-route")
    def new_billed_route() -> dict[str, str]:
        return {"status": "synthetic"}

    with pytest.raises(AssertionError, match="new-billed-route"):
        _assert_post_cost_policy(app)


def test_shared_token_policy_and_hot_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.delenv("SHIELD_ALLOW_ANONYMOUS", raising=False)
    client = TestClient(_app(), raise_server_exceptions=False)
    route = "/api/v1/agents/quality"
    assert client.post(route, json={}).status_code == 503
    monkeypatch.setenv("SHIELD_ALLOW_ANONYMOUS", "1")
    # An invalid body must reach validation only after authentication succeeds.
    assert client.post(route, json={}).status_code == 422
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "first-token")
    assert client.post(route, json={}).status_code == 401
    assert (
        client.post(route, json={}, headers={"X-Shield-Token": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            route, json={}, headers={"X-Shield-Token": "first-token"}
        ).status_code
        == 422
    )
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "second-token")
    assert (
        client.post(
            route, json={}, headers={"X-Shield-Token": "first-token"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            route, json={}, headers={"X-Shield-Token": "second-token"}
        ).status_code
        == 422
    )


def test_authorized_fallacy_request_runs_synthetic_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api import frontend_endpoints
    from api.fallacy_detection import FallacyDetectionResponse

    detector = AsyncMock(
        return_value=FallacyDetectionResponse(
            tier="llm",
            fallacies=[],
            fallacy_count=0,
            below_threshold=0,
            processing_time=0.01,
        )
    )
    monkeypatch.setattr(frontend_endpoints, "detect_fallacies", detector)
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "test-token")
    client = TestClient(_app(), raise_server_exceptions=False)
    payload = {"text": "synthetic text"}
    assert client.post("/api/fallacies", json=payload).status_code == 401
    response = client.post(
        "/api/fallacies", json=payload, headers={"X-Shield-Token": "test-token"}
    )
    assert response.status_code == 200
    detector.assert_awaited_once()
