"""Every API POST has an explicit cost classification and billed calls require auth.

#2820 (1): the census reads the routes of the app ``api.main`` actually
serves. It previously rebuilt a twin app from a hand-written ROUTERS tuple
that mirrored ``api/main.py``'s include_router calls — a new router added
to main.py and not to the tuple escaped the census silently. Reading the
served app via ``app.openapi()["paths"]`` (the surface #1853 established as
reliable where ``app.routes`` under-reports) makes drift impossible: a new
router IS in the census the moment it is included.

The empty route list once observed in a gate session was not reproducible
on the gate stack (fastapi 0.135.2 measured: 56 routes, 48 openapi paths at
import) — the instrument, not the app, was the problem.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api import auth
from api.main import app as MAIN_APP


@pytest.fixture(autouse=True)
def closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHIELD_ALLOW_ANONYMOUS", raising=False)
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1000")
    monkeypatch.setattr(auth, "_budget_used", 0)


def _assert_post_cost_policy(app) -> None:
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


def test_census_reads_the_served_app_not_a_twin() -> None:
    """The census target IS api.main's app — the ROUTERS twin is gone (#2820)."""
    assert MAIN_APP.title == "Argumentation Analysis API"
    assert len(MAIN_APP.openapi()["paths"]) >= 40


def test_all_post_routes_are_classified_and_cost_routes_are_guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_post_cost_policy(MAIN_APP)
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "synthetic-token")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    for path, methods in MAIN_APP.openapi()["paths"].items():
        if "post" not in methods or path.startswith("/api/v1/jtms/"):
            continue
        if methods["post"].get("x-cost-class") in {"local", "local-model"}:
            continue
        response = client.post(path, json={})
        assert response.status_code == 401, f"Unguarded POST route: {path}"
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1")
    monkeypatch.setattr(auth, "_budget_used", 1)
    for path, methods in MAIN_APP.openapi()["paths"].items():
        if "post" not in methods or path.startswith("/api/v1/jtms/"):
            continue
        if methods["post"].get("x-cost-class") in {"local", "local-model"}:
            continue
        response = client.post(
            path, json={}, headers={"X-Shield-Token": "synthetic-token"}
        )
        assert response.status_code == 429, f"Unbudgeted POST route: {path}"


def test_new_post_without_guard_fails_census() -> None:
    """A router included by main.py IS censused — prove the census reddens.

    Adds a synthetic unguarded POST to the served app itself (the drift the
    old twin could not see) and resets the app's cached OpenAPI schema.
    """
    route = MAIN_APP.router.routes[-1]

    @MAIN_APP.post("/api/new-billed-route")
    def new_billed_route() -> dict[str, str]:
        return {"status": "synthetic"}

    added = MAIN_APP.router.routes[-1]
    MAIN_APP.openapi_schema = None
    try:
        with pytest.raises(AssertionError, match="new-billed-route"):
            _assert_post_cost_policy(MAIN_APP)
    finally:
        MAIN_APP.router.routes.remove(added)
        assert MAIN_APP.router.routes[-1] is route
        MAIN_APP.openapi_schema = None


def test_shared_token_policy_and_hot_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.delenv("SHIELD_ALLOW_ANONYMOUS", raising=False)
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
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


def test_billed_budget_rejects_after_limit_without_invoking_service(
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
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    headers = {"X-Shield-Token": "test-token"}
    assert (
        client.post(
            "/api/fallacies", json={"text": "synthetic"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/fallacies", json={"text": "synthetic"}, headers=headers
        ).status_code
        == 429
    )
    detector.assert_awaited_once()
    assert client.post("/api/fallacies", json={"text": "synthetic"}).status_code == 401
    assert auth._budget_used == 1


def test_invalid_budget_refuses_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "test-token")
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "not-a-number")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/agents/quality", json={}, headers={"X-Shield-Token": "test-token"}
    )
    assert response.status_code == 503
    assert "BILLED_REQUEST_BUDGET" in response.json()["detail"]
    assert auth._budget_used == 0


def test_local_route_does_not_consume_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "test-token")
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    headers = {"X-Shield-Token": "test-token"}
    # A local route's 422 has no reserved unit to release (#2820)...
    assert (
        client.post("/api/v1/framework/analyze", json={}, headers=headers).status_code
        == 422
    )
    assert auth._budget_used == 0
    # ...and a billed route's 422 releases the unit it reserved — only an
    # ACCEPTED request keeps it (the concurrency pin lives in
    # test_budget_refund_2820.py).
    assert (
        client.post("/api/v1/agents/quality", json={}, headers=headers).status_code
        == 422
    )
    assert auth._budget_used == 0


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
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    payload = {"text": "synthetic text"}
    assert client.post("/api/fallacies", json=payload).status_code == 401
    response = client.post(
        "/api/fallacies", json=payload, headers={"X-Shield-Token": "test-token"}
    )
    assert response.status_code == 200
    detector.assert_awaited_once()
