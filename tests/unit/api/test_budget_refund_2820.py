"""#2820 (2) — the budget counts ACCEPTED requests, not authenticated ones.

``require_billed_request`` reserves a unit after the token check but BEFORE
FastAPI validates the body: a valid token with an invalid body answers 422
having spent one unit. A token-holder could exhaust ``BILLED_REQUEST_BUDGET``
with malformed bodies alone — requests that cost nothing (the service is
never invoked). DEPLOYMENT.md sells the limit as "accepted cost-bearing
requests" (#2820); this file pins that meaning: the unit is released when
the request is rejected by validation.

Exercised on the real served app (``api.main.app``), service doubled — no
LLM, no network.
"""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api import auth, frontend_endpoints
from api.fallacy_detection import FallacyDetectionResponse
from api.main import app as MAIN_APP


@pytest.fixture(autouse=True)
def closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHIELD_ALLOW_ANONYMOUS", raising=False)
    monkeypatch.delenv("SHIELD_ENDPOINT_TOKEN", raising=False)
    monkeypatch.setenv("SHIELD_ENDPOINT_TOKEN", "test-token")
    monkeypatch.setattr(auth, "_budget_used", 0)


@pytest.fixture
def detector(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
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
    return detector


HEADERS = {"X-Shield-Token": "test-token"}


def test_validation_rejected_request_releases_its_unit(
    monkeypatch: pytest.MonkeyPatch, detector: AsyncMock
) -> None:
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    rejected = client.post("/api/fallacies", json={}, headers=HEADERS)
    assert rejected.status_code == 422
    assert auth._budget_used == 0, (
        "#2820: a request rejected by body validation kept its reserved "
        "unit — the budget counts authenticated requests, not accepted ones"
    )
    accepted = client.post(
        "/api/fallacies", json={"text": "synthetic"}, headers=HEADERS
    )
    assert (
        accepted.status_code == 200
    ), "the released unit must be reusable by the next valid request"
    detector.assert_awaited_once()
    assert auth._budget_used == 1


def test_local_route_validation_error_never_touches_the_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local (unbilled) route's 422 has no reserved unit to release."""
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "1")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)
    assert (
        client.post("/api/v1/framework/analyze", json={}, headers=HEADERS).status_code
        == 422
    )
    assert auth._budget_used == 0


def test_concurrent_accepted_requests_are_atomic(
    monkeypatch: pytest.MonkeyPatch, detector: AsyncMock
) -> None:
    """8 concurrent VALID requests under budget 3: exactly 3 accepted.

    The old pin (3 x 422 = 3 units) was the #2820 defect itself; atomicity
    is now pinned on accepted requests — the reserve is kept on success.
    """
    monkeypatch.setenv("BILLED_REQUEST_BUDGET", "3")
    client = TestClient(MAIN_APP, raise_server_exceptions=False)

    def attempt(_: int) -> int:
        return client.post(
            "/api/fallacies", json={"text": "synthetic"}, headers=HEADERS
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(attempt, range(8)))
    assert statuses.count(200) == 3
    assert statuses.count(429) == 5
    assert auth._budget_used == 3
