# -*- coding: utf-8 -*-
"""#2526: the routes the frontend calls, on the services that compute them.

``/api/validate`` runs the real ``ValidationService``: it scores the argument by
heuristics and reads nothing from its ``LogicService`` but ``is_healthy``, so a
healthy stand-in replaces the LLM-backed one. ``/api/logic/belief-set`` needs an
LLM; here it runs on a stand-in service, which checks the route's wiring and its
status codes, not the conversion.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import frontend_endpoints
from api.frontend_endpoints import frontend_router, get_logic_service
from argumentation_analysis.services.web_api.models.response_models import (
    LogicBeliefSet,
    LogicBeliefSetResponse,
)

SYLLOGISM = {
    "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
    "conclusion": "Donc Socrate est mortel",
    "argument_type": "deductive",
}


class _HealthyLogic:
    def is_healthy(self):
        return True


class _BeliefSets:
    def __init__(self, error=None):
        self.error = error
        self.requests = []

    async def text_to_belief_set(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return LogicBeliefSetResponse(
            success=True,
            belief_set=LogicBeliefSet(
                id="bs-1",
                logic_type=request.logic_type,
                content="rains => wet\nrains",
                source_text=request.text,
            ),
            processing_time=0.0,
        )


@pytest.fixture
def app(monkeypatch):
    # The services are module-level singletons: start each test without them.
    monkeypatch.setattr(frontend_endpoints, "_logic_service", None)
    monkeypatch.setattr(frontend_endpoints, "_validation_service", None)
    app = FastAPI()
    app.include_router(frontend_router, prefix="/api")
    return app


def test_validate_scores_the_argument(app):
    app.dependency_overrides[get_logic_service] = _HealthyLogic

    response = TestClient(app).post("/api/validate", json=SYLLOGISM)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["premises"] == SYLLOGISM["premises"]
    result = body["result"]
    assert 0.0 < result["validity_score"] <= 1.0
    assert result["is_valid"] is (result["validity_score"] > 0.6)
    assert result["logical_structure"]["method"] == "heuristic"


def test_validate_refuses_an_argument_without_premises(app):
    app.dependency_overrides[get_logic_service] = _HealthyLogic

    response = TestClient(app).post(
        "/api/validate", json={"premises": [], "conclusion": "Donc X"}
    )

    assert response.status_code == 422


def test_belief_set_returns_what_the_service_built(app):
    service = _BeliefSets()
    app.dependency_overrides[get_logic_service] = lambda: service

    # The body LogicGraph.js sends, through api.js analyzeLogicGraph.
    response = TestClient(app).post(
        "/api/logic/belief-set",
        json={
            "text": "S'il pleut, le sol est mouillé. Il pleut.",
            "logic_type": "propositional",
            "options": {"layout": "hierarchical"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["belief_set"]["content"] == "rains => wet\nrains"
    assert [r.logic_type for r in service.requests] == ["propositional"]


def test_belief_set_refuses_a_request_without_text(app):
    app.dependency_overrides[get_logic_service] = lambda: _BeliefSets()

    response = TestClient(app).post(
        "/api/logic/belief-set", json={"logic_type": "propositional"}
    )

    assert response.status_code == 422


def test_a_failed_conversion_is_a_server_error_without_its_traceback(app):
    error = ValueError("Erreur lors de la conversion: boom\nTRACEBACK:\nsecret frame")
    app.dependency_overrides[get_logic_service] = lambda: _BeliefSets(error)

    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/logic/belief-set",
        json={"text": "Il pleut.", "logic_type": "propositional"},
    )

    assert response.status_code == 500
    assert "TRACEBACK" not in response.text
