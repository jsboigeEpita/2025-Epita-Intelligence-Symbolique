#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'integration pour l'API d'analyse argumentative via Flask TestClient.
=============================================================================

Equivalent in-process des tests Playwright API de test_argument_analyzer.py.
Ne necessite PAS de serveur backend en cours d'execution.
"""

import pytest
import json
import logging

logger = logging.getLogger(__name__)

try:
    from services.web_api_from_libs.app import create_app

    _flask_app_available = True
except Exception as e:
    _flask_app_available = False
    logger.warning(f"Flask app import failed: {e}")

pytestmark = pytest.mark.skipif(
    not _flask_app_available,
    reason="services.web_api_from_libs.app not importable",
)


@pytest.fixture(scope="module")
def flask_client():
    """Create a Flask test client for the web_api_from_libs app."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check_endpoint(flask_client):
    """
    Test de l'endpoint /api/health via Flask TestClient.
    Equivalent de test_health_check_endpoint dans test_argument_analyzer.py.
    """
    response = flask_client.get("/api/health")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    json_response = response.get_json()
    assert (
        json_response.get("status") == "ok"
    ), f"Expected 'status: ok', got: {json_response}"


def test_malformed_analyze_request_returns_400(flask_client):
    """
    Test d'envoi d'une requete malformee a /api/analyze.
    Equivalent de test_malformed_analyze_request_returns_400 dans test_argument_analyzer.py.
    """
    # Send empty JSON body (no 'text' field) — should return 400
    response = flask_client.post(
        "/api/analyze",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert (
        response.status_code == 400
    ), f"Expected 400 (Bad Request), got {response.status_code}"


def test_successful_simple_argument_analysis(flask_client):
    """
    Test d'analyse d'argument via /api/analyze.
    Equivalent de test_successful_simple_argument_analysis dans test_argument_analyzer.py.
    """
    argument_text = (
        "Tous les hommes sont mortels. Socrate est un homme. "
        "Donc Socrate est mortel."
    )
    request_payload = {
        "text": argument_text,
        "options": {"depth": "standard", "mode": "neutral"},
    }

    response = flask_client.post(
        "/api/analyze",
        data=json.dumps(request_payload),
        content_type="application/json",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    response_body = response.get_json()

    assert (
        response_body.get("success") is True
    ), f"Expected 'success' to be True, got: {response_body.get('success')}"
    assert "fallacies" in response_body, "Missing 'fallacies' key in response"
    assert (
        "argument_structure" in response_body
    ), "Missing 'argument_structure' key in response"
    assert isinstance(
        response_body.get("fallacy_count"), int
    ), f"Expected 'fallacy_count' to be int, got: {type(response_body.get('fallacy_count'))}"
